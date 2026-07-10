import logging

from app.rag.embeddings import EmbeddingProvider
from app.rag.vector_store import SearchResult, VectorStore

logger = logging.getLogger(__name__)


class Retriever:
    def __init__(
        self,
        vector_store: VectorStore,
        embedding_provider: EmbeddingProvider,
        top_k: int = 5,
        score_threshold: float = 0.3,
    ):
        self.vector_store = vector_store
        self.embedding_provider = embedding_provider
        self.top_k = top_k
        self.score_threshold = score_threshold

    def retrieve(self, query: str, top_k: int | None = None) -> list[SearchResult]:
        k = top_k or self.top_k

        query_embedding = self.embedding_provider.embed(query)
        if not query_embedding:
            logger.warning("Failed to generate query embedding")
            return []

        results = self.vector_store.search(query_embedding, top_k=k)
        filtered = [r for r in results if r.score >= self.score_threshold]

        logger.info("Retrieved %d documents for query (filtered from %d)", len(filtered), len(results))
        return filtered

    def retrieve_context(self, query: str, top_k: int | None = None) -> str:
        results = self.retrieve(query, top_k)
        if not results:
            return ""

        context_parts = []
        for i, result in enumerate(results, 1):
            context_parts.append(
                f"[{i}] (score: {result.score:.2f}) {result.document.content}"
            )
        return "\n\n".join(context_parts)

    def retrieve_for_recommendation(
        self,
        crop: str,
        disease: str,
        severity: str,
        top_k: int = 3,
    ) -> str:
        query = f"{crop} {disease} {severity} treatment recommendation"
        return self.retrieve_context(query, top_k)
