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
