import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class Document:
    id: str
    content: str
    metadata: dict = field(default_factory=dict)
    embedding: list[float] = field(default_factory=list)


@dataclass
class SearchResult:
    document: Document
    score: float


class VectorStore(ABC):
    @abstractmethod
    def add(self, documents: list[Document]) -> None:
        raise NotImplementedError

    @abstractmethod
    def search(self, query_embedding: list[float], top_k: int = 5) -> list[SearchResult]:
        raise NotImplementedError

    @abstractmethod
    def delete(self, ids: list[str]) -> None:
        raise NotImplementedError

    @abstractmethod
    def count(self) -> int:
        raise NotImplementedError


class InMemoryVectorStore(VectorStore):
    def __init__(self):
        self._documents: dict[str, Document] = {}

    def add(self, documents: list[Document]) -> None:
        for doc in documents:
            self._documents[doc.id] = doc

    def search(self, query_embedding: list[float], top_k: int = 5) -> list[SearchResult]:
        if not self._documents or not query_embedding:
            return []

        query_vec = np.array(query_embedding, dtype=np.float32)
        query_norm = np.linalg.norm(query_vec)
        if query_norm > 0:
            query_vec = query_vec / query_norm

        results: list[SearchResult] = []
        for doc in self._documents.values():
            if not doc.embedding:
                continue
            doc_vec = np.array(doc.embedding, dtype=np.float32)
            doc_norm = np.linalg.norm(doc_vec)
            if doc_norm > 0:
                doc_vec = doc_vec / doc_norm
            score = float(np.dot(query_vec, doc_vec))
            results.append(SearchResult(document=doc, score=score))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    def delete(self, ids: list[str]) -> None:
        for doc_id in ids:
            self._documents.pop(doc_id, None)

    def count(self) -> int:
        return len(self._documents)

    def get_all(self) -> list[Document]:
        return list(self._documents.values())
