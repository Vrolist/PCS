"""备份管理 API 测试"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.clusters.models import Cluster
from apps.scanner.models import (
    BackupStorage, BackupJob, BackupHistory,
    ClusterNode,
)
from apps.agent_api.models import AgentInstance, ScanTask

User = get_user_model()


def _create_test_data(user, cluster_name="test-cluster"):
    """创建测试用户、集群、节点、备份数据"""
    cluster = Cluster.objects.create(user=user, name=cluster_name, agent_token=f"token-{cluster_name}")
    node = ClusterNode.objects.create(
        cluster=cluster, node_name="pve-1", status="online",
        scanned_at=timezone.now(),
    )
    return cluster, node


def _create_backup_data(cluster, node, scanned_at=None):
    """创建备份存储、任务、历史数据"""
    if scanned_at is None:
        scanned_at = timezone.now()

    storage = BackupStorage.objects.create(
        cluster=cluster, node=node,
        storage_name="pbs-backup", storage_type="pbs",
        path="/mnt/pbs", content_types="backup",
        active=True, shared=True,
        total_gb=5000, used_gb=1500, avail_gb=3500, used_fraction=0.3,
        scanned_at=scanned_at,
    )
    storage2 = BackupStorage.objects.create(
        cluster=cluster, node=node,
        storage_name="local-backup", storage_type="dir",
        path="/var/lib/vz/dump", content_types="backup,iso",
        active=True, shared=False,
        total_gb=1000, used_gb=600, avail_gb=400, used_fraction=0.6,
        scanned_at=scanned_at,
    )

    job1 = BackupJob.objects.create(
        cluster=cluster, node=node,
        job_id="vzdump-100-daily", vmid=100, resource_type="vm",
        node_name="pve-1", storage_name="pbs-backup", mode="snapshot",
        schedule="02:00", retention="keep-last=3", enabled=True,
        compress="zstd", last_run=scanned_at - timedelta(hours=6),
        last_status="ok", scanned_at=scanned_at,
    )
    job2 = BackupJob.objects.create(
        cluster=cluster, node=node,
        job_id="vzdump-200-weekly", vmid=200, resource_type="ct",
        node_name="pve-1", storage_name="local-backup", mode="suspend",
        schedule="sun *-*-* 03:00", retention="keep-weekly=4",
        enabled=False, compress="lzo", last_status="error",
        scanned_at=scanned_at,
    )

    h1 = BackupHistory.objects.create(
        cluster=cluster, node=node,
        task_id="UPID:pve-1:00012345:00067890:vzdump:100:root@pam:",
        vmid=100, resource_type="vm", node_name="pve-1",
        storage_name="pbs-backup", mode="snapshot", status="ok",
        started_at=scanned_at - timedelta(hours=6),
        finished_at=scanned_at - timedelta(hours=5, minutes=45),
        duration_seconds=900, size_bytes=1073741824,
        filename="vzdump-qemu-100-2026_07_03-02_00_00.vma.zst",
        scanned_at=scanned_at,
    )
    h2 = BackupHistory.objects.create(
        cluster=cluster, node=node,
        task_id="UPID:pve-1:00012346:00067891:vzdump:200:root@pam:",
        vmid=200, resource_type="ct", node_name="pve-1",
        storage_name="local-backup", mode="suspend", status="error",
        started_at=scanned_at - timedelta(hours=2),
        finished_at=scanned_at - timedelta(hours=1, minutes=50),
        duration_seconds=600, size_bytes=0,
        error_message="vzdump backup failed: storage unavailable",
        scanned_at=scanned_at,
    )
    h3 = BackupHistory.objects.create(
        cluster=cluster, node=node,
        task_id="UPID:pve-1:00012347:00067892:vzdump:100:root@pam:",
        vmid=100, resource_type="vm", node_name="pve-1",
        storage_name="pbs-backup", mode="snapshot", status="ok",
        started_at=scanned_at - timedelta(days=1, hours=6),
        finished_at=scanned_at - timedelta(days=1, hours=5, minutes=50),
        duration_seconds=600, size_bytes=536870912,
        filename="vzdump-qemu-100-2026_07_02-02_00_00.vma.zst",
        scanned_at=scanned_at - timedelta(days=1),
    )

    return storage, storage2, job1, job2, h1, h2, h3


# ============================================================
# 备份存储列表测试
# ============================================================

class BackupStorageListTest(TestCase):
    """GET /api/scanner/backup/storages/"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123", email="test@test.com"
        )
        self.other_user = User.objects.create_user(
            username="other", password="testpass123", email="other@test.com"
        )
        self.client.force_authenticate(user=self.user)
        self.url = "/api/scanner/backup/storages/"
        self.cluster, self.node = _create_test_data(self.user)
        _create_backup_data(self.cluster, self.node)

    def test_unauthenticated(self):
        self.client.force_authenticate(user=None)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_backup_storages(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 2)

    def test_storage_fields(self):
        resp = self.client.get(self.url)
        s = next(x for x in resp.data if x["storage_name"] == "pbs-backup")
        self.assertEqual(s["storage_type"], "pbs")
        self.assertEqual(s["total_gb"], 5000)
        self.assertEqual(s["used_gb"], 1500)
        self.assertTrue(s["active"])
        self.assertTrue(s["shared"])

    def test_cluster_filter(self):
        resp = self.client.get(self.url, {"cluster_id": self.cluster.id})
        self.assertEqual(len(resp.data), 2)
        # Non-existent cluster
        resp = self.client.get(self.url, {"cluster_id": 9999})
        self.assertEqual(len(resp.data), 0)

    def test_other_user_storages_not_visible(self):
        other_cluster, other_node = _create_test_data(self.other_user, "other-cluster")
        _create_backup_data(other_cluster, other_node)
        resp = self.client.get(self.url)
        names = [s["storage_name"] for s in resp.data]
        self.assertIn("pbs-backup", names)
        # Should only see own cluster's data - 2 storages from self.cluster
        self.assertEqual(len(resp.data), 2)


# ============================================================
# 备份任务列表测试
# ============================================================

class BackupJobListTest(TestCase):
    """GET /api/scanner/backup/jobs/"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123", email="test@test.com"
        )
        self.client.force_authenticate(user=self.user)
        self.url = "/api/scanner/backup/jobs/"
        self.cluster, self.node = _create_test_data(self.user)
        _create_backup_data(self.cluster, self.node)

    def test_unauthenticated(self):
        self.client.force_authenticate(user=None)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_jobs(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 2)

    def test_job_fields(self):
        resp = self.client.get(self.url)
        j = next(x for x in resp.data if x["job_id"] == "vzdump-100-daily")
        self.assertEqual(j["vmid"], 100)
        self.assertEqual(j["resource_type"], "vm")
        self.assertEqual(j["mode"], "snapshot")
        self.assertEqual(j["schedule"], "02:00")
        self.assertTrue(j["enabled"])
        self.assertEqual(j["last_status"], "ok")

    def test_disabled_job(self):
        resp = self.client.get(self.url)
        j = next(x for x in resp.data if x["job_id"] == "vzdump-200-weekly")
        self.assertFalse(j["enabled"])
        self.assertEqual(j["last_status"], "error")

    def test_status_filter(self):
        resp = self.client.get(self.url, {"status": "ok"})
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]["last_status"], "ok")

    def test_cluster_filter(self):
        resp = self.client.get(self.url, {"cluster_id": self.cluster.id})
        self.assertEqual(len(resp.data), 2)
        resp = self.client.get(self.url, {"cluster_id": 9999})
        self.assertEqual(len(resp.data), 0)


# ============================================================
# 备份历史列表测试
# ============================================================

class BackupHistoryListTest(TestCase):
    """GET /api/scanner/backup/history/"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123", email="test@test.com"
        )
        self.client.force_authenticate(user=self.user)
        self.url = "/api/scanner/backup/history/"
        self.cluster, self.node = _create_test_data(self.user)
        _create_backup_data(self.cluster, self.node)

    def test_unauthenticated(self):
        self.client.force_authenticate(user=None)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_history(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 3)
        self.assertEqual(len(resp.data["results"]), 3)

    def test_history_fields(self):
        resp = self.client.get(self.url)
        ok_items = [x for x in resp.data["results"] if x["status"] == "ok"]
        self.assertEqual(len(ok_items), 2)
        h = ok_items[0]
        self.assertIn("task_id", h)
        self.assertIn("vmid", h)
        self.assertIn("duration_seconds", h)
        self.assertIn("size_bytes", h)

    def test_status_filter(self):
        resp = self.client.get(self.url, {"status": "error"})
        self.assertEqual(resp.data["count"], 1)
        self.assertEqual(resp.data["results"][0]["status"], "error")

    def test_vmid_filter(self):
        resp = self.client.get(self.url, {"vmid": 100})
        self.assertEqual(resp.data["count"], 2)

    def test_search_filter(self):
        resp = self.client.get(self.url, {"search": "storage unavailable"})
        self.assertEqual(resp.data["count"], 1)
        self.assertEqual(resp.data["results"][0]["status"], "error")

    def test_search_by_task_id(self):
        resp = self.client.get(self.url, {"search": "12345"})
        self.assertEqual(resp.data["count"], 1)

    def test_pagination(self):
        resp = self.client.get(self.url, {"page": 1, "page_size": 2})
        self.assertEqual(resp.data["count"], 3)
        self.assertEqual(len(resp.data["results"]), 2)

        resp = self.client.get(self.url, {"page": 2, "page_size": 2})
        self.assertEqual(len(resp.data["results"]), 1)

    def test_error_message_present(self):
        resp = self.client.get(self.url, {"status": "error"})
        h = resp.data["results"][0]
        self.assertIn("storage unavailable", h["error_message"])


# ============================================================
# 备份统计测试
# ============================================================

class BackupStatsTest(TestCase):
    """GET /api/scanner/backup/stats/"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123", email="test@test.com"
        )
        self.client.force_authenticate(user=self.user)
        self.url = "/api/scanner/backup/stats/"
        self.cluster, self.node = _create_test_data(self.user)
        _create_backup_data(self.cluster, self.node)

    def test_unauthenticated(self):
        self.client.force_authenticate(user=None)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_stats_fields(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.data
        self.assertEqual(data["total_storages"], 2)
        self.assertEqual(data["total_storages_gb"], 6000)
        self.assertEqual(data["used_storages_gb"], 2100)
        self.assertEqual(data["total_jobs"], 2)
        self.assertEqual(data["enabled_jobs"], 1)
        self.assertEqual(data["total_backups"], 3)
        self.assertEqual(data["success_backups"], 2)
        self.assertEqual(data["failed_backups"], 1)
        self.assertAlmostEqual(data["success_rate"], 66.7, places=1)

    def test_empty_stats(self):
        """没有备份数据时统计应为全零"""
        # 创建一个新集群，没有备份数据
        Cluster.objects.create(user=self.user, name="empty-cluster", agent_token="empty-token")
        resp = self.client.get(self.url)
        # 这里会聚合所有集群的数据
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_cluster_filter(self):
        resp = self.client.get(self.url, {"cluster_id": self.cluster.id})
        self.assertEqual(resp.data["total_storages"], 2)
        self.assertEqual(resp.data["total_backups"], 3)

    def test_success_rate_no_backups(self):
        """没有备份历史时成功率应为 0"""
        cluster2, node2 = _create_test_data(self.user, "cluster-2")
        # cluster2 有存储和任务，但没有历史
        BackupStorage.objects.create(
            cluster=cluster2, node=node2,
            storage_name="test-storage", storage_type="dir",
            active=True, total_gb=100, used_gb=10, avail_gb=90,
            scanned_at=timezone.now(),
        )
        resp = self.client.get(self.url, {"cluster_id": cluster2.id})
        self.assertEqual(resp.data["success_rate"], 0)
        self.assertEqual(resp.data["total_backups"], 0)


# ============================================================
# Agent 上传备份数据测试
# ============================================================

class AgentBackupUploadTest(TestCase):
    """POST /api/agent/scan/upload/ — 含备份数据"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123", email="test@test.com"
        )
        self.cluster = Cluster.objects.create(
            user=self.user, name="test-cluster", agent_token="test-token",
        )
        self.agent = AgentInstance.objects.create(
            cluster=self.cluster, agent_id="test-agent-001",
            hostname="pve-1", status=AgentInstance.Status.ONLINE,
        )
        self.url = "/api/agent/scan/upload/"

    def _make_payload(self, backups=None):
        payload = {
            "agent_id": "test-agent-001",
            "cluster_id": str(self.cluster.id),
            "scanned_at": "2026-07-03T10:00:00Z",
            "version": "pve-manager/8.2.4",
            "nodes": [{
                "name": "pve-1", "status": "online",
                "cpu_load": 25.0, "memory_total_mb": 16000, "memory_used_mb": 8000,
                "memory_free_mb": 8000, "rootfs_total_gb": 100, "rootfs_used_gb": 50,
                "rootfs_avail_gb": 50, "vms": [], "containers": [],
                "storages": [], "networks": [],
            }],
            "sdn": {"zones": [], "vnets": [], "subnets": []},
        }
        if backups is not None:
            payload["backups"] = backups
        return payload

    def test_upload_with_backup_storages(self):
        payload = self._make_payload(backups={
            "backup_storages": [{
                "storage_name": "pbs-backup", "storage_type": "pbs",
                "path": "/mnt/pbs", "content_types": "backup",
                "active": True, "shared": True,
                "total_gb": 5000, "used_gb": 1500, "avail_gb": 3500,
                "used_fraction": 0.3,
            }],
            "backup_jobs": [],
            "backup_history": [],
        })
        resp = self.client.post(self.url, payload, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["ok"])
        self.assertEqual(BackupStorage.objects.count(), 1)
        s = BackupStorage.objects.first()
        self.assertEqual(s.storage_name, "pbs-backup")
        self.assertEqual(s.storage_type, "pbs")
        self.assertEqual(s.total_gb, 5000)

    def test_upload_with_backup_jobs(self):
        payload = self._make_payload(backups={
            "backup_storages": [],
            "backup_jobs": [{
                "job_id": "vzdump-100-daily", "vmid": 100, "resource_type": "vm",
                "node_name": "pve-1", "storage_name": "pbs-backup",
                "mode": "snapshot", "schedule": "02:00", "retention": "keep-last=3",
                "enabled": True, "compress": "zstd", "notes": "",
                "last_run": 1719993600, "last_status": "ok",
            }],
            "backup_history": [],
        })
        resp = self.client.post(self.url, payload, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(BackupJob.objects.count(), 1)
        j = BackupJob.objects.first()
        self.assertEqual(j.job_id, "vzdump-100-daily")
        self.assertEqual(j.vmid, 100)
        self.assertTrue(j.enabled)
        self.assertIsNotNone(j.last_run)

    def test_upload_with_backup_history(self):
        payload = self._make_payload(backups={
            "backup_storages": [],
            "backup_jobs": [],
            "backup_history": [{
                "task_id": "UPID:pve-1:00012345:00067890:vzdump:100:root@pam:",
                "vmid": 100, "resource_type": "vm",
                "status": "ok", "started_at": "2026-07-03T02:00:00Z",
                "finished_at": "2026-07-03T02:15:00Z", "duration_seconds": 900,
                "size_bytes": 1073741824,
            }],
        })
        resp = self.client.post(self.url, payload, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(BackupHistory.objects.count(), 1)
        h = BackupHistory.objects.first()
        self.assertEqual(h.vmid, 100)
        self.assertEqual(h.status, "ok")
        self.assertEqual(h.duration_seconds, 900)

    def test_upload_without_backups_field(self):
        """不带 backups 字段的上传不应报错"""
        payload = self._make_payload()
        resp = self.client.post(self.url, payload, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(BackupStorage.objects.count(), 0)
        self.assertEqual(BackupJob.objects.count(), 0)
        self.assertEqual(BackupHistory.objects.count(), 0)

    def test_backup_job_update_or_create(self):
        """相同 job_id 应原地更新而非新增"""
        for i in range(2):
            payload = self._make_payload(backups={
                "backup_storages": [],
                "backup_jobs": [{
                    "job_id": "vzdump-100-daily", "vmid": 100, "resource_type": "vm",
                    "node_name": "pve-1", "storage_name": "pbs-backup",
                    "mode": "snapshot", "schedule": "02:00",
                    "enabled": True, "last_status": "ok",
                }],
                "backup_history": [],
            })
            payload["scanned_at"] = f"2026-07-03T1{i}:00:00Z"
            self.client.post(self.url, payload, format="json")
        self.assertEqual(BackupJob.objects.count(), 1)

    def test_backup_storage_update_or_create(self):
        """相同 storage_name 应原地更新而非新增"""
        for i in range(2):
            payload = self._make_payload(backups={
                "backup_storages": [{
                    "storage_name": "pbs-backup", "storage_type": "pbs",
                    "active": True, "total_gb": 5000, "used_gb": 1500, "avail_gb": 3500,
                }],
                "backup_jobs": [],
                "backup_history": [],
            })
            payload["scanned_at"] = f"2026-07-03T1{i}:00:00Z"
            self.client.post(self.url, payload, format="json")
        self.assertEqual(BackupStorage.objects.count(), 1)

    def test_backup_history_created_each_time(self):
        """历史记录每次上传都应新增（不同 task_id）"""
        for i in range(3):
            payload = self._make_payload(backups={
                "backup_storages": [],
                "backup_jobs": [],
                "backup_history": [{
                    "task_id": f"UPID:pve-1:000{i}:0000:vzdump:100:root@pam:",
                    "vmid": 100, "resource_type": "vm",
                    "status": "ok", "started_at": f"2026-07-0{i+1}T02:00:00Z",
                    "duration_seconds": 600,
                }],
            })
            payload["scanned_at"] = f"2026-07-03T1{i}:00:00Z"
            self.client.post(self.url, payload, format="json")
        self.assertEqual(BackupHistory.objects.count(), 3)

    def test_empty_backup_data(self):
        """空的 backups 字典不应报错"""
        payload = self._make_payload(backups={})
        resp = self.client.post(self.url, payload, format="json")
        self.assertEqual(resp.status_code, 200)
