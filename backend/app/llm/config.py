from dataclasses import dataclass


@dataclass
class LLMConfig:
    provider: str = "none"
    model: str = ""
    temperature: float = 0.7
    max_tokens: int = 1024
    timeout_seconds: int = 30

    @classmethod
    def for_disease_advisory(cls) -> "LLMConfig":
        return cls(
            temperature=0.3,
            max_tokens=512,
        )

    @classmethod
    def for_chat(cls) -> "LLMConfig":
        return cls(
            temperature=0.7,
            max_tokens=1024,
        )

    @classmethod
    def for_structured_output(cls) -> "LLMConfig":
        return cls(
            temperature=0.2,
            max_tokens=1024,
        )
