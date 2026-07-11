import logging
from dataclasses import dataclass

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models import Conversation

logger = logging.getLogger(__name__)

MAX_RECENT_MESSAGES = 30
COMPACT_THRESHOLD = 20


@dataclass
class ChatContext:
    messages: list[dict]
    context_summary: str | None
    disease_history: list[dict]
    metadata: dict


class ChatContextManager:
    def __init__(self, db: Session):
        self.db = db

    def build(
        self,
        user_id: int,
        system_prompt: str,
        current_message: str,
        context: dict,
        llm_provider=None,
    ) -> ChatContext:
        conversations = self._fetch_recent(user_id)

        crop_data = (
            context.get("crop") if isinstance(context, dict) else getattr(context, "crop", None)
        )
        if hasattr(crop_data, "get"):
            crop_name = crop_data.get("crop_type", "unknown")
        elif crop_data and hasattr(crop_data, "crop_type"):
            crop_name = crop_data.crop_type
        else:
            crop_name = "unknown"

        location = (
            context.get("location")
            if isinstance(context, dict)
            else getattr(context, "location", "unknown")
        )
        weather = (
            context.get("weather") if isinstance(context, dict) else getattr(context, "weather", {})
        )
        disease_history = (
            context.get("history") if isinstance(context, dict) else getattr(context, "history", [])
        )

        context_summary = None
        recent = conversations

        if len(conversations) > COMPACT_THRESHOLD:
            older = conversations[: len(conversations) - MAX_RECENT_MESSAGES]
            recent = conversations[len(conversations) - MAX_RECENT_MESSAGES :]
            context_summary = self._compact(older, llm_provider)

        messages = [{"role": "system", "content": system_prompt}]

        if context_summary:
            messages.append(
                {"role": "system", "content": f"Conversation summary so far:\n{context_summary}"}
            )

        metadata_parts = []
        if crop_name != "unknown":
            metadata_parts.append(f"Crop: {crop_name}")
        if location and location != "unknown":
            metadata_parts.append(f"Location: {location}")
        if isinstance(weather, dict) and weather.get("status") != "unavailable":
            temp = weather.get("temperature_c", "N/A")
            cond = weather.get("condition", "N/A")
            humidity = weather.get("humidity_percent", "N/A")
            metadata_parts.append(f"Weather: {cond}, {temp}C, {humidity}% humidity")
        if disease_history:
            recent_dx = disease_history[:3]
            dx_str = "; ".join(
                f"{h.get('crop', '')}: {h.get('disease', '')} ({h.get('severity', '')})"
                for h in recent_dx
            )
            metadata_parts.append(f"Recent diagnoses: {dx_str}")

        if metadata_parts:
            messages.append({"role": "system", "content": "Context:\n" + "\n".join(metadata_parts)})

        for conv in recent:
            messages.append({"role": "user", "content": conv.question})
            messages.append({"role": "assistant", "content": conv.response})

        messages.append({"role": "user", "content": current_message})

        return ChatContext(
            messages=messages,
            context_summary=context_summary,
            disease_history=disease_history if isinstance(disease_history, list) else [],
            metadata={
                "crop": crop_name,
                "location": location,
                "conversation_count": len(conversations),
                "compacted": context_summary is not None,
            },
        )

    def _fetch_recent(self, user_id: int, limit: int = 50) -> list[Conversation]:
        stmt = (
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(desc(Conversation.created_at))
            .limit(limit)
        )
        rows = list(self.db.scalars(stmt).all())
        rows.reverse()
        return rows

    def _compact(self, conversations: list[Conversation], llm_provider=None) -> str | None:
        if not conversations:
            return None

        turns = []
        for conv in conversations:
            q = (conv.question or "")[:200]
            a = (conv.response or "")[:200]
            turns.append(f"User: {q}\nAgriAI: {a}")

        raw = "\n".join(turns)

        if llm_provider and hasattr(llm_provider, "complete") and llm_provider.is_available:
            try:
                summary = llm_provider.complete(
                    system_prompt=(
                        "Summarize this agricultural chat conversation in 3-5 concise bullet points. "
                        "Focus on: what crops/diseases were discussed, what advice was given, "
                        "what actions the farmer said they would take. Be factual and brief."
                    ),
                    user_prompt=raw,
                    temperature=0.3,
                    max_tokens=300,
                )
                if summary and len(summary.strip()) > 20:
                    return summary.strip()
            except Exception:
                logger.warning("LLM compaction failed, using extractive fallback", exc_info=True)

        lines = []
        for conv in conversations:
            q = (conv.question or "")[:100]
            if q:
                lines.append(f"- {q}")
        return "\n".join(lines[:10]) if lines else None
