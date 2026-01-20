import pytest

from agent.retrieval import search_catalog
from agent.vector_store import VectorStoreUnavailable


def test_search_catalog_empty_query_returns_empty():
    res = search_catalog("   ")
    assert res.results == []
    assert res.degraded is True
    assert "Empty query" in res.warnings[0]


def test_search_catalog_prefers_vector_when_available(monkeypatch):
    called = {"vector": 0, "orm": 0}

    def fake_vector(q: str, k: int):
        called["vector"] += 1
        return [{"id": "x", "distance": 0.1, "metadata": {"libro_id": 1}, "document": "doc"}]

    def fake_orm(q: str, k: int):
        called["orm"] += 1
        return [{"libro_id": 1, "titulo": "T"}]

    res = search_catalog("harry", k=3, prefer_vector=True, vector_search_fn=fake_vector, orm_search_fn=fake_orm)
    assert res.source == "vector"
    assert res.degraded is False
    assert len(res.results) == 1
    assert called["vector"] == 1
    assert called["orm"] == 0


def test_search_catalog_falls_back_to_orm_when_vector_unavailable():
    def fake_vector(q: str, k: int):
        raise VectorStoreUnavailable("no chroma")

    def fake_orm(q: str, k: int):
        return [{"libro_id": 99, "titulo": "fallback"}]

    res = search_catalog("something", k=2, prefer_vector=True, vector_search_fn=fake_vector, orm_search_fn=fake_orm)
    assert res.source == "orm"
    assert res.degraded is True
    assert res.results[0]["libro_id"] == 99
    assert any("no chroma" in w for w in res.warnings)


def test_search_catalog_can_skip_vector():
    def fake_vector(q: str, k: int):
        raise AssertionError("vector should not be called")

    def fake_orm(q: str, k: int):
        return [{"libro_id": 1}]

    res = search_catalog("abc", prefer_vector=False, vector_search_fn=fake_vector, orm_search_fn=fake_orm)
    assert res.source == "orm"
    assert res.degraded is True
    assert res.results == [{"libro_id": 1}]


@pytest.mark.parametrize("k", ["bad", 0, -5])
def test_search_catalog_invalid_k_is_handled(k):
    def fake_orm(q: str, k: int):
        assert k == 5
        return []

    res = search_catalog("abc", k=k, prefer_vector=False, orm_search_fn=fake_orm)
    assert res.k == 5
