# Estado del feature Agente LLM

## Preparativos completados (pre Fase 0)
- Definidas variables en backend/.env.example para LLM (provider, modelo, base_url, api_key, timeouts, modos de costo, BYO key) y Vector DB (dir, colección, manifest).
- Default de desarrollo: `LLM_PROVIDER=openai_compatible`, `LLM_MODEL=llama-3-8b-instruct`, pensado para endpoint local compatible.
- Dataset base: fixtures existentes `backend/apps/libros/fixtures/libros_prueba.json` como fuente inicial para build de Chroma.
- Regla de ubicación: todo el feature del agente se centraliza en `backend/agent/` (código, scripts, vector_db, manifests). Se crearán helper(s) y orquestación en `backend/agent/` y, si se requiere app Django, `backend/apps/agent/` sólo para integrar con DRF/URLs.
- Contrato de respuesta definido en plan: campos `message`, `results[]`, `actions[]`, `trace`, `error`.

## Pendientes inmediatos
- Crear manifiesto inicial para embeddings (`vector_db/manifest.json`) cuando se genere el primer índice.
- Implementar script `backend/apps/libros/scripts/build_vector_db.py` (adaptado del notebook) y smoke test de retrieval.
- Implementar `backend/apps/agent/llm_factory.py` con selección por env, timeouts, BYO key opcional y stub para tests.
- Documentar el contrato en drf-spectacular y habilitar endpoint `/api/agent/` (mock de LLM para E2E básico).

## Notas de operación
- Si falla el vector DB, responder en modo degradado (búsqueda exacta + flag `degraded=true`).
- Si falla el LLM o no hay cuota, usar el mismo modo degradado y registrar el evento.
- BYO key: deshabilitado por defecto (`LLM_ALLOW_BYO_KEY=false`); habilitar sólo si se desea trasladar costo al usuario.

## Próximos hitos
1) Generar y versionar el primer `vector_db` + manifest.
2) Añadir helper de `vector_store` y API de retrieval determinística.
3) Integrar LLM factory y endpoint `/api/agent/` con stub para pruebas.
