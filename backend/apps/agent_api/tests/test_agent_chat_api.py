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


def test_agent_chat_trace_flag_parsing(monkeypatch):
    captured: dict = {}

    def fake_handle_agent_message(message, **kwargs):
        captured["include_trace"] = kwargs.get("include_trace")

        class Resp:
            error = None

            def to_dict(self):
                return {
                    "message": "ok",
                    "results": [],
                    "actions": [],
                    "trace": {"ok": True},
                }

        return Resp()

    monkeypatch.setattr("apps.agent_api.views.handle_agent_message", fake_handle_agent_message)

    factory = APIRequestFactory()
    request = factory.post("/api/agent/", {"message": "hola", "trace": "true"}, format="json")
    response = AgentChatView.as_view()(request)

    assert response.status_code == 200
    assert captured["include_trace"] is True


def test_agent_chat_byo_key_forwarding(monkeypatch):
    captured: dict = {}

    def fake_handle_agent_message(message, **kwargs):
        captured["byo_api_key"] = kwargs.get("byo_api_key")

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
    request = factory.post(
        "/api/agent/",
        {"message": "hola"},
        format="json",
        HTTP_X_LLM_API_KEY="test-key",
    )
    response = AgentChatView.as_view()(request)

    assert response.status_code == 200
    assert captured["byo_api_key"] == "test-key"


def test_agent_chat_rejects_non_string_message(monkeypatch):
    captured: dict = {}

    def fake_handle_agent_message(message, **kwargs):
        captured["message"] = message

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
    request = factory.post("/api/agent/", {"message": {"bad": "payload"}}, format="json")
    response = AgentChatView.as_view()(request)

    assert response.status_code == 400
    assert captured["message"] is None


def test_agent_chat_k_is_clamped_to_max(monkeypatch):
    captured: dict = {}

    def fake_handle_agent_message(message, **kwargs):
        captured["k"] = kwargs.get("k")

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
    request = factory.post("/api/agent/", {"message": "hola", "k": 999}, format="json")
    response = AgentChatView.as_view()(request)

    assert response.status_code == 200
    assert captured["k"] == 50


def test_agent_chat_parses_prefer_vector_boolish(monkeypatch):
    captured: dict = {}

    def fake_handle_agent_message(message, **kwargs):
        captured["prefer_vector"] = kwargs.get("prefer_vector")

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
    request = factory.post("/api/agent/", {"message": "hola", "prefer_vector": "false"}, format="json")
    response = AgentChatView.as_view()(request)

    assert response.status_code == 200
    assert captured["prefer_vector"] is False
