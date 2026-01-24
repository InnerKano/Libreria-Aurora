from django.urls import path

from .views import AgentActionView, AgentChatView, AgentSearchView, AgentStatusView

urlpatterns = [
    path("", AgentChatView.as_view(), name="agent-chat"),
    path("search/", AgentSearchView.as_view(), name="agent-search"),
    path("actions/", AgentActionView.as_view(), name="agent-actions"),
    path("status/", AgentStatusView.as_view(), name="agent-status"),
]
