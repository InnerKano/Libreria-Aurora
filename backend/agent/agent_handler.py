from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Optional

from django.core.exceptions import ImproperlyConfigured

from .llm_factory import build_llm_runnable
from .retrieval import RetrievalResult, search_catalog


@dataclass(frozen=True)
class AgentResponse:
    message: str
    results: list[dict[str, Any]]
    actions: list[dict[str, Any]]
    trace: Optional[dict[str, Any]] = None
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "message": self.message,
            "results": self.results,
            "actions": self.actions,
        }
        if self.trace is not None:
            payload["trace"] = self.trace
        if self.error is not None:
            payload["error"] = self.error
        return payload


def _clean_message(message: Optional[str]) -> str:
    return (message or "").strip()


def _default_actions_from_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []

    for item in results[:5]:
        libro_id = item.get("libro_id")
        if libro_id is None:
            continue
        actions.append({"type": "view_book", "libro_id": libro_id})

    if results:
        actions.append({"type": "refine_search", "hint": "Puedes pedirme filtrar por autor, ISBN o categoría."})

    return actions


def _build_fallback_message(*, query: str, results_count: int, degraded: bool, warnings: list[str]) -> str:
    if query == "":
        return "Escribe una consulta para buscar libros (por título, autor o ISBN)."

    mode = " (modo degradado)" if degraded else ""
    if results_count == 0:
        base = f"No encontré resultados para '{query}'{mode}."
        if warnings:
            base += "\n\nDetalles: " + "; ".join(warnings)
        return base

    base = f"Encontré {results_count} resultados para '{query}'{mode}."
    if degraded:
        base += "\n\nNota: el buscador semántico no estaba disponible, así que usé búsqueda exacta."
    return base


def _build_llm_prompt(*, user_message: str, retrieval: RetrievalResult) -> str:
    safe_results = retrieval.results[:5]

    instruction = (
        "Eres un asistente para una librería.\n"
        "Reglas: NO inventes precios/IDs/stock.\n"
        "Usa únicamente los resultados provistos (si no hay, dilo).\n"
        "Responde en español, conciso, con 2-5 bullets máximo.\n"
    )

    context = {
        "query": retrieval.query,
        "degraded": retrieval.degraded,
        "source": retrieval.source,
        "results": safe_results,
    }

    return (
        instruction
        + "\nMensaje del usuario:\n"
        + user_message
        + "\n\nContexto de búsqueda (JSON):\n"
        + json.dumps(context, ensure_ascii=False)
        + "\n"
    )


def handle_agent_message(
    message: Optional[str],
    *,
    k: int = 5,
    prefer_vector: bool = True,
    include_trace: bool = False,
    retrieval_fn: Optional[Callable[..., RetrievalResult]] = None,
    llm: Optional[Any] = None,
    byo_api_key: Optional[str] = None,
) -> AgentResponse:
    """Minimal conversational handler.

    Responsibilities:
    - Validate/normalize the user message.
    - Run retrieval (vector + fallback ORM) to produce results.
    - Produce a stable JSON response contract for the API layer.

    Notes:
    - This function intentionally does NOT depend on DRF.
    - LLM usage is best-effort: it only generates the `message` field.
      The `results` list always comes from retrieval (source of truth).
    """

    cleaned = _clean_message(message)
    if cleaned == "":
        return AgentResponse(
            message="Mensaje vacío. Escribe qué libro buscas.",
            results=[],
            actions=[],
            trace={"degraded": True} if include_trace else None,
            error="invalid_request",
        )

    retrieval_fn = retrieval_fn or search_catalog
    retrieval = retrieval_fn(cleaned, k=k, prefer_vector=prefer_vector)
    actions = _default_actions_from_results(retrieval.results)

    llm_meta: dict[str, Any] = {}
    final_message: str

    try:
        runnable = llm or build_llm_runnable(byo_api_key=byo_api_key)
        prompt = _build_llm_prompt(user_message=cleaned, retrieval=retrieval)
        llm_resp = runnable.invoke(prompt)
        final_message = (llm_resp or {}).get("content") or ""
        llm_meta = {
            "provider": (llm_resp or {}).get("provider"),
            "model": (llm_resp or {}).get("model"),
            "latency_ms": (llm_resp or {}).get("latency_ms"),
            "error": (llm_resp or {}).get("error"),
        }
        if final_message.strip() == "":
            raise RuntimeError("LLM returned empty content")
    except ImproperlyConfigured as e:
        final_message = _build_fallback_message(
            query=retrieval.query,
            results_count=len(retrieval.results),
            degraded=retrieval.degraded,
            warnings=retrieval.warnings + [str(e)],
        )
        llm_meta = {"error": str(e), "provider": "unconfigured"}
    except Exception as e:
        final_message = _build_fallback_message(
            query=retrieval.query,
            results_count=len(retrieval.results),
            degraded=retrieval.degraded,
            warnings=retrieval.warnings + [f"LLM failed: {e}"],
        )
        llm_meta = {"error": str(e), "provider": "failed"}

    trace: Optional[dict[str, Any]] = None
    if include_trace:
        trace = {
            "query": retrieval.query,
            "k": retrieval.k,
            "source": retrieval.source,
            "degraded": retrieval.degraded,
            "warnings": retrieval.warnings,
            "llm": llm_meta,
        }

    return AgentResponse(
        message=final_message,
        results=retrieval.results,
        actions=actions,
        trace=trace,
        error=None,
    )


__all__ = ["AgentResponse", "handle_agent_message"]
