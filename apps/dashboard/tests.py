"""Dashboard API 测试"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.clusters.models import Cluster
from apps.scanner.models import ClusterNode, ScanHistory, DetectionResult

User = get_user_model()


class DashboardStatsTest(TestCase):
    """GET /api/dashboard/stats/"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123", email="test@test.com"
        )
        self.client.force_authenticate(user=self.user)
        self.url = "/api/dashboard/stats/"

    def test_unauthenticated(self):
        self.client.force_authenticate(user=None)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_empty_state(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data, {
            "total_clusters": 0,
            "total_nodes": 0,
            "online_nodes": 0,
            "total_vms": 0,
            "total_containers": 0,
            "active_alerts": 0,
        })

    def test_cluster_count(self):
        Cluster.objects.create(name="集群A")
        Cluster.objects.create(name="集群B")
        resp = self.client.get(self.url)
        self.assertEqual(resp.data["total_clusters"], 2)

    def test_clusters_all_visible(self):
        Cluster.objects.create(name="所有集群")
        resp = self.client.get(self.url)
        self.assertEqual(resp.data["total_clusters"], 1)

    def test_total_nodes_from_cluster_model(self):
        Cluster.objects.create(name="集群A", total_nodes=5, total_vms=10)
        Cluster.objects.create(name="集群B", total_nodes=3, total_vms=8)
        resp = self.client.get(self.url)
        self.assertEqual(resp.data["total_nodes"], 8)
        self.assertEqual(resp.data["total_vms"], 18)

    def test_online_nodes(self):
        now = timezone.now()
        cluster = Cluster.objects.create(name="集群A", total_nodes=3)
        # 在线节点（去重）
        ClusterNode.objects.create(
            cluster=cluster, node_name="pve-1", status="online",
            scanned_at=now,
        )
        ClusterNode.objects.create(
            cluster=cluster, node_name="pve-2", status="online",
            scanned_at=now,
        )
        ClusterNode.objects.create(
            cluster=cluster, node_name="pve-3", status="offline",
            scanned_at=now,
        )
        resp = self.client.get(self.url)
        self.assertEqual(resp.data["online_nodes"], 2)

    def test_online_nodes_dedup_by_name(self):
        """同一节点多次扫描，只计一次在线"""
        now = timezone.now()
        cluster = Cluster.objects.create(name="集群A", total_nodes=1)
        ClusterNode.objects.create(
            cluster=cluster, node_name="pve-1", status="online", scanned_at=now,
        )
        ClusterNode.objects.create(
            cluster=cluster, node_name="pve-1", status="online",
            scanned_at=now - timezone.timedelta(hours=1),
        )
        resp = self.client.get(self.url)
        self.assertEqual(resp.data["online_nodes"], 1)

    def test_active_alerts(self):
        cluster = Cluster.objects.create(name="集群A")
        # 未解决的告警
        DetectionResult.objects.create(
            cluster=cluster, category="resource", severity="critical",
            title="CPU 过高", detail="...", is_resolved=False,
        )
        DetectionResult.objects.create(
            cluster=cluster, category="resource", severity="warning",
            title="磁盘空间不足", detail="...", is_resolved=False,
        )
        # 已解决的不计
        DetectionResult.objects.create(
            cluster=cluster, category="resource", severity="info",
            title="已恢复", detail="...", is_resolved=True,
        )
        resp = self.client.get(self.url)
        self.assertEqual(resp.data["active_alerts"], 2)


class DashboardAlertsTest(TestCase):
    """GET /api/dashboard/alerts/"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123", email="test@test.com"
        )
        self.client.force_authenticate(user=self.user)
        self.url = "/api/dashboard/alerts/"
        self.cluster = Cluster.objects.create(name="生产集群")
        self.other_cluster = Cluster.objects.create(name="其他集群")

    def test_unauthenticated(self):
        self.client.force_authenticate(user=None)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_empty_alerts(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data, [])

    def test_returns_unresolved_only(self):
        now = timezone.now()
        # 未解决的
        DetectionResult.objects.create(
            cluster=self.cluster, category="resource", severity="critical",
            title="CPU 过高", detail="CPU使用率超过80%",
            affected_resource="pve-1", is_resolved=False, created_at=now,
        )
        # 已解决的
        DetectionResult.objects.create(
            cluster=self.cluster, category="resource", severity="warning",
            title="已恢复", detail="...", is_resolved=True,
        )
        resp = self.client.get(self.url)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]["title"], "CPU 过高")

    def test_limit_parameter(self):
        now = timezone.now()
        for i in range(5):
            DetectionResult.objects.create(
                cluster=self.cluster, category="resource", severity="warning",
                title=f"告警{i}", detail="...", is_resolved=False,
                created_at=now - timezone.timedelta(hours=i),
            )
        resp = self.client.get(self.url, {"limit": 3})
        self.assertEqual(len(resp.data), 3)

    def test_default_limit(self):
        now = timezone.now()
        for i in range(15):
            DetectionResult.objects.create(
                cluster=self.cluster, category="resource", severity="info",
                title=f"告警{i}", detail="...", is_resolved=False,
                created_at=now - timezone.timedelta(hours=i),
            )
        resp = self.client.get(self.url)
        self.assertEqual(len(resp.data), 10)

    def test_ordered_by_created_at_desc(self):
        now = timezone.now()
        DetectionResult.objects.create(
            cluster=self.cluster, category="resource", severity="info",
            title="旧告警", detail="...", is_resolved=False,
            created_at=now - timezone.timedelta(hours=2),
        )
        DetectionResult.objects.create(
            cluster=self.cluster, category="resource", severity="info",
            title="新告警", detail="...", is_resolved=False,
            created_at=now,
        )
        resp = self.client.get(self.url)
        self.assertEqual(resp.data[0]["title"], "新告警")
        self.assertEqual(resp.data[1]["title"], "旧告警")

    def test_response_fields(self):
        now = timezone.now()
        DetectionResult.objects.create(
            cluster=self.cluster, category="resource", severity="critical",
            title="CPU 过高", detail="详细信息",
            affected_resource="pve-1", is_resolved=False, created_at=now,
        )
        resp = self.client.get(self.url)
        item = resp.data[0]
        self.assertIn("id", item)
        self.assertEqual(item["title"], "CPU 过高")
        self.assertEqual(item["severity"], "critical")
        self.assertEqual(item["category"], "resource")
        self.assertEqual(item["affected_resource"], "pve-1")
        self.assertEqual(item["detail"], "详细信息")
        self.assertEqual(item["cluster_name"], "生产集群")
        self.assertIn("created_at", item)

    def test_other_user_alerts_included(self):
        now = timezone.now()
        DetectionResult.objects.create(
            cluster=self.other_cluster, category="resource", severity="critical",
            title="其他集群告警", detail="...", is_resolved=False, created_at=now,
        )
        resp = self.client.get(self.url)
        self.assertEqual(len(resp.data), 1)


class DashboardTrendsTest(TestCase):
    """GET /api/dashboard/trends/"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123", email="test@test.com"
        )
        self.client.force_authenticate(user=self.user)
        self.url = "/api/dashboard/trends/"
        self.cluster = Cluster.objects.create(name="集群A")

    def test_unauthenticated(self):
        self.client.force_authenticate(user=None)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_empty_trends(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data, {"dates": [], "cpu_avg": [], "memory_avg": []})

    def test_trends_with_data(self):
        now = timezone.now()
        # 今天的数据
        ScanHistory.objects.create(
            cluster=self.cluster,
            snapshot_data={"avg_cpu_usage": 0.35, "avg_memory_usage": 0.62},
            scanned_at=now,
        )
        # 昨天的数据
        ScanHistory.objects.create(
            cluster=self.cluster,
            snapshot_data={"avg_cpu_usage": 0.42, "avg_memory_usage": 0.65},
            scanned_at=now - timezone.timedelta(days=1),
        )
        resp = self.client.get(self.url)
        self.assertEqual(len(resp.data["dates"]), 2)
        self.assertEqual(resp.data["cpu_avg"], [42.0, 35.0])  # 先旧后新
        self.assertEqual(resp.data["memory_avg"], [65.0, 62.0])

    def test_days_parameter(self):
        now = timezone.now()
        ScanHistory.objects.create(
            cluster=self.cluster,
            snapshot_data={"avg_cpu_usage": 0.35, "avg_memory_usage": 0.62},
            scanned_at=now,
        )
        # 30 天前的数据，默认 days=7 不应包含
        ScanHistory.objects.create(
            cluster=self.cluster,
            snapshot_data={"avg_cpu_usage": 0.80, "avg_memory_usage": 0.90},
            scanned_at=now - timezone.timedelta(days=30),
        )
        resp = self.client.get(self.url, {"days": 7})
        self.assertEqual(len(resp.data["dates"]), 1)

        resp2 = self.client.get(self.url, {"days": 31})
        self.assertEqual(len(resp2.data["dates"]), 2)

    def test_empty_snapshot_data_handled(self):
        now = timezone.now()
        ScanHistory.objects.create(
            cluster=self.cluster, snapshot_data={}, scanned_at=now,
        )
        # 只包含非 CPU/内存字段的快照
        ScanHistory.objects.create(
            cluster=self.cluster,
            snapshot_data={"total_nodes": 3, "total_vms": 10},
            scanned_at=now,
        )
        resp = self.client.get(self.url)
        self.assertEqual(resp.data, {"dates": [], "cpu_avg": [], "memory_avg": []})

    def test_daily_average(self):
        """同一天多条记录取平均值"""
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        ScanHistory.objects.create(
            cluster=self.cluster,
            snapshot_data={"avg_cpu_usage": 0.20, "avg_memory_usage": 0.50},
            scanned_at=today_start,
        )
        ScanHistory.objects.create(
            cluster=self.cluster,
            snapshot_data={"avg_cpu_usage": 0.40, "avg_memory_usage": 0.70},
            scanned_at=today_start + timezone.timedelta(hours=12),
        )
        resp = self.client.get(self.url)
        self.assertEqual(len(resp.data["dates"]), 1)
        self.assertEqual(resp.data["cpu_avg"], [30.0])  # (20+40)/2 = 30
        self.assertEqual(resp.data["memory_avg"], [60.0])  # (50+70)/2 = 60

    def test_all_clusters_trends_included(self):
        now = timezone.now()
        yesterday = now - timezone.timedelta(days=1)
        ScanHistory.objects.create(
            cluster=self.cluster,
            snapshot_data={"avg_cpu_usage": 0.35, "avg_memory_usage": 0.62},
            scanned_at=now,
        )
        other_cluster = Cluster.objects.create(name="其他集群")
        ScanHistory.objects.create(
            cluster=other_cluster,
            snapshot_data={"avg_cpu_usage": 0.90, "avg_memory_usage": 0.95},
            scanned_at=yesterday,
        )
        resp = self.client.get(self.url)
        self.assertEqual(len(resp.data["dates"]), 2)


class DashboardNodesTest(TestCase):
    """GET /api/dashboard/nodes/"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123", email="test@test.com"
        )
        self.client.force_authenticate(user=self.user)
        self.url = "/api/dashboard/nodes/"
        self.cluster = Cluster.objects.create(name="生产集群")

    def test_unauthenticated(self):
        self.client.force_authenticate(user=None)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_empty_nodes(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data, [])

    def test_returns_latest_node_status(self):
        now = timezone.now()
        old_time = now - timezone.timedelta(hours=2)
        # 旧扫描
        ClusterNode.objects.create(
            cluster=self.cluster, node_name="pve-1", status="online",
            cpu_load=0.20, memory_total_mb=32768, memory_used_mb=4000,
            memory_usage_pct=12.0, rootfs_total_gb=480, rootfs_used_gb=80,
            pve_version="pve-manager/8.1.0", ip_address="192.168.1.101",
            disk_io_delay_ms=5.0, scanned_at=old_time,
        )
        # 新扫描
        ClusterNode.objects.create(
            cluster=self.cluster, node_name="pve-1", status="online",
            cpu_load=0.35, memory_total_mb=32768, memory_used_mb=8200,
            memory_usage_pct=25.0, rootfs_total_gb=480, rootfs_used_gb=120,
            pve_version="pve-manager/8.1.4", ip_address="192.168.1.101",
            disk_io_delay_ms=12.5, scanned_at=now,
        )
        resp = self.client.get(self.url)
        self.assertEqual(len(resp.data), 1)
        node = resp.data[0]
        self.assertEqual(node["name"], "pve-1")
        self.assertEqual(node["cpu_load"], 0.35)
        self.assertEqual(node["memory_used_mb"], 8200)
        self.assertEqual(node["pve_version"], "pve-manager/8.1.4")
        self.assertEqual(node["cluster_name"], "生产集群")
        self.assertEqual(node["disk_io_delay_ms"], 12.5)
        self.assertIn("last_scan", node)

    def test_multiple_nodes(self):
        now = timezone.now()
        ClusterNode.objects.create(
            cluster=self.cluster, node_name="pve-1", status="online",
            cpu_load=0.35, memory_total_mb=32768, memory_used_mb=8200,
            memory_usage_pct=25.0, rootfs_total_gb=480, rootfs_used_gb=120,
            pve_version="pve-manager/8.1.4", ip_address="192.168.1.101",
            scanned_at=now,
        )
        ClusterNode.objects.create(
            cluster=self.cluster, node_name="pve-2", status="online",
            cpu_load=0.50, memory_total_mb=65536, memory_used_mb=20000,
            memory_usage_pct=30.0, rootfs_total_gb=960, rootfs_used_gb=300,
            pve_version="pve-manager/8.1.4", ip_address="192.168.1.102",
            scanned_at=now,
        )
        resp = self.client.get(self.url)
        self.assertEqual(len(resp.data), 2)
        names = {n["name"] for n in resp.data}
        self.assertEqual(names, {"pve-1", "pve-2"})

    def test_all_clusters_nodes_included(self):
        now = timezone.now()
        other_cluster = Cluster.objects.create(name="其他集群")
        ClusterNode.objects.create(
            cluster=other_cluster, node_name="pve-x", status="online",
            scanned_at=now,
        )
        resp = self.client.get(self.url)
        self.assertEqual(len(resp.data), 1)

    def test_response_fields(self):
        now = timezone.now()
        ClusterNode.objects.create(
            cluster=self.cluster, node_name="pve-1", status="online",
            cpu_load=0.35, memory_total_mb=32768, memory_used_mb=8200,
            memory_usage_pct=25.0, rootfs_total_gb=480, rootfs_used_gb=120,
            pve_version="pve-manager/8.1.4", ip_address="192.168.1.101",
            disk_io_delay_ms=12.5, scanned_at=now,
        )
        resp = self.client.get(self.url)
        node = resp.data[0]
        expected_keys = {
            "name", "status", "cpu_load", "memory_total_mb", "memory_used_mb",
            "memory_usage_pct", "rootfs_total_gb", "rootfs_used_gb",
            "pve_version", "ip_address", "cluster_name", "disk_io_delay_ms",
            "last_scan",
        }
        self.assertEqual(set(node.keys()), expected_keys)

    def test_null_fields_handled(self):
        now = timezone.now()
        ClusterNode.objects.create(
            cluster=self.cluster, node_name="pve-1", status="offline",
            scanned_at=now,
        )
        resp = self.client.get(self.url)
        node = resp.data[0]
        self.assertIsNone(node["cpu_load"])
        self.assertIsNone(node["memory_total_mb"])
        self.assertIsNone(node["disk_io_delay_ms"])
