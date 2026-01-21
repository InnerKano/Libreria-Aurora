from __future__ import annotations

from rest_framework.test import APIRequestFactory

from apps.agent_api.views import AgentChatView


def test_agent_chat_endpoint_returns_stable_contract(monkeypatch):
    def fake_handle_agent_message(message, **kwargs):
        class Resp:
            error = None

            def to_dict(self):
                return {
                    "message": "ok",
                    "results": [{"libro_id": 1, "titulo": "A"}],
                    "actions": [{"type": "view_book", "libro_id": 1}],
                }

        return Resp()

    monkeypatch.setattr("apps.agent_api.views.handle_agent_message", fake_handle_agent_message)

    factory = APIRequestFactory()
    request = factory.post("/api/agent/", {"message": "hola"}, format="json")
    response = AgentChatView.as_view()(request)

    assert response.status_code == 200
    assert set(response.data.keys()) >= {"message", "results", "actions"}


def test_agent_chat_endpoint_returns_400_on_invalid_request(monkeypatch):
    def fake_handle_agent_message(message, **kwargs):
        class Resp:
            error = "invalid_request"

            def to_dict(self):
                return {
                    "error": "invalid_request",
                    "message": "Mensaje vacío",
                    "results": [],
                    "actions": [],
                }

        return Resp()

    monkeypatch.setattr("apps.agent_api.views.handle_agent_message", fake_handle_agent_message)

    factory = APIRequestFactory()
    request = factory.post("/api/agent/", {"message": "   "}, format="json")
    response = AgentChatView.as_view()(request)

    assert response.status_code == 400
    assert response.data["error"] == "invalid_request"
    assert response.data["results"] == []
    assert response.data["actions"] == []
