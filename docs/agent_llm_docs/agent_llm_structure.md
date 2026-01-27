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
	- Fase 6 (evaluación): `test_golden_set.py`, `test_prompts.py`, `test_vector_smoke.py`.

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
	- Fase 6 (evaluación): `test_agent_chat_api.py` (parsing robusto adicional).

---

## Regla de nombres (importante)

- NO crear una app Django llamada `backend/apps/agent/`.
- Motivo: el paquete core `backend/agent` se importa como `agent.*` y una app `apps.agent` puede provocar **colisión de imports** (especialmente en pytest y autodiscovery de Django).
- Por eso el wiring se llama `agent_api`.

---

## Resumen de dependencias (dirección única)

- `backend/apps/agent_api/*`  → puede importar → `backend/agent/*`
- `backend/agent/*` → NO debe importar → `backend/apps/agent_api/*`

---

# Implementación actual (Fase 5A): endpoint conversacional mínimo

Esta sección documenta **qué se implementó** para la Fase 5A y **cómo está estructurado** el código para que sea mantenible y escalable.

## Objetivo de la Fase 5A (por qué existe)

- Entregar un endpoint conversacional usable por frontend **sin bloquear** el roadmap del agente (tools mutables, grafo, etc.).
- Mantener un **contrato JSON estable** para UI (chat) desde el inicio.
- Ser responsable con el dominio: el sistema **no inventa** IDs/precios/stock. La “fuente de verdad” es el catálogo (retrieval/ORM).
- Permitir operar en modo “sin LLM” o “LLM no disponible” sin romper el endpoint (degradación controlada).

## API pública (wiring)

### Endpoint

- `POST /api/agent/` (conversacional)
- `GET /api/agent/search/` (retrieval directo; ya existía)

### Archivos involucrados

- Wiring y HTTP:
	- `backend/apps/agent_api/views.py`
		- `AgentChatView` (POST `/api/agent/`)
		- `AgentSearchView` (GET `/api/agent/search/`)
	- `backend/apps/agent_api/urls.py`
		- `path("", AgentChatView.as_view(), ...)`
		- `path("search/", AgentSearchView.as_view(), ...)`

### Contrato del request (Fase 5A)

Body JSON:
- `message: str` (requerido)
- `k: int` (opcional, default 5)
- `prefer_vector: bool` (opcional, default true)
- `trace: bool` (opcional, default false)

Notas:
- `trace` está pensado para debugging en desarrollo (no para producción abierta).

### Contrato del response (Fase 5A)

Siempre presente:
- `message: str` (respuesta para UI)
- `results: list[dict]` (resultados del catálogo)
- `actions: list[dict]` (acciones sugeridas; por ahora read-only)

Opcional:
- `trace: dict` (solo si se solicita)
- `error: str` (solo si request inválido; el endpoint responde HTTP 400)

## Core del agente (orquestación sin DRF)

### Archivos involucrados

- Handler conversacional:
	- `backend/agent/agent_handler.py`
		- `handle_agent_message(...)` → punto de entrada del “chat handler”
		- `AgentResponse` → wrapper para asegurar contrato estable + `to_dict()`

- Retrieval (fuente de verdad):
	- `backend/agent/retrieval.py`
		- `search_catalog(...)` → vector search (si disponible) + fallback ORM

- LLM (opcional, no obligatorio para responder):
	- `backend/agent/llm_factory.py`
		- `build_llm_runnable(...)` → devuelve runnable con `.invoke()` / `.ainvoke()`

### Responsabilidades (para mantenimiento)

- `handle_agent_message` hace:
	1) Normaliza/valida `message`.
	2) Ejecuta retrieval (`search_catalog`) para obtener `results`.
	3) Construye `actions` seguras a partir de `results`.
	4) (Opcional) Pide un LLM vía factory y le pasa un prompt con contexto de retrieval para redactar `message`.
	5) Si el LLM falla/no está configurado: genera `message` determinista y útil (fallback), sin romper el contrato.

Regla importante:
- El LLM **no decide inventario, precio, IDs**. Solo redacta.
- `results` siempre proviene de retrieval/ORM (o lista vacía) para evitar alucinaciones.

---

# Implementación: LLM OpenAI-compatible (Ollama)

Esta sección documenta **la estructura**, **el porqué** y **dónde vive** la integración con un servidor
OpenAI-compatible local (Ollama), manteniendo la arquitectura modular y responsable.

## Objetivo (por qué existe)
- Habilitar un LLM local sin acoplar el core a un proveedor específico.
- Mantener un contrato estable para UI y tests, incluso si el LLM falla.
- Permitir configuración por entorno sin tocar el código.

## Dónde vive (archivos y responsabilidades)

### Core reusable
- `backend/agent/llm_factory.py`
	- `load_llm_config()` lee variables `LLM_*` y valida política de costos/BYO.
	- `build_llm_runnable(...)` crea el runnable del LLM o fallback a stub.
	- `OpenAICompatibleLLM` usa `langchain_openai.ChatOpenAI` para servidores compatibles.

- `backend/agent/prompts.py`
	- `build_llm_prompt(...)` define formato, idioma y reglas de salida.
	- `PromptConfig` controla bullets y longitud máxima.

- `backend/agent/guardrails.py`
	- `validate_llm_message(...)` evita JSON/código y exige bullets.

- `backend/agent/agent_handler.py`
	- `handle_agent_message(...)` orquesta retrieval + LLM.
	- `_coerce_bullets(...)` re-formatea respuestas del LLM si no cumplen guardrails,
	  evitando fallbacks innecesarios y manteniendo consistencia visual.

### Configuración y dependencias
- `backend/.env`
	- `LLM_PROVIDER=openai_compatible`
	- `LLM_MODEL=llama3.1:latest` (nombre exacto de Ollama)
	- `LLM_BASE_URL=http://localhost:11434/v1`
	- `LLM_API_KEY=local`

- `backend/requirements.txt`
	- `langchain_openai` habilita el cliente OpenAI-compatible sin acoplarse al SDK directo.

## Flujo (cómo funciona)
1) `AgentChatView` recibe el request y llama `handle_agent_message(...)`.
2) `handle_agent_message` ejecuta retrieval y arma el prompt.
3) `build_llm_runnable` crea el cliente OpenAI-compatible contra Ollama.
4) La respuesta del LLM se valida con guardrails.
5) Si no cumple formato, `_coerce_bullets` ajusta el texto en vez de degradar.

## Por qué es escalable y responsable
- **Modularidad:** el core no conoce HTTP ni headers; solo consume un runnable.
- **Configuración por entorno:** cambiar de Ollama a OpenAI requiere solo `.env`.
- **Resiliencia:** si el LLM falla, el endpoint mantiene contrato estable.
- **Mantenibilidad:** el comportamiento se gobierna por guardrails y prompts explícitos.

## Puntos de extensión (futuro)
- Agregar proveedores adicionales dentro de `llm_factory.py` sin tocar el core.
- Ajustar reglas de formato en `guardrails.py` y `prompts.py` sin cambios de wiring.
- Añadir métricas por proveedor/latencia en `observability.py` si se requiere.

---

# Implementación actual (Fase 8 – Iteración 2): acciones mutables con auth

Esta sección documenta **la estructura**, **los archivos** y **el porqué** de la integración de acciones mutables (carrito/reserva/estado) de forma segura, modular y mantenible.

## Objetivo (por qué existe)
- Habilitar acciones mutables con **JWT obligatorio** sin romper el contrato estable del agente.
- Reutilizar reglas de negocio existentes (compras/reservas) evitando duplicar lógica.
- Mantener el core del agente libre de DRF y el wiring delgado.

## API pública (wiring)

### Endpoint
- `POST /api/agent/actions/` (acciones mutables, requiere JWT)

### Archivos involucrados
- Wiring y HTTP:
	- `backend/apps/agent_api/views.py`
		- `AgentActionView.post(...)`
	- `backend/apps/agent_api/urls.py`
		- `path("actions/", AgentActionView.as_view(), ...)`

### Contrato del request
Body JSON:
- `action: str` (requerido)
- `payload: dict` (opcional; inputs específicos por acción)
- `trace: bool` (opcional, default false)

Acciones soportadas:
- `add_to_cart` → `payload: {"book_id": int, "cantidad": int}`
- `reserve_book` → `payload: {"book_id": int, "cantidad": int}`
- `order_status` → `payload: {"order_id": int}`

### Contrato del response
Siempre presente:
- `message: str`
- `results: list[dict]` (resultado de la acción, normalizado)
- `actions: list[dict]` (incluye `action_result` con `ok/error/warnings`)

Opcional:
- `trace: dict`
- `error: str` (HTTP 400 si la acción es inválida o falla)

## Core del agente (orquestación sin DRF)

### Archivos involucrados
- Core handler:
	- `backend/agent/agent_handler.py`
		- `handle_agent_action(...)` → orquesta la ejecución de tools mutables y mantiene el contrato.
		- `_parse_int(...)` → parsing seguro para inputs.

### Tools mutables (core)
- `backend/agent/tools.py`:
	- `tool_add_to_cart(...)` → agrega libro al carrito del usuario.
	- `tool_reserve_book(...)` → crea reserva con reglas de negocio.
	- `tool_order_status(...)` → devuelve estado y items del pedido.

Serializadores internos:
- `_serialize_reserva(...)`
- `_serialize_pedido(...)`
- `_normalize_quantity(...)` (validación y clamp de cantidad)

## Reutilización de dominio (por qué es responsable)
- Las tools mutables delegan a modelos y reglas existentes en `apps.compras` para evitar duplicación.
- Se valida stock, límites de reserva y estado usando la lógica actual de negocio.

## Observabilidad y rate limiting
- `throttle_scope=agent_action` en el endpoint.
- Métricas: `agent.action_ms`, `agent.action_ok`, `agent.action_failed`.
- Configuración en `backend/config/settings.py` y `.env.example`.

## Tests (dónde se valida)
- Wiring/API:
	- `backend/apps/agent_api/tests/test_agent_actions_api.py`
		- Auth requerida (401 sin JWT).
		- Acción inválida → 400 con `error=invalid_action`.
		- `add_to_cart` exitoso con resultados normalizados.

## UI (pendiente)
- El frontend debe integrar `/api/agent/actions/` para ejecutar acciones mutables.
- La UI debe enviar JWT y mapear acciones a payloads esperados.
- Mantener el contrato estable evita acoplarse al proveedor LLM.

---

# Implementación actual (UI): barra lateral del agente (frontend)

Esta sección documenta **qué se agregó en la UI**, **dónde vive**, y **por qué** se diseñó así
para ser modular, responsable y mantenible.

## Objetivo (por qué existe)
- Exponer el asistente sin romper el layout actual ni tapar el `NavBar`.
- Mantener una integración reversible y aislada (componente de barra lateral + chat).
- Consumir el contrato estable del backend (`message/results/actions`) sin acoplarse al proveedor LLM.

## Dónde vive (archivos y responsabilidades)

### UI core (React)
- `libreria-aurora/src/components/agent/AgentDrawer.jsx`
	- Renderiza la **barra lateral izquierda**.
	- Respeta el alto del `NavBar` con `topOffset` (`12vh`).
	- No bloquea navegación superior (overlay solo bajo el nav).

- `libreria-aurora/src/components/agent/AgentChat.jsx`
	- Maneja el flujo del chat y las llamadas a:
		- `POST /api/agent/` (read-only)
		- `POST /api/agent/actions/` (acciones mutables con JWT)
	- Mapea resultados (`results`) y ejecuta acciones (carrito/reserva/estado).
	- Resuelve degradación con mensajes claros.

### Integración global
- `libreria-aurora/src/components/navBar.jsx`
	- Botón de apertura del asistente (ícono de chat).
	- Monta `AgentDrawer` para que esté disponible en todas las vistas.

### Configuración API
- `libreria-aurora/src/api/config.js`
	- Endpoints agregados:
		- `agentChat`, `agentSearch`, `agentActions`.

## Flujo de UI (cómo funciona)
1) Usuario pulsa el botón de asistente en el `NavBar`.
2) Se abre la barra lateral izquierda sin cubrir el nav.
3) El usuario escribe; `AgentChat` envía a `/api/agent/`.
4) Se renderiza `message` + cards de resultados.
5) Si hay JWT, se habilitan acciones mutables y se usa `/api/agent/actions/`.

## Por qué es escalable y responsable
- **Modularidad:** los componentes del agente están aislados en `components/agent/`.
- **Contrato estable:** la UI usa solo `message/results/actions`.
- **Seguridad:** acciones mutables requieren JWT y están deshabilitadas sin token.
- **Mantenibilidad:** el drawer no altera rutas ni estados globales existentes.

## Puntos de extensión (futuro)
- Reutilizar `BookCard` para resultados del chat si se desea consistencia visual.
- Integrar historial de conversación (persistencia opcional en localStorage).
- Mostrar trazas (`trace`) solo en modo desarrollo.

---

# Implementación actual (Fase 5B): endurecimiento del endpoint conversacional

Esta sección documenta **qué se fortaleció** en la Fase 5B y **dónde vive** la lógica para mantener el endpoint estable, seguro y fácil de mantener sin romper la arquitectura.

## Objetivo (por qué existe)

- Endurecer la capa HTTP con validaciones y parsing robusto.
- Incorporar BYO key (Bring Your Own API Key) de manera **segura y no persistente**.
- Mantener el contrato JSON intacto, sin dependencia del frontend ni del proveedor LLM.

## Qué se fortaleció (qué hace)

1) **Parsing robusto de inputs**
	 - Tipos inválidos o mixtos no rompen el endpoint.
	 - `k` se normaliza con límites razonables para evitar abuso o errores.
	 - `prefer_vector` y `trace` se interpretan de forma consistente (bool-ish).

2) **BYO key vía header**
	 - Se acepta la key en el header `X-LLM-API-Key`.
	 - La key **no se persiste** y solo se pasa al handler para esta llamada.
	 - La política final de uso sigue la factory (`LLM_ALLOW_BYO_KEY`, `LLM_COST_MODE`).

3) **Documentación y tests adicionales**
	 - El header se documenta en OpenAPI.
	 - Tests de wiring verifican el forwarding del header y el rechazo de mensajes no-string.

## Dónde vive (archivos y funciones)

### Capa DRF / Wiring (backend/apps/agent_api/)

- [backend/apps/agent_api/views.py](backend/apps/agent_api/views.py)
	- `AgentChatView.post(...)`:
		- Normaliza `message`, `k`, `prefer_vector`, `trace`.
		- Lee `X-LLM-API-Key` y lo pasa a `handle_agent_message(...)`.
	- Helpers locales:
		- `_parse_bool(...)` → parsing robusto de booleanos.
		- `_parse_int(...)` → parsing de enteros con límites.

- [backend/apps/agent_api/tests/test_agent_chat_api.py](backend/apps/agent_api/tests/test_agent_chat_api.py)
	- `test_agent_chat_byo_key_forwarding`: valida el forwarding de BYO key.
	- `test_agent_chat_rejects_non_string_message`: asegura que mensajes no-string se tratan como inválidos.

### Core del agente (backend/agent/)

- [backend/agent/agent_handler.py](backend/agent/agent_handler.py)
	- `handle_agent_message(...)`:
		- Acepta `byo_api_key` y lo entrega a la LLM factory.
		- Mantiene contrato estable (no depende de DRF).

- [backend/agent/llm_factory.py](backend/agent/llm_factory.py)
	- `build_llm_runnable(byo_api_key=...)`:
		- Aplica políticas BYO/paid/hybrid y fallback seguro.

## Responsabilidades (para mantenimiento)

- **Agent API (wiring):** valida, normaliza y protege inputs del mundo externo.
- **Core agent:** orquesta, pero no conoce headers ni requests.
- **LLM factory:** decide proveedor/keys/fallback sin exposición de secretos.

## Por qué es escalable

- El parsing robusto se mantiene aislado en el wiring: si cambian reglas, no se toca el core.
- BYO key se integra como un input opcional: el core sigue determinista.
- Los tests cubren el comportamiento sin depender de servicios externos.

---

# Implementación actual (Fase 6): evaluación y tests (estructural)

Esta sección describe **dónde vive** la cobertura de evaluación del agente, **por qué existe**, y **cómo mantenerla** sin contaminar la lógica productiva.

## Objetivo (por qué existe)

- Validar el contrato estable del agente con casos representativos.
- Detectar regresiones tempranas sin depender de servicios externos ni de la BD.
- Mantener pruebas deterministas, rápidas y portables entre entornos.

## Dónde vive (qué archivos)

### Core (sin HTTP)

- Golden set y pruebas de regresión:
	- `backend/agent/tests/fixtures/agent_golden_set.json`
	- `backend/agent/tests/test_golden_set.py`
	- **Qué valida:** contrato mínimo, rutas de tools (`lookup_book`, `filter_catalog`), resultados mínimos.
	- **Cómo está diseñado:** usa stubs para retrieval/LLM y monkeypatch de tools para mantener determinismo.

- Prompts:
	- `backend/agent/tests/test_prompts.py`
	- **Qué valida:** el prompt contiene el mensaje del usuario y el contexto mínimo de retrieval.
	- **Por qué es importante:** evita regressions silenciosas en el contenido del prompt.

- Vector store (smoke test determinista):
	- `backend/agent/tests/test_vector_smoke.py`
	- **Qué valida:** o bien el vector DB responde, o falla con un error controlado/entendible.
	- **Nota de diseño:** no requiere conexión externa y no usa skips; valida comportamiento en ambos escenarios.

### Wiring / API (DRF)

- Parsing robusto adicional:
	- `backend/apps/agent_api/tests/test_agent_chat_api.py`
	- **Qué valida:** límites de `k` (clamp) y parsing bool-ish de `prefer_vector`.

## Responsabilidades (para mantenimiento)

- **Tests core:** validan la lógica de orquestación sin Django/HTTP; deben seguir siendo rápidos y deterministas.
- **Tests de API:** validan el wiring y parsing; no prueban lógica del agente (eso vive en core).
- **Golden set:** se actualiza cuando cambian reglas del contrato; evita cambios accidentales en respuestas.

## Cómo escalar sin romper estructura

- Agregar nuevos casos al golden set sin modificar el handler directamente.
- Si se introducen tools mutables (Fase 7+), crear casos de golden set separados por permisos/auth.
- Mantener tests de vector store sin “acoplar” a un artifact específico; validar errores claros.

---

# Implementación actual (Fase 7): observabilidad y operación (estructura)

Esta sección documenta **dónde vive** la observabilidad añadida, **por qué existe** y **cómo mantenerla** sin acoplar la lógica del agente a DRF ni exponer datos sensibles.

## Objetivo (por qué existe)

- Trazabilidad mínima por request (request_id) para debugging y soporte.
- Medición de latencias y degradación (vector vs ORM) sin introducir dependencia de terceros.
- Rate limiting y logging seguro (sin exponer API keys ni prompts completos).

## Dónde vive (qué archivos y funciones)

### Core (sin Django/DRF)

- [backend/agent/observability.py](backend/agent/observability.py)
	- `new_request_id()` → genera un ID por request.
	- `truncate_text()` / `redact_api_key()` → sanitiza texto sensible.
	- `record_counter()` / `record_timing()` → métricas ligeras en memoria.
	- `METRICS.snapshot()` → estado actual (útil para inspección interna).

- [backend/agent/agent_handler.py](backend/agent/agent_handler.py)
	- Registra timings (`agent.retrieval_ms`, `agent.llm_total_ms`).
	- Contadores de degradación y estados LLM (`agent.retrieval_degraded`, `agent.llm_success`, etc.).
	- Agrega `request_id` y `timings_ms` a `trace` cuando `include_trace=true`.

### Wiring / API (DRF)

- [backend/apps/agent_api/views.py](backend/apps/agent_api/views.py)
	- Añade `X-Request-Id` en responses.
	- Logging estructurado con `log_event()`.
	- `throttle_scope` por endpoint (`agent_chat`, `agent_search`).
	- Respeta `trace` y muestreo (`should_sample_trace()`).

### Configuración

- [backend/config/settings.py](backend/config/settings.py)
	- Logging `agent` separado del logger global.
	- `ScopedRateThrottle` con límites por scope.

- [backend/.env.example](backend/.env.example)
	- Variables de observabilidad (`AGENT_TRACE_*`, `AGENT_RATE_LIMIT_*`).

### Tests (Fase 7)

- [backend/agent/tests/test_agent_handler.py](backend/agent/tests/test_agent_handler.py)
	- Verifica `request_id` y `timings_ms` en `trace`.
	- Verifica contadores/timings con monkeypatch.

- [backend/apps/agent_api/tests/test_agent_observability.py](backend/apps/agent_api/tests/test_agent_observability.py)
	- Verifica `X-Request-Id` y `trace.request_id` en responses.

## Responsabilidades (para mantenimiento)

- **Core**: genera métricas y trace sin depender de HTTP ni de DRF.
- **Wiring**: agrega headers, throttling y logging seguro del request.
- **Config**: define límites y niveles de logging por entorno.

## Guías de mantenimiento (escalable y responsable)

- No registrar texto completo del usuario ni keys; siempre usar `truncate_text()`/`redact_api_key()`.
- No acoplar métricas a servicios externos aquí; si se integra Prometheus/Sentry, hacerlo en un wrapper sin tocar el core.
- Mantener `trace` opcional para evitar dependencia del frontend.

---

# Implementación actual (Fase 4): prompts y guardrails (core)

Esta sección documenta **dónde vive la lógica de prompt/validación**, por qué existe y cómo se integra de forma responsable.

## Objetivo (por qué existe)

- Asegurar que el LLM **no invente datos** ni rompa el contrato del endpoint.
- Mantener la **redacción del LLM controlada** (longitud, formato con bullets, idioma).
- Evitar que el frontend reciba salidas inesperadas (JSON, bloques de código).

## Dónde vive (qué archivos)

- Prompt base y few-shots:
	- `backend/agent/prompts.py`
		- `PromptConfig` (límites configurables)
		- `build_llm_prompt(...)` (construye el prompt con contexto de retrieval)
- Guardrails de salida:
	- `backend/agent/guardrails.py`
		- `validate_llm_message(...)` (valida longitud, formato y estilo)
		- `GuardrailResult` (ok + errores legibles)
- Integración en el handler:
	- `backend/agent/agent_handler.py`
		- Usa `build_llm_prompt(...)` antes de llamar al LLM.
		- Valida el `message` del LLM con `validate_llm_message(...)`.
		- Si falla: se activa el fallback determinista (`_build_fallback_message`).

## Responsabilidades (cómo se integra)

1) `handle_agent_message` arma el prompt con `build_llm_prompt`.
2) El LLM redacta **solo** el campo `message`.
3) `validate_llm_message` asegura límites de formato:
	- Longitud máxima.
	- Presencia de bullets.
	- Prohibición de JSON o bloques de código.
4) Si el mensaje es inválido, **no se rompe el contrato**: se usa fallback.

## Por qué esto es escalable

- `PromptConfig` permite evolucionar límites sin tocar el handler.
- `validate_llm_message` es reusable si se añaden más endpoints o formatos.
- Se puede incorporar guardrails más estrictos (por ejemplo, detección de idioma) sin modificar el wiring DRF.

## Tests (dónde se valida)

- `backend/agent/tests/test_agent_handler.py`
	- Verifica que el handler haga fallback si el LLM no respeta guardrails.
	- Mantiene el contrato estable aunque el LLM falle.

---

# Implementación actual (Fase 3): tools read-only (core)

Esta sección documenta **cómo está estructurada** la Fase 3 (tools) y **cómo se integra** con el handler, para que sea mantenible y escalable antes de avanzar a Fase 4 (prompts/guardrails).

## Objetivo (por qué existe)

- Reforzar el principio “**fuente de verdad = catálogo**”: ante preguntas concretas (“ver libro 123”, “isbn …”, “categoria: …”), el backend debe responder con datos deterministas.
- Evitar alucinaciones y evitar “magia” del LLM: las tools son funciones server-side con validación y salida estructurada.
- Mantener seguridad: por ahora son **read-only** (no mutan BD, no crean pedidos, no cambian stock).

## Dónde vive (qué archivos)

- Core tools: `backend/agent/tools.py`
	- Contiene las funciones tool y un contrato de retorno estable.
	- No depende de DRF.
	- Cuando requiere ORM, importa Django de forma defensiva (para permitir tests/unit sin DB cuando aplica).

- Orquestación / routing: `backend/agent/agent_handler.py`
	- Decide cuándo aplicar una tool vs cuándo hacer retrieval normal.
	- Mantiene el contrato del endpoint: `message`, `results`, `actions` (y opcionalmente `trace`).

## Contratos internos (para consistencia)

### `ToolResult` (salida estructurada)

En `backend/agent/tools.py` cada tool retorna `ToolResult(ok, data, error, warnings)` para:
- Manejar fallos sin excepciones “sueltas” hacia el handler.
- Dejar claro si hubo degradación (por ejemplo, ORM no disponible o parámetros inválidos).
- Facilitar testeo (asserts sobre `ok`, `error` y `data`).

### Serialización consistente de libros

- `_serialize_libro(libro)` centraliza el shape de salida de `Libro`.
- Esto evita que cada tool “invente” su JSON y reduce drift entre tools/retrieval/endpoint.

## Tools implementadas (qué hacen y para qué sirven)

Todas viven en `backend/agent/tools.py`.

- `tool_search_catalog(query, k, prefer_vector, search_fn=None)`
	- Wrapper validado sobre `search_catalog`.
	- Permite inyectar `search_fn` en tests para no depender del vector store.

- `tool_lookup_book(book_id=None, isbn=None)`
	- Consulta exacta (ORM) para “un libro específico”.
	- Devuelve error estructurado si faltan identificadores, si Django no está disponible o si no se encuentra.

- `tool_filter_catalog(filters, k=5)`
	- Filtros deterministas por atributos típicos (`categoria`, `autor`, `editorial`, `disponible`, `precio_min`, `precio_max`, `q`).
	- Está pensada para preguntas tipo “categoria: Fantasía disponible precio_max: 25”.

- `tool_recommend_similar(book_id, k=5, search_fn=None)`
	- Construye una query a partir del libro base y usa retrieval (vector/ORM) para sugerir similares.
	- Filtra el mismo `book_id` para no recomendar el mismo libro.

## Integración en el handler (cómo se decide usar tools)

La integración está en `backend/agent/agent_handler.py` y sigue una regla simple de prioridad:

1) Si el mensaje contiene **ID** o **ISBN** → usar `tool_lookup_book`.
2) Si el mensaje contiene **filtros explícitos** (prefijos tipo `categoria:` o flags como `disponible`) → usar `tool_filter_catalog`.
3) Si no aplica nada anterior → usar retrieval estándar `search_catalog`.

Para soportar esto sin dependencias extra, el handler incluye extractores básicos:

- `_extract_book_id(message)`
- `_extract_isbn(message)`
- `_extract_filters(message)`

Notas de diseño (responsable y escalable):
- El routing actual es deliberadamente simple (regex/keywords) para evitar introducir un “tool selection model” prematuro.
- Si mañana crece el número de tools, se puede migrar este routing a un router dedicado (por ejemplo `agent/tool_router.py`) sin cambiar el contrato del endpoint.

## Observabilidad / trace (sin romper contrato)

- Cuando `trace=true`, el handler puede incluir metadata en `trace["tool"]` indicando qué tool se aplicó y con qué inputs normalizados.
- `trace` sigue siendo opcional: el frontend no debe depender de él.

## Tests (qué se prueba y dónde)

- Core tools: `backend/agent/tests/test_tools.py`
	- Incluye tests sin DB (con `monkeypatch`) y tests con DB (`@pytest.mark.django_db`) para tools ORM.
	- Requisito de entorno: para correr los tests con DB necesitas PostgreSQL levantado (por ejemplo vía `docker compose up -d` en la raíz del repo).

- Orquestación del handler: `backend/agent/tests/test_agent_handler.py`
	- Incluye un test que verifica que ante un mensaje con “id 123” se usa `tool_lookup_book` y no el fallback de retrieval.

---

### Por qué esto es escalable

- El core es testeable con mocks (no requiere HTTP).
- El wiring DRF es delgado: valida input y delega a `handle_agent_message`.
- Cuando se agreguen tools mutables (carrito/reservas), se pueden añadir en el core como funciones con validación y luego exponerlas progresivamente.

## Tests (por qué están separados)

- Core tests (sin HTTP):
	- `backend/agent/tests/test_agent_handler.py`
		- Cubre: request inválido, LLM ok, LLM falla → fallback, contrato de `actions`.

- Wiring/API tests:
	- `backend/apps/agent_api/tests/test_agent_chat_api.py`
		- Cubre: contrato mínimo en 200, y error estructurado en 400.

Esto reduce flakiness: la lógica del core no depende de Django request lifecycle y la API sólo prueba wiring.

## Guías para la siguiente iteración (Fase 5B) sin romper arquitectura

- Si documentas con drf-spectacular:
	- Mantén el schema del endpoint estable y agrega ejemplos (request/response) sin cambiar campos.
	- Los ejemplos del schema viven en `backend/apps/agent_api/views.py` dentro de los decoradores `@extend_schema`.

- Si agregas tools mutables:
	- No las llames desde el LLM “en crudo”.
	- Define schemas de input por tool y valida server-side.
	- En `agent_api`, exige JWT/permisos para las tools que muten estado.

- Si agregas memoria/conversación:
	- Evita guardar prompts crudos o datos sensibles.
	- Diseña un `conversation_id` y un storage explícito (y documentado) en lugar de “magia” en el handler.

---

# Implementación actual (Iteración 1): historial de chat

Esta sección documenta **la estructura**, **los archivos** y **las responsabilidades** de la Iteración 1 del historial de chat. El objetivo es mantener **modularidad**, **privacidad** y un **contrato estable** que permita escalar sin romper el core del agente.

## Objetivo (por qué existe)

- Persistir un **chat único por usuario** para continuidad.
- Permitir análisis y métricas sin acoplarse al core del LLM.
- Mantener la separación **core vs wiring** (sin contaminar el handler ni el API existente).

## Dónde vive (estructura y archivos)

### 1) App dedicada de historial (wiring + storage)

**Ubicación:** `backend/apps/agent_history/`

**Archivos clave:**
- Modelos: `backend/apps/agent_history/models.py`
	- `AgentConversation` (conversación única por usuario)
	- `AgentMessage` (mensajes con `role`, `content`, `meta`)

- Serializers: `backend/apps/agent_history/serializers.py`
	- `AgentConversationSerializer`
	- `AgentMessageSerializer`

- Servicios: `backend/apps/agent_history/services.py`
	- `get_or_create_active_conversation(user)`
	- `record_message(conversation, role, content, meta=None)`
	- `archive_active_conversations(user)`

- Endpoints: `backend/apps/agent_history/views.py`
	- `AgentHistoryView` (GET/POST/DELETE)
	- `AgentHistoryMessageView` (POST)

- Rutas: `backend/apps/agent_history/urls.py`
	- `path("", AgentHistoryView.as_view(), ...)`
	- `path("messages/", AgentHistoryMessageView.as_view(), ...)`

- Migraciones: `backend/apps/agent_history/migrations/0001_initial.py`

### 2) Integración mínima con el chat actual

**Ubicación:** `backend/apps/agent_api/views.py`

**Qué hace:**
- En `AgentChatView.post(...)` se persiste el mensaje del usuario y la respuesta del asistente cuando:
	- hay sesión válida (JWT)
	- `save_history=true`
	- no hubo error de request

## Contrato y API (Iteración 1)

- `GET /api/agent/history/` → devuelve conversación activa + mensajes.
- `POST /api/agent/history/` → crea/retorna conversación activa.
- `POST /api/agent/history/messages/` → agrega un mensaje puntual.
- `DELETE /api/agent/history/` → archiva conversación activa y crea una nueva.

**Autenticación:** obligatoria (JWT) para acceder a historial.

## Por qué es modular y escalable

- **Separación clara:** el core `backend/agent/` no conoce DB ni DRF.
- **Wiring delgado:** el historial vive en su app (`agent_history`) y se conecta vía servicios.
- **Extensible:** se pueden agregar métricas, retención o “archivos de conversación” sin tocar `agent_handler`.

## Tests (mantenibilidad)

- Tests API del historial:
	- `backend/apps/agent_history/tests/test_history_api.py`
	- Cubre: creación, mensajes, persistencia desde `/api/agent/`, archivado.

## Puntos de extensión futuros

- Agregar retención y borrado lógico (cron/management command).
- Añadir paginación de mensajes.
- Exponer métricas agregadas por conversación sin exponer contenido crudo.

---

# Implementación prevista (Iteración 2): UI con carga de historial y continuación

## Objetivo (por qué existe)

- Cargar el historial de chat cuando el usuario abre el drawer (si está autenticado).
- Mostrar mensajes previos sin necesidad de reimplementar la conversación.
- Permitir "continuar" desde donde se quedó, manteniendo contexto y privacidad.
- Mantener modularidad: cambios en frontend no rompen backend, y viceversa.

## Contratos y flujos (arquitectura de integración)

### Contrato de carga de historial (GET `/api/agent/history/`)

Respuesta (200 OK):
```json
{
  "conversation": {
    "id": int,
    "user": int,
    "status": "active",
    "created_at": "2026-01-26T...",
    "updated_at": "2026-01-26T...",
    "message_count": 5
  },
  "messages": [
    {
      "id": int,
      "role": "user",
      "content": "Busca libros de ciencia ficción",
      "created_at": "2026-01-26T...",
      "meta": {}
    },
    {
      "id": int,
      "role": "assistant",
      "content": "Encontré 3 libros...",
      "created_at": "2026-01-26T...",
      "meta": {}
    }
  ]
}
```

Respuesta sin autenticación (401 Unauthorized): se renderiza el chat vacío (modo guest).

### Contrato de flujo de chat (POST `/api/agent/` + persistencia)

Al enviar un mensaje con `save_history=true` y JWT válido:
1. El endpoint `/api/agent/` responde con `message` + `results` + `actions`.
2. Paralelamente (o en post-hook), `/api/agent/history/messages/` persiste el mensaje del usuario y el del asistente.
3. El frontend renderiza el mensaje + historial se actualiza en BD.

### Flujo de lógica en el frontend

1. **Al montar `AgentChat`** (si hay JWT):
   - GET `/api/agent/history/` → obtiene conversación + mensajes.
   - Renderiza los mensajes previos (display-only).

2. **Al enviar un mensaje**:
   - POST `/api/agent/` con `message` + `save_history=true`.
   - Renderiza la respuesta.
   - Opcionalmente (si quiere garantía de persistencia): POST `/api/agent/history/messages/` si no se persistió automáticamente.

3. **En modo guest (sin JWT)**:
   - GET `/api/agent/history/` retorna 401.
   - El frontend mostrará un CTA de "Inicia sesión para guardar tu historial".
   - El chat funciona en memoria (local state).

## Archivos involucrados y responsabilidades

### Backend (ya existen, ajustes mínimos)

**`backend/apps/agent_history/views.py`**
- Endpoint `GET /api/agent/history/` ya existe; asegurarse que retorna `message_count` para paginación futura.
- Endpoint `POST /api/agent/history/messages/` ya existe; se usa si el frontend quiere persistencia explícita.

**`backend/apps/agent_api/views.py`**
- Endpoint `/api/agent/` ya persiste mensajes cuando `save_history=true` y hay JWT.
- Se puede añadir flag `persist_history_confirmation` en respuesta para que frontend sepa si se guardó.

### Frontend (implementar en Iteración 2)

**`libreria-aurora/src/components/agent/AgentChat.jsx`** (nuevo o ampliado)
- **Responsabilidad:** lógica del chat conversacional.
- **Qué debe hacer:**
  - `useEffect` con dependencia `[user, jwt]`:
    - Si hay JWT, llamar `GET /api/agent/history/`.
    - Renderizar mensajes previos en estado local.
  - Formulario de input para nuevos mensajes.
  - Al enviar: POST `/api/agent/` con `save_history=true`.
  - Renderizar nuevos mensajes (usuario + asistente) en la lista.

**`libreria-aurora/src/components/agent/AgentDrawer.jsx`**
- **Responsabilidad:** contenedor visual de la barra lateral.
- **Cambios:** importar y montar `AgentChat`.
- No necesita cambios grandes; solo asegurar que pasa `user` y `jwt` si están disponibles.

**`libreria-aurora/src/api/config.js`**
- **Responsabilidad:** configuración de endpoints.
- **Qué debe tener:**
  - Endpoints para historial (si no están):
    - `GET /api/agent/history/` (agentHistory.get)
    - `POST /api/agent/history/` (agentHistory.create)
    - `POST /api/agent/history/messages/` (agentHistory.addMessage)

**`libreria-aurora/src/hooks/`** (opcional, nuevo hook personalizado)
- **Propuesta:** crear un hook `useAgentChat` que centralice la lógica de carga de historial, manejo de estado y persistencia.
- **Beneficio:** reutilizable en otros componentes si se amplía la UI del agente.

## Principios de diseño (responsable, modular, escalable)

### 1. Separación de responsabilidades
- **Backend persiste:** datos validados, con JWT, respetando integridad.
- **Frontend visualiza:** historial persistido, pero también mantiene estado local para UX sin lag.
- **API contrato estable:** no cambia si la UI evoluaciona o se añaden canales.

### 2. Modo guest vs autenticado
- Sin JWT: chat en memoria (localStorage opcional), no hay acceso a `/api/agent/history/`.
- Con JWT: carga historial persistido, puede guardar (si `save_history=true`).
- Transición suave: si usuario inicia sesión mientras chatea en modo guest, su historial local se puede ignorar o fusionar (decisión de negocio futura).

### 3. Resiliencia y manejo de errores
- Si `GET /api/agent/history/` falla (timeout/500): renderizar chat vacío con advertencia y permitir enviar mensajes.
- Si `POST /api/agent/` falla: mostrar error pero no reintentar persistencia automáticamente (user control).
- Si `POST /api/agent/history/messages/` falla (solo si es explícito): mostrar CTA de "Reintentar guardar".

### 4. Paginación futura (extensible sin romper contrato)
- Respuesta de `GET /api/agent/history/` incluye `message_count`.
- Frontend puede usar query params: `?page=1&per_page=10` en futuro.
- Backend lo ignora ahora; lo habilita en Iteración 3 sin cambiar API.

## Tareas concretas para implementar

### Backend (validación y ajustes)
1. Confirmar que `/api/agent/history/` retorna respuesta con estructura correcta.
2. Confirmar que POST `/api/agent/` persiste mensajes cuando `save_history=true`.
3. Tests manuales: GET historial, enviar mensaje, recibir, confirmar persistencia.

### Frontend (implementación nueva)
1. Crear o ampliar `AgentChat.jsx`:
   - Hook `useEffect` para cargar historial al montar.
   - Estado local para mensajes (combina historial + nuevos).
   - Handlers para input y envío de mensajes.

2. Actualizar `AgentDrawer.jsx` para montar `AgentChat`.

3. Crear o actualizar endpoints en `api/config.js`.

4. Tests:
   - Test que al montar con JWT, se carga historial.
   - Test que al enviar un mensaje, se renderiza y se persiste (mock de API).
   - Test que sin JWT, no se carga historial (401 esperado).

## Validaciones de seguridad y privacidad

- **JWT obligatorio:** `/api/agent/history/` retorna 401 si no hay token válido.
- **Truncado de contenido:** respuesta de historial no incluye campos sensibles (por ejemplo, `trace` completo).
- **Rate limiting:** mantener `throttle_scope` en endpoints de historial para evitar abuso de lectura.
- **Logs seguros:** no registrar contenido completo de mensajes en desarrollo.

## Decisiones de diseño (por qué se hacen así)

### ¿Por qué `useEffect` con dependencia `[user, jwt]`?
- Evita llamadas innecesarias si el usuario o token no cambian.
- Si el usuario inicia sesión, se recarga automáticamente.

### ¿Por qué `save_history=true` como flag opcional en POST `/api/agent/`?
- Permite que el frontend controle cuándo guardar (por ejemplo, solo guardar mensajes útiles).
- En futuro, se puede añadir una UI de "No guardar esta conversación" por privacidad.

### ¿Por qué no usar localStorage para historial local?
- Simplifica la Iteración 2: enfoque es cargar historial persistido.
- localStorage se puede añadir en Iteración 3 como mejora de offline.

### ¿Por qué no paginar automáticamente?
- Iteración 2 es MVP: cargar todo el historial es suficiente para la mayoría de usuarios.
- Si el historial crece (100+ mensajes), se puede optimizar en Iteración 3 con paginación.

## Cómo escalar sin romper

### Si se añade paginación (Iteración 3)
- Backend habilita `?page=1&per_page=10` sin cambiar estructura actual.
- Frontend actualiza `useEffect` para manejar paginación.
- API contrato permanece estable.

### Si se añade búsqueda en historial
- Nuevo endpoint: `GET /api/agent/history/search/?q=<texto>`.
- Frontend usa nuevo hook `useHistorySearch`.
- Historial base (`GET /api/agent/history/`) no cambia.

### Si se integra análisis/rating de conversaciones
- Nuevo campo en `AgentConversation`: `rating`, `useful_count`.
- Endpoint para actualizar: `PATCH /api/agent/history/{id}/rating/`.
- Frontend añade UI de stars/thumbs sin afectar chat.

## Resumen de responsabilidades por iteración

| Iteración | Backend | Frontend | Estado |
|-----------|---------|----------|--------|
| 1 (MVP) | Modelos, endpoints CRUD, persistencia desde /api/agent/ | N/A | ✅ Completado |
| 2 (esta) | Validaciones, ajustes de respuesta | Cargar historial, mostrar, continuar conversación | 📋 Por hacer |
| 3 | Paginación, archivado, retención | Paginación UI, "Nueva conversación", historial anterior | Pendiente |
| 4 | Métricas agregadas, dashboard admin | Panel de estadísticas (futuro) | Pendiente |

---

# Implementación actual (Iteración 2): UI con carga de historial y continuación

Esta sección documenta **cómo quedó implementada** la Iteración 2 en el frontend, con enfoque en estructura, responsabilidades y mantenibilidad.

## Objetivo (por qué existe)

- Recuperar historial desde backend cuando hay JWT.
- Mantener un flujo conversacional continuo, sin romper el contrato `message/results/actions`.
- Mantener la UI modular (componentes aislados) y escalable para paginación futura.

## Dónde vive (archivos y responsabilidades)

### 1) UI del chat (principal)

**Archivo:** `libreria-aurora/src/components/agent/AgentChat.jsx`

**Responsabilidades principales:**
- Cargar historial en `useEffect()` cuando existe token.
- Mostrar mensajes previos y nuevos en el mismo estado local.
- Enviar mensajes al endpoint conversacional con `save_history=true` si hay JWT.
- Mostrar estados de error y CTA para usuarios invitados.

**Funciones internas clave (para mantenimiento):**
- `readAuthToken()` → lectura segura del JWT desde `localStorage`.
- `readLlmEnabled()` → toggle de LLM en UI (persistente en `localStorage`).
- `handleSend()` → envío de mensaje a `/api/agent/` y render de respuesta.
- `handleAction()` → envío de acciones mutables a `/api/agent/actions/` (ya existente).

**Flujo real de carga de historial:**
1) Detecta token en `useEffect()`.
2) Llama `GET /api/agent/history/` con `Authorization: Bearer`.
3) Si responde con mensajes, reemplaza el estado local de `messages` con el historial.
4) Si falla, muestra banner de error y permite continuar en modo local.

**Estados UI agregados (responsables):**
- `historyLoading` → indicador de carga de historial.
- `historyError` → error legible si falla la carga.
- `isAuthenticated` → define si se muestra CTA “inicia sesión”.

### 2) Configuración de endpoints

**Archivo:** `libreria-aurora/src/api/config.js`

**Endpoints añadidos para Iteración 2:**
- `agentHistory: "/api/agent/history/"`
- `agentHistoryMessages: "/api/agent/history/messages/"`

**Responsabilidad:** asegurar URLs centralizadas y consistentes para futuras extensiones (paginación, búsqueda).

## Decisiones de diseño (por qué es escalable)

### 1) Carga de historial solo si hay JWT
- Evita llamadas innecesarias y errores 401 visibles al usuario invitado.
- Respeta el principio de privacidad: el historial solo existe para usuarios autenticados.

### 2) Estado local como fuente de UX
- El historial se carga una vez y se mezcla con mensajes nuevos localmente.
- No bloquea el envío si el backend falla (degradación controlada).

### 3) `save_history=true` controlado desde frontend
- La persistencia queda explícita y habilita futuros toggles de privacidad.
- Permite evolucionar a “no guardar esta conversación” sin tocar backend.

## Impacto en mantenimiento

- Los cambios quedaron **aislados** en `AgentChat.jsx` y `config.js`.
- No se modificó el core del agente ni el wiring DRF (cumple separación de capas).
- El diseño permite añadir paginación sin reestructurar la UI actual.

## Puntos de extensión futuros (sin romper lo actual)

- **Paginación:** añadir query params en `GET /api/agent/history/` y manejar estados de carga incremental.
- **Búsqueda en historial:** nuevo endpoint y un hook dedicado (`useHistorySearch`).
- **Indicador de persistencia:** si backend expone `persist_history_confirmation`, se puede renderizar un badge en cada mensaje.
