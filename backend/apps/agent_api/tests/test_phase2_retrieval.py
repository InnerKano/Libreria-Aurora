import pytest

from agent.retrieval import search_catalog
from agent.vector_store import VectorStoreUnavailable


def test_phase2_search_catalog_falls_back_to_orm_when_vector_unavailable():
    def fake_vector(q: str, k: int):
        raise VectorStoreUnavailable("no chroma")

    def fake_orm(q: str, k: int):
        return [{"libro_id": 99, "titulo": "fallback"}]

    res = search_catalog("something", k=2, prefer_vector=True, vector_search_fn=fake_vector, orm_search_fn=fake_orm)
    assert res.source == "orm"
    assert res.degraded is True
    assert res.results[0]["libro_id"] == 99
    assert any("no chroma" in w for w in res.warnings)


@pytest.mark.parametrize("k", ["bad", 0, -5])
def test_phase2_search_catalog_invalid_k_is_handled(k):
    def fake_orm(q: str, k: int):
        assert k == 5
        return []

    res = search_catalog("abc", k=k, prefer_vector=False, orm_search_fn=fake_orm)
    assert res.k == 5
