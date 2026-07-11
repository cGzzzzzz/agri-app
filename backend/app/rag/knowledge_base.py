import json
import logging
import uuid
from pathlib import Path

from app.rag.embeddings import EmbeddingProvider
from app.rag.vector_store import Document, VectorStore

logger = logging.getLogger(__name__)


class KnowledgeBase:
    def __init__(
        self,
        vector_store: VectorStore,
        embedding_provider: EmbeddingProvider,
        documents_dir: Path | str | None = None,
    ):
        self.vector_store = vector_store
        self.embedding_provider = embedding_provider
        self.documents_dir = (
            Path(documents_dir) if documents_dir else Path(__file__).parent / "documents"
        )

    def ingest_file(self, file_path: Path, metadata: dict | None = None) -> int:
        if not file_path.exists():
            logger.warning("Document file not found: %s", file_path)
            return 0

        try:
            content = file_path.read_text(encoding="utf-8")
            data = json.loads(content)
        except json.JSONDecodeError:
            content = file_path.read_text(encoding="utf-8")
            data = [{"content": content, "metadata": {}}]

        if isinstance(data, dict):
            data = [data]

        documents: list[Document] = []
        for item in data:
            text = item.get("content", item.get("text", ""))
            if not text:
                continue

            doc_metadata = {
                "source": file_path.name,
                "crop": item.get("crop", ""),
                "disease": item.get("disease", ""),
                "type": item.get("type", "knowledge"),
            }
            if metadata:
                doc_metadata.update(metadata)

            doc_id = str(uuid.uuid4())
            documents.append(
                Document(
                    id=doc_id,
                    content=text,
                    metadata=doc_metadata,
                )
            )

        if not documents:
            return 0

        embeddings = self.embedding_provider.embed_batch([d.content for d in documents])
        for doc, embedding in zip(documents, embeddings, strict=False):
            doc.embedding = embedding

        self.vector_store.add(documents)
        logger.info("Ingested %d documents from %s", len(documents), file_path.name)
        return len(documents)

    def ingest_directory(self, metadata: dict | None = None) -> int:
        if not self.documents_dir.exists():
            logger.warning("Documents directory not found: %s", self.documents_dir)
            return 0

        total = 0
        for json_file in self.documents_dir.glob("*.json"):
            count = self.ingest_file(json_file, metadata)
            total += count
        return total

    def ingest_crop_disease(
        self,
        crop: str,
        disease: str,
        symptoms: list[str],
        treatments: list[str],
        prevention: list[str],
        severity_info: str = "",
    ) -> int:
        documents: list[Document] = []

        symptoms_text = f"Symptoms of {disease} in {crop}: " + "; ".join(symptoms)
        documents.append(
            Document(
                id=str(uuid.uuid4()),
                content=symptoms_text,
                metadata={"crop": crop, "disease": disease, "type": "symptoms"},
            )
        )

        treatments_text = f"Treatment for {disease} in {crop}: " + "; ".join(treatments)
        documents.append(
            Document(
                id=str(uuid.uuid4()),
                content=treatments_text,
                metadata={"crop": crop, "disease": disease, "type": "treatment"},
            )
        )

        prevention_text = f"Prevention of {disease} in {crop}: " + "; ".join(prevention)
        documents.append(
            Document(
                id=str(uuid.uuid4()),
                content=prevention_text,
                metadata={"crop": crop, "disease": disease, "type": "prevention"},
            )
        )

        if severity_info:
            documents.append(
                Document(
                    id=str(uuid.uuid4()),
                    content=f"Severity information for {disease} in {crop}: {severity_info}",
                    metadata={"crop": crop, "disease": disease, "type": "severity"},
                )
            )

        embeddings = self.embedding_provider.embed_batch([d.content for d in documents])
        for doc, embedding in zip(documents, embeddings, strict=False):
            doc.embedding = embedding

        self.vector_store.add(documents)
        return len(documents)

    def count(self) -> int:
        return self.vector_store.count()
