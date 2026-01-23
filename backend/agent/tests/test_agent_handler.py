from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import pytest

from agent.agent_handler import handle_agent_message


@dataclass(frozen=True)
class FakeRetrievalResult:
    query: str
    k: int
    source: str
    degraded: bool
    results: list[dict[str, Any]]
    warnings: list[str]


class FakeLLM:
    def __init__(self, content: str):
        self._content = content

    def invoke(self, prompt: str, *, metadata: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        return {
            "content": self._content,
            "provider": "fake",
            "model": "fake",
            "latency_ms": 1,
            "prompt_tokens": None,
            "completion_tokens": None,
            "error": None,
        }


def test_handle_agent_message_empty_returns_structured_error():
    resp = handle_agent_message("   ", include_trace=True, retrieval_fn=lambda *a, **k: None)  # type: ignore[arg-type]
    payload = resp.to_dict()

    assert payload["error"] == "invalid_request"
    assert payload["results"] == []
    assert payload["actions"] == []
    assert "trace" in payload


def test_handle_agent_message_uses_llm_for_message_but_keeps_results_from_retrieval():
    def fake_retrieval(query: str, *, k: int = 5, prefer_vector: bool = True):
        return FakeRetrievalResult(
            query=query,
            k=k,
            source="orm",
            degraded=True,
            results=[{"libro_id": 123, "titulo": "X", "precio": "9.99"}],
            warnings=["Vector store unavailable"],
        )

    resp = handle_agent_message(
        "busco algo",
        k=3,
        prefer_vector=True,
        include_trace=True,
        retrieval_fn=fake_retrieval,  # type: ignore[arg-type]
        llm=FakeLLM("- Hola, aquí tienes resultados\n- ¿Quieres ver detalles?"),
    )

    payload = resp.to_dict()
    assert payload["error"] is None if "error" in payload else True
    assert payload["message"] == "- Hola, aquí tienes resultados\n- ¿Quieres ver detalles?"
    assert payload["results"][0]["libro_id"] == 123
    assert payload["actions"][0]["type"] == "view_book"
    assert payload["trace"]["degraded"] is True


def test_handle_agent_message_llm_failure_falls_back_to_template():
    class ExplodingLLM:
        def invoke(self, prompt: str, *, metadata=None):
            raise RuntimeError("boom")

    def fake_retrieval(query: str, *, k: int = 5, prefer_vector: bool = True):
        return FakeRetrievalResult(
            query=query,
            k=k,
            source="orm",
            degraded=True,
            results=[{"libro_id": 1, "titulo": "A"}],
            warnings=[],
        )

    resp = handle_agent_message(
        "algo",
        include_trace=False,
        retrieval_fn=fake_retrieval,  # type: ignore[arg-type]
        llm=ExplodingLLM(),
    )

    payload = resp.to_dict()
    assert "Encontré" in payload["message"] or "Encontre" in payload["message"]
    assert payload["results"]


def test_handle_agent_message_guardrails_rejects_invalid_llm_message():
    def fake_retrieval(query: str, *, k: int = 5, prefer_vector: bool = True):
        return FakeRetrievalResult(
            query=query,
            k=k,
            source="orm",
            degraded=True,
            results=[{"libro_id": 1, "titulo": "A"}],
            warnings=[],
        )

    resp = handle_agent_message(
        "algo",
        include_trace=False,
        retrieval_fn=fake_retrieval,  # type: ignore[arg-type]
        llm=FakeLLM("Respuesta sin bullets"),
    )

    payload = resp.to_dict()
    assert "Encontré" in payload["message"] or "Encontre" in payload["message"]
    assert payload["results"]


@pytest.mark.parametrize(
    "results", [[], [{"libro_id": 10, "titulo": "A"}], [{"id": "x"}]],
)
def test_actions_are_safe_and_optional(results):
    def fake_retrieval(query: str, *, k: int = 5, prefer_vector: bool = True):
        return FakeRetrievalResult(
            query=query,
            k=k,
            source="orm",
            degraded=True,
            results=results,
            warnings=[],
        )

    resp = handle_agent_message(
        "algo",
        include_trace=False,
        retrieval_fn=fake_retrieval,  # type: ignore[arg-type]
        llm=FakeLLM("- ok\n- ok"),
    )

    payload = resp.to_dict()
    assert isinstance(payload["actions"], list)


def test_handle_agent_message_uses_lookup_tool_when_id_present(monkeypatch):
    called = {"lookup": 0, "retrieval": 0}

    def fake_lookup_book(*, book_id=None, isbn=None):
        called["lookup"] += 1

        class Resp:
            ok = True
            error = None
            warnings = []
            data = {"results": [{"libro_id": 123, "titulo": "A"}]}

        return Resp()

    def fake_retrieval(query: str, *, k: int = 5, prefer_vector: bool = True):
        called["retrieval"] += 1
        return FakeRetrievalResult(
            query=query,
            k=k,
            source="orm",
            degraded=True,
            results=[],
            warnings=[],
        )

    monkeypatch.setattr("agent.agent_handler.tool_lookup_book", fake_lookup_book)

    resp = handle_agent_message(
        "ver libro 123",
        include_trace=True,
        retrieval_fn=fake_retrieval,  # type: ignore[arg-type]
        llm=FakeLLM("- ok\n- ok"),
    )

    payload = resp.to_dict()
    assert called["lookup"] == 1
    assert called["retrieval"] == 0
    assert payload["results"][0]["libro_id"] == 123


def test_handle_agent_message_includes_request_id_and_timings_in_trace():
    def fake_retrieval(query: str, *, k: int = 5, prefer_vector: bool = True):
        return FakeRetrievalResult(
            query=query,
            k=k,
            source="orm",
            degraded=True,
            results=[{"libro_id": 1, "titulo": "A"}],
            warnings=[],
        )

    resp = handle_agent_message(
        "algo",
        include_trace=True,
        retrieval_fn=fake_retrieval,  # type: ignore[arg-type]
        llm=FakeLLM("- ok\n- ok"),
        request_id="req-123",
    )

    payload = resp.to_dict()
    assert payload["trace"]["request_id"] == "req-123"
    assert isinstance(payload["trace"]["timings_ms"]["retrieval"], int)
    assert isinstance(payload["trace"]["timings_ms"]["llm"], int)


def test_handle_agent_message_records_metrics(monkeypatch):
    counters: list[tuple[str, int]] = []
    timings: list[tuple[str, int]] = []

    def fake_counter(name: str, value: int = 1):
        counters.append((name, value))

    def fake_timing(name: str, duration_ms: int):
        timings.append((name, duration_ms))

    monkeypatch.setattr("agent.agent_handler.record_counter", fake_counter)
    monkeypatch.setattr("agent.agent_handler.record_timing", fake_timing)

    def fake_retrieval(query: str, *, k: int = 5, prefer_vector: bool = True):
        return FakeRetrievalResult(
            query=query,
            k=k,
            source="orm",
            degraded=True,
            results=[{"libro_id": 1, "titulo": "A"}],
            warnings=[],
        )

    handle_agent_message(
        "algo",
        include_trace=False,
        retrieval_fn=fake_retrieval,  # type: ignore[arg-type]
        llm=FakeLLM("- ok\n- ok"),
    )

    counter_names = {name for name, _ in counters}
    timing_names = {name for name, _ in timings}

    assert "agent.llm_success" in counter_names
    assert "agent.retrieval_orm" in counter_names
    assert "agent.retrieval_ms" in timing_names
    assert "agent.llm_total_ms" in timing_names
