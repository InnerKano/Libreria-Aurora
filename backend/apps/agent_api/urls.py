from django.urls import path

from .views import AgentChatView, AgentSearchView

urlpatterns = [
    path("", AgentChatView.as_view(), name="agent-chat"),
    path("search/", AgentSearchView.as_view(), name="agent-search"),
]
