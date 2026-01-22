from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .retrieval import RetrievalResult


@dataclass(frozen=True)
class PromptConfig:
    language: str = "es"
    max_bullets: int = 5
    min_bullets: int = 2
    max_chars: int = 800


def _instruction_block(cfg: PromptConfig) -> str:
    return (
        "Eres un asistente para una librería.\n"
        "Reglas estrictas:\n"
        "- NO inventes precios, IDs, stock ni disponibilidad.\n"
        "- Usa únicamente los resultados provistos.\n"
        "- Si no hay resultados, dilo claramente y sugiere refinar la búsqueda.\n"
        "- Responde en español, conciso.\n"
        f"- Usa entre {cfg.min_bullets} y {cfg.max_bullets} bullets, máximo {cfg.max_chars} caracteres.\n"
        "- No incluyas JSON ni bloques de código.\n"
    )


def _few_shots() -> str:
    return (
        "Ejemplo 1:\n"
        "Usuario: Busco ciencia ficción con robots\n"
        "Respuesta:\n"
        "- Tengo resultados relacionados con ciencia ficción y robots.\n"
        "- ¿Quieres filtrar por autor o por año de publicación?\n\n"
        "Ejemplo 2:\n"
        "Usuario: isbn 9780307474728\n"
        "Respuesta:\n"
        "- Encontré el libro asociado a ese ISBN.\n"
        "- ¿Quieres ver el detalle o buscar similares?\n"
    )


def build_llm_prompt(*, user_message: str, retrieval: RetrievalResult, config: PromptConfig | None = None) -> str:
    cfg = config or PromptConfig()

    safe_results = retrieval.results[:5]
    context = {
        "query": retrieval.query,
        "degraded": retrieval.degraded,
        "source": retrieval.source,
        "results": safe_results,
    }

    return (
        _instruction_block(cfg)
        + "\n"
        + _few_shots()
        + "\nMensaje del usuario:\n"
        + user_message
        + "\n\nContexto de búsqueda (JSON):\n"
        + json.dumps(context, ensure_ascii=False)
        + "\n"
    )


__all__ = ["PromptConfig", "build_llm_prompt"]
