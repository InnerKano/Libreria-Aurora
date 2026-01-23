## Objetivo
- Diseñar y planear un **agente LLM** para la librería que asista en búsqueda, recomendaciones y acciones guiadas (carrito/reservas) sin romper los contratos actuales del backend/ frontend.
- Asegurar reproducibilidad, límites claros (sin alucinaciones sobre inventario/precios) y una ruta de entrega incremental.

## Alcance inicial
- Flujo conversacional que cubra: búsqueda de libros por texto libre, sugerencias basadas en catálogo y estado de usuario (opcional), guía para agregar al carrito/reservar, estado de pedidos/reservas.
- No incluye cambios profundos de UI: se expondrá primero como endpoint API; la UI puede consumirlo como chat lateral.
- Sin escritura directa en BD por el LLM: las acciones mutables se exponen como tools con validaciones.

## Supuestos y restricciones
- Backend Django activo con auth JWT y catálogo consistente.
- Se podrá usar un proveedor LLM vía API (definir en `.env`: `LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_KEY`).
- El índice vectorial se construirá offline con Chroma y se cargará en runtime desde disco (`./vector_db`).
- No se expondrán llaves ni secretos al frontend.

## Estrategia de LLM (alineada al playbook)
- **LLM factory** (patrón de [agentic_llm_knowledge](docs/reference_docs/agentic_llm_knowledge.md)): una sola capa que instancia el modelo según env vars, con timeouts y retries centralizados, y permite inyectar un stub en tests.
- **Proveedores**: soportar `openai`/`azure`/`compatible` (LM Studio/Ollama/vLLM) vía `LLM_PROVIDER`, `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY`.
- **Costos**: modelo barato por defecto (gpt-4o-mini/claude-haiku/deepseek-mini), caché de respuestas frecuentes, rate limiting y cuotas por usuario.
- **BYO key opcional**: modo donde el usuario entrega su API key en la request; no se persiste, se usa solo en memoria para esa llamada (requiere login y validación). Si no hay key y el modo es paid, usar la key del servidor.
- **Fallas y fallback**: si el LLM no responde o se queda sin cuota, responder en modo degradado (búsqueda exacta + mensaje) y registrar el evento.
- **Regla de ubicación**: todo el feature del agente (código, scripts, vector_db, manifests) vive bajo `backend/agent/` para centralizar mantenibilidad.

## Artefactos existentes reutilizables
- Playbook técnico de agentes: [docs/reference_docs/agentic_llm_knowledge.md](docs/reference_docs/agentic_llm_knowledge.md).
- Notebook para construir `vector_db` en Colab (fase 2): [docs/reference_docs/colab_vector_db.ipynb](docs/reference_docs/colab_vector_db.ipynb).
- Esquema funcional y dominios en backend (apps `libros`, `busqueda`, `compras`, `finanzas`, `usuarios`, etc.).

## Caso de uso prioritario
- “Asistente de catálogo”: entiende consultas libres, recupera libros relevantes, presenta 3–5 resultados con metadatos clave, ofrece opciones de acción (ver detalle, agregar al carrito, reservar, marcar favoritos en futuro).
- Secundario (fase 2): “Estado de pedido/reserva” y “recomendaciones basadas en historial”.

## Checklist de readiness (antes de construir)
- Dataset del catálogo limpio y exportable desde backend (fixture o query estable).
- Script de build de vector DB definido y reproducible (ver notebook de Colab adaptado a local/CI).
- Decisión de modelo de embeddings (ej. `mixedbread-ai/mxbai-embed-large-v1`) y normalización consistente.
- Variables de entorno preparadas: `LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_KEY`, `VECTOR_DB_DIR`, `VECTOR_COLLECTION`.
- Estrategia de pruebas: unit (parsers, formateo), integración (tools + mocks), smoke E2E con LLM stub.

## Plan por fases

### Decisiones de ubicación y contratos (añadidos)
- Ubicación del agente:
	- Core reusable (código/tools/vector helpers): `backend/agent/`
	- Integración Django/DRF (wiring): `backend/apps/agent_api/` (nombre elegido para evitar colisión con el paquete core `backend/agent`)
- Tests del feature:
	- Unit (core, sin HTTP): `backend/agent/tests/`
	- Integración (API/wiring): `backend/apps/agent_api/tests/`
- Documento guía de estructura (qué va en cada carpeta): `docs/agent_llm_docs/agent_llm_structure.md`.
- Regla obligatoria: artefactos y scripts del agente se concentran en `backend/agent/` (incluye `vector_db/`, manifests, scripts de build y helpers).
- Contrato de respuesta (salida del endpoint): objeto JSON con campos obligatorios `message: str`, `results: list[dict]`, `actions: list[dict]`, `trace: list|dict (opcional para debugging)`, `error: str (opcional, mutuamente excluyente con results útiles)`. Documentar en drf-spectacular.
- Manifest de embeddings: registrar en `vector_db/manifest.json` el modelo, normalización (cosine), fecha de build, tamaño de la colección, campos embeddeados y hash del dataset.
- Fallback de datos: si `vector_db` falla, usar búsqueda exacta por ORM y responder indicando modo degradado.
- Tools mutables requieren JWT válido; si falta, responder con error estructurado `{ "error": "auth_required", "message": "Necesitas iniciar sesión" }`.
- LLM factory: interfaz única `.invoke()` configurable por env; admite proveedor externo o endpoint local compatible. Permite inyectar stub en tests.
- Registro vivo del feature: documentar avances/decisiones en `docs/agent_llm_docs/agent_llm_status.md`.

### Fase 0 — Descubrimiento y contratos
- Definir 8–10 escenarios con inputs/outputs esperados (búsqueda libre, filtros, “no encontré”, inventario agotado, pedido inexistente).
- Establecer “fuentes de verdad”: catálogo y stock en BD; nunca inventar precios/IDs.
- Contrato de salida para el agente: estructura JSON con campos `message`, `results`, `actions` (link a front), `trace` para debugging.

### Fase 1 — Datos y vector DB
- Preparar corpus RAG:
	- Documento: nombre, autor, categoría, sinopsis corta, precio, disponibilidad, `libro_id`.
	- Metadata para filtros: categoría, idioma, disponibilidad, precio.
- Adaptar el notebook [docs/reference_docs/colab_vector_db.ipynb](docs/reference_docs/colab_vector_db.ipynb) a un script reproducible local `backend/apps/libros/scripts/build_vector_db.py`:
	- Adaptar el notebook [docs/reference_docs/colab_vector_db.ipynb](docs/reference_docs/colab_vector_db.ipynb) a un notebook reproducible local **centralizado** en `backend/agent/notebooks/build_vector_db.ipynb`:
	- Entrada: CSV/JSON exportado del catálogo.
	- Salida: carpeta `vector_db/` versionada (manifest con modelo, fecha, count).
	- Smoke test: `similarity_search("Cien años de soledad")` devuelve hits plausibles.
- Publicar artefacto en repo (si tamaño lo permite) o ZIP versionado en releases internas.
- Fase 1B — Notebook/artefacto reproducible: mantener notebook como referencia y asegurar que el script CLI emule sus pasos (descarga/validación de datos, build, smoke test, export ZIP). Documentar parámetros y outputs en el manifest.

### Fase 2 — Capa de retrieval estable (sin LLM)
- Implementar helper de carga/cache del vector store (Chroma) en backend (ej. módulo `apps/busqueda/vector_store.py`).
- API determinística `search_catalog(query: str, k: int = 5) -> list[dict]` con manejo de vacío y errores estructurados.
- Structured search de respaldo usando ORM/SQL para filtros exactos (categoría, precio, disponibilidad) y para validaciones de inventario.
- Tests de integración que mockean el store y smoke tests reales con `vector_db` local.
- Exponer modo degradado: si el store no carga, retorna resultado vacío y un flag `degraded=true` para que el agente responda sin LLM o con mensaje controlado.

### Fase 3 — Diseño del agente y tools
- Framework sugerido: LangGraph/LangChain con control explícito de estado y herramientas; en su defecto, orquestación manual con prompts + funciones Python.
- Tools mínimas:
	1) `tool_search_catalog(query, k)` → usa retrieval.
	2) `tool_lookup_book(book_id)` → usa ORM para datos exactos.
	3) `tool_add_to_cart(user_id, book_id, qty)` → valida stock y usa lógica de `compras`.
	4) `tool_reservation(user_id, book_id)` → valida reglas de reservas.
	5) `tool_order_status(user_id, order_id)` → devuelve estado.
- Tools adicionales recomendados (extensibles por fases):
	6) `tool_filter_catalog(filters)` → filtros exactos por categoría/precio/disponibilidad con ORM; complementa el retrieval semántico.
	7) `tool_recommend_similar(book_id)` → nearest-neighbors por embeddings para “parecidos a…”.
	8) `tool_user_history(user_id)` → solo lectura de compras/búsquedas recientes para personalizar respuestas.
	9) `tool_hold_stock(user_id, book_id, qty)` (opcional) → reserva temporal corta antes de pagar, si negocio lo permite.
	10) `tool_list_promos()` / `tool_shipping_eta(zipcode)` (si aplica) → reduce alucinaciones en FAQs.
	11) `tool_escalate_to_human(message)` → registra ticket en `mensajeria` cuando el agente no pueda resolver.
- Política de decisiones:
	- El LLM nunca construye SQL ni toca la BD directa; solo llama tools.
	- Acciones mutables requieren `user_id` autenticado; si falta, responder con requerimiento de login.
	- Límites de tokens/respuestas para evitar derrapes; incluir trazas de tool-calls en logs.
	- El asistente debe usar retrieval primero; si retrieval falla, informar modo degradado y evitar alucinaciones.
- Fase 3B — LLM factory: implementar módulo `backend/agent/llm_factory.py` (ya creado) y exponerlo vía wiring en `backend/apps/agent_api/` cuando se haga el endpoint conversacional. Tests unitarios para fallback de configuración y selección de provider.

### Fase 4 — Prompts y guardrails
- Prompt base con: rol del asistente, dominios soportados, cosas que no debe inventar (precios/IDs), formato de respuesta JSON para el frontend.
- Few-shots con escenarios típicos + edge cases (“no hay stock”, “libro no encontrado”).
- Guardrails: longitud máxima, lista blanca de acciones, manejo de errores estructurados (`{"error": "..."}`).
- Incluir instrucciones de costos/limitaciones: preferir respuestas concisas, evitar llamados innecesarios a tools, y pedir confirmación antes de acciones mutables.

### Fase 5 — API y wiring
- Exponer endpoint `/api/agent/` (POST) que reciba `message`, `context` (user_id opcional) y devuelva la respuesta estructurada.
- Middleware de autenticación JWT para habilitar tools mutables.
- Logging y trazas: guardar `conversation_id`, prompts truncados, tool invocations y latencias.
- Rate limiting básico por usuario/IP para evitar abuso.
- LLM factory inyectada en el handler: selecciona modelo según env y, opcionalmente, permite BYO key en cabecera segura (no se persiste).
- Config flags en `.env`: `LLM_TIMEOUT_SEC`, `LLM_MAX_TOKENS`, `LLM_COST_MODE` (`paid|byo_key|hybrid`).
- Fase 5B — Registro y documentación: actualizar `agent_llm_status.md` tras cada entrega parcial (retrieval-only, tools mutables, etc.) y publicar contrato en drf-spectacular.

### Fase 6 — Evaluación y tests
- Unit: formateo de prompts, parser de resultados, validación de schemas.
- Integración: tools con mocks de LLM; simulación de conversaciones con golden outputs.
- E2E limitado: 3–5 diálogos en staging con modelo barato; capturar métricas de relevancia y tasa de errores.
- Métricas mínimas: coverage de tools llamados, éxito en “agregar al carrito”, precisión@k de retrieval en un set de queries de prueba.
- Golden set: mantener 3–5 conversaciones “doradas” para regresión (ej. búsqueda con sinónimos, sin stock, auth faltante, recomendación similar, fallo de vector DB con fallback ORM).
- Smoke test automatizado de `vector_db` (carga + query) en CI si es viable.

### Fase 7 — Observabilidad y operación
- Dashboards de latencia y tasa de errores por tool/LLM.
- Alertas por timeouts de LLM y por fallos de carga del vector DB.
- Modo degradado: si el vector DB falla, responder con búsqueda exacta + mensaje de fallback.
- Rotación de llaves y cambio de modelo via configuración sin despliegue (variables en `.env`).
- Logging seguro: enmascarar datos sensibles y truncar prompts en trazas.
- Timeouts y reintentos: fijar timeouts cortos para LLM y cada tool; reintentos limitados solo en operaciones idempotentes.
- Métricas de costos: contar tokens o llamadas por usuario/sesión para monitorear gasto y activar cuotas.

### Fase 8 — Entrega incremental (roadmap)
- Iteración 1: retrieval-only API con respuestas estructuradas (sin acciones mutables) para pruebas internas.
- Iteración 2: habilitar tools de carrito/reservas con usuarios autenticados.
- Iteración 3: recomendaciones personalizadas (usar historial de compras/búsqueda) y resumen de pedidos.
- Iteración 4: hardening (rate-limit, trazas completas, panel de monitoreo) y preparación para producción.

---

## Anexo: análisis de UI para el feature Agente LLM

### Objetivo de UI
- Exponer el asistente sin romper la experiencia actual.
- Unificar búsqueda, resultados y acciones mutables en un flujo **intuitivo** y **responsable**.
- Respetar la arquitectura actual: React + componentes existentes + API REST.

### Principios de diseño (responsable, modular, escalable)
- **Contrato estable**: la UI debe consumir `message/results/actions` sin asumir proveedor LLM.
- **Fuente de verdad**: inventario/precio/stock siempre proviene de `results` del backend.
- **Acciones explícitas**: acciones mutables (carrito/reserva/estado) requieren JWT y confirmación visual.
- **Degradación controlada**: si el agente cae a modo degradado, la UI informa sin romper el flujo.

### Mapeo UI ↔ Backend (fases)

#### Iteración 1 (read-only)
- Endpoint: `POST /api/agent/`
- UI: chat lateral o sección dentro de `SearchBook`/`catalogo`.
- Uso: mostrar `message` + lista de `results` con cards reutilizables.

#### Iteración 2 (acciones mutables)
- Endpoint: `POST /api/agent/actions/` (JWT)
- UI: botones de acción por resultado (Agregar al carrito / Reservar / Ver estado).
- Confirmaciones y feedback: modal/inline con respuesta de `actions`.

#### Iteración 3+ (personalización)
- Integrar “recomendaciones” y “estado de pedidos” como acciones sugeridas.

### Componentes sugeridos (sin romper estructura actual)
- Reutilizar cards de libros existentes:
	- `libreria-aurora/src/components/book/bookCard.jsx`
- Agregar un contenedor de chat modular:
	- `libreria-aurora/src/components/agent/AgentChat.jsx` (nuevo)
- Agregar una barra lateral opcional:
	- `libreria-aurora/src/components/agent/AgentDrawer.jsx` (nuevo)

### Flujo UI recomendado (intuitivo)
1) Usuario escribe en el chat o busca.
2) UI envía a `/api/agent/`.
3) UI renderiza `message` + `results` con cards.
4) Si el usuario está autenticado, se muestran acciones (carrito/reserva/estado).
5) La acción dispara `/api/agent/actions/` y muestra feedback de éxito/error.

### Manejo de autenticación (responsable)
- Si no hay JWT: las acciones mutables se deshabilitan y muestran CTA “Inicia sesión”.
- La UI no guarda ni expone claves LLM.

### Errores y trazas (mantenibilidad)
- Mostrar errores de forma legible (`error` del backend).
- Si `trace=true` está habilitado en desarrollo, mostrar un panel dev opcional.

### Entregables UI mínimos por fase
- Iteración 1: chat + resultados reutilizando cards existentes.
- Iteración 2: botones de acción con confirmación y feedback.
- Iteración 3: historial y recomendaciones contextualizadas.

### Riesgos UI y mitigación
- **Acoplamiento al LLM** → consumir solo contrato estable.
- **Acciones sin auth** → deshabilitar UI y mostrar CTA.
- **Resultados vacíos** → fallback a recomendaciones de búsqueda o filtros.

## Riesgos y mitigaciones
- **Alucinaciones sobre inventario/precio** → siempre validar contra BD via tools; no confiar en texto del LLM.
- **Inconsistencia embeddings vs query** → fijar modelo y normalización en manifest; tests de smoke tras cada rebuild.
- **Costos/latencia del LLM** → modelo eficiente por defecto, cache de respuestas para FAQs, timeouts cortos.
- **Seguridad** → auth obligatoria para acciones mutables, sanitizar entradas, no exponer trazas internas al frontend.

