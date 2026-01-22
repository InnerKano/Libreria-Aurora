from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class GuardrailResult:
    ok: bool
    errors: list[str]


def _count_bullets(lines: Iterable[str]) -> int:
    markers = ("- ", "• ", "* ")
    return sum(1 for line in lines if line.strip().startswith(markers))


def validate_llm_message(
    message: str,
    *,
    min_chars: int = 1,
    max_chars: int = 800,
    min_bullets: int = 2,
    max_bullets: int = 5,
) -> GuardrailResult:
    errors: list[str] = []

    text = (message or "").strip()
    if len(text) < min_chars:
        errors.append("empty_or_too_short")
    if len(text) > max_chars:
        errors.append("too_long")

    if text.startswith("{") or text.startswith("["):
        errors.append("looks_like_json")
    if "```" in text:
        errors.append("contains_code_block")

    lines = [line for line in text.splitlines() if line.strip()]
    bullets = _count_bullets(lines)
    if bullets == 0:
        errors.append("missing_bullets")
    if bullets < min_bullets:
        errors.append("too_few_bullets")
    if bullets > max_bullets:
        errors.append("too_many_bullets")

    return GuardrailResult(ok=not errors, errors=errors)


__all__ = ["GuardrailResult", "validate_llm_message"]
