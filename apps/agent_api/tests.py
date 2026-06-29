from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.clusters.models import Cluster
from apps.scanner.models import ClusterNode, LXC, ScanHistory, Storage, VM

from .models import AgentInstance, ScanTask


def _create_user_cluster():
    """创建测试用户和集群"""
    user = User.objects.create_user(
        username="agent_tester", email="agent@test.com", password="Test1234!"
    )
    cluster = Cluster.objects.create(
        user=user, name="test-cluster", agent_token="test-token-001"
    )
    return user, cluster


def _scan_payload(cluster_id: str, agent_id: str) -> dict:
    """构造一份最小化的扫描上传数据"""
    return {
        "agent_id": agent_id,
        "cluster_id": cluster_id,
        "scanned_at": "2026-06-29T10:30:00Z",
        "version": "pve-manager/8.2.4",
        "nodes": [
            {
                "name": "pve-1",
                "status": "online",
                "pve_version": "8.2.4/abc",
                "kernel_version": "6.8.8-1-pve",
                "cpu_model": "AMD EPYC 7443P",
                "cpu_cores": 48,
                "cpu_sockets": 2,
                "cpu_load": 35.0,
                "memory_total_mb": 131072,
                "memory_used_mb": 65536,
                "memory_free_mb": 65536,
                "memory_usage_pct": 50.0,
                "rootfs_total_gb": 100.0,
                "rootfs_used_gb": 45.2,
                "rootfs_avail_gb": 54.8,
                "swap_total_mb": 4096,
                "swap_used_mb": 128,
                "disk_io_delay_ms": 12.5,
                "diskstat": [
                    {"dev": "sda", "read": 1000, "write": 2000, "read_ios": 10, "write_ios": 20, "io_ms": 12.5}
                ],
                "ip_address": "192.168.1.10",
                "uptime_seconds": 1209600,
                "is_ceph_node": False,
                "vms": [
                    {
                        "vmid": 100,
                        "name": "web-server",
                        "status": "running",
                        "cpu_cores": 4,
                        "cpu_sockets": 1,
                        "cpu_usage": 25.0,
                        "memory_mb": 8192,
                        "memory_used_mb": 4096,
                        "disk_gb": 50.0,
                        "max_disk_gb": 100.0,
                        "net_in_bps": 1048576,
                        "net_out_bps": 524288,
                        "uptime_seconds": 604800,
                        "os_type": "l26",
                        "tags": "production",
                    },
                    {
                        "vmid": 101,
                        "name": "db-server",
                        "status": "running",
                        "cpu_cores": 8,
                        "cpu_sockets": 1,
                        "cpu_usage": 60.0,
                        "memory_mb": 16384,
                        "memory_used_mb": 12288,
                        "disk_gb": 200.0,
                        "max_disk_gb": 500.0,
                        "tags": "production,database",
                    },
                ],
                "containers": [
                    {
                        "vmid": 200,
                        "name": "redis-cache",
                        "status": "running",
                        "cpu_cores": 2,
                        "cpu_usage": 15.0,
                        "memory_mb": 2048,
                        "memory_used_mb": 1024,
                        "swap_mb": 512,
                        "swap_used_mb": 0,
                        "disk_gb": 20.0,
                        "uptime_seconds": 86400,
                        "tags": "cache",
                    },
                ],
                "storages": [
                    {
                        "name": "local",
                        "type": "dir",
                        "active": True,
                        "used_gb": 500.0,
                        "avail_gb": 1500.0,
                        "total_gb": 2000.0,
                        "used_fraction": 0.25,
                        "content_types": "images,rootdir,vztmpl,iso",
                        "shared": False,
                    },
                ],
                "networks": [
                    {
                        "name": "vmbr0",
                        "type": "bridge",
                        "active": True,
                        "method": "static",
                        "address": "192.168.1.10/24",
                        "gateway": "192.168.1.1",
                        "speed_mbps": 10000,
                    },
                ],
            },
        ],
        "ceph": {
            "health": "HEALTH_OK",
            "total_osds": 12,
            "up_osds": 12,
            "in_osds": 12,
            "pool_count": 4,
            "total_used_gb": 2048.0,
            "total_avail_gb": 6144.0,
            "total_space_gb": 8192.0,
        },
    }


# ============================================================
# 1. Agent 注册
# ============================================================

class AgentRegisterAPITest(TestCase):
    """POST /api/agent/register/"""

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/agent/register/"
        _, self.cluster = _create_user_cluster()

    def test_register_success(self):
        resp = self.client.post(self.url, {
            "agent_token": "test-token-001",
            "pve_api_endpoint": "https://192.168.1.100:8006",
            "pve_username": "root@pam",
            "pve_password": "pvepass",
            "hostname": "pve-node-1",
            "scan_interval": 3600,
        }, format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertIn("agent_id", resp.data)
        self.assertEqual(resp.data["status"], "online")
        self.assertTrue(AgentInstance.objects.filter(hostname="pve-node-1").exists())

    def test_register_invalid_token(self):
        resp = self.client.post(self.url, {
            "agent_token": "wrong-token",
            "pve_api_endpoint": "https://192.168.1.100:8006",
            "pve_username": "root@pam",
            "pve_password": "pass",
            "hostname": "pve-node-1",
        }, format="json")
        self.assertEqual(resp.status_code, 403)

    def test_register_missing_fields(self):
        resp = self.client.post(self.url, {}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_register_missing_token(self):
        resp = self.client.post(self.url, {
            "pve_api_endpoint": "https://192.168.1.100:8006",
            "pve_username": "root@pam",
            "pve_password": "pass",
            "hostname": "pve-node-1",
        }, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_register_missing_pve_endpoint(self):
        resp = self.client.post(self.url, {
            "agent_token": "test-token-001",
            "pve_username": "root@pam",
            "pve_password": "pass",
            "hostname": "pve-node-1",
        }, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_register_reuse_hostname_updates(self):
        """同一集群相同 hostname 重复注册 → 更新而非新建"""
        self.client.post(self.url, {
            "agent_token": "test-token-001",
            "pve_api_endpoint": "https://192.168.1.100:8006",
            "pve_username": "root@pam",
            "pve_password": "pass",
            "hostname": "pve-node-1",
            "scan_interval": 3600,
        }, format="json")
        resp2 = self.client.post(self.url, {
            "agent_token": "test-token-001",
            "pve_api_endpoint": "https://192.168.1.101:8006",
            "pve_username": "root@pam",
            "pve_password": "newpass",
            "hostname": "pve-node-1",
            "scan_interval": 1800,
        }, format="json")
        self.assertEqual(resp2.status_code, 201)
        # 只有一条记录
        self.assertEqual(AgentInstance.objects.filter(hostname="pve-node-1").count(), 1)
        agent = AgentInstance.objects.get(hostname="pve-node-1")
        self.assertEqual(agent.pve_api_endpoint, "https://192.168.1.101:8006")
        self.assertEqual(agent.scan_interval, 1800)

    def test_register_activates_cluster(self):
        """注册后集群状态从 pending 变为 active"""
        self.assertEqual(self.cluster.status, Cluster.Status.PENDING)
        self.client.post(self.url, {
            "agent_token": "test-token-001",
            "pve_api_endpoint": "https://192.168.1.100:8006",
            "pve_username": "root@pam",
            "pve_password": "pass",
            "hostname": "pve-node-1",
        }, format="json")
        self.cluster.refresh_from_db()
        self.assertEqual(self.cluster.status, Cluster.Status.ACTIVE)


# ============================================================
# 2. Agent 心跳
# ============================================================

class AgentHeartbeatAPITest(TestCase):
    """POST /api/agent/heartbeat/"""

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/agent/heartbeat/"
        _, self.cluster = _create_user_cluster()
        self.agent = AgentInstance.objects.create(
            cluster=self.cluster,
            agent_id="test-agent-id-001",
            hostname="pve-node-1",
            status=AgentInstance.Status.ONLINE,
        )

    def test_heartbeat_success(self):
        resp = self.client.post(self.url, {
            "agent_id": "test-agent-id-001",
            "status": "online",
            "current_task": "",
        }, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["ok"])
        self.agent.refresh_from_db()
        self.assertEqual(self.agent.status, "online")

    def test_heartbeat_with_task(self):
        resp = self.client.post(self.url, {
            "agent_id": "test-agent-id-001",
            "status": "online",
            "current_task": "scanning",
        }, format="json")
        self.assertEqual(resp.status_code, 200)
        self.agent.refresh_from_db()
        self.assertEqual(self.agent.current_task, "scanning")

    def test_heartbeat_updates_status(self):
        self.client.post(self.url, {
            "agent_id": "test-agent-id-001",
            "status": "error",
        }, format="json")
        self.agent.refresh_from_db()
        self.assertEqual(self.agent.status, "error")

    def test_heartbeat_nonexistent_agent(self):
        resp = self.client.post(self.url, {
            "agent_id": "nonexistent-id",
            "status": "online",
        }, format="json")
        self.assertEqual(resp.status_code, 404)

    def test_heartbeat_missing_agent_id(self):
        resp = self.client.post(self.url, {
            "status": "online",
        }, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_heartbeat_missing_fields(self):
        resp = self.client.post(self.url, {}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_heartbeat_invalid_status(self):
        resp = self.client.post(self.url, {
            "agent_id": "test-agent-id-001",
            "status": "invalid-status",
        }, format="json")
        self.assertEqual(resp.status_code, 400)


# ============================================================
# 3. 扫描数据上传
# ============================================================

class ScanUploadAPITest(TestCase):
    """POST /api/agent/scan/upload/"""

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/agent/scan/upload/"
        _, self.cluster = _create_user_cluster()
        self.agent = AgentInstance.objects.create(
            cluster=self.cluster,
            agent_id="test-agent-id-001",
            hostname="pve-node-1",
        )

    def test_upload_full_scan_success(self):
        payload = _scan_payload(str(self.cluster.id), "test-agent-id-001")
        resp = self.client.post(self.url, payload, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["ok"])
        self.assertIn("scan_task_id", resp.data)

    def test_upload_creates_cluster_node(self):
        payload = _scan_payload(str(self.cluster.id), "test-agent-id-001")
        self.client.post(self.url, payload, format="json")
        self.assertTrue(ClusterNode.objects.filter(node_name="pve-1").exists())

    def test_upload_creates_vms(self):
        payload = _scan_payload(str(self.cluster.id), "test-agent-id-001")
        self.client.post(self.url, payload, format="json")
        self.assertEqual(VM.objects.count(), 2)
        self.assertTrue(VM.objects.filter(vmid=100, name="web-server").exists())
        self.assertTrue(VM.objects.filter(vmid=101, name="db-server").exists())

    def test_upload_creates_lxc(self):
        payload = _scan_payload(str(self.cluster.id), "test-agent-id-001")
        self.client.post(self.url, payload, format="json")
        self.assertEqual(LXC.objects.count(), 1)
        self.assertTrue(LXC.objects.filter(vmid=200, name="redis-cache").exists())

    def test_upload_creates_storage(self):
        payload = _scan_payload(str(self.cluster.id), "test-agent-id-001")
        self.client.post(self.url, payload, format="json")
        self.assertEqual(Storage.objects.count(), 1)
        st = Storage.objects.first()
        self.assertEqual(st.storage_name, "local")
        self.assertEqual(st.type, "dir")

    def test_upload_creates_scan_history(self):
        payload = _scan_payload(str(self.cluster.id), "test-agent-id-001")
        self.client.post(self.url, payload, format="json")
        self.assertEqual(ScanHistory.objects.count(), 1)
        history = ScanHistory.objects.first()
        self.assertEqual(history.snapshot_data["total_nodes"], 1)
        self.assertEqual(history.snapshot_data["total_vms"], 2)
        self.assertEqual(history.snapshot_data["total_lxc"], 1)

    def test_upload_creates_scan_task(self):
        payload = _scan_payload(str(self.cluster.id), "test-agent-id-001")
        self.client.post(self.url, payload, format="json")
        self.assertEqual(ScanTask.objects.count(), 1)
        task = ScanTask.objects.first()
        self.assertEqual(task.status, ScanTask.Status.COMPLETED)
        self.assertEqual(task.total_nodes, 1)
        self.assertIsNotNone(task.completed_at)
        self.assertIsNotNone(task.duration_seconds)

    def test_upload_updates_cluster_stats(self):
        payload = _scan_payload(str(self.cluster.id), "test-agent-id-001")
        self.client.post(self.url, payload, format="json")
        self.cluster.refresh_from_db()
        self.assertEqual(self.cluster.total_nodes, 1)
        self.assertEqual(self.cluster.total_vms, 2)
        self.assertEqual(self.cluster.total_lxc, 1)
        self.assertEqual(self.cluster.total_storage, 1)
        self.assertEqual(self.cluster.pve_version, "pve-manager/8.2.4")

    def test_upload_updates_agent_stats(self):
        payload = _scan_payload(str(self.cluster.id), "test-agent-id-001")
        self.client.post(self.url, payload, format="json")
        self.agent.refresh_from_db()
        self.assertEqual(self.agent.total_scans, 1)
        self.assertIsNotNone(self.agent.last_scan_at)
        self.assertEqual(self.agent.current_task, "")

    def test_upload_stores_diskstat(self):
        payload = _scan_payload(str(self.cluster.id), "test-agent-id-001")
        self.client.post(self.url, payload, format="json")
        node = ClusterNode.objects.first()
        self.assertEqual(node.disk_io_delay_ms, 12.5)
        self.assertEqual(len(node.diskstat), 1)
        self.assertEqual(node.diskstat[0]["dev"], "sda")

    def test_upload_nonexistent_agent(self):
        payload = _scan_payload(str(self.cluster.id), "bad-agent-id")
        resp = self.client.post(self.url, payload, format="json")
        self.assertEqual(resp.status_code, 404)

    def test_upload_nonexistent_cluster(self):
        payload = _scan_payload("999999", "test-agent-id-001")
        resp = self.client.post(self.url, payload, format="json")
        self.assertEqual(resp.status_code, 404)

    def test_upload_missing_fields(self):
        resp = self.client.post(self.url, {}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_upload_empty_nodes(self):
        payload = _scan_payload(str(self.cluster.id), "test-agent-id-001")
        payload["nodes"] = []
        resp = self.client.post(self.url, payload, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(ClusterNode.objects.count(), 0)

    def test_upload_no_ceph(self):
        """无 Ceph 数据时仍能正常上传"""
        payload = _scan_payload(str(self.cluster.id), "test-agent-id-001")
        payload["ceph"] = None
        resp = self.client.post(self.url, payload, format="json")
        self.assertEqual(resp.status_code, 200)

    def test_upload_vm_fields_accuracy(self):
        """验证 VM 字段精确写入"""
        payload = _scan_payload(str(self.cluster.id), "test-agent-id-001")
        self.client.post(self.url, payload, format="json")
        vm = VM.objects.get(vmid=100)
        self.assertEqual(vm.name, "web-server")
        self.assertEqual(vm.status, "running")
        self.assertEqual(vm.cpu_cores, 4)
        self.assertEqual(vm.cpu_usage, 25.0)
        self.assertEqual(vm.memory_mb, 8192)
        self.assertEqual(vm.memory_used_mb, 4096)
        self.assertEqual(vm.os_type, "l26")
        self.assertEqual(vm.tags, "production")

    def test_upload_node_io_fields(self):
        """验证节点 I/O 延迟字段"""
        payload = _scan_payload(str(self.cluster.id), "test-agent-id-001")
        self.client.post(self.url, payload, format="json")
        node = ClusterNode.objects.first()
        self.assertEqual(node.cpu_load, 35.0)
        self.assertEqual(node.memory_total_mb, 131072)
        self.assertEqual(node.memory_usage_pct, 50.0)
        self.assertEqual(node.disk_io_delay_ms, 12.5)
        self.assertEqual(node.uptime_seconds, 1209600)


# ============================================================
# 4. 任务查询
# ============================================================

class AgentTasksAPITest(TestCase):
    """GET /api/agent/tasks/"""

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/agent/tasks/"
        _, self.cluster = _create_user_cluster()
        self.agent = AgentInstance.objects.create(
            cluster=self.cluster,
            agent_id="test-agent-id-001",
            hostname="pve-node-1",
        )

    def test_get_tasks_empty(self):
        resp = self.client.get(self.url, {"agent_id": "test-agent-id-001"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, [])

    def test_get_tasks_returns_running_tasks(self):
        """只返回其他 Agent 的 running 状态的任务"""
        other_agent = AgentInstance.objects.create(
            cluster=self.cluster, agent_id="other-agent-id",
            hostname="pve-node-2",
        )
        ScanTask.objects.create(
            agent=other_agent, cluster=self.cluster,
            task_type="full_scan", status=ScanTask.Status.RUNNING,
        )
        resp = self.client.get(self.url, {"agent_id": "test-agent-id-001"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)

    def test_get_tasks_excludes_completed(self):
        ScanTask.objects.create(
            agent=self.agent, cluster=self.cluster,
            task_type="full_scan", status=ScanTask.Status.COMPLETED,
        )
        resp = self.client.get(self.url, {"agent_id": "test-agent-id-001"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 0)

    def test_get_tasks_excludes_own_agent(self):
        """不返回自己创建的任务"""
        ScanTask.objects.create(
            agent=self.agent, cluster=self.cluster,
            task_type="full_scan", status=ScanTask.Status.RUNNING,
        )
        resp = self.client.get(self.url, {"agent_id": "test-agent-id-001"})
        self.assertEqual(len(resp.data), 0)

    def test_get_tasks_another_agent(self):
        """返回其他 Agent 创建的 running 任务"""
        other_agent = AgentInstance.objects.create(
            cluster=self.cluster, agent_id="other-agent-id",
            hostname="pve-node-2",
        )
        ScanTask.objects.create(
            agent=other_agent, cluster=self.cluster,
            task_type="full_scan", status=ScanTask.Status.RUNNING,
        )
        resp = self.client.get(self.url, {"agent_id": "test-agent-id-001"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)

    def test_get_tasks_nonexistent_agent(self):
        resp = self.client.get(self.url, {"agent_id": "nonexistent"})
        self.assertEqual(resp.status_code, 404)

    def test_get_tasks_missing_agent_id(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 400)


# ============================================================
# 5. 集成测试：完整扫描流程
# ============================================================

class AgentScanIntegrationTest(TestCase):
    """完整流程：注册 → 心跳 → 扫描上传 → 任务查询"""

    def setUp(self):
        self.client = APIClient()
        _, self.cluster = _create_user_cluster()

    def test_full_scan_flow(self):
        # 1. 注册
        reg = self.client.post("/api/agent/register/", {
            "agent_token": "test-token-001",
            "pve_api_endpoint": "https://192.168.1.100:8006",
            "pve_username": "root@pam",
            "pve_password": "pass",
            "hostname": "pve-node-1",
            "scan_interval": 3600,
        }, format="json")
        self.assertEqual(reg.status_code, 201)
        agent_id = reg.data["agent_id"]

        # 2. 心跳
        hb = self.client.post("/api/agent/heartbeat/", {
            "agent_id": agent_id,
            "status": "online",
        }, format="json")
        self.assertEqual(hb.status_code, 200)

        # 3. 扫描上传
        payload = _scan_payload(str(self.cluster.id), agent_id)
        upload = self.client.post("/api/agent/scan/upload/", payload, format="json")
        self.assertEqual(upload.status_code, 200)

        # 4. 验证数据
        self.assertEqual(ClusterNode.objects.count(), 1)
        self.assertEqual(VM.objects.count(), 2)
        self.assertEqual(LXC.objects.count(), 1)
        self.assertEqual(Storage.objects.count(), 1)
        self.assertEqual(ScanHistory.objects.count(), 1)

        # 5. 查询任务
        tasks = self.client.get("/api/agent/tasks/", {"agent_id": agent_id})
        self.assertEqual(tasks.status_code, 200)

        # 6. 集群状态
        self.cluster.refresh_from_db()
        self.assertEqual(self.cluster.status, Cluster.Status.ACTIVE)
        self.assertEqual(self.cluster.total_nodes, 1)
        self.assertEqual(self.cluster.total_vms, 2)

    def test_multiple_scan_increments_counter(self):
        """多次扫描递增 Agent 计数"""
        reg = self.client.post("/api/agent/register/", {
            "agent_token": "test-token-001",
            "pve_api_endpoint": "https://192.168.1.100:8006",
            "pve_username": "root@pam",
            "pve_password": "pass",
            "hostname": "pve-node-1",
        }, format="json")
        agent_id = reg.data["agent_id"]

        payload1 = _scan_payload(str(self.cluster.id), agent_id)
        payload1["scanned_at"] = "2026-06-29T10:00:00Z"
        self.client.post("/api/agent/scan/upload/", payload1, format="json")

        payload2 = _scan_payload(str(self.cluster.id), agent_id)
        payload2["scanned_at"] = "2026-06-29T11:00:00Z"
        self.client.post("/api/agent/scan/upload/", payload2, format="json")

        agent = AgentInstance.objects.get(agent_id=agent_id)
        self.assertEqual(agent.total_scans, 2)
        self.assertEqual(ScanTask.objects.count(), 2)
        self.assertEqual(ScanHistory.objects.count(), 2)


# ============================================================
# 6. Agent 卸载通知
# ============================================================

class AgentUnregisterAPITest(TestCase):
    """POST /api/agent/unregister/"""

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/agent/unregister/"
        _, self.cluster = _create_user_cluster()
        self.agent = AgentInstance.objects.create(
            cluster=self.cluster,
            agent_id="test-agent-id-001",
            hostname="pve-node-1",
            status=AgentInstance.Status.ONLINE,
        )

    def test_unregister_success(self):
        resp = self.client.post(self.url, {
            "agent_id": "test-agent-id-001",
        }, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["ok"])
        self.agent.refresh_from_db()
        self.assertEqual(self.agent.status, AgentInstance.Status.OFFLINE)

    def test_unregister_nonexistent_agent(self):
        resp = self.client.post(self.url, {
            "agent_id": "nonexistent",
        }, format="json")
        self.assertEqual(resp.status_code, 404)

    def test_unregister_missing_agent_id(self):
        resp = self.client.post(self.url, {}, format="json")
        self.assertEqual(resp.status_code, 400)


# ============================================================
# 7. 版本查询
# ============================================================

class AgentVersionAPITest(TestCase):
    """GET /api/agent/version/"""

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/agent/version/"

    def test_version_returns_info(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("latest_version", resp.data)
        self.assertIn("download_url", resp.data)
        self.assertIn("changelog", resp.data)

    def test_version_has_current(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.data["latest_version"], "0.2.0")


# ============================================================
# 8. 安装脚本
# ============================================================

class AgentInstallScriptAPITest(TestCase):
    """GET /api/agent/install.sh"""

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/agent/install.sh"

    def test_install_script_returns_bash(self):
        resp = self.client.get(self.url, {
            "token": "test-token",
            "platform": "https://platform:8000",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/plain", resp["Content-Type"])
        content = resp.content.decode()
        self.assertIn("#!/bin/bash", content)
        self.assertIn("test-token", content)
        self.assertIn("pcs-agent", content)

    def test_install_script_contains_platform(self):
        resp = self.client.get(self.url, {"token": "abc123"})
        content = resp.content.decode()
        # platform_url 从请求 host 自动推导
        self.assertIn("testserver", content)
        self.assertIn("abc123", content)

    def test_install_script_queries_pve_info(self):
        resp = self.client.get(self.url, {"token": "abc123"})
        content = resp.content.decode()
        # 新版脚本从平台查询 PVE 信息
        self.assertIn("pve-info", content)

    def test_uninstall_script(self):
        resp = self.client.get(self.url, {"uninstall": ""})
        content = resp.content.decode()
        self.assertIn("卸载", content)
        self.assertIn("systemctl stop", content)
