#!/usr/bin/env python3
"""
一键写入 3 个完整测试集群数据（节点 / 虚拟机 / 容器 / 存储 / 网络 / Ceph / HA / 告警 / 历史）。

用法:
  python3 seed_test_clusters.py          # 仅新增（跳过已存在的集群）
  python3 seed_test_clusters.py --clean  # 先删除旧测试数据，再重新写入
"""
import os, sys, django, random

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

import argparse
from datetime import datetime, timedelta, timezone
from apps.accounts.models import User
from apps.clusters.models import Cluster
from apps.scanner.models import (
    ClusterNode, VM, LXC, Storage, NetworkInterface,
    CephStatus, ScanHistory, HAResource,
    DetectionRule, DetectionResult,
)

NOW = datetime.now(timezone.utc)

# ─── CLI ──────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--clean", action="store_true", help="先删除旧测试数据")
args = parser.parse_args()

user = User.objects.first()
if not user:
    print("❌ 数据库中没有用户，请先创建用户")
    sys.exit(1)
print(f"✓ 用户: {user.username}")

# ─── clean ────────────────────────────────────
if args.clean:
    old_ids = Cluster.objects.filter(user=user, name__startswith="测试").values_list("id", flat=True)
    count = len(old_ids)
    if old_ids:
        HAResource.objects.filter(cluster_id__in=old_ids).delete()
        DetectionResult.objects.filter(cluster_id__in=old_ids).delete()
        DetectionRule.objects.filter(cluster_id__in=old_ids).delete()
        ScanHistory.objects.filter(cluster_id__in=old_ids).delete()
        CephStatus.objects.filter(cluster_id__in=old_ids).delete()
        for cls in Cluster.objects.filter(id__in=old_ids):
            for n in cls.nodes.all():
                VM.objects.filter(node=n).delete()
                LXC.objects.filter(node=n).delete()
                Storage.objects.filter(node=n).delete()
                NetworkInterface.objects.filter(node=n).delete()
            cls.nodes.all().delete()
        Cluster.objects.filter(id__in=old_ids).delete()
        print(f"✓ 已清理 {count} 个旧集群及所有关联数据")
    else:
        print("  （无旧数据需清理）")

# ─── skip check ───────────────────────────────
if Cluster.objects.filter(user=user, name__startswith="测试").exists():
    print("⚠ 已存在测试集群，跳过写入（如需重写请加 --clean）")
    sys.exit(0)

# ─── helpers ──────────────────────────────────
def create_cluster(name, desc, endpoint="https://0.0.0.0:8006"):
    c = Cluster.objects.create(
        user=user, name=name, description=desc, status="active",
        pve_endpoint=endpoint, pve_token="test-token", total_nodes=0,
        last_scanned_at=NOW,
    )
    print(f"  ✓ 集群: {name} (id={c.id})")
    return c


def create_node(cluster, name, ip, **kw):
    defaults = dict(
        cluster=cluster, node_name=name, status="online", ip_address=ip,
        pve_version="pve-manager/8.2.4", kernel_version="6.8.12-1-pve",
        cpu_model="Intel Xeon E5-2680 v4", cpu_cores=16, cpu_sockets=2, cpu_load=0.35,
        memory_total_mb=65536, memory_used_mb=24000, memory_free_mb=41536,
        memory_usage_pct=36.6, rootfs_total_gb=238, rootfs_used_gb=45,
        rootfs_avail_gb=181, swap_total_mb=8192, swap_used_mb=128,
        disk_io_delay_ms=2.5, uptime_seconds=2_592_000,
        scanned_at=NOW,
    )
    defaults.update(kw)
    n = ClusterNode.objects.create(**defaults)
    print(f"    节点: {name}")
    return n


def create_iface(node, name, type_, **kw):
    defaults = dict(node=node, name=name, type=type_, active=True, scanned_at=NOW)
    if kw.get("address"):
        defaults["method"] = "static"
    defaults.update(kw)
    return NetworkInterface.objects.create(**defaults)


def create_vm(node, vmid, name, status, cpu_cores, memory_mb, disk_gb, **kw):
    usage = round(random.uniform(0.02, 0.75), 3) if status == "running" else 0
    defaults = dict(
        node=node, vmid=vmid, name=name, status=status,
        cpu_cores=cpu_cores, cpu_sockets=1, cpu_usage=usage,
        memory_mb=memory_mb, memory_used_mb=int(memory_mb * usage) if status == "running" else 0,
        disk_gb=disk_gb, max_disk_gb=disk_gb,
        net_in_bps=random.randint(1000, 500000) if status == "running" else 0,
        net_out_bps=random.randint(500, 300000) if status == "running" else 0,
        disk_write_iops=round(random.uniform(10, 500), 1) if status == "running" else 0,
        disk_read_iops=round(random.uniform(5, 200), 1) if status == "running" else 0,
        uptime_seconds=random.randint(86400, 2_592_000) if status == "running" else 0,
        scanned_at=NOW,
    )
    defaults.update(kw)
    return VM.objects.create(**defaults)


def create_lxc(node, vmid, name, status, cpu_cores, memory_mb, disk_gb, **kw):
    usage = round(random.uniform(0.05, 0.65), 3) if status == "running" else 0
    defaults = dict(
        node=node, vmid=vmid, name=name, status=status,
        cpu_cores=cpu_cores, cpu_usage=usage,
        memory_mb=memory_mb, memory_used_mb=int(memory_mb * usage) if status == "running" else 0,
        swap_mb=kw.pop("swap_mb", memory_mb), swap_used_mb=64,
        disk_gb=disk_gb,
        uptime_seconds=random.randint(86400, 2_592_000) if status == "running" else 0,
        scanned_at=NOW,
    )
    defaults.update(kw)
    return LXC.objects.create(**defaults)


def create_storage(node, name, stype, total_gb, used_gb, content="images,rootdir,vztmpl,backup,iso", shared=False):
    avail = total_gb - used_gb
    return Storage.objects.create(
        node=node, storage_name=name, type=stype, status="available", active=True,
        total_gb=total_gb, used_gb=used_gb, avail_gb=avail,
        used_fraction=round(used_gb / total_gb, 4) if total_gb else 0,
        content_types=content, shared=shared, scanned_at=NOW,
    )


# ════════════════════════════════════════════════
# Cluster A: 5 节点 + Ceph + Bond + HA
# ════════════════════════════════════════════════
print("\n━━━ Cluster A ━━━")
ca = create_cluster(
    "测试A-五节点Bond",
    "生产集群，5节点，Bond聚合+3层网段+Ceph分布式存储",
)

# --- 节点（各异化数据）---
node_a_specs = [
    {"name": "pve-a1", "ip": "192.168.10.1", "cpu_model": "Intel Xeon E5-2680 v4",
     "cpu_cores": 14, "cpu_sockets": 2, "cpu_load": 0.42,
     "memory_total_mb": 128*1024, "memory_used_mb": 68000, "memory_free_mb": 75000,
     "rootfs_total_gb": 479, "rootfs_used_gb": 52, "rootfs_avail_gb": 427,
     "swap_total_mb": 8192, "swap_used_mb": 256, "disk_io_delay_ms": 8.2, "uptime_seconds": 5_184_000},
    {"name": "pve-a2", "ip": "192.168.10.2", "cpu_model": "Intel Xeon E5-2680 v4",
     "cpu_cores": 14, "cpu_sockets": 2, "cpu_load": 0.28,
     "memory_total_mb": 128*1024, "memory_used_mb": 52000, "memory_free_mb": 75000,
     "rootfs_total_gb": 479, "rootfs_used_gb": 198, "rootfs_avail_gb": 281,
     "swap_total_mb": 8192, "swap_used_mb": 0, "disk_io_delay_ms": 3.1, "uptime_seconds": 4_320_000},
    {"name": "pve-a3", "ip": "192.168.10.3", "cpu_model": "Intel Xeon Gold 6248",
     "cpu_cores": 20, "cpu_sockets": 2, "cpu_load": 0.55,
     "memory_total_mb": 256*1024, "memory_used_mb": 145000, "memory_free_mb": 111000,
     "rootfs_total_gb": 953, "rootfs_used_gb": 380, "rootfs_avail_gb": 573,
     "swap_total_mb": 16384, "swap_used_mb": 512, "disk_io_delay_ms": 12.5, "uptime_seconds": 2_592_000},
    {"name": "pve-a4", "ip": "192.168.10.4", "cpu_model": "Intel Xeon Gold 6248",
     "cpu_cores": 20, "cpu_sockets": 2, "cpu_load": 0.18,
     "memory_total_mb": 256*1024, "memory_used_mb": 89000, "memory_free_mb": 167000,
     "rootfs_total_gb": 953, "rootfs_used_gb": 210, "rootfs_avail_gb": 743,
     "swap_total_mb": 16384, "swap_used_mb": 0, "disk_io_delay_ms": 1.8, "uptime_seconds": 1_728_000},
    {"name": "pve-a5", "ip": "192.168.10.5", "cpu_model": "AMD EPYC 7443P",
     "cpu_cores": 24, "cpu_sockets": 2, "cpu_load": 0.65,
     "memory_total_mb": 512*1024, "memory_used_mb": 310000, "memory_free_mb": 202000,
     "rootfs_total_gb": 1907, "rootfs_used_gb": 680, "rootfs_avail_gb": 1227,
     "swap_total_mb": 32768, "swap_used_mb": 1024, "disk_io_delay_ms": 15.0, "uptime_seconds": 864_000},
]
nodes_a = []
for spec in node_a_specs:
    n = create_node(ca, spec["name"], spec["ip"],
        cpu_model=spec["cpu_model"], cpu_cores=spec["cpu_cores"],
        cpu_sockets=spec["cpu_sockets"], cpu_load=spec["cpu_load"],
        memory_total_mb=spec["memory_total_mb"], memory_used_mb=spec["memory_used_mb"],
        memory_free_mb=spec["memory_free_mb"],
        memory_usage_pct=round(spec["memory_used_mb"] / spec["memory_total_mb"] * 100, 1),
        rootfs_total_gb=spec["rootfs_total_gb"], rootfs_used_gb=spec["rootfs_used_gb"],
        rootfs_avail_gb=spec["rootfs_avail_gb"],
        swap_total_mb=spec["swap_total_mb"], swap_used_mb=spec["swap_used_mb"],
        disk_io_delay_ms=spec["disk_io_delay_ms"], uptime_seconds=spec["uptime_seconds"],
        is_ceph_node=True, is_ha_node=True,
    )
    nodes_a.append(n)

# --- 网络接口 ---
for i, node in enumerate(nodes_a, 1):
    create_iface(node, "vmbr0", "bridge", address=f"192.168.10.{i}", gateway="192.168.10.254",
                 bridge_ports="bond0 eno1")
    create_iface(node, "bond0", "bond", bond_mode="802.3ad", bond_slaves="enp1s0 enp2s0")
    create_iface(node, "eno1", "eth")
    create_iface(node, "enp1s0", "eth")
    create_iface(node, "enp2s0", "eth")
    create_iface(node, "bond1", "bond", bond_mode="balance-rr", bond_slaves="enp3s0 enp4s0")
    create_iface(node, "enp3s0", "eth")
    create_iface(node, "enp4s0", "eth")

# --- VM ---
vm_id = 100
vm_defs_a = [
    (0, "web-prod-01",  "running", 4,  8192,  100, "www,prod",   "生产Web服务器-01"),
    (0, "web-prod-02",  "running", 4,  8192,  100, "www,prod",   "生产Web服务器-02"),
    (0, "db-master",    "running", 8,  32768, 500, "db,prod",    "MySQL主库"),
    (1, "db-slave",     "running", 8,  32768, 500, "db,prod",    "MySQL从库"),
    (1, "redis-cache",  "running", 4,  16384, 100, "cache,prod", "Redis缓存集群"),
    (2, "mq-broker",    "running", 4,  16384, 200, "mq,prod",    "RabbitMQ消息队列"),
    (2, "monitoring",   "running", 4,  16384, 200, "ops",        "Prometheus+Grafana监控"),
    (3, "dev-jenkins",  "running", 4,  8192,  200, "ci,dev",     "Jenkins CI服务器"),
    (3, "dev-gitlab",   "running", 4,  8192,  100, "git,dev",    "GitLab代码仓库"),
    (4, "k8s-master",   "running", 4,  16384, 100, "k8s,prod",   "K8S Master节点"),
    (4, "k8s-worker-01","running", 8,  32768, 200, "k8s,prod",   "K8S Worker-01"),
    (4, "k8s-worker-02","running", 8,  32768, 200, "k8s,prod",   "K8S Worker-02"),
    (0, "test-env",     "stopped", 2,  4096,  50,  "test",       "临时测试环境"),
    (1, "win-template", "stopped", 2,  4096,  80,  "template",   "Windows模板"),
    (2, "backup-srv",   "running", 2,  4096,  100, "backup,ops", "备份管理服务器"),
]
for ni, name, st, cores, mem, disk, tags, desc in vm_defs_a:
    create_vm(nodes_a[ni], vm_id, name, st, cores, mem, disk, tags=tags, description=desc)
    vm_id += 1

# --- LXC ---
ct_id = 200
ct_defs_a = [
    (0, "nginx-proxy",  "running", 2, 2048,  10, "web,prod",  "Nginx反向代理"),
    (0, "php-fpm",      "running", 4, 4096,  20, "www,prod",  "PHP-FPM应用服务"),
    (1, "mysql-slave-ct","running",2, 2048,  10, "db,prod",   "MySQL从库辅助容器"),
    (2, "grafana-ct",   "running", 2, 2048,  10, "ops",       "Grafana可视化"),
    (3, "node-exporter","running", 1, 512,   5,  "ops",       "Node Exporter监控"),
    (4, "coredns",      "running", 1, 512,   2,  "k8s,dns",   "CoreDNS K8S DNS"),
    (4, "traefik",      "running", 2, 2048,  10, "k8s,ingress","Traefik Ingress"),
    (0, "portainer",    "running", 1, 1024,  10, "ops",        "Portainer容器管理"),
    (1, "zabbix-agent", "running", 1, 512,   2,  "ops",        "Zabbix监控Agent"),
    (3, "ansible-ct",   "stopped", 1, 512,   5,  "ops,dev",    "Ansible自动化"),
]
for ni, name, st, cores, mem, disk, tags, desc in ct_defs_a:
    create_lxc(nodes_a[ni], ct_id, name, st, cores, mem, disk, tags=tags, description=desc)
    ct_id += 1

# --- 存储 ---
for i, node in enumerate(nodes_a):
    create_storage(node, "local",     "dir",    238, 52,  "images,rootdir,vztmpl,backup,iso")
    create_storage(node, "local-lvm", "lvm",    1800, 800, "images,rootdir")
    create_storage(node, "ceph-ssd",  "rbd",    2000, 650, "images,rootdir")
    create_storage(node, "ceph-hdd",  "rbd",    8000, 3200, "images,rootdir,backup")

# --- Ceph ---
CephStatus.objects.create(
    cluster=ca, health="HEALTH_OK",
    total_osds=40, up_osds=40, in_osds=40, pool_count=4,
    total_used_gb=3850, total_avail_gb=6150, total_space_gb=10000,
    extra_data={"osd_stats": [{"id": i, "up": True, "in": True, "kb_used": random.randint(80000000, 120000000)} for i in range(40)]},
    scanned_at=NOW,
)

# --- HA ---
ha_group = HAResource.objects.create(
    cluster=ca, sid="group:prod-critical", resource_type="vm", vmid=None,
    state="started", ha_group="prod-critical", ha_status="active",
    crm_state="started", max_restarts=3, max_shutdown=60,
    raw_data={"nodes": ["pve-a1", "pve-a2", "pve-a3"], "nofailback": True},
    scanned_at=NOW,
)
for vmid, node in [(102, nodes_a[0]), (103, nodes_a[1]), (104, nodes_a[2])]:
    HAResource.objects.create(
        cluster=ca, sid=f"vm:{vmid}", resource_type="vm", vmid=vmid,
        node_name=node.node_name, state="started", ha_group="prod-critical",
        ha_status="active", crm_state="started",
        max_restarts=3, max_shutdown=60, scanned_at=NOW,
    )

# --- 告警 ---
DetectionRule.objects.create(
    cluster=ca, name="CPU使用率过高", category="resource", severity="warning",
    condition_config={"field": "cpu_load", "operator": "gt", "value": 0.8},
    description="节点CPU负载持续超过80%", suggestion="检查是否有异常进程，考虑迁移负载",
    is_enabled=True,
)
DetectionRule.objects.create(
    cluster=ca, name="磁盘空间不足", category="resource", severity="critical",
    condition_config={"field": "disk_usage_pct", "operator": "gt", "value": 90},
    description="存储使用率超过90%", suggestion="清理无用数据或扩容",
    is_enabled=True,
)
DetectionResult.objects.create(
    cluster=ca, category="resource", severity="warning",
    title="节点 pve-a3 CPU使用率偏高",
    detail="pve-a3 当前CPU负载 55%，高于阈值50%",
    affected_resource="pve-a3", suggestion="关注负载变化趋势",
    is_resolved=False,
)
DetectionResult.objects.create(
    cluster=ca, category="resource", severity="critical",
    title="节点 pve-a5 磁盘I/O延迟过高",
    detail="pve-a5 I/O延迟 15ms，超过阈值10ms，可能影响VM性能",
    affected_resource="pve-a5", suggestion="检查磁盘健康状态，考虑更换故障盘",
    is_resolved=False,
)
DetectionResult.objects.create(
    cluster=ca, category="resource", severity="info",
    title="节点 pve-a4 CPU使用率偏低",
    detail="pve-a4 CPU负载仅18%，资源利用率较低",
    affected_resource="pve-a4", suggestion="可考虑将部分VM迁移至此节点",
    is_resolved=True, resolved_at=NOW - timedelta(days=3),
)

# --- 扫描历史（7天，每30分钟1条）---
base = NOW - timedelta(days=7)
for day in range(7):
    for half in range(48):
        t = base + timedelta(days=day, minutes=half * 30)
        ScanHistory.objects.create(
            cluster=ca,
            snapshot_data={
                "total_nodes": 5, "total_vms": 15, "total_containers": 10,
                "avg_cpu_usage": round(random.uniform(0.25, 0.55), 3),
                "avg_mem_usage": round(random.uniform(0.40, 0.70), 3),
                "ceph_health": "HEALTH_OK",
            },
            scanned_at=t,
        )

ca.total_nodes = 5
ca.save(update_fields=["total_nodes"])

# ════════════════════════════════════════════════
# Cluster B: 3 节点 + 无 Ceph
# ════════════════════════════════════════════════
print("\n━━━ Cluster B ━━━")
cb = create_cluster(
    "测试B-三节点混合",
    "3节点混合架构：AMD+Intel，无Ceph，使用NFS共享存储",
)

node_b_specs = [
    {"name": "node-big", "ip": "192.168.20.1", "cpu_model": "AMD EPYC 7763",
     "cpu_cores": 32, "cpu_sockets": 1, "cpu_load": 0.38,
     "memory_total_mb": 256*1024, "memory_used_mb": 130000, "memory_free_mb": 126000,
     "rootfs_total_gb": 953, "rootfs_used_gb": 180, "rootfs_avail_gb": 773,
     "swap_total_mb": 16384, "swap_used_mb": 0, "disk_io_delay_ms": 4.5, "uptime_seconds": 6_048_000},
    {"name": "node-small-a", "ip": "192.168.20.2", "cpu_model": "Intel Xeon E-2388G",
     "cpu_cores": 8, "cpu_sockets": 1, "cpu_load": 0.45,
     "memory_total_mb": 65536, "memory_used_mb": 38000, "memory_free_mb": 27536,
     "rootfs_total_gb": 238, "rootfs_used_gb": 65, "rootfs_avail_gb": 173,
     "swap_total_mb": 4096, "swap_used_mb": 0, "disk_io_delay_ms": 2.0, "uptime_seconds": 4_320_000},
    {"name": "node-small-b", "ip": "192.168.20.3", "cpu_model": "Intel Xeon E-2388G",
     "cpu_cores": 8, "cpu_sockets": 1, "cpu_load": 0.12,
     "memory_total_mb": 65536, "memory_used_mb": 22000, "memory_free_mb": 43536,
     "rootfs_total_gb": 238, "rootfs_used_gb": 42, "rootfs_avail_gb": 196,
     "swap_total_mb": 4096, "swap_used_mb": 0, "disk_io_delay_ms": 1.2, "uptime_seconds": 2_592_000},
]
nodes_b = []
for spec in node_b_specs:
    n = create_node(cb, spec["name"], spec["ip"],
        cpu_model=spec["cpu_model"], cpu_cores=spec["cpu_cores"],
        cpu_sockets=spec["cpu_sockets"], cpu_load=spec["cpu_load"],
        memory_total_mb=spec["memory_total_mb"], memory_used_mb=spec["memory_used_mb"],
        memory_free_mb=spec["memory_free_mb"],
        memory_usage_pct=round(spec["memory_used_mb"] / spec["memory_total_mb"] * 100, 1),
        rootfs_total_gb=spec["rootfs_total_gb"], rootfs_used_gb=spec["rootfs_used_gb"],
        rootfs_avail_gb=spec["rootfs_avail_gb"],
        swap_total_mb=spec["swap_total_mb"], swap_used_mb=spec["swap_used_mb"],
        disk_io_delay_ms=spec["disk_io_delay_ms"], uptime_seconds=spec["uptime_seconds"],
        is_ceph_node=False, is_ha_node=False,
    )
    nodes_b.append(n)

# --- 网络接口 ---
# node-big: vmbr0 (4口) + vmbr1 (2口业务)
create_iface(nodes_b[0], "vmbr0", "bridge", address="192.168.20.1", gateway="192.168.20.254",
             bridge_ports="eno1 eno2 eno3 eno4")
for eno in ["eno1", "eno2", "eno3", "eno4"]:
    create_iface(nodes_b[0], eno, "eth")
create_iface(nodes_b[0], "vmbr1", "bridge", address="10.10.1.1", bridge_ports="enp1s0 enp2s0")
create_iface(nodes_b[0], "enp1s0", "eth")
create_iface(nodes_b[0], "enp2s0", "eth")

# node-small-a: vmbr0 (1口)
create_iface(nodes_b[1], "vmbr0", "bridge", address="192.168.20.2", gateway="192.168.20.254",
             bridge_ports="eno1")
create_iface(nodes_b[1], "eno1", "eth")
create_iface(nodes_b[1], "enp1s0", "eth")

# node-small-b: vmbr0 (1口)
create_iface(nodes_b[2], "vmbr0", "bridge", address="192.168.20.3", gateway="192.168.20.254",
             bridge_ports="eno1")
create_iface(nodes_b[2], "eno1", "eth")

# --- VM ---
vm_id = 100
vm_defs_b = [
    (0, "app-server-01", "running", 8, 16384, 200, "app,prod",  "应用服务器-01"),
    (0, "app-server-02", "running", 8, 16384, 200, "app,prod",  "应用服务器-02"),
    (0, "db-server",     "running", 8, 32768, 500, "db,prod",   "PostgreSQL数据库"),
    (1, "web-front",     "running", 4, 8192,  100, "www,prod",  "前端Nginx"),
    (1, "api-gateway",   "running", 4, 8192,  50,  "api,prod",  "API网关"),
    (2, "dev-server",    "running", 4, 8192,  100, "dev",       "开发测试服务器"),
    (0, "old-app",       "stopped", 4, 4096,  100, "legacy",    "旧版应用(待下线)"),
]
for ni, name, st, cores, mem, disk, tags, desc in vm_defs_b:
    create_vm(nodes_b[ni], vm_id, name, st, cores, mem, disk, tags=tags, description=desc)
    vm_id += 1

# --- LXC ---
ct_id = 200
ct_defs_b = [
    (0, "haproxy",     "running", 2, 2048, 10, "proxy,prod",  "HAProxy负载均衡"),
    (1, "tomcat-app",  "running", 4, 8192, 20, "java,prod",   "Tomcat Java应用"),
    (1, "redis-sentinel","running",1, 1024, 5,  "cache,prod",  "Redis哨兵"),
    (2, "build-agent", "running", 2, 4096, 20, "ci,dev",      "构建Agent"),
    (0, "log-collector","running",2, 2048, 10, "ops",         "日志采集"),
]
for ni, name, st, cores, mem, disk, tags, desc in ct_defs_b:
    create_lxc(nodes_b[ni], ct_id, name, st, cores, mem, disk, tags=tags, description=desc)
    ct_id += 1

# --- 存储 ---
create_storage(nodes_b[0], "local",     "dir",   953, 180, "images,rootdir,vztmpl,backup,iso")
create_storage(nodes_b[0], "local-lvm", "lvm",   1500, 600, "images,rootdir")
create_storage(nodes_b[0], "shared-nfs", "nfs",  8000, 2800, "images,rootdir,backup", shared=True)
create_storage(nodes_b[1], "local",     "dir",   238, 65,  "images,rootdir,vztmpl,backup,iso")
create_storage(nodes_b[1], "local-lvm", "lvm",   500, 180, "images,rootdir")
create_storage(nodes_b[2], "local",     "dir",   238, 42,  "images,rootdir,vztmpl,backup,iso")
create_storage(nodes_b[2], "local-lvm", "lvm",   500, 95,  "images,rootdir")

# --- 无 Ceph ---
# --- 无 HA ---
DetectionResult.objects.create(
    cluster=cb, category="resource", severity="info",
    title="节点 node-small-b 资源利用率低",
    detail="node-small-b CPU仅12%，内存使用率33.6%，可整合负载",
    affected_resource="node-small-b", suggestion="考虑将部分VM迁移到此节点",
    is_resolved=False,
)

base = NOW - timedelta(days=7)
for day in range(7):
    for half in range(48):
        t = base + timedelta(days=day, minutes=half * 30)
        ScanHistory.objects.create(
            cluster=cb,
            snapshot_data={
                "total_nodes": 3, "total_vms": 7, "total_containers": 5,
                "avg_cpu_usage": round(random.uniform(0.20, 0.50), 3),
                "avg_mem_usage": round(random.uniform(0.35, 0.65), 3),
            },
            scanned_at=t,
        )

cb.total_nodes = 3
cb.save(update_fields=["total_nodes"])

# ════════════════════════════════════════════════
# Cluster C: 1 节点 + VLAN
# ════════════════════════════════════════════════
print("\n━━━ Cluster C ━━━")
cc = create_cluster(
    "测试C-单节点双桥VLAN",
    "单节点实验室环境，双网桥+VLAN隔离",
)

nc = create_node(cc, "pve-single", "10.0.0.1",
    cpu_model="Intel Core i7-13700", cpu_cores=8, cpu_sockets=1,
    cpu_load=0.22, memory_total_mb=32768, memory_used_mb=8500,
    memory_free_mb=24268, memory_usage_pct=26.0,
    rootfs_total_gb=476, rootfs_used_gb=120, rootfs_avail_gb=356,
    swap_total_mb=8192, swap_used_mb=0,
    disk_io_delay_ms=1.0, uptime_seconds=864_000,
    is_ceph_node=False, is_ha_node=False,
)

# --- 网络接口 ---
create_iface(nc, "vmbr0", "bridge", address="10.0.0.1", gateway="10.0.0.254", bridge_ports="eno1")
create_iface(nc, "eno1", "eth")
create_iface(nc, "vmbr1", "bridge", bridge_ports="eno2 eno3")
create_iface(nc, "eno2", "eth")
create_iface(nc, "eno3", "eth")
create_iface(nc, "vmbr1.100", "vlan", address="172.16.0.1", vlan_id=100)

# --- VM ---
vm_id = 100
vm_defs_c = [
    (0, "home-assistant", "running", 2, 4096, 32, "iot,home", "HomeAssistant智能家居"),
    (0, "plex-media",     "running", 4, 8192, 200, "media",    "Plex媒体服务器"),
    (0, "docker-host",    "running", 4, 8192, 100, "docker",   "Docker容器宿主"),
]
for ni, name, st, cores, mem, disk, tags, desc in vm_defs_c:
    create_vm(nc, vm_id, name, st, cores, mem, disk, tags=tags, description=desc)
    vm_id += 1

# --- LXC ---
ct_id = 200
ct_defs_c = [
    (0, "pihole",     "running", 1, 512,  2, "dns,home",   "Pi-hole DNS"),
    (0, "wireguard",  "running", 1, 512,  2, "vpn,home",   "WireGuard VPN"),
    (0, "mosquitto",  "running", 1, 256,  1, "iot,mqtt",   "MQTT Broker"),
    (0, "zigbee2mqtt","running", 1, 512,  2, "iot,zigbee", "Zigbee2MQTT网关"),
]
for ni, name, st, cores, mem, disk, tags, desc in ct_defs_c:
    create_lxc(nc, ct_id, name, st, cores, mem, disk, tags=tags, description=desc)
    ct_id += 1

# --- 存储 ---
create_storage(nc, "local",     "dir",   476, 120, "images,rootdir,vztmpl,backup,iso")
create_storage(nc, "local-lvm", "lvm",   200, 65,  "images,rootdir")

# --- 无 Ceph / HA ---
base = NOW - timedelta(days=7)
for day in range(7):
    for half in range(48):
        t = base + timedelta(days=day, minutes=half * 30)
        ScanHistory.objects.create(
            cluster=cc,
            snapshot_data={
                "total_nodes": 1, "total_vms": 3, "total_containers": 4,
                "avg_cpu_usage": round(random.uniform(0.10, 0.35), 3),
                "avg_mem_usage": round(random.uniform(0.20, 0.45), 3),
            },
            scanned_at=t,
        )

cc.total_nodes = 1
cc.save(update_fields=["total_nodes"])

# ─── 汇总 ──────────────────────────────────────
print("\n━━━ 完成 ━━━")
total_vms = VM.objects.filter(node__cluster__name__startswith="测试").count()
total_lxc = LXC.objects.filter(node__cluster__name__startswith="测试").count()
total_sto = Storage.objects.filter(node__cluster__name__startswith="测试").count()
total_if = NetworkInterface.objects.filter(node__cluster__name__startswith="测试").count()
total_ceph = CephStatus.objects.filter(cluster__name__startswith="测试").count()
total_ha = HAResource.objects.filter(cluster__name__startswith="测试").count()
total_hist = ScanHistory.objects.filter(cluster__name__startswith="测试").count()
total_alert = DetectionResult.objects.filter(cluster__name__startswith="测试").count()

print(f"  集群: 3 个")
print(f"  节点: 9 个")
print(f"  虚拟机: {total_vms} 个")
print(f"  容器: {total_lxc} 个")
print(f"  存储: {total_sto} 个")
print(f"  网络接口: {total_if} 条")
print(f"  Ceph: {total_ceph} 条")
print(f"  HA资源: {total_ha} 条")
print(f"  扫描历史: {total_hist} 条")
print(f"  告警: {total_alert} 条")
print(f"\n刷新页面查看数据。")
