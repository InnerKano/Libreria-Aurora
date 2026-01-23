from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
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
    def __init__(self, content: str = "- Encontré resultados.\n- ¿Quieres ver detalles?"):
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


@pytest.fixture()
def golden_set() -> list[dict[str, Any]]:
    fixture_path = Path(__file__).parent / "fixtures" / "agent_golden_set.json"
    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    return data["cases"]


@pytest.fixture(autouse=True)
def _patch_tools(monkeypatch):
    def fake_lookup_book(*, book_id=None, isbn=None):
        if book_id:
            results = [{"libro_id": book_id, "titulo": "Libro ID"}]
        elif isbn:
            results = [{"libro_id": 321, "isbn": isbn, "titulo": "Libro ISBN"}]
        else:
            results = []

        class Resp:
            ok = bool(results)
            error = None if results else "not_found"
            warnings = []
            data = {"results": results}

        return Resp()

    def fake_filter_catalog(filters: dict[str, Any], k: int = 5):
        results = [{"libro_id": 555, "titulo": "Libro Filtrado", "categoria": filters.get("categoria")}]

        class Resp:
            ok = True
            error = None
            warnings = []
            data = {"results": results[:k]}

        return Resp()

    monkeypatch.setattr("agent.agent_handler.tool_lookup_book", fake_lookup_book)
    monkeypatch.setattr("agent.agent_handler.tool_filter_catalog", fake_filter_catalog)


def test_golden_set_contract(golden_set):
    def fake_retrieval(query: str, *, k: int = 5, prefer_vector: bool = True):
        return FakeRetrievalResult(
            query=query,
            k=k,
            source="orm",
            degraded=True,
            results=[{"libro_id": 101, "titulo": "Libro A"}],
            warnings=[],
        )

    for case in golden_set:
        message = case["message"]
        expected = case["expected"]

        resp = handle_agent_message(
            message,
            k=case.get("k", 5),
            prefer_vector=case.get("prefer_vector", True),
            include_trace=True,
            retrieval_fn=fake_retrieval,  # type: ignore[arg-type]
            llm=FakeLLM(),
        )
        payload = resp.to_dict()

        if expected.get("error"):
            assert payload.get("error") == expected["error"]
            assert payload["results"] == []
            assert payload["actions"] == []
            continue

        assert payload["message"]
        assert "results" in payload
        assert "actions" in payload
        assert len(payload["results"]) >= expected.get("min_results", 0)

        if expected.get("actions"):
            assert isinstance(payload["actions"], list)

        tool_name = expected.get("tool")
        if tool_name:
            assert payload["trace"]["tool"]["name"] == tool_name
