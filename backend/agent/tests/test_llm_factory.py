"""Tests for agent.llm_factory."""
from types import SimpleNamespace
from typing import Any

import pytest
from django.core.exceptions import ImproperlyConfigured

from agent.llm_factory import (
    OpenAICompatibleLLM,
    StubLLM,
    build_llm_runnable,
)


class _FakeChatResponse:
    def __init__(self, content: str) -> None:
        self.choices = [SimpleNamespace(message=SimpleNamespace(content=content))]
        self.usage = SimpleNamespace(prompt_tokens=1, completion_tokens=1)


class _FakeChatCompletions:
    def __init__(self, content: str) -> None:
        self._content = content

    def create(self, *args: Any, **kwargs: Any) -> _FakeChatResponse:  # noqa: ANN401
        return _FakeChatResponse(self._content)


class _FakeChat:
    def __init__(self, content: str) -> None:
        self.completions = _FakeChatCompletions(content)


class _FakeOpenAIClient:
    def __init__(self, content: str = "ok") -> None:
        self.chat = _FakeChat(content)


class _FakeOpenAI:
    def __init__(self, content: str = "ok") -> None:
        self._content = content

    def OpenAI(self, *args: Any, **kwargs: Any) -> _FakeOpenAIClient:  # noqa: N802, ANN401
        return _FakeOpenAIClient(self._content)


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    keys = [
        "LLM_PROVIDER",
        "LLM_MODEL",
        "LLM_BASE_URL",
        "LLM_API_KEY",
        "LLM_TIMEOUT_SEC",
        "LLM_MAX_TOKENS",
        "LLM_COST_MODE",
        "LLM_ALLOW_BYO_KEY",
    ]
    for key in keys:
        monkeypatch.delenv(key, raising=False)


def test_stub_provider_returns_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "stub")
    llm = build_llm_runnable()
    assert isinstance(llm, StubLLM)
    out = llm.invoke("hola")
    assert out["provider"] == "stub"
    assert out["content"]


def test_missing_key_in_paid_mode_falls_back_to_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("LLM_COST_MODE", "paid")
    monkeypatch.setenv("LLM_API_KEY", "")  # sin key
    llm = build_llm_runnable()
    assert isinstance(llm, StubLLM)
    out = llm.invoke("hola")
    assert "modo stub" in out["content"]


def test_byo_key_mode_without_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("LLM_COST_MODE", "byo_key")
    monkeypatch.setenv("LLM_ALLOW_BYO_KEY", "true")
    with pytest.raises(ImproperlyConfigured):
        build_llm_runnable()


def test_openai_compatible_uses_fake_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("LLM_COST_MODE", "hybrid")
    monkeypatch.setenv("LLM_ALLOW_BYO_KEY", "true")

    fake_openai = _FakeOpenAI(content="respuesta")
    monkeypatch.setenv("LLM_API_KEY", "server-key")
    monkeypatch.setattr("agent.llm_factory.openai", fake_openai)

    llm = build_llm_runnable()
    assert isinstance(llm, OpenAICompatibleLLM)
    out = llm.invoke("hola")
    assert out["content"] == "respuesta"
    assert out["provider"] == "openai_compatible"
    assert out["model"]


__all__ = ["test_stub_provider_returns_stub", "test_missing_key_in_paid_mode_falls_back_to_stub", "test_byo_key_mode_without_key_raises", "test_openai_compatible_uses_fake_client"]
