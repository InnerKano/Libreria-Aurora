from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional

from django.core.exceptions import ImproperlyConfigured

from .guardrails import validate_llm_message
from .llm_factory import build_llm_runnable
from .observability import record_counter, record_timing
from .prompts import build_llm_prompt
from .retrieval import RetrievalResult, search_catalog
from .tools import (
    tool_add_to_cart,
    tool_filter_catalog,
    tool_lookup_book,
    tool_order_status,
    tool_reserve_book,
)


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


def _extract_book_id(message: str) -> Optional[int]:
    match = re.search(r"\b(?:libro|id)\s*(\d+)\b", message, re.IGNORECASE)
    if not match:
        return None
    try:
        return int(match.group(1))
    except Exception:
        return None


def _extract_isbn(message: str) -> Optional[str]:
    match = re.search(r"\bisbn\s*[:=]?\s*([0-9Xx-]{10,17})\b", message)
    if not match:
        return None
    raw = match.group(1)
    cleaned = re.sub(r"[^0-9Xx]", "", raw)
    return cleaned or None


def _extract_filters(message: str) -> dict[str, Any]:
    filters: dict[str, Any] = {}

    def _capture(pattern: str) -> Optional[str]:
        m = re.search(pattern, message, re.IGNORECASE)
        return m.group(1).strip() if m else None

    categoria = _capture(r"\bcategoria\s*[:=]\s*([^,;\n]+)")
    if categoria:
        filters["categoria"] = categoria

    autor = _capture(r"\bautor\s*[:=]\s*([^,;\n]+)")
    if autor:
        filters["autor"] = autor

    editorial = _capture(r"\beditorial\s*[:=]\s*([^,;\n]+)")
    if editorial:
        filters["editorial"] = editorial

    precio_min = _capture(r"\bprecio_min\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)")
    if precio_min is not None:
        filters["precio_min"] = precio_min

    precio_max = _capture(r"\bprecio_max\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)")
    if precio_max is not None:
        filters["precio_max"] = precio_max

    if re.search(r"\bdisponible\b", message, re.IGNORECASE):
        filters["disponible"] = True
    if re.search(r"\bagotado\b", message, re.IGNORECASE):
        filters["disponible"] = False

    return filters


def _coerce_bullets(message: str, *, min_bullets: int = 2, max_bullets: int = 5) -> str:
    text = (message or "").strip()
    if not text:
        return ""

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    bullet_markers = ("- ", "• ", "* ")
    if any(line.startswith(bullet_markers) for line in lines):
        return text

    # Split into simple sentence-like chunks.
    parts: list[str] = []
    chunk = ""
    for char in text:
        chunk += char
        if char in {".", "!", "?", "\n"}:
            cleaned = chunk.strip()
            if cleaned:
                parts.append(cleaned)
            chunk = ""
    if chunk.strip():
        parts.append(chunk.strip())

    if not parts:
        parts = [text]

    bullets = [p.strip().rstrip(".") for p in parts if p.strip()]

    if len(bullets) < min_bullets:
        bullets.append("¿Quieres ver detalles del libro?")
    if len(bullets) < min_bullets:
        bullets.append("Puedo filtrar por autor, ISBN o categoría.")

    bullets = bullets[:max_bullets]
    return "\n".join(f"- {item}" for item in bullets)


def handle_agent_message(
    message: Optional[str],
    *,
    k: int = 5,
    prefer_vector: bool = True,
    include_trace: bool = False,
    retrieval_fn: Optional[Callable[..., RetrievalResult]] = None,
    llm: Optional[Any] = None,
    byo_api_key: Optional[str] = None,
    request_id: Optional[str] = None,
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
    retrieval: RetrievalResult
    tool_meta: Optional[dict[str, Any]] = None

    book_id = _extract_book_id(cleaned)
    isbn = _extract_isbn(cleaned)

    retrieval_started = time.monotonic()

    if book_id is not None or isbn is not None:
        lookup = tool_lookup_book(book_id=book_id, isbn=isbn)
        if lookup.ok and lookup.data and lookup.data.get("results"):
            retrieval = RetrievalResult(
                query=cleaned,
                k=1,
                source="orm",
                degraded=True,
                results=lookup.data.get("results", []),
                warnings=lookup.warnings,
            )
            tool_meta = {"name": "lookup_book", "ok": True}
        else:
            tool_meta = {"name": "lookup_book", "ok": False, "error": lookup.error}
            retrieval = retrieval_fn(cleaned, k=k, prefer_vector=prefer_vector)
    else:
        filters = _extract_filters(cleaned)
        if filters:
            filtered = tool_filter_catalog(filters, k=k)
            retrieval = RetrievalResult(
                query=cleaned,
                k=k,
                source="orm",
                degraded=True,
                results=(filtered.data or {}).get("results", []),
                warnings=filtered.warnings,
            )
            tool_meta = {"name": "filter_catalog", "ok": filtered.ok, "filters": filters}
        else:
            retrieval = retrieval_fn(cleaned, k=k, prefer_vector=prefer_vector)
    actions = _default_actions_from_results(retrieval.results)

    retrieval_ms = int((time.monotonic() - retrieval_started) * 1000)
    record_timing("agent.retrieval_ms", retrieval_ms)
    if retrieval.degraded:
        record_counter("agent.retrieval_degraded")
    if retrieval.source == "vector":
        record_counter("agent.retrieval_vector")
    else:
        record_counter("agent.retrieval_orm")

    llm_meta: dict[str, Any] = {}
    final_message: str
    llm_started = time.monotonic()

    try:
        runnable = llm or build_llm_runnable(byo_api_key=byo_api_key)
        prompt = build_llm_prompt(user_message=cleaned, retrieval=retrieval)
        llm_resp = runnable.invoke(prompt)
        final_message = (llm_resp or {}).get("content") or ""
        record_counter("agent.llm_success")
        llm_meta = {
            "provider": (llm_resp or {}).get("provider"),
            "model": (llm_resp or {}).get("model"),
            "latency_ms": (llm_resp or {}).get("latency_ms"),
            "error": (llm_resp or {}).get("error"),
        }
        guard = validate_llm_message(final_message)
        if not guard.ok:
            coerced = _coerce_bullets(final_message)
            if coerced and validate_llm_message(coerced).ok:
                final_message = coerced
                llm_meta["coerced"] = True
            else:
                raise RuntimeError(f"LLM guardrails failed: {','.join(guard.errors)}")
    except ImproperlyConfigured as e:
        record_counter("agent.llm_unconfigured")
        final_message = _build_fallback_message(
            query=retrieval.query,
            results_count=len(retrieval.results),
            degraded=retrieval.degraded,
            warnings=retrieval.warnings + [str(e)],
        )
        llm_meta = {"error": str(e), "provider": "unconfigured"}
    except Exception as e:
        record_counter("agent.llm_failed")
        final_message = _build_fallback_message(
            query=retrieval.query,
            results_count=len(retrieval.results),
            degraded=retrieval.degraded,
            warnings=retrieval.warnings + [f"LLM failed: {e}"],
        )
        llm_meta = {"error": str(e), "provider": "failed"}

    llm_ms = int((time.monotonic() - llm_started) * 1000)
    record_timing("agent.llm_total_ms", llm_ms)

    trace: Optional[dict[str, Any]] = None
    if include_trace:
        trace = {
            "request_id": request_id,
            "query": retrieval.query,
            "k": retrieval.k,
            "source": retrieval.source,
            "degraded": retrieval.degraded,
            "warnings": retrieval.warnings,
            "timings_ms": {
                "retrieval": retrieval_ms,
                "llm": llm_ms,
            },
            "llm": llm_meta,
        }
        if tool_meta is not None:
            trace["tool"] = tool_meta

    return AgentResponse(
        message=final_message,
        results=retrieval.results,
        actions=actions,
        trace=trace,
        error=None,
    )


def _parse_int(value: Any, *, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


def handle_agent_action(
    action: Optional[str],
    payload: Optional[dict[str, Any]],
    *,
    user_id: int,
    include_trace: bool = False,
    request_id: Optional[str] = None,
) -> AgentResponse:
    normalized = (action or "").strip().lower()
    payload = payload or {}

    started = time.monotonic()

    if normalized == "add_to_cart":
        book_id = _parse_int(payload.get("book_id"), default=-1)
        cantidad = payload.get("cantidad", 1)
        tool_result = tool_add_to_cart(user_id=user_id, book_id=book_id, cantidad=cantidad)
    elif normalized == "reserve_book":
        book_id = _parse_int(payload.get("book_id"), default=-1)
        cantidad = payload.get("cantidad", 1)
        tool_result = tool_reserve_book(user_id=user_id, book_id=book_id, cantidad=cantidad)
    elif normalized == "order_status":
        order_id = _parse_int(payload.get("order_id"), default=-1)
        tool_result = tool_order_status(user_id=user_id, order_id=order_id)
    else:
        return AgentResponse(
            message="Acción inválida. Usa: add_to_cart, reserve_book u order_status.",
            results=[],
            actions=[],
            trace={"request_id": request_id, "action": normalized} if include_trace else None,
            error="invalid_action",
        )

    duration_ms = int((time.monotonic() - started) * 1000)
    record_timing("agent.action_ms", duration_ms)
    record_counter("agent.action_ok" if tool_result.ok else "agent.action_failed")

    data = tool_result.data or {}
    if isinstance(data, dict) and isinstance(data.get("results"), list):
        results = data.get("results", [])
    elif isinstance(data, dict) and data.get("result") is not None:
        results = [data.get("result")]
    else:
        results = []

    message = (data.get("message") if isinstance(data, dict) else None) or (
        f"Acción '{normalized}' completada." if tool_result.ok else f"No se pudo ejecutar '{normalized}'."
    )

    actions = [
        {
            "type": "action_result",
            "action": normalized,
            "ok": tool_result.ok,
            "error": tool_result.error,
            "warnings": tool_result.warnings,
            "data": tool_result.data,
        }
    ]

    trace: Optional[dict[str, Any]] = None
    if include_trace:
        trace = {
            "request_id": request_id,
            "action": normalized,
            "ok": tool_result.ok,
            "error": tool_result.error,
            "warnings": tool_result.warnings,
            "duration_ms": duration_ms,
        }

    return AgentResponse(
        message=message,
        results=results,
        actions=actions,
        trace=trace,
        error=None if tool_result.ok else (tool_result.error or "action_failed"),
    )


__all__ = ["AgentResponse", "handle_agent_message", "handle_agent_action"]
