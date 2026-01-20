# Estructura del feature “Agente” (carpetas y responsabilidades)

Este feature está dividido en **dos capas** a propósito:

1) **Core del agente (reutilizable, sin Django)** → `backend/agent/`
2) **Integración Django/DRF (wiring de endpoints)** → `backend/apps/agent_api/`

Esto es una decisión **responsable, profesional y escalable** porque:
- Evita acoplar la lógica del agente a Django/DRF.
- Permite testear la mayor parte del feature sin base de datos/requests.
- Define una dirección clara de dependencias: **`agent_api` depende de `agent`, nunca al revés**.
- Evita colisiones de imports: una app llamada `apps.agent` colisiona con el paquete `agent.*`.

---

## 1) `backend/agent/` (core reusable del agente)

### Qué es
Paquete Python con la **lógica del feature** que debe poder ejecutarse con mínimas dependencias del framework.

### Qué debe ir aquí
- Retrieval (vectorial + fallback) y contratos de salida.
- Factory de LLM y wrappers de proveedores.
- Tools del agente (funciones puras que reciben inputs y devuelven outputs estructurados), siempre que no dependan de request/DRF.
- Prompts, parsers y schemas internos del agente.
- Artefactos del vector DB y sus metadatos:
	- `backend/agent/vector_db/` (Chroma persistido)
	- `backend/agent/vector_db/manifest.json`
- Scripts/notebooks reproducibles del agente:
	- `backend/agent/notebooks/`
	- `backend/agent/scripts/`

### Qué NO debe ir aquí
- Vistas DRF, rutas, permisos, throttling, serializers DRF.
- Cualquier lógica que dependa de `request.user` o auth JWT.

### Tests
- Tests unitarios del core (sin HTTP) en `backend/agent/tests/`.
	- Ejemplo: `test_llm_factory.py`, `test_retrieval.py`.

---

## 2) `backend/apps/agent_api/` (wiring Django/DRF)

### Qué es
Una app Django “delgada” que expone el feature del agente como API.

### Qué debe ir aquí
- `views.py`: endpoints (por ejemplo `/api/agent/search/` y en fases posteriores `/api/agent/`).
- `urls.py`: ruteo.
- Validaciones de request/response de capa API.
- Integración de auth/permissions (JWT), rate limiting, logging/tracing.
- Serializers DRF si son necesarios (para requests/responses complejas).

### Qué NO debe ir aquí
- La lógica central de retrieval/LLM/tools (eso vive en `backend/agent/`).

### Tests
- Tests de endpoints y wiring (DRF) en `backend/apps/agent_api/tests/`.
	- Ejemplo: `test_phase2_api.py`.

---

## Regla de nombres (importante)

- NO crear una app Django llamada `backend/apps/agent/`.
- Motivo: el paquete core `backend/agent` se importa como `agent.*` y una app `apps.agent` puede provocar **colisión de imports** (especialmente en pytest y autodiscovery de Django).
- Por eso el wiring se llama `agent_api`.

---

## Resumen de dependencias (dirección única)

- `backend/apps/agent_api/*`  → puede importar → `backend/agent/*`
- `backend/agent/*` → NO debe importar → `backend/apps/agent_api/*`
