from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

Usuario = get_user_model()


class UsuarioSetStaffAPITests(TestCase):
	def setUp(self):
		self.client = APIClient()
		# crear usuarios
		self.staff = Usuario.objects.create_user(username='staff', email='staff@example.com', password='staffpass', numero_identificacion='111111111')
		self.staff.is_staff = True
		self.staff.save()

		self.normal = Usuario.objects.create_user(username='normal', email='normal@example.com', password='normalpass', numero_identificacion='222222222')

	def test_staff_can_promote_user(self):
		self.client.force_authenticate(user=self.staff)
		url = f"/api/usuarios/{self.normal.id}/set_staff/"
		resp = self.client.post(url, {'is_staff': True}, format='json')
		self.assertEqual(resp.status_code, 200)
		self.normal.refresh_from_db()
		self.assertTrue(self.normal.is_staff)

	def test_non_staff_cannot_promote(self):
		self.client.force_authenticate(user=self.normal)
		url = f"/api/usuarios/{self.staff.id}/set_staff/"
		resp = self.client.post(url, {'is_staff': True}, format='json')
		self.assertEqual(resp.status_code, 403)

	def test_prevent_self_demote(self):
		self.client.force_authenticate(user=self.staff)
		url = f"/api/usuarios/{self.staff.id}/set_staff/"
		resp = self.client.post(url, {'is_staff': False}, format='json')
		self.assertEqual(resp.status_code, 400)
