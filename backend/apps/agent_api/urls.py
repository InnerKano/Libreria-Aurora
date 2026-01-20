from django.urls import path

from .views import AgentSearchView

urlpatterns = [
    path("search/", AgentSearchView.as_view(), name="agent-search"),
]
