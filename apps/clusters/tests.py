"""集群 API 测试"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.agent_api.models import AgentInstance

from .models import Cluster

User = get_user_model()


class ClusterAPITest(TestCase):
    """GET/POST /api/clusters/"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123", email="test@test.com"
        )
        self.client.force_authenticate(user=self.user)
        self.url = "/api/clusters/"

    def test_create_cluster(self):
        resp = self.client.post(self.url, {
            "name": "生产集群",
            "description": "PVE 生产环境",
            "pve_endpoint": "https://192.168.1.200:8006",
            "pve_token": "root@pam!monitor:abc123",
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["name"], "生产集群")
        self.assertIn("agent_token", resp.data)

    def test_create_duplicate_name(self):
        Cluster.objects.create(user=self.user, name="生产集群",
                               pve_endpoint="https://1.1.1.1:8006", pve_token="t")
        resp = self.client.post(self.url, {
            "name": "生产集群",
            "pve_endpoint": "https://1.1.1.1:8006",
            "pve_token": "t",
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_requires_pve_fields(self):
        resp = self.client.post(self.url, {"name": "集群"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_clusters(self):
        Cluster.objects.create(user=self.user, name="集群A",
                               pve_endpoint="https://1.1.1.1:8006", pve_token="t")
        Cluster.objects.create(user=self.user, name="集群B",
                               pve_endpoint="https://2.2.2.2:8006", pve_token="t")
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 2)

    def test_list_other_user_clusters(self):
        other = User.objects.create_user(username="other", password="pass123")
        Cluster.objects.create(user=other, name="其他集群")
        resp = self.client.get(self.url)
        self.assertEqual(resp.data["count"], 0)


class ClusterDetailAPITest(TestCase):
    """GET/PUT/PATCH/DELETE /api/clusters/:id/"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123", email="test@test.com"
        )
        self.client.force_authenticate(user=self.user)
        self.cluster = Cluster.objects.create(
            user=self.user, name="测试集群", description="测试用",
            pve_endpoint="https://192.168.1.200:8006", pve_token="root@pam!monitor:abc123",
        )
        self.url = f"/api/clusters/{self.cluster.id}/"

    def test_get_detail(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["name"], "测试集群")
        self.assertIn("agents", resp.data)
        self.assertIn("install_command", resp.data)

    def test_install_command_contains_token(self):
        resp = self.client.get(self.url)
        self.assertIn(self.cluster.agent_token, resp.data["install_command"])

    def test_update_cluster(self):
        resp = self.client.patch(self.url, {
            "description": "更新后的描述",
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.cluster.refresh_from_db()
        self.assertEqual(self.cluster.description, "更新后的描述")

    def test_delete_cluster(self):
        resp = self.client.delete(self.url)
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Cluster.objects.filter(id=self.cluster.id).exists())

    def test_agents_in_detail(self):
        AgentInstance.objects.create(
            cluster=self.cluster, agent_id="agent-001", hostname="pve-1",
            status=AgentInstance.Status.ONLINE,
        )
        AgentInstance.objects.create(
            cluster=self.cluster, agent_id="agent-002", hostname="pve-2",
            status=AgentInstance.Status.OFFLINE,
        )
        resp = self.client.get(self.url)
        self.assertEqual(len(resp.data["agents"]), 2)

    def test_other_user_cannot_access(self):
        other = User.objects.create_user(username="other", password="pass123")
        self.client.force_authenticate(user=other)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
