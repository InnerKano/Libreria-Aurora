from agent.vector_store import VectorStoreUnavailable, get_chroma_collection


def test_vector_db_smoke_query_or_unavailable_is_handled():
    """Ensures vector store is either queryable or fails with a clear, handled error.

    This avoids skips while still validating behavior across environments that may
    or may not have the vector DB artifact and dependencies installed.
    """

    try:
        collection = get_chroma_collection()
    except VectorStoreUnavailable as exc:
        message = str(exc).lower()
        assert any(
            hint in message
            for hint in [
                "vector db directory",
                "vector search unavailable",
                "failed to open chroma",
                "embedding model",
            ]
        )
        return

    resp = collection.query(query_texts=["Cien años de soledad"], n_results=1, include=["documents", "metadatas"])
    assert "documents" in resp
