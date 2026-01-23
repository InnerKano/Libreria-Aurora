from __future__ import annotations

import pytest
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.agent_api.views import AgentActionView
from apps.libros.models import Categoria, Libro
from apps.usuarios.models import Usuario


@pytest.mark.django_db
def test_agent_actions_requires_authentication():
    factory = APIRequestFactory()
    request = factory.post(
        "/api/agent/actions/",
        {"action": "add_to_cart", "payload": {"book_id": 1, "cantidad": 1}},
        format="json",
    )
    response = AgentActionView.as_view()(request)

    assert response.status_code == 401


@pytest.mark.django_db
def test_agent_actions_add_to_cart_success():
    categoria = Categoria.objects.create(nombre="Ficcion")
    libro = Libro.objects.create(
        titulo="Libro de prueba",
        autor="Autor",
        isbn="1234567890123",
        categoria=categoria,
        editorial="Editorial",
        precio="19.99",
        stock=5,
        año_publicacion=2020,
        descripcion="Desc",
    )
    user = Usuario.objects.create_user(
        username="user1",
        password="pass1234",
        numero_identificacion="12345678",
    )

    factory = APIRequestFactory()
    request = factory.post(
        "/api/agent/actions/",
        {"action": "add_to_cart", "payload": {"book_id": libro.id, "cantidad": 1}},
        format="json",
    )
    force_authenticate(request, user=user)
    response = AgentActionView.as_view()(request)

    assert response.status_code == 200
    assert response.data["actions"][0]["ok"] is True
    assert response.data["results"][0]["libro"]["libro_id"] == libro.id


@pytest.mark.django_db
def test_agent_actions_invalid_action_returns_400():
    user = Usuario.objects.create_user(
        username="user2",
        password="pass1234",
        numero_identificacion="87654321",
    )

    factory = APIRequestFactory()
    request = factory.post(
        "/api/agent/actions/",
        {"action": "delete_all", "payload": {}},
        format="json",
    )
    force_authenticate(request, user=user)
    response = AgentActionView.as_view()(request)

    assert response.status_code == 400
    assert response.data["error"] == "invalid_action"
