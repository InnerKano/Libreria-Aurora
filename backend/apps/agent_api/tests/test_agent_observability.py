from __future__ import annotations

from rest_framework.test import APIRequestFactory

from apps.agent_api.views import AgentChatView, AgentSearchView


def test_agent_chat_sets_request_id_header(monkeypatch):
    def fake_handle_agent_message(message, **kwargs):
        class Resp:
            error = None

            def to_dict(self):
                return {
                    "message": "ok",
                    "results": [],
                    "actions": [],
                }

        return Resp()

    monkeypatch.setattr("apps.agent_api.views.handle_agent_message", fake_handle_agent_message)

    factory = APIRequestFactory()
    request = factory.post("/api/agent/", {"message": "hola"}, format="json")
    response = AgentChatView.as_view()(request)

    assert response.status_code == 200
    assert response["X-Request-Id"]


def test_agent_search_sets_request_id_header(monkeypatch):
    class FakeResult:
        query = "harry"
        k = 5
        source = "orm"
        degraded = True
        results = []
        warnings = []

    def fake_search_catalog(q, *, k=5, prefer_vector=True):
        return FakeResult()

    monkeypatch.setattr("apps.agent_api.views.search_catalog", fake_search_catalog)

    factory = APIRequestFactory()
    request = factory.get("/api/agent/search/?q=harry")
    response = AgentSearchView.as_view()(request)

    assert response.status_code == 200
    assert response["X-Request-Id"]


def test_agent_chat_injects_trace_request_id_when_sampled(monkeypatch):
    def fake_handle_agent_message(message, **kwargs):
        class Resp:
            error = None

            def to_dict(self):
                return {
                    "message": "ok",
                    "results": [],
                    "actions": [],
                }

        return Resp()

    monkeypatch.setattr("apps.agent_api.views.handle_agent_message", fake_handle_agent_message)
    monkeypatch.setattr("apps.agent_api.views.should_sample_trace", lambda *a, **k: True)

    factory = APIRequestFactory()
    request = factory.post("/api/agent/", {"message": "hola", "trace": True}, format="json")
    response = AgentChatView.as_view()(request)

    assert response.status_code == 200
    assert "trace" in response.data
    assert response.data["trace"]["request_id"]
