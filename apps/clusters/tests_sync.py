"""集群数据同步（push_cluster_data / _collect_cluster_data / ClusterSyncView）测试"""
from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.scanner.models import (
    ClusterNode,
    CephStatus,
    HAResource,
    LXC,
    LXCConfig,
    NetworkInterface,
    ScanHistory,
    SDNSubnet,
    SDNVNet,
    SDNZone,
    Storage,
    VM,
    VMConfig,
)

from .models import Cluster
from .sync import _collect_cluster_data, push_cluster_data

User = get_user_model()


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _make_cluster(**overrides):
    """创建一个可直接用于同步测试的集群（默认已启用同步）"""
    defaults = dict(
        name="同步测试集群",
        pve_endpoint="https://192.168.1.200:8006",
        pve_token="root@pam!monitor:abc123",
        pve_version="pve-manager/8.2.4",
        sync_enabled=True,
        sync_url="https://pcss.example.com",
        sync_id="sync-cluster-001",
        sync_token="s3cret-t0ken",
    )
    defaults.update(overrides)
    return Cluster.objects.create(**defaults)


def _make_node(cluster, **overrides):
    now = timezone.now()
    defaults = dict(
        cluster=cluster,
        node_name="pve-1",
        status="online",
        pve_version="pve-manager/8.2.4",
        cpu_cores=8,
        cpu_load=0.35,
        memory_total_mb=32768,
        memory_used_mb=12000,
        memory_free_mb=20768,
        memory_usage_pct=36.6,
        rootfs_total_gb=100,
        rootfs_used_gb=45,
        rootfs_avail_gb=55,
        scanned_at=now,
    )
    defaults.update(overrides)
    return ClusterNode.objects.create(**defaults)


# ===================================================================
# 1. push_cluster_data 测试
# ===================================================================


class PushClusterDataConfigTest(TestCase):
    """push_cluster_data 配置校验"""

    def test_sync_not_enabled(self):
        cluster = _make_cluster(sync_enabled=False)
        result = push_cluster_data(cluster)
        self.assertFalse(result["ok"])
        self.assertIn("同步未启用", result["message"])

    def test_missing_sync_url(self):
        cluster = _make_cluster(sync_url="")
        result = push_cluster_data(cluster)
        self.assertFalse(result["ok"])
        self.assertIn("配置不完整", result["message"])

    def test_missing_sync_id(self):
        cluster = _make_cluster(sync_id="")
        result = push_cluster_data(cluster)
        self.assertFalse(result["ok"])
        self.assertIn("配置不完整", result["message"])

    def test_missing_sync_token(self):
        cluster = _make_cluster(sync_token="")
        result = push_cluster_data(cluster)
        self.assertFalse(result["ok"])
        self.assertIn("配置不完整", result["message"])


class PushClusterDataSuccessTest(TestCase):
    """push_cluster_data 成功推送"""

    @patch("apps.clusters.sync.requests.post")
    def test_push_succeeds(self, mock_post):
        cluster = _make_cluster()
        _make_node(cluster)

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"ok": True}
        mock_resp.elapsed.total_seconds.return_value = 0.5
        mock_post.return_value = mock_resp

        result = push_cluster_data(cluster)
        self.assertTrue(result["ok"])
        self.assertEqual(result["message"], "同步成功")
        self.assertIsNotNone(result["synced_at"])

        # 验证 POST 目标 URL
        call_args = mock_post.call_args
        self.assertEqual(
            call_args[0][0],
            "https://pcss.example.com/api/sync/upload/",
        )

        # 验证 last_synced_at 已更新
        cluster.refresh_from_db()
        self.assertIsNotNone(cluster.last_synced_at)

    @patch("apps.clusters.sync.requests.post")
    def test_push_includes_sync_type_full_when_first(self, mock_post):
        cluster = _make_cluster(last_synced_at=None)
        _make_node(cluster)

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"ok": True}
        mock_resp.elapsed.total_seconds.return_value = 0.3
        mock_post.return_value = mock_resp

        push_cluster_data(cluster)

        sent_json = mock_post.call_args[1].get("json") or mock_post.call_args[0][1]
        self.assertEqual(sent_json.get("sync_type"), "full")

    @patch("apps.clusters.sync.requests.post")
    def test_push_includes_sync_type_incremental(self, mock_post):
        cluster = _make_cluster(last_synced_at=timezone.now())
        _make_node(cluster)

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"ok": True}
        mock_resp.elapsed.total_seconds.return_value = 0.3
        mock_post.return_value = mock_resp

        push_cluster_data(cluster)

        sent_json = mock_post.call_args[1].get("json") or mock_post.call_args[0][1]
        self.assertEqual(sent_json.get("sync_type"), "incremental")

    @patch("apps.clusters.sync.requests.post")
    def test_push_force_full_overrides_incremental(self, mock_post):
        cluster = _make_cluster(last_synced_at=timezone.now())
        _make_node(cluster)

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"ok": True}
        mock_resp.elapsed.total_seconds.return_value = 0.3
        mock_post.return_value = mock_resp

        push_cluster_data(cluster, force_full=True)

        sent_json = mock_post.call_args[1].get("json") or mock_post.call_args[0][1]
        self.assertEqual(sent_json.get("sync_type"), "full")

    @patch("apps.clusters.sync.requests.post")
    def test_push_sends_auth_fields(self, mock_post):
        cluster = _make_cluster()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"ok": True}
        mock_resp.elapsed.total_seconds.return_value = 0.3
        mock_post.return_value = mock_resp

        push_cluster_data(cluster)

        sent_json = mock_post.call_args[1].get("json") or mock_post.call_args[0][1]
        self.assertEqual(sent_json["sync_id"], cluster.sync_id)
        self.assertEqual(sent_json["sync_token"], cluster.sync_token)
        self.assertEqual(sent_json["cluster_id"], cluster.id)
        self.assertEqual(sent_json["cluster_name"], cluster.name)
        self.assertEqual(sent_json["version"], cluster.pve_version)


class PushClusterDataErrorTest(TestCase):
    """push_cluster_data 错误响应"""

    @patch("apps.clusters.sync.requests.post")
    def test_returns_error_on_401(self, mock_post):
        cluster = _make_cluster()

        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = "Unauthorized"
        mock_post.return_value = mock_resp

        result = push_cluster_data(cluster)
        self.assertFalse(result["ok"])
        self.assertIn("认证失败", result["message"])
        # 401 不应重试
        self.assertEqual(mock_post.call_count, 1)

    @patch("apps.clusters.sync.requests.post")
    def test_returns_error_on_423(self, mock_post):
        cluster = _make_cluster()

        mock_resp = MagicMock()
        mock_resp.status_code = 423
        mock_resp.text = "Cluster deactivated"
        mock_post.return_value = mock_resp

        result = push_cluster_data(cluster)
        self.assertFalse(result["ok"])
        self.assertIn("停用", result["message"])
        self.assertEqual(mock_post.call_count, 1)

    @patch("apps.clusters.sync.requests.post")
    def test_returns_error_on_410(self, mock_post):
        cluster = _make_cluster()

        mock_resp = MagicMock()
        mock_resp.status_code = 410
        mock_resp.text = "Cluster deleted"
        mock_post.return_value = mock_resp

        result = push_cluster_data(cluster)
        self.assertFalse(result["ok"])
        self.assertIn("删除", result["message"])
        self.assertEqual(mock_post.call_count, 1)

    @patch("time.sleep", return_value=None)
    @patch("apps.clusters.sync.requests.post")
    def test_retries_on_connection_error(self, mock_post, mock_sleep):
        cluster = _make_cluster()

        mock_post.side_effect = ConnectionError("Network unreachable")

        result = push_cluster_data(cluster)
        self.assertFalse(result["ok"])
        self.assertIn("同步失败", result["message"])
        self.assertEqual(mock_post.call_count, 3)  # SYNC_MAX_RETRIES = 3

    @patch("time.sleep", return_value=None)
    @patch("apps.clusters.sync.requests.post")
    def test_retries_on_timeout(self, mock_post, mock_sleep):
        cluster = _make_cluster()

        import requests as _requests
        mock_post.side_effect = _requests.Timeout("timed out")

        result = push_cluster_data(cluster)
        self.assertFalse(result["ok"])
        self.assertIn("超时", result["message"])
        self.assertEqual(mock_post.call_count, 3)

    @patch("time.sleep", return_value=None)
    @patch("apps.clusters.sync.requests.post")
    def test_succeeds_on_retry_after_initial_failure(self, mock_post, mock_sleep):
        cluster = _make_cluster()
        _make_node(cluster)

        fail_resp = MagicMock()
        fail_resp.status_code = 503
        fail_resp.text = "Service Unavailable"

        success_resp = MagicMock()
        success_resp.status_code = 200
        success_resp.json.return_value = {"ok": True}
        success_resp.elapsed.total_seconds.return_value = 0.4

        mock_post.side_effect = [fail_resp, success_resp]

        result = push_cluster_data(cluster)
        self.assertTrue(result["ok"])
        self.assertEqual(mock_post.call_count, 2)

    @patch("apps.clusters.sync.requests.post")
    def test_no_retry_on_401_423_410(self, mock_post):
        """401/423/410 是明确拒绝，不应重试"""
        cluster = _make_cluster()

        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = "Unauthorized"
        mock_post.return_value = mock_resp

        push_cluster_data(cluster)
        self.assertEqual(mock_post.call_count, 1)

        # 423
        mock_resp.status_code = 423
        push_cluster_data(cluster)
        self.assertEqual(mock_post.call_count, 2)

        # 410
        mock_resp.status_code = 410
        push_cluster_data(cluster)
        self.assertEqual(mock_post.call_count, 3)


# ===================================================================
# 2. _collect_cluster_data 测试
# ===================================================================


class CollectClusterDataNodeTest(TestCase):
    """_collect_cluster_data 节点数据收集"""

    def setUp(self):
        self.cluster = _make_cluster()
        self.now = timezone.now()

    def test_collects_node_data(self):
        node = _make_node(self.cluster, node_name="pve-1")
        data = _collect_cluster_data(self.cluster)
        self.assertEqual(len(data["nodes"]), 1)
        n = data["nodes"][0]
        self.assertEqual(n["name"], "pve-1")
        self.assertEqual(n["status"], "online")
        self.assertEqual(n["cpu_cores"], 8)
        self.assertEqual(n["memory_total_mb"], 32768)

    def test_deduplicates_nodes_by_name(self):
        """同名节点只取最新一条"""
        _make_node(self.cluster, node_name="pve-1", scanned_at=self.now - timedelta(hours=1))
        _make_node(self.cluster, node_name="pve-1", scanned_at=self.now)
        data = _collect_cluster_data(self.cluster)
        self.assertEqual(len(data["nodes"]), 1)

    def test_collects_multiple_nodes(self):
        _make_node(self.cluster, node_name="pve-1")
        _make_node(self.cluster, node_name="pve-2")
        _make_node(self.cluster, node_name="pve-3")
        data = _collect_cluster_data(self.cluster)
        names = [n["name"] for n in data["nodes"]]
        self.assertEqual(len(names), 3)
        self.assertIn("pve-1", names)
        self.assertIn("pve-2", names)
        self.assertIn("pve-3", names)

    def test_excludes_old_nodes(self):
        """超过 7 天的节点数据不应被收集"""
        old_time = self.now - timedelta(days=8)
        _make_node(self.cluster, node_name="pve-old", scanned_at=old_time)
        data = _collect_cluster_data(self.cluster)
        self.assertEqual(len(data["nodes"]), 0)

    def test_includes_recent_nodes(self):
        recent_time = self.now - timedelta(days=6)
        _make_node(self.cluster, node_name="pve-recent", scanned_at=recent_time)
        data = _collect_cluster_data(self.cluster)
        self.assertEqual(len(data["nodes"]), 1)


class CollectClusterDataVMContainerTest(TestCase):
    """_collect_cluster_data VM / 容器数据收集"""

    def setUp(self):
        self.cluster = _make_cluster()
        self.node = _make_node(self.cluster)
        self.now = timezone.now()

    def test_collects_vms(self):
        vm = VM.objects.create(
            node=self.node, vmid=100, name="ubuntu", status="running",
            cpu_cores=2, memory_mb=4096, disk_gb=50, scanned_at=self.now,
        )
        VMConfig.objects.create(
            vm=vm, cpu_type="host", cpu_cores=2, memory_mb=4096,
            ha_enabled=True, ha_group="ha-group1", scanned_at=self.now,
        )
        data = _collect_cluster_data(self.cluster)
        self.assertEqual(len(data["nodes"]), 1)
        node_data = data["nodes"][0]
        self.assertIn("vms", node_data)
        self.assertEqual(len(node_data["vms"]), 1)
        vm_data = node_data["vms"][0]
        self.assertEqual(vm_data["vmid"], 100)
        self.assertEqual(vm_data["name"], "ubuntu")
        self.assertEqual(vm_data["status"], "running")
        self.assertIn("config", vm_data)
        self.assertTrue(vm_data["config"]["ha_enabled"])

    def test_collects_containers(self):
        ct = LXC.objects.create(
            node=self.node, vmid=200, name="nginx", status="running",
            cpu_cores=1, memory_mb=512, disk_gb=8, scanned_at=self.now,
        )
        LXCConfig.objects.create(
            container=ct, hostname="nginx", cpu_cores=1, memory_mb=512,
            ha_enabled=False, scanned_at=self.now,
        )
        data = _collect_cluster_data(self.cluster)
        node_data = data["nodes"][0]
        self.assertIn("containers", node_data)
        self.assertEqual(len(node_data["containers"]), 1)
        ct_data = node_data["containers"][0]
        self.assertEqual(ct_data["vmid"], 200)
        self.assertEqual(ct_data["name"], "nginx")
        self.assertFalse(ct_data["config"]["ha_enabled"])

    def test_collects_storages(self):
        Storage.objects.create(
            node=self.node, storage_name="local", type="dir", status="available",
            active=True, used_gb=20, avail_gb=80, total_gb=100,
            scanned_at=self.now,
        )
        data = _collect_cluster_data(self.cluster)
        node_data = data["nodes"][0]
        self.assertIn("storages", node_data)
        self.assertEqual(len(node_data["storages"]), 1)
        self.assertEqual(node_data["storages"][0]["name"], "local")

    def test_collects_networks(self):
        NetworkInterface.objects.create(
            node=self.node, name="vmbr0", type="bridge", active=True,
            method="static", address="192.168.1.1/24",
            scanned_at=self.now,
        )
        data = _collect_cluster_data(self.cluster)
        node_data = data["nodes"][0]
        self.assertIn("networks", node_data)
        self.assertEqual(len(node_data["networks"]), 1)
        self.assertEqual(node_data["networks"][0]["name"], "vmbr0")


class CollectClusterDataCephHATest(TestCase):
    """_collect_cluster_data Ceph / HA 数据收集"""

    def setUp(self):
        self.cluster = _make_cluster()
        self.now = timezone.now()

    def test_collects_ceph_status(self):
        CephStatus.objects.create(
            cluster=self.cluster, health="HEALTH_OK",
            total_osds=12, up_osds=12, in_osds=12, pool_count=3,
            total_used_gb=500, total_avail_gb=1500, total_space_gb=2000,
            scanned_at=self.now,
        )
        data = _collect_cluster_data(self.cluster)
        self.assertIn("ceph", data)
        ceph = data["ceph"]
        self.assertEqual(ceph["health"], "HEALTH_OK")
        self.assertEqual(ceph["total_osds"], 12)

    def test_no_ceph_when_none(self):
        data = _collect_cluster_data(self.cluster)
        self.assertNotIn("ceph", data)

    def test_collects_ha_resources(self):
        HAResource.objects.create(
            cluster=self.cluster, sid="vm:100", resource_type="vm",
            vmid=100, node_name="pve-1", state="started",
            ha_group="ha-group1", ha_status="active", crm_state="started",
            scanned_at=self.now,
        )
        data = _collect_cluster_data(self.cluster)
        self.assertIn("ha_resources", data)
        self.assertEqual(len(data["ha_resources"]), 1)
        ha = data["ha_resources"][0]
        self.assertEqual(ha["sid"], "vm:100")
        self.assertEqual(ha["type"], "vm")

    def test_ha_deduplicates_by_sid(self):
        """同 sid 只取最新一条"""
        HAResource.objects.create(
            cluster=self.cluster, sid="vm:100", resource_type="vm",
            vmid=100, state="stopped", scanned_at=self.now - timedelta(hours=1),
        )
        HAResource.objects.create(
            cluster=self.cluster, sid="vm:100", resource_type="vm",
            vmid=100, state="started", scanned_at=self.now,
        )
        data = _collect_cluster_data(self.cluster)
        self.assertEqual(len(data["ha_resources"]), 1)


class CollectClusterDataSDNTest(TestCase):
    """_collect_cluster_data SDN 数据收集"""

    def setUp(self):
        self.cluster = _make_cluster()
        self.now = timezone.now()

    def test_collects_sdn_zones(self):
        SDNZone.objects.create(
            cluster=self.cluster, zone="zone1", zone_type="vlan",
            nodes="pve-1,pve-2", scanned_at=self.now,
        )
        data = _collect_cluster_data(self.cluster)
        self.assertIn("sdn", data)
        self.assertEqual(len(data["sdn"]["zones"]), 1)
        self.assertEqual(data["sdn"]["zones"][0]["zone"], "zone1")

    def test_collects_sdn_vnets(self):
        SDNVNet.objects.create(
            cluster=self.cluster, vnet="vnet1", vnet_type="vlan",
            vlan=100, zone_name="zone1", scanned_at=self.now,
        )
        data = _collect_cluster_data(self.cluster)
        self.assertIn("sdn", data)
        self.assertEqual(len(data["sdn"]["vnets"]), 1)
        self.assertEqual(data["sdn"]["vnets"][0]["vnet"], "vnet1")

    def test_collects_sdn_subnets(self):
        SDNSubnet.objects.create(
            cluster=self.cluster, subnet="10.0.0.0/24", vnet_name="vnet1",
            gateway="10.0.0.1", dns_server="8.8.8.8",
            scanned_at=self.now,
        )
        data = _collect_cluster_data(self.cluster)
        self.assertIn("sdn", data)
        self.assertEqual(len(data["sdn"]["subnets"]), 1)
        self.assertEqual(data["sdn"]["subnets"][0]["subnet"], "10.0.0.0/24")

    def test_sdn_not_present_when_empty(self):
        data = _collect_cluster_data(self.cluster)
        self.assertNotIn("sdn", data)


class CollectClusterDataScanHistoryTest(TestCase):
    """_collect_cluster_data 扫描历史收集"""

    def setUp(self):
        self.cluster = _make_cluster()
        self.now = timezone.now()

    def test_collects_scan_history(self):
        ScanHistory.objects.create(
            cluster=self.cluster,
            snapshot_data={"total_nodes": 3, "total_vms": 25},
            scanned_at=self.now,
        )
        data = _collect_cluster_data(self.cluster)
        self.assertIn("scan_history", data)
        self.assertEqual(len(data["scan_history"]), 1)
        self.assertEqual(data["scan_history"][0]["snapshot_data"]["total_nodes"], 3)

    def test_no_history_when_empty(self):
        data = _collect_cluster_data(self.cluster)
        self.assertNotIn("scan_history", data)


# ===================================================================
# 3. ClusterSyncView 测试
# ===================================================================


class ClusterSyncViewTest(TestCase):
    """POST /api/clusters/<pk>/sync/"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="syncuser", password="testpass123", email="sync@test.com",
        )
        self.client.force_authenticate(user=self.user)
        self.cluster = _make_cluster()
        self.url = f"/api/clusters/{self.cluster.id}/sync/"

    def test_requires_authentication(self):
        self.client.force_authenticate(user=None)
        resp = self.client.post(self.url, format="json")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_cluster_not_found(self):
        resp = self.client.post("/api/clusters/9999/sync/", format="json")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("不存在", resp.data["error"])

    def test_sync_not_enabled(self):
        self.cluster.sync_enabled = False
        self.cluster.save(update_fields=["sync_enabled"])
        resp = self.client.post(self.url, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("未启用", resp.data["error"])

    def test_sync_missing_url(self):
        self.cluster.sync_url = ""
        self.cluster.save(update_fields=["sync_url"])
        resp = self.client.post(self.url, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("同步目标地址", resp.data["error"])

    @patch("apps.clusters.sync.requests.post")
    def test_sync_succeeds(self, mock_post):
        _make_node(self.cluster)

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"ok": True}
        mock_resp.elapsed.total_seconds.return_value = 0.6
        mock_post.return_value = mock_resp

        resp = self.client.post(self.url, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data["ok"])

        # 验证 cluster.last_synced_at 已更新
        self.cluster.refresh_from_db()
        self.assertIsNotNone(self.cluster.last_synced_at)

    @patch("apps.clusters.sync.requests.post")
    def test_sync_passes_force_full(self, mock_post):
        _make_node(self.cluster)

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"ok": True}
        mock_resp.elapsed.total_seconds.return_value = 0.3
        mock_post.return_value = mock_resp

        resp = self.client.post(self.url, {"force_full": True}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        sent_json = mock_post.call_args[1].get("json") or mock_post.call_args[0][1]
        self.assertEqual(sent_json["sync_type"], "full")

    @patch("apps.clusters.sync.requests.post")
    def test_sync_error_returns_400(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = "Unauthorized"
        mock_post.return_value = mock_resp

        resp = self.client.post(self.url, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(resp.data["ok"])
