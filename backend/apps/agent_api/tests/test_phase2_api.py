from rest_framework.test import APIRequestFactory

from agent.retrieval import RetrievalResult


def test_phase2_agent_search_endpoint_contract(monkeypatch):
    # Patch the view to avoid DB/Chroma dependencies in this unit test.
    from apps.agent_api import views

    def fake_search_catalog(q, *, k=5, prefer_vector=True, **kwargs):
        return RetrievalResult(
            query=q,
            k=int(k),
            source="orm",
            degraded=True,
            results=[{"libro_id": 1, "titulo": "Test"}],
            warnings=["vector unavailable"],
        )

    monkeypatch.setattr(views, "search_catalog", fake_search_catalog)

    factory = APIRequestFactory()
    request = factory.get("/api/agent/search/", {"q": "harry", "k": 3})
    response = views.AgentSearchView.as_view()(request)
    response.render()

    assert response.status_code == 200
    data = response.data

    assert data["query"] == "harry"
    assert data["k"] == 3
    assert "source" in data
    assert "degraded" in data
    assert isinstance(data["warnings"], list)
    assert isinstance(data["results"], list)
