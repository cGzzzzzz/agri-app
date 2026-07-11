from app.rag.vector_store import Document, InMemoryVectorStore


class TestInMemoryVectorStore:
    def test_add_and_count(self):
        store = InMemoryVectorStore()
        docs = [
            Document(id="1", content="hello", embedding=[1.0, 0.0, 0.0]),
            Document(id="2", content="world", embedding=[0.0, 1.0, 0.0]),
        ]
        store.add(docs)
        assert store.count() == 2

    def test_search_returns_similar(self):
        store = InMemoryVectorStore()
        store.add(
            [
                Document(id="a", content="disease", embedding=[1.0, 0.0, 0.0]),
                Document(id="b", content="healthy", embedding=[0.0, 1.0, 0.0]),
            ]
        )
        results = store.search([1.0, 0.0, 0.0], top_k=2)
        assert len(results) == 2
        assert results[0].document.id == "a"
        assert results[0].score > results[1].score

    def test_search_empty_store(self):
        store = InMemoryVectorStore()
        results = store.search([1.0, 0.0])
        assert results == []

    def test_search_empty_query(self):
        store = InMemoryVectorStore()
        store.add([Document(id="1", content="x", embedding=[1.0])])
        results = store.search([], top_k=1)
        assert results == []

    def test_delete(self):
        store = InMemoryVectorStore()
        store.add(
            [
                Document(id="1", content="a", embedding=[1.0]),
                Document(id="2", content="b", embedding=[0.5]),
            ]
        )
        store.delete(["1"])
        assert store.count() == 1

    def test_top_k_limits_results(self):
        store = InMemoryVectorStore()
        docs = [
            Document(id=str(i), content=f"doc{i}", embedding=[float(i), 0.0]) for i in range(10)
        ]
        store.add(docs)
        results = store.search([1.0, 0.0], top_k=3)
        assert len(results) == 3

    def test_get_all(self):
        store = InMemoryVectorStore()
        store.add([Document(id="1", content="a"), Document(id="2", content="b")])
        all_docs = store.get_all()
        assert len(all_docs) == 2


class TestDocument:
    def test_document_defaults(self):
        doc = Document(id="1", content="hello")
        assert doc.metadata == {}
        assert doc.embedding == []

    def test_document_with_metadata(self):
        doc = Document(id="1", content="hello", metadata={"crop": "rice"})
        assert doc.metadata["crop"] == "rice"
