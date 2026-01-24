from __future__ import annotations

from types import SimpleNamespace

from rest_framework.test import APIRequestFactory, force_authenticate

from apps.agent_api.views import AgentStatusView


def test_agent_status_requires_auth():
    factory = APIRequestFactory()
    request = factory.get("/api/agent/status/")
    response = AgentStatusView.as_view()(request)

    assert response.status_code == 401


def test_agent_status_returns_contract():
    factory = APIRequestFactory()
    request = factory.get("/api/agent/status/")
    user = SimpleNamespace(is_authenticated=True, id=1, pk=1)
    force_authenticate(request, user=user)

    response = AgentStatusView.as_view()(request)

    assert response.status_code == 200
    assert "llm" in response.data
    assert "retrieval" in response.data
    assert "tools" in response.data
    assert "limits" in response.data
