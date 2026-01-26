from django.urls import path

from .views import AgentHistoryMessageView, AgentHistoryView

urlpatterns = [
    path("", AgentHistoryView.as_view(), name="agent-history"),
    path("messages/", AgentHistoryMessageView.as_view(), name="agent-history-messages"),
]
