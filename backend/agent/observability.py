from __future__ import annotations

import logging
import os
import random
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Any

DEFAULT_TRACE_MAX_CHARS = int(os.getenv("AGENT_TRACE_MAX_CHARS", "400"))
DEFAULT_TRACE_SAMPLE_RATE = float(os.getenv("AGENT_TRACE_SAMPLE_RATE", "1.0"))

_logger = logging.getLogger("agent")


def new_request_id() -> str:
    return uuid.uuid4().hex


def now_ms() -> int:
    return int(time.time() * 1000)


def elapsed_ms(start_monotonic: float) -> int:
    return int((time.monotonic() - start_monotonic) * 1000)


def truncate_text(text: Any, *, max_len: int | None = None) -> str:
    if text is None:
        return ""
    raw = str(text)
    limit = max_len if max_len is not None else DEFAULT_TRACE_MAX_CHARS
    if limit <= 0:
        return ""
    if len(raw) <= limit:
        return raw
    return raw[: max(0, limit - 3)] + "..."


def redact_api_key(value: Any) -> str:
    if not value:
        return ""
    raw = str(value)
    if len(raw) <= 8:
        return "***"
    return f"{raw[:2]}***{raw[-2:]}"


def should_sample_trace(rate: float | None = None) -> bool:
    effective = DEFAULT_TRACE_SAMPLE_RATE if rate is None else rate
    if effective <= 0:
        return False
    if effective >= 1:
        return True
    return random.random() <= effective


def log_event(event: str, **fields: Any) -> None:
    payload = {"event": event, **fields}
    _logger.info(payload)


@dataclass
class _Metric:
    count: int = 0
    total_ms: int = 0
    max_ms: int = 0


class MetricsStore:
    """In-memory metrics store (lightweight, process-local)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[str, int] = {}
        self._timings: dict[str, _Metric] = {}

    def increment(self, name: str, value: int = 1) -> None:
        with self._lock:
            self._counters[name] = self._counters.get(name, 0) + value

    def record_timing(self, name: str, duration_ms: int) -> None:
        with self._lock:
            metric = self._timings.get(name)
            if metric is None:
                metric = _Metric()
                self._timings[name] = metric
            metric.count += 1
            metric.total_ms += duration_ms
            metric.max_ms = max(metric.max_ms, duration_ms)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "counters": dict(self._counters),
                "timings": {
                    name: {
                        "count": metric.count,
                        "total_ms": metric.total_ms,
                        "max_ms": metric.max_ms,
                    }
                    for name, metric in self._timings.items()
                },
            }


METRICS = MetricsStore()


def record_counter(name: str, value: int = 1) -> None:
    METRICS.increment(name, value=value)


def record_timing(name: str, duration_ms: int) -> None:
    METRICS.record_timing(name, duration_ms=duration_ms)
