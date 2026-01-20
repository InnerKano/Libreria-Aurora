"""LLM factory centralizada para el feature agentic.

Decisiones clave:
- Selección de proveedor por variables de entorno (.env) con fallback seguro a stub.
- Soporta BYO key opcional si `LLM_ALLOW_BYO_KEY=true` y el caller entrega la key.
- Devuelve un "runnable" minimalista con `.invoke()` / `.ainvoke()` que entrega metadatos.
"""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

from django.core.exceptions import ImproperlyConfigured

try:
    import openai  # type: ignore
except ImportError:  # pragma: no cover - se maneja en runtime
    openai = None

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    model: str
    base_url: Optional[str]
    api_key: Optional[str]
    timeout_sec: int
    max_tokens: int
    cost_mode: str
    allow_byo_key: bool


def _env_bool(name: str, default: bool = False) -> bool:
    return str(os.getenv(name, str(default))).strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default))
    try:
        return int(raw)
    except (TypeError, ValueError) as exc:
        raise ImproperlyConfigured(f"{name} debe ser un entero. Valor recibido: {raw}") from exc


def load_llm_config() -> LLMConfig:
    provider = (os.getenv("LLM_PROVIDER", "openai_compatible") or "openai_compatible").strip()
    model = (os.getenv("LLM_MODEL", "llama-3-8b-instruct") or "llama-3-8b-instruct").strip()
    base_url = os.getenv("LLM_BASE_URL") or None
    api_key = os.getenv("LLM_API_KEY") or None
    timeout_sec = _env_int("LLM_TIMEOUT_SEC", 15)
    max_tokens = _env_int("LLM_MAX_TOKENS", 512)
    cost_mode = (os.getenv("LLM_COST_MODE", "paid") or "paid").strip().lower()
    allow_byo_key = _env_bool("LLM_ALLOW_BYO_KEY", False)

    if cost_mode not in {"paid", "byo_key", "hybrid"}:
        raise ImproperlyConfigured("LLM_COST_MODE debe ser uno de: paid, byo_key, hybrid")

    return LLMConfig(
        provider=provider,
        model=model,
        base_url=base_url,
        api_key=api_key,
        timeout_sec=timeout_sec,
        max_tokens=max_tokens,
        cost_mode=cost_mode,
        allow_byo_key=allow_byo_key,
    )


class StubLLM:
    """LLM determinista para tests o fallback sin red."""

    def __init__(self, config: LLMConfig, canned_response: str = "Respuesta stub del LLM.") -> None:
        self.config = config
        self.canned_response = canned_response

    def _build_response(self, prompt: str, latency_ms: int) -> Dict[str, Any]:
        return {
            "content": self.canned_response,
            "provider": "stub",
            "model": "stub",
            "latency_ms": latency_ms,
            "prompt_tokens": None,
            "completion_tokens": None,
            "error": None,
            "prompt": prompt,
        }

    def invoke(self, prompt: str, *, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        start = time.perf_counter()
        latency_ms = int((time.perf_counter() - start) * 1000)
        return self._build_response(prompt, latency_ms)

    async def ainvoke(self, prompt: str, *, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        # No async real; suficiente para tests/aserciones.
        return self.invoke(prompt, metadata=metadata)


class OpenAICompatibleLLM:
    """Cliente para endpoints OpenAI-compatible (OpenAI, vLLM, LM Studio, Ollama API)."""

    def __init__(self, config: LLMConfig, api_key: str):
        if openai is None:
            raise ImproperlyConfigured(
                "Falta la dependencia 'openai'. Instala openai>=1.30.0 para usar LLM_PROVIDER=openai_compatible."
            )
        self.config = config
        self._client = openai.OpenAI(api_key=api_key, base_url=config.base_url or None, timeout=config.timeout_sec)

    def invoke(self, prompt: str, *, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        start = time.perf_counter()
        response = self._client.chat.completions.create(
            model=self.config.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=self.config.max_tokens if self.config.max_tokens > 0 else None,
            stream=False,
        )
        latency_ms = int((time.perf_counter() - start) * 1000)
        choice = response.choices[0].message.content or ""
        usage = getattr(response, "usage", None)
        prompt_tokens = getattr(usage, "prompt_tokens", None) if usage else None
        completion_tokens = getattr(usage, "completion_tokens", None) if usage else None

        return {
            "content": choice,
            "provider": self.config.provider,
            "model": self.config.model,
            "latency_ms": latency_ms,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "error": None,
            "prompt": prompt,
        }

    async def ainvoke(self, prompt: str, *, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        # openai-python ya es async-friendly, pero aquí usamos el cliente sync para reducir dependencias.
        return self.invoke(prompt, metadata=metadata)


def build_llm_runnable(*, byo_api_key: Optional[str] = None) -> Any:
    """Factory principal.

    Reglas:
    - `LLM_PROVIDER`:
        - "stub"/"local_stub"/"test" => siempre retorna stub determinista.
        - "openai_compatible" => usa OpenAI client con base_url opcional.
    - `LLM_COST_MODE`:
        - paid: usa LLM_API_KEY del servidor; si falta, cae a stub.
        - byo_key: exige key del usuario (header/caller); si falta, lanza ImproperlyConfigured.
        - hybrid: prioriza key de usuario si se permite, si no hay usa la del servidor, si ninguna existe cae a stub.
    - `LLM_ALLOW_BYO_KEY` debe ser true para aceptar la key del usuario.
    """

    config = load_llm_config()
    provider = config.provider.lower()

    if provider in {"stub", "local_stub", "test"}:
        logger.warning("LLM_PROVIDER=%s => usando StubLLM (sin red)", provider)
        return StubLLM(config)

    if provider != "openai_compatible":
        raise ImproperlyConfigured(f"LLM_PROVIDER={config.provider} no soportado.")

    # Selección de API key siguiendo cost_mode y bandera BYO.
    selected_key: Optional[str] = None
    if config.allow_byo_key and byo_api_key:
        selected_key = byo_api_key
    elif config.cost_mode == "byo_key":
        selected_key = byo_api_key
    elif config.cost_mode in {"paid", "hybrid"}:
        selected_key = config.api_key or (byo_api_key if config.allow_byo_key else None)

    if not selected_key:
        if config.cost_mode == "byo_key":
            raise ImproperlyConfigured("LLM_COST_MODE=byo_key requiere que el caller provea la API key del LLM.")
        logger.warning("No hay LLM_API_KEY configurada; se usará StubLLM como fallback.")
        return StubLLM(config, canned_response="LLM sin API key: respondiendo en modo stub.")

    return OpenAICompatibleLLM(config, api_key=selected_key)


__all__ = [
    "LLMConfig",
    "load_llm_config",
    "build_llm_runnable",
    "StubLLM",
    "OpenAICompatibleLLM",
]
