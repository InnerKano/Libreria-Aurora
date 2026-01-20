# Estado del feature Agente LLM

## Preparativos completados (pre Fase 0)
- Definidas variables en backend/.env.example para LLM (provider, modelo, base_url, api_key, timeouts, modos de costo, BYO key) y Vector DB (dir, colección, manifest).
- Default de desarrollo: `LLM_PROVIDER=openai_compatible`, `LLM_MODEL=llama-3-8b-instruct`, pensado para endpoint local compatible.
- Dataset base: fixtures existentes `backend/apps/libros/fixtures/libros_prueba.json` como fuente inicial para build de Chroma.
- Regla de ubicación: todo el feature del agente se centraliza en `backend/agent/` (código, scripts, vector_db, manifests). Se crearán helper(s) y orquestación en `backend/agent/` y, si se requiere app Django, `backend/apps/agent/` sólo para integrar con DRF/URLs.
- Contrato de respuesta definido en plan: campos `message`, `results[]`, `actions[]`, `trace`, `error`.

## Pendientes inmediatos
- [COMPLETADO] Vector DB + manifest generados con notebook (Colab/local):
	- Notebook: `backend/agent/notebooks/build_vector_db.ipynb`
	- Artefacto: `backend/agent/vector_db/` (incluye `chroma.sqlite3` + segmentos)
	- Manifest: `backend/agent/vector_db/manifest.json`
	- Export: `backend/agent/vector_db.zip` (incluye la carpeta `vector_db/` con el manifest dentro)
- [COMPLETADO] Implementar `backend/agent/llm_factory.py` con selección por env, timeouts, BYO key opcional y stub para tests.
- Documentar el contrato en drf-spectacular y habilitar endpoint `/api/agent/` (mock de LLM para E2E básico).

## Actualización: `llm_factory` (responsable, modular, escalable)

### Objetivo (por qué existe)
- Desacoplar el resto del sistema de cualquier proveedor específico de LLM.
- Centralizar configuración y políticas (timeouts, tokens, costo/BYO, fallbacks) en un solo lugar.
- Habilitar desarrollo y pruebas **sin red** mediante un stub determinista.

### Ubicación y responsabilidad
- Código: `backend/agent/llm_factory.py`.
- Contrato: expone una única función de entrada `build_llm_runnable(...)` que devuelve un objeto con `.invoke()` / `.ainvoke()`.
- Regla: el resto del backend (views/tools/grafo) **no** debe instanciar clientes directamente; siempre debe pedir un runnable a la factory.

### Interfaz estable (lo que el resto del sistema usa)
- `build_llm_runnable(byo_api_key: str | None)`
	- Retorna `StubLLM` o `OpenAICompatibleLLM` según config.
	- `.invoke(prompt)` retorna un dict estable con:
		- `content`, `provider`, `model`, `latency_ms`
		- `prompt_tokens`/`completion_tokens` (si el proveedor los entrega)
		- `error` (siempre presente; `None` en éxito)

### Configuración por entorno (`backend/.env`)
Variables ya definidas en `backend/.env.example`:
- `LLM_PROVIDER`:
	- `stub|local_stub|test` => fuerza stub (sin red).
	- `openai_compatible` => usa un endpoint OpenAI-compatible (OpenAI / LM Studio / vLLM / Ollama compatible).
- `LLM_MODEL`: nombre del modelo.
- `LLM_BASE_URL`: base URL del server compatible (opcional; útil en local).
- `LLM_API_KEY`: key del servidor (modo paid/hybrid).
- `LLM_TIMEOUT_SEC`: timeout en segundos.
- `LLM_MAX_TOKENS`: máximo de tokens de salida.
- `LLM_COST_MODE`: `paid|byo_key|hybrid`.
- `LLM_ALLOW_BYO_KEY`: `true|false`.

### Política de costos y BYO key (responsabilidad y seguridad)
- `paid`: usa `LLM_API_KEY` del servidor. Si falta, **no crashea**: cae a stub y registra warning.
- `byo_key`: requiere key del usuario. Si falta, lanza `ImproperlyConfigured` (error de configuración/uso).
- `hybrid`: prioriza key de usuario **solo** si `LLM_ALLOW_BYO_KEY=true`; si no hay, usa key del servidor; si ninguna existe, cae a stub.

Buenas prácticas (para mantenimiento):
- La BYO key no se persiste: debe recibirse por request (header) y pasarse solo a `build_llm_runnable(...)`.
- No loguear keys ni headers crudos.
- En producción, `LLM_ALLOW_BYO_KEY` debería ser `false` salvo que el caso de negocio lo requiera.

### Dependencias
- La ruta `openai_compatible` usa el paquete `openai` (client oficial). Si no está instalado, la factory falla con mensaje claro.
- Tests no requieren red y pueden usar un cliente fake (patch de `openai`).

### Tests (primeros del proyecto)
- Tests agregados: `backend/agent/tests/test_llm_factory.py`.
- Casos cubiertos:
	- Provider `stub` retorna `StubLLM`.
	- Modo `paid` sin key cae a `StubLLM` (degradación controlada).
	- Modo `byo_key` sin key lanza error.
	- Modo `openai_compatible` se prueba con cliente fake (sin red).

Cómo correrlos (local):
- Desde `backend/`: `pytest -q agent/tests/test_llm_factory.py`

### Extensibilidad (cómo escalar sin reescribir)
- Para añadir proveedores nuevos:
	1) Crear una clase nueva con `.invoke()` / `.ainvoke()`.
	2) Extender el switch de `LLM_PROVIDER` en `build_llm_runnable`.
	3) Añadir tests de selección y fallback.
- Para añadir features operativas (retries/backoff, tracing): implementar dentro de la factory (o wrapper) sin tocar tools/grafo.

### Troubleshooting rápido
- Siempre usa stub: revisa `LLM_PROVIDER` y si `LLM_API_KEY` está vacía (modo `paid/hybrid`).
- Error “Falta la dependencia 'openai'”: instala `openai>=1.30.0`.
- Pylance marca imports no resueltos pero pytest funciona: el intérprete de VS Code no está apuntando al `backend/venv`.

## Cómo reproducir el build (resumen)
- Local: correr el notebook y dejar `DO_CLONE_REPO=False`, `DO_INSTALL_DEPS=False` (si tu venv ya está listo).
- Colab: setear `DO_CLONE_REPO=True` + `DO_INSTALL_DEPS=True`, correr todo, y descargar `backend/agent/vector_db.zip`.
- Dataset alternativo: usar `VECTOR_DATASET_PATH` para apuntar a un JSON genérico (lista con `text`/`page_content` + opcional `id`/`metadata`).

## Notas de operación
- Si falla el vector DB, responder en modo degradado (búsqueda exacta + flag `degraded=true`).
- Si falla el LLM o no hay cuota, usar el mismo modo degradado y registrar el evento.
- BYO key: deshabilitado por defecto (`LLM_ALLOW_BYO_KEY=false`); habilitar sólo si se desea trasladar costo al usuario.

## Próximos hitos
1) Generar y versionar el primer `vector_db` + manifest.
2) Añadir helper de `vector_store` y API de retrieval determinística.
3) Integrar LLM factory y endpoint `/api/agent/` con stub para pruebas.
