from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.agent_history.models import AgentMessage, AgentConversation


class AgentHistoryAPITest(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="history_user",
            email="history@example.com",
            password="password123",
        )
        self.client.force_authenticate(user=self.user)

    def test_history_flow_and_persistence(self):
        history_url = "/api/agent/history/"
        messages_url = "/api/agent/history/messages/"
        chat_url = "/api/agent/"

        response = self.client.get(history_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("conversation", response.data)
        self.assertIn("messages", response.data)
        self.assertEqual(response.data["messages"], [])

        message_payload = {"role": "user", "content": "Hola historial"}
        response = self.client.post(messages_url, message_payload, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["role"], "user")

        response = self.client.get(history_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["messages"]), 1)

        chat_payload = {
            "message": "Busco novelas",
            "k": 3,
            "prefer_vector": False,
            "use_llm": False,
            "save_history": True,
        }
        response = self.client.post(chat_url, chat_payload, format="json")
        self.assertEqual(response.status_code, 200)

        conversation = AgentConversation.objects.filter(user=self.user).first()
        self.assertIsNotNone(conversation)
        self.assertEqual(
            AgentMessage.objects.filter(conversation=conversation).count(),
            3,
        )

        response = self.client.delete(history_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("conversation", response.data)
        self.assertEqual(response.data["messages"], [])
