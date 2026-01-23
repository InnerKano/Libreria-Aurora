from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, OpenApiResponse, extend_schema

from agent.agent_handler import handle_agent_message
from agent.retrieval import search_catalog


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
        q = request.query_params.get("q", "")
        k = request.query_params.get("k", 5)
        prefer_vector_raw = request.query_params.get("prefer_vector", "true")
        prefer_vector = str(prefer_vector_raw).strip().lower() not in {"0", "false", "no"}

        res = search_catalog(q, k=k, prefer_vector=prefer_vector)
        return Response(
            {
                "query": res.query,
                "k": res.k,
                "source": res.source,
                "degraded": res.degraded,
                "warnings": res.warnings,
                "results": res.results,
            }
        )


class AgentChatView(APIView):
    permission_classes = [AllowAny]

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
        data = request.data or {}
        message_raw = data.get("message")
        message = message_raw if isinstance(message_raw, str) else None

        k_int = _parse_int(data.get("k", 5), default=5)
        prefer_vector = _parse_bool(data.get("prefer_vector", True), default=True)
        trace = _parse_bool(data.get("trace", False), default=False)

        byo_api_key = request.headers.get("X-LLM-API-Key")

        resp = handle_agent_message(
            message,
            k=k_int,
            prefer_vector=bool(prefer_vector),
            include_trace=bool(trace),
            byo_api_key=byo_api_key,
        )

        status_code = 400 if resp.error else 200
        return Response(resp.to_dict(), status=status_code)
