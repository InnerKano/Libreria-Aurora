from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import AgentConversationSerializer, AgentMessageSerializer
from .services import archive_active_conversations, get_or_create_active_conversation, record_message


def _build_history_payload(conversation):
    messages = conversation.messages.all().order_by("created_at")
    return {
        "conversation": AgentConversationSerializer(conversation).data,
        "messages": AgentMessageSerializer(messages, many=True).data,
    }


class AgentHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        conversation = get_or_create_active_conversation(request.user)
        return Response(_build_history_payload(conversation), status=200)

    def post(self, request):
        conversation = get_or_create_active_conversation(request.user)
        return Response(_build_history_payload(conversation), status=201)

    def delete(self, request):
        archive_active_conversations(request.user)
        conversation = get_or_create_active_conversation(request.user)
        return Response(_build_history_payload(conversation), status=200)


class AgentHistoryMessageView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data or {}
        role = data.get("role")
        content = data.get("content")
        meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}

        if role not in {"user", "assistant", "system"}:
            return Response(
                {"error": "invalid_role", "message": "Role inválido."}, status=400
            )
        if not isinstance(content, str) or not content.strip():
            return Response(
                {"error": "invalid_content", "message": "Contenido vacío."}, status=400
            )

        conversation = get_or_create_active_conversation(request.user)
        message = record_message(conversation, role, content.strip(), meta=meta)
        return Response(AgentMessageSerializer(message).data, status=201)
