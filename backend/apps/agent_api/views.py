import time

from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, OpenApiResponse, extend_schema

from agent.agent_handler import handle_agent_action, handle_agent_message
from agent.llm_factory import load_llm_config
from agent.observability import (
    elapsed_ms,
    log_event,
    new_request_id,
    should_sample_trace,
    truncate_text,
)
from agent.retrieval import search_catalog
from agent.vector_store import load_vector_store_config
from django.conf import settings


def _parse_bool(value: object, *, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return default


def _parse_int(value: object, *, default: int, min_value: int = 1, max_value: int = 50) -> int:
    try:
        parsed = int(value)  # type: ignore[arg-type]
    except Exception:
        return default
    if parsed < min_value:
        return min_value
    if parsed > max_value:
        return max_value
    return parsed


class AgentSearchView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "agent_search"

    @extend_schema(
        description=(
            "Busqueda semantica (si vector DB esta disponible) con fallback a ORM. "
            "Devuelve 'degraded=true' cuando se usa el fallback."  # noqa: E501
        ),
        parameters=[
            OpenApiParameter(
                name="q",
                type=OpenApiTypes.STR,
                description="Consulta de texto (requerida)",
                required=True,
            ),
            OpenApiParameter(
                name="k",
                type=OpenApiTypes.INT,
                description="Cantidad de resultados (default: 5)",
                required=False,
            ),
            OpenApiParameter(
                name="prefer_vector",
                type=OpenApiTypes.BOOL,
                description="Si false, fuerza fallback ORM.",
                required=False,
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                examples=[
                    OpenApiExample(
                        "Respuesta 200 (vector)",
                        value={
                            "query": "Cien años de soledad",
                            "k": 5,
                            "source": "vector",
                            "degraded": False,
                            "warnings": [],
                            "results": [
                                {
                                    "id": "libro_123",
                                    "document": "Cien años de soledad...",
                                    "metadata": {"libro_id": 123, "titulo": "Cien años de soledad"},
                                    "distance": 0.12,
                                }
                            ],
                        },
                        response_only=True,
                        status_codes=["200"],
                    ),
                    OpenApiExample(
                        "Respuesta 200 (ORM degradado)",
                        value={
                            "query": "Cien años de soledad",
                            "k": 5,
                            "source": "orm",
                            "degraded": True,
                            "warnings": ["Vector store not available"],
                            "results": [
                                {
                                    "libro_id": 123,
                                    "titulo": "Cien años de soledad",
                                    "autor": "Gabriel García Márquez",
                                    "isbn": "9780307474728",
                                    "precio": "19.99",
                                    "categoria": "Novela",
                                    "stock": 4,
                                    "editorial": "Sudamericana",
                                    "año_publicacion": 1967,
                                    "descripcion": "...",
                                }
                            ],
                        },
                        response_only=True,
                        status_codes=["200"],
                    ),
                ],
            )
        },
    )
    def get(self, request):
        request_id = new_request_id()
        started = time.monotonic()
        q = request.query_params.get("q", "")
        k = request.query_params.get("k", 5)
        prefer_vector_raw = request.query_params.get("prefer_vector", "true")
        prefer_vector = str(prefer_vector_raw).strip().lower() not in {"0", "false", "no"}

        res = search_catalog(q, k=k, prefer_vector=prefer_vector)
        response = Response(
            {
                "query": res.query,
                "k": res.k,
                "source": res.source,
                "degraded": res.degraded,
                "warnings": res.warnings,
                "results": res.results,
            }
        )
        response["X-Request-Id"] = request_id
        log_event(
            "agent.search",
            request_id=request_id,
            duration_ms=elapsed_ms(started),
            query=truncate_text(q),
            k=res.k,
            source=res.source,
            degraded=res.degraded,
            results_count=len(res.results),
            warnings_count=len(res.warnings),
        )
        return response


class AgentChatView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "agent_chat"

    @extend_schema(
        description=(
            "Endpoint conversacional del agente (read-only en esta iteración). "
            "Usa retrieval como fuente de verdad y, opcionalmente, un LLM para redactar el mensaje. "
            "Siempre devuelve un JSON estable con message/results/actions y opcionalmente trace/error."
        ),
        parameters=[
            OpenApiParameter(
                name="X-LLM-API-Key",
                type=OpenApiTypes.STR,
                description=(
                    "API key del usuario para modo BYO (opcional). "
                    "No se persiste y solo se usa para esta llamada si LLM_ALLOW_BYO_KEY=true."
                ),
                required=False,
                location=OpenApiParameter.HEADER,
            )
        ],
        request=OpenApiTypes.OBJECT,
        examples=[
            OpenApiExample(
                "Request ejemplo",
                value={
                    "message": "Busco novelas de realismo mágico",
                    "k": 5,
                    "prefer_vector": True,
                    "use_llm": True,
                    "trace": True,
                },
                request_only=True,
            )
        ],
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                examples=[
                    OpenApiExample(
                        "Respuesta 200",
                        value={
                            "message": "- Encontré 2 resultados.\n- ¿Quieres ver detalles o filtrar por autor?",
                            "results": [
                                {
                                    "libro_id": 123,
                                    "titulo": "Cien años de soledad",
                                    "autor": "Gabriel García Márquez",
                                    "isbn": "9780307474728",
                                    "precio": "19.99",
                                    "categoria": "Novela",
                                    "stock": 4,
                                }
                            ],
                            "actions": [
                                {"type": "view_book", "libro_id": 123},
                                {
                                    "type": "refine_search",
                                    "hint": "Puedes pedirme filtrar por autor, ISBN o categoría.",
                                },
                            ],
                            "trace": {
                                "query": "novelas de realismo mágico",
                                "k": 5,
                                "source": "orm",
                                "degraded": True,
                                "warnings": ["Vector store not available"],
                                "llm": {"provider": "stub", "model": "stub", "latency_ms": 3, "error": None},
                            },
                        },
                        response_only=True,
                        status_codes=["200"],
                    )
                ],
            ),
            400: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                examples=[
                    OpenApiExample(
                        "Respuesta 400 (request invalido)",
                        value={
                            "message": "Mensaje vacío. Escribe qué libro buscas.",
                            "results": [],
                            "actions": [],
                            "error": "invalid_request",
                        },
                        response_only=True,
                        status_codes=["400"],
                    )
                ],
            ),
        },
    )
    def post(self, request):
        request_id = new_request_id()
        started = time.monotonic()
        data = request.data or {}
        message_raw = data.get("message")
        message = message_raw if isinstance(message_raw, str) else None

        k_int = _parse_int(data.get("k", 5), default=5)
        prefer_vector = _parse_bool(data.get("prefer_vector", True), default=True)
        trace = _parse_bool(data.get("trace", False), default=False)
        use_llm = _parse_bool(data.get("use_llm", True), default=True)

        byo_api_key = request.headers.get("X-LLM-API-Key")
        if byo_api_key and not request.user.is_authenticated:
            return Response(
                {
                    "error": "auth_required",
                    "message": "Necesitas iniciar sesión para usar tu API key.",
                    "results": [],
                    "actions": [],
                },
                status=401,
            )

        resp = handle_agent_message(
            message,
            k=k_int,
            prefer_vector=bool(prefer_vector),
            use_llm=bool(use_llm),
            include_trace=bool(trace),
            byo_api_key=byo_api_key,
            request_id=request_id,
        )

        status_code = 400 if resp.error else 200
        payload = resp.to_dict()
        sampled = should_sample_trace()
        if trace and sampled and payload.get("trace") is None:
            payload["trace"] = {"request_id": request_id}

        response = Response(payload, status=status_code)
        response["X-Request-Id"] = request_id

        trace_payload = payload.get("trace") if isinstance(payload, dict) else None
        log_event(
            "agent.chat",
            request_id=request_id,
            duration_ms=elapsed_ms(started),
            message=truncate_text(message_raw),
            k=k_int,
            prefer_vector=bool(prefer_vector),
            status=status_code,
            error=payload.get("error") if isinstance(payload, dict) else None,
            degraded=(trace_payload or {}).get("degraded") if trace_payload else None,
            source=(trace_payload or {}).get("source") if trace_payload else None,
            results_count=len(payload.get("results", [])) if isinstance(payload, dict) else 0,
            warnings_count=len((trace_payload or {}).get("warnings", [])) if trace_payload else None,
            sampled_trace=sampled,
        )
        return response


class AgentStatusView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "agent_chat"

    @extend_schema(
        description=(
            "Estado operativo del agente (solo lectura). "
            "Expone configuración no sensible de LLM, vector DB, tools y límites."
        ),
        responses={
            200: OpenApiResponse(response=OpenApiTypes.OBJECT),
        },
    )
    def get(self, request):
        llm_cfg = load_llm_config()
        provider = llm_cfg.provider.strip().lower()
        is_stub = provider in {"stub", "local_stub", "test"}
        has_server_key = bool(llm_cfg.api_key)
        byo_allowed = bool(llm_cfg.allow_byo_key)

        if llm_cfg.cost_mode == "byo_key":
            llm_available = False
            llm_mode = "byo_key"
            requires_byo_key = True
        elif llm_cfg.cost_mode == "paid":
            llm_available = has_server_key and not is_stub
            llm_mode = "paid"
            requires_byo_key = False
        else:
            llm_available = (has_server_key or byo_allowed) and not is_stub
            llm_mode = "hybrid"
            requires_byo_key = False

        vector_cfg = load_vector_store_config()
        vector_db_dir = str(vector_cfg.db_dir)
        vector_manifest = str(vector_cfg.manifest_path) if vector_cfg.manifest_path else None
        vector_ready = vector_cfg.db_dir.exists() and bool(vector_cfg.embedding_model)

        throttle_rates = (getattr(settings, "REST_FRAMEWORK", {}) or {}).get(
            "DEFAULT_THROTTLE_RATES", {}
        )

        payload = {
            "llm": {
                "provider": llm_cfg.provider,
                "model": llm_cfg.model,
                "base_url": llm_cfg.base_url,
                "available": llm_available,
                "mode": llm_mode,
                "requires_byo_key": requires_byo_key,
                "byo_key_allowed": byo_allowed,
                "server_key_configured": has_server_key,
                "timeout_sec": llm_cfg.timeout_sec,
                "max_tokens": llm_cfg.max_tokens,
                "cost_mode": llm_cfg.cost_mode,
            },
            "retrieval": {
                "prefer_vector_default": True,
                "vector_ready": vector_ready,
                "vector_db_dir": vector_db_dir,
                "vector_manifest": vector_manifest,
                "collection": vector_cfg.collection,
                "embedding_model": vector_cfg.embedding_model,
                "normalize_embeddings": vector_cfg.normalize_embeddings,
            },
            "tools": {
                "read_only": [
                    "search_catalog",
                    "lookup_book",
                    "filter_catalog",
                    "recommend_similar",
                ],
                "actions": ["add_to_cart", "reserve_book", "order_status"],
                "actions_requires_auth": True,
            },
            "limits": {
                "rate_limits": throttle_rates,
            },
        }

        return Response(payload, status=200)


class AgentActionView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "agent_action"

    @extend_schema(
        description=(
            "Endpoint de acciones mutables del agente (requiere JWT). "
            "Acciones soportadas: add_to_cart, reserve_book, order_status. "
            "Devuelve el contrato estable message/results/actions y opcionalmente trace/error."
        ),
        request=OpenApiTypes.OBJECT,
        examples=[
            OpenApiExample(
                "Request add_to_cart",
                value={"action": "add_to_cart", "payload": {"book_id": 123, "cantidad": 1}, "trace": False},
                request_only=True,
            ),
            OpenApiExample(
                "Request reserve_book",
                value={"action": "reserve_book", "payload": {"book_id": 123, "cantidad": 1}},
                request_only=True,
            ),
            OpenApiExample(
                "Request order_status",
                value={"action": "order_status", "payload": {"order_id": 456}},
                request_only=True,
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                examples=[
                    OpenApiExample(
                        "Respuesta 200",
                        value={
                            "message": "Libro agregado al carrito.",
                            "results": [
                                {
                                    "carrito_id": 1,
                                    "libro": {"libro_id": 123, "titulo": "Ejemplo"},
                                    "cantidad": 1,
                                }
                            ],
                            "actions": [
                                {
                                    "type": "action_result",
                                    "action": "add_to_cart",
                                    "ok": True,
                                    "error": None,
                                }
                            ],
                        },
                        response_only=True,
                        status_codes=["200"],
                    )
                ],
            ),
            400: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                examples=[
                    OpenApiExample(
                        "Respuesta 400 (acción inválida)",
                        value={
                            "message": "Acción inválida. Usa: add_to_cart, reserve_book u order_status.",
                            "results": [],
                            "actions": [],
                            "error": "invalid_action",
                        },
                        response_only=True,
                        status_codes=["400"],
                    )
                ],
            ),
        },
    )
    def post(self, request):
        request_id = new_request_id()
        started = time.monotonic()
        data = request.data or {}
        action = data.get("action")
        payload = data.get("payload") if isinstance(data.get("payload"), dict) else {}
        trace = _parse_bool(data.get("trace", False), default=False)

        resp = handle_agent_action(
            action if isinstance(action, str) else None,
            payload,
            user_id=request.user.id,
            include_trace=bool(trace),
            request_id=request_id,
        )

        status_code = 400 if resp.error else 200
        payload_out = resp.to_dict()
        sampled = should_sample_trace()
        if trace and sampled and payload_out.get("trace") is None:
            payload_out["trace"] = {"request_id": request_id}

        response = Response(payload_out, status=status_code)
        response["X-Request-Id"] = request_id

        trace_payload = payload_out.get("trace") if isinstance(payload_out, dict) else None
        log_event(
            "agent.action",
            request_id=request_id,
            duration_ms=elapsed_ms(started),
            action=truncate_text(action),
            status=status_code,
            error=payload_out.get("error") if isinstance(payload_out, dict) else None,
            ok=(trace_payload or {}).get("ok") if trace_payload else None,
            sampled_trace=sampled,
        )
        return response
