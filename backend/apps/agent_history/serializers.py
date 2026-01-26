from rest_framework import serializers

from .models import AgentConversation, AgentMessage


class AgentMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentMessage
        fields = ["id", "role", "content", "meta", "created_at"]


class AgentConversationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentConversation
        fields = ["id", "status", "created_at", "updated_at", "last_message_at"]
