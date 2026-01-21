from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema

from agent.agent_handler import handle_agent_message
from agent.retrieval import search_catalog


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
        responses={200: OpenApiTypes.OBJECT},
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
        request=OpenApiTypes.OBJECT,
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
    )
    def post(self, request):
        data = request.data or {}
        message = data.get("message")

        k = data.get("k", 5)
        prefer_vector = data.get("prefer_vector", True)
        trace = data.get("trace", False)

        # Normalize bool-ish values from JSON or strings.
        if isinstance(prefer_vector, str):
            prefer_vector = prefer_vector.strip().lower() not in {"0", "false", "no"}
        if isinstance(trace, str):
            trace = trace.strip().lower() in {"1", "true", "yes"}

        try:
            k_int = int(k)
        except Exception:
            k_int = 5

        resp = handle_agent_message(
            message,
            k=k_int,
            prefer_vector=bool(prefer_vector),
            include_trace=bool(trace),
        )

        status_code = 400 if resp.error else 200
        return Response(resp.to_dict(), status=status_code)
