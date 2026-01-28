from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.compras.models import Pedidos, PedidoLibro, HistorialDeCompras
from apps.libros.models import Categoria, Libro


class AdminPedidosTests(APITestCase):
	def setUp(self):
		User = get_user_model()
		self.staff_user = User.objects.create_user(
			username="staff_user",
			email="staff@example.com",
			password="testpass123",
			is_staff=True,
			tipo_usuario="BIBLIOTECARIO",
		)
		self.normal_user = User.objects.create_user(
			username="normal_user",
			email="user@example.com",
			password="testpass123",
			tipo_usuario="LECTOR",
		)

		self.categoria = Categoria.objects.create(nombre="Ficción")
		self.libro = Libro.objects.create(
			titulo="Libro de prueba",
			autor="Autor",
			isbn="1234567890123",
			categoria=self.categoria,
			editorial="Editorial",
			precio=Decimal("19.90"),
			stock=10,
			año_publicacion=2024,
			descripcion="Desc",
		)

		self.pedido = Pedidos.objects.create(usuario=self.normal_user, estado="Pendiente")
		PedidoLibro.objects.create(pedido=self.pedido, libro=self.libro, cantidad=2)

		self.admin_list_url = "/api/compras/pedidos/admin_list/"
		self.admin_cambiar_estado_url = "/api/compras/pedidos/admin_cambiar_estado/"

	def test_admin_list_requires_staff(self):
		self.client.force_authenticate(user=self.normal_user)
		response = self.client.get(self.admin_list_url)
		self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

	def test_admin_list_returns_pedidos(self):
		self.client.force_authenticate(user=self.staff_user)
		response = self.client.get(self.admin_list_url)

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(len(response.data), 1)

		pedido = response.data[0]
		self.assertEqual(pedido["id"], self.pedido.id)
		self.assertEqual(pedido["usuario"]["username"], self.normal_user.username)
		self.assertEqual(len(pedido["pedidolibro_set"]), 1)
		self.assertEqual(pedido["pedidolibro_set"][0]["libro"]["titulo"], self.libro.titulo)

	def test_admin_cambiar_estado_requires_staff(self):
		self.client.force_authenticate(user=self.normal_user)
		response = self.client.post(
			self.admin_cambiar_estado_url,
			{"pedido_id": self.pedido.id, "nuevo_estado": "Entregado"},
			format="json",
		)
		self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

	def test_admin_cambiar_estado_updates_and_creates_historial(self):
		self.client.force_authenticate(user=self.staff_user)
		response = self.client.post(
			self.admin_cambiar_estado_url,
			{"pedido_id": self.pedido.id, "nuevo_estado": "Entregado"},
			format="json",
		)

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.pedido.refresh_from_db()
		self.assertEqual(self.pedido.estado, "Entregado")
		self.assertTrue(HistorialDeCompras.objects.filter(pedido=self.pedido).exists())

