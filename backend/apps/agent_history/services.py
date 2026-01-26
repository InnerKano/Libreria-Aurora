from django.db import transaction
from django.utils import timezone

from .models import AgentConversation, AgentMessage, ConversationStatus


def get_or_create_active_conversation(user):
    with transaction.atomic():
        active = (
            AgentConversation.objects.select_for_update()
            .filter(user=user, status=ConversationStatus.ACTIVE)
            .first()
        )
        if active:
            return active
        AgentConversation.objects.filter(user=user, status=ConversationStatus.ACTIVE).update(
            status=ConversationStatus.ARCHIVED, updated_at=timezone.now()
        )
        return AgentConversation.objects.create(user=user, status=ConversationStatus.ACTIVE)


def archive_active_conversations(user):
    return AgentConversation.objects.filter(user=user, status=ConversationStatus.ACTIVE).update(
        status=ConversationStatus.ARCHIVED, updated_at=timezone.now()
    )


def record_message(conversation, role, content, meta=None):
    if meta is None:
        meta = {}
    message = AgentMessage.objects.create(
        conversation=conversation,
        role=role,
        content=content,
        meta=meta,
    )
    conversation.last_message_at = timezone.now()
    conversation.save(update_fields=["last_message_at", "updated_at"])
    return message
