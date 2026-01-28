from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from apps.compras.models import Pedidos, PedidoLibro, HistorialDeCompras, Devolucion
from apps.finanzas.models import Saldo
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
		Saldo.objects.get_or_create(usuario=self.normal_user, defaults={"saldo": Decimal("0.00")})

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

	def test_admin_cambiar_estado_cancelado_refunds_and_historial(self):
		self.client.force_authenticate(user=self.staff_user)
		response = self.client.post(
			self.admin_cambiar_estado_url,
			{"pedido_id": self.pedido.id, "nuevo_estado": "Cancelado"},
			format="json",
		)

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.pedido.refresh_from_db()
		self.assertEqual(self.pedido.estado, "Cancelado")
		self.assertTrue(HistorialDeCompras.objects.filter(pedido=self.pedido).exists())

		saldo = Saldo.objects.get(usuario=self.normal_user)
		self.assertGreater(saldo.saldo, Decimal("0.00"))
		self.libro.refresh_from_db()
		self.assertEqual(self.libro.stock, 12)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class DevolucionesTests(APITestCase):
	def setUp(self):
		User = get_user_model()
		self.user = User.objects.create_user(
			username="comprador",
			email="comprador@example.com",
			password="testpass123",
			tipo_usuario="LECTOR",
		)
		self.staff = User.objects.create_user(
			username="staff",
			email="staff@example.com",
			password="testpass123",
			is_staff=True,
			tipo_usuario="BIBLIOTECARIO",
		)

		self.categoria = Categoria.objects.create(nombre="Historia")
		self.libro = Libro.objects.create(
			titulo="Libro Historia",
			autor="Autor",
			isbn="9999999999999",
			categoria=self.categoria,
			editorial="Editorial",
			precio=Decimal("10.00"),
			stock=10,
			año_publicacion=2024,
			descripcion="Desc",
		)

		self.pedido = Pedidos.objects.create(usuario=self.user, estado="Entregado")
		PedidoLibro.objects.create(pedido=self.pedido, libro=self.libro, cantidad=1)
		self.historial = HistorialDeCompras.objects.create(usuario=self.user, pedido=self.pedido)

		self.devolver_url = "/api/compras/historial-compras/devolver_compra/"
		self.resolve_url = "/api/compras/devoluciones/resolve/"
		self.confirmar_url = "/api/compras/devoluciones/confirmar/"
		self.admin_list_url = "/api/compras/devoluciones/admin_list/"

	def test_user_can_request_devolucion(self):
		self.client.force_authenticate(user=self.user)
		response = self.client.post(self.devolver_url, {"historial_id": self.historial.id}, format="json")
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertIn("token", response.data)
		self.pedido.refresh_from_db()
		self.assertEqual(self.pedido.estado, "En Devolución")
		self.assertTrue(Devolucion.objects.filter(pedido=self.pedido).exists())

	def test_resolve_devolucion_by_token(self):
		self.client.force_authenticate(user=self.user)
		response = self.client.post(self.devolver_url, {"historial_id": self.historial.id}, format="json")
		token = response.data["token"]

		self.client.force_authenticate(user=None)
		resolve = self.client.get(f"{self.resolve_url}{token}/")
		self.assertEqual(resolve.status_code, status.HTTP_200_OK)
		self.assertEqual(resolve.data["pedido"]["id"], self.pedido.id)

	def test_confirmar_devolucion_updates_estado(self):
		self.client.force_authenticate(user=self.user)
		response = self.client.post(self.devolver_url, {"historial_id": self.historial.id}, format="json")
		token = response.data["token"]

		payload = {
			"items": [
				{"libro_id": self.libro.id, "cantidad": 1}
			]
		}
		confirm = self.client.post(f"{self.confirmar_url}{token}/", payload, format="json")
		self.assertEqual(confirm.status_code, status.HTTP_200_OK)

		devolucion = Devolucion.objects.get(token=token)
		self.assertEqual(devolucion.estado, "En Proceso")
		self.pedido.refresh_from_db()
		self.assertEqual(self.pedido.estado, "En Devolución")

	def test_admin_can_update_estado_devuelta(self):
		self.client.force_authenticate(user=self.user)
		response = self.client.post(self.devolver_url, {"historial_id": self.historial.id}, format="json")
		token = response.data["token"]
		devolucion = Devolucion.objects.get(token=token)

		payload = {
			"items": [
				{"libro_id": self.libro.id, "cantidad": 1}
			]
		}
		confirm = self.client.post(f"{self.confirmar_url}{token}/", payload, format="json")
		self.assertEqual(confirm.status_code, status.HTTP_200_OK)

		self.client.force_authenticate(user=self.staff)
		update = self.client.post(
			f"/api/compras/devoluciones/{devolucion.id}/admin_update_estado/",
			{"estado": "Devuelta"},
			format="json",
		)
		self.assertEqual(update.status_code, status.HTTP_200_OK)
		self.pedido.refresh_from_db()
		self.assertEqual(self.pedido.estado, "Devuelto")

	def test_admin_list_requires_staff(self):
		self.client.force_authenticate(user=self.user)
		response = self.client.get(self.admin_list_url)
		self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

