#!/usr/bin/env python3
"""
PVE 集群模拟测试数据种子脚本

支持 5 种架构级别的模拟数据生成，可重复执行：
  - detect: 检测现有测试数据
  - delete: 删除所有测试数据
  - upload: 生成并上传模拟数据

用法:
  python scripts/seed_test_data.py detect
  python scripts/seed_test_data.py delete
  python scripts/seed_test_data.py upload [--levels 1,2,3,4,5] [--scans 7]
  python scripts/seed_test_data.py reset [--levels 1,2,3,4,5] [--scans 7]

零依赖，仅使用 Python 标准库。
"""

import argparse
import json
import random
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# ============================================================
# 配置
# ============================================================

BASE_URL = "http://127.0.0.1:8000"
USERNAME = "buladou"
PASSWORD = "husongsxx"

TEST_CLUSTER_PREFIX = "[TEST]"

# CPU 型号池
CPU_MODELS = [
    "Intel(R) Xeon(R) Platinum 8380 CPU @ 2.30GHz",
    "Intel(R) Xeon(R) Gold 6348 CPU @ 2.60GHz",
    "AMD EPYC 7443P 24-Core Processor",
    "AMD EPYC 7543P 32-Core Processor",
    "AMD EPYC 9654 96-Core Processor",
    "Intel(R) Xeon(R) CPU E5-2680 v4 @ 2.40GHz",
]

PVE_VERSIONS = [
    "pve-manager/8.2.4/8a926dcaae49e658 (running kernel: 6.8.8-1-pve)",
    "pve-manager/8.3.2/f156893a3f28ad76 (running kernel: 6.11.11-1-pve)",
    "pve-manager/8.1.4/ec5affc9e41f1d31 (running kernel: 6.5.13-3-pve)",
]

KERNEL_VERSIONS = [
    "6.8.8-1-pve",
    "6.11.11-1-pve",
    "6.5.13-3-pve",
]


# ============================================================
# 配置修改辅助
# ============================================================

_config = {
    "BASE_URL": BASE_URL,
    "USERNAME": USERNAME,
    "PASSWORD": PASSWORD,
}


def _set_config(key, value):
    _config[key] = value


def _cfg(key):
    return _config[key]


# ============================================================
# HTTP 工具
# ============================================================

def api_request(path, method="GET", data=None, token=None, raw=False):
    """发送 HTTP 请求"""
    url = f"{_cfg('BASE_URL')}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    body = json.dumps(data).encode() if data is not None else None
    req = Request(url, data=body, headers=headers, method=method)

    try:
        with urlopen(req, timeout=30) as resp:
            body = resp.read().decode()
            if raw:
                return resp.status, body
            return resp.status, json.loads(body) if body else {}
    except HTTPError as e:
        body = e.read().decode()
        try:
            return e.code, json.loads(body)
        except json.JSONDecodeError:
            return e.code, body
    except URLError as e:
        print(f"  [错误] 连接失败: {e}")
        sys.exit(1)


def login():
    """登录获取 JWT"""
    status, data = api_request("/api/auth/login/", "POST", {
        "username": _cfg("USERNAME"), "password": _cfg("PASSWORD")
    })
    if status != 200:
        print(f"[错误] 登录失败: {status} {data}")
        sys.exit(1)
    return data["access"]


# ============================================================
# 数据层级定义
# ============================================================

def _rand_ip(base, suffix):
    return f"{base}.{suffix}"


def _gen_node(name, ip_suffix, cpu_model_idx, cpu_cores, cpu_sockets,
              mem_gb, rootfs_gb, swap_gb, ceph_node=False, ha_node=False,
              disk_devices=None, networks=None):
    """生成单个节点数据"""
    cpu_load = round(random.uniform(5, 75), 1)
    mem_total = mem_gb * 1024
    mem_used = int(mem_total * random.uniform(0.25, 0.75))
    mem_free = mem_total - mem_used
    rootfs_total = float(rootfs_gb)
    rootfs_used = round(rootfs_total * random.uniform(0.2, 0.6), 2)
    rootfs_avail = round(rootfs_total - rootfs_used, 2)

    if disk_devices is None:
        disk_devices = [
            {"dev": "sda", "read": random.randint(1000000, 5000000000),
             "write": random.randint(5000000, 10000000000),
             "read_ios": random.randint(1000, 100000),
             "write_ios": random.randint(5000, 200000),
             "io_ms": round(random.uniform(0.5, 25), 1)}
        ]

    disk_io_delay = round(sum(d["io_ms"] for d in disk_devices), 1)

    if networks is None:
        networks = [
            {"name": "vmbr0", "type": "bridge", "active": True,
             "method": "static", "address": f"192.168.{ip_suffix}.10/24",
             "gateway": "192.168.1.1", "speed_mbps": 10000,
             "bridge_ports": "enp0s31f6", "mtu": 1500}
        ]

    return {
        "name": name, "status": "online",
        "pve_version": PVE_VERSIONS[cpu_model_idx % len(PVE_VERSIONS)],
        "kernel_version": KERNEL_VERSIONS[cpu_model_idx % len(KERNEL_VERSIONS)],
        "cpu_model": CPU_MODELS[cpu_model_idx % len(CPU_MODELS)],
        "cpu_cores": cpu_cores, "cpu_sockets": cpu_sockets,
        "cpu_load": cpu_load,
        "memory_total_mb": mem_total, "memory_used_mb": mem_used,
        "memory_free_mb": mem_free, "memory_usage_pct": round(mem_used / mem_total * 100, 1),
        "rootfs_total_gb": rootfs_total, "rootfs_used_gb": rootfs_used,
        "rootfs_avail_gb": rootfs_avail,
        "swap_total_mb": swap_gb * 1024,
        "swap_used_mb": random.randint(0, int(swap_gb * 1024 * 0.1)),
        "disk_io_delay_ms": disk_io_delay, "diskstat": disk_devices,
        "ip_address": f"192.168.{ip_suffix}.10",
        "uptime_seconds": random.randint(86400, 86400 * 90),
        "is_ceph_node": ceph_node, "is_ha_node": ha_node,
    }


def _gen_vm(vmid, name, cpu_cores, mem_gb, disk_gb, status="running",
            has_template=False, snapshot_count=0, tags="", description=""):
    """生成 VM 数据"""
    is_running = status == "running"
    return {
        "vmid": vmid, "name": name, "status": status,
        "cpu_cores": cpu_cores, "cpu_sockets": 1,
        "cpu_usage": round(random.uniform(0.5, 60), 1) if is_running else 0,
        "memory_mb": mem_gb * 1024,
        "memory_used_mb": int(mem_gb * 1024 * random.uniform(0.3, 0.8)) if is_running else 0,
        "balloon_min_mb": mem_gb * 512, "balloon_max_mb": mem_gb * 1024,
        "disk_gb": round(disk_gb * random.uniform(0.2, 0.8), 2),
        "max_disk_gb": float(disk_gb),
        "disk_write_iops": random.randint(0, 50000) if is_running else 0,
        "disk_read_iops": random.randint(0, 30000) if is_running else 0,
        "net_in_bps": random.randint(0, 50000000) if is_running else 0,
        "net_out_bps": random.randint(0, 50000000) if is_running else 0,
        "uptime_seconds": random.randint(86400, 86400 * 60) if is_running else 0,
        "os_type": random.choice(["l26", "l26", "l26", "other"]),
        "snapshot_count": snapshot_count, "has_template": has_template,
        "tags": tags, "description": description,
    }


def _gen_vm_config(vmid, cpu_cores, mem_gb):
    """生成 VM 配置"""
    return {
        "cpu_type": random.choice(["host", "max", "kvm64"]),
        "cpu_cores": cpu_cores, "cpu_sockets": 1,
        "memory_mb": mem_gb * 1024,
        "balloon_min_mb": mem_gb * 512,
        "os_type": "l26",
        "boot_order": "scsi0,net0",
        "scsi_disks": [{"file": f"local-lvm:vm-{vmid}-disk-0", "size_gb": round(mem_gb * 2, 1)}],
        "ide_disks": [],
        "net_devices": [{"model": "virtio", "bridge": "vmbr0", "mac": f"BC:24:11:AA:{vmid:04X}"}],
        "agent_enabled": True,
        "description": "", "tags": "",
        "raw_config": {},
    }


def _gen_lxc(vmid, name, cpu_cores, mem_gb, disk_gb, status="running", tags=""):
    """生成 LXC 容器数据"""
    is_running = status == "running"
    return {
        "vmid": vmid, "name": name, "status": status,
        "cpu_cores": cpu_cores,
        "cpu_usage": round(random.uniform(0.5, 40), 1) if is_running else 0,
        "memory_mb": mem_gb * 1024,
        "memory_used_mb": int(mem_gb * 1024 * random.uniform(0.2, 0.7)) if is_running else 0,
        "swap_mb": int(mem_gb * 1024 * 0.5),
        "swap_used_mb": random.randint(0, int(mem_gb * 256)) if is_running else 0,
        "disk_gb": float(disk_gb),
        "uptime_seconds": random.randint(3600, 86400 * 30) if is_running else 0,
        "tags": tags, "description": "",
    }


def _gen_lxc_config(vmid, cpu_cores, mem_gb):
    return {
        "hostname": f"ct-{vmid}",
        "cpu_cores": cpu_cores,
        "memory_mb": mem_gb * 1024,
        "swap_mb": int(mem_gb * 512),
        "os_type": random.choice(["alpine", "debian", "ubuntu", "centos"]),
        "rootfs": {"storage": "local-lvm", "size_gb": 8.0},
        "mount_points": [],
        "net_devices": [{"iface": "eth0", "bridge": "vmbr0", "ip": f"192.168.1.{vmid}/24"}],
        "description": "", "tags": "",
        "startup_order": "",
        "raw_config": {},
    }


def _gen_storage(name, stype, total_gb, used_ratio=None):
    if used_ratio is None:
        used_ratio = random.uniform(0.15, 0.65)
    total = float(total_gb)
    used = round(total * used_ratio, 2)
    avail = round(total - used, 2)
    content_map = {
        "dir": "images,rootdir,vztmpl,iso,backup",
        "lvmthin": "images,rootdir",
        "nfs": "images,iso,backup",
        "zfspool": "images,rootdir",
        "rbd": "images",
        "cephfs": "cephfs",
    }
    return {
        "name": name, "type": stype, "active": True,
        "used_gb": used, "avail_gb": avail, "total_gb": total,
        "used_fraction": round(used / total, 4) if total > 0 else 0,
        "content_types": content_map.get(stype, "images"),
        "shared": stype in ("nfs", "rbd", "cephfs"),
    }


def _gen_network(name, ntype, ip, gateway="192.168.1.1", speed=10000, **extra):
    net = {
        "name": name, "type": ntype, "active": True,
        "method": "static", "address": ip, "gateway": gateway,
        "speed_mbps": speed,
    }
    if ntype == "bridge":
        net["bridge_ports"] = extra.get("bridge_ports", "enp0s31f6")
    elif ntype == "bond":
        net["bond_mode"] = extra.get("bond_mode", "802.3ad")
        net["bond_slaves"] = extra.get("bond_slaves", "enp0s31f6 enp0s17f6")
    net["mtu"] = extra.get("mtu", 1500)
    return net


# ============================================================
# 五级架构数据
# ============================================================

def level_1_single_node():
    """Level 1 — 单节点入门: 1节点, 无Ceph, 无HA"""
    node = _gen_node("pve-single", "10", 0, cpu_cores=4, cpu_sockets=1,
                     mem_gb=16, rootfs_gb=200, swap_gb=4)
    node["vms"] = []
    node["containers"] = [
        _gen_lxc(201, "alpine-dns", 1, 0.25, 2, tags="infra"),
        _gen_lxc(202, "nginx-proxy", 1, 0.5, 4, tags="web"),
        _gen_lxc(203, "home-assistant", 2, 1.0, 8, tags="iot"),
    ]
    node["lxc_configs"] = {
        str(201): _gen_lxc_config(201, 1, 0.25),
        str(202): _gen_lxc_config(202, 1, 0.5),
        str(203): _gen_lxc_config(203, 2, 1.0),
    }
    node["storages"] = [
        _gen_storage("local", "dir", 200, 0.22),
        _gen_storage("local-lvm", "lvmthin", 180, 0.35),
    ]
    node["networks"] = [
        _gen_network("vmbr0", "bridge", "192.168.10.10/24", bridge_ports="enp0s31f6"),
    ]
    node["vm_configs"] = {}
    return {
        "name": "单节点入门集群",
        "desc": "1节点 / 0VM / 3容器 / 无Ceph / 无HA",
        "pve_version": "8.2.4",
        "nodes": [node], "ceph": None, "ha_resources": [],
    }


def level_2_dual_node():
    """Level 2 — 双节点小集群: 2节点, 无Ceph, 无HA"""
    nodes = []
    # Node 1
    n1 = _gen_node("pve-1", "20", 1, cpu_cores=8, cpu_sockets=1,
                   mem_gb=32, rootfs_gb=100, swap_gb=8)
    n1["vms"] = [
        _gen_vm(100, "ubuntu-web", 2, 4, 50, tags="production,web"),
        _gen_vm(101, "centos-db", 4, 16, 200, tags="production,database"),
        _gen_vm(102, "dev-vm", 2, 4, 40, tags="development",
                has_template=False, snapshot_count=1),
    ]
    n1["vm_configs"] = {
        str(100): _gen_vm_config(100, 2, 4),
        str(101): _gen_vm_config(101, 4, 16),
        str(102): _gen_vm_config(102, 2, 4),
    }
    n1["containers"] = [
        _gen_lxc(200, "redis-1", 1, 1.0, 4, tags="cache"),
        _gen_lxc(201, "nginx-1", 1, 0.5, 2, tags="web"),
        _gen_lxc(202, "grafana", 2, 2.0, 10, tags="monitoring"),
        _gen_lxc(203, "prometheus", 2, 4.0, 20, tags="monitoring"),
        _gen_lxc(204, "portainer", 1, 0.5, 2, tags="docker"),
    ]
    n1["lxc_configs"] = {
        str(v): _gen_lxc_config(v, 1, 1) for v in [200, 201, 202, 203, 204]
    }
    n1["storages"] = [
        _gen_storage("local", "dir", 100, 0.3),
        _gen_storage("local-lvm", "lvmthin", 500, 0.4),
        _gen_storage("nfs-data", "nfs", 2000, 0.25),
    ]
    n1["networks"] = [
        _gen_network("vmbr0", "bridge", "192.168.20.10/24", bridge_ports="enp0s31f6"),
        _gen_network("vmbr1", "bridge", "10.0.0.10/24", bridge_ports="enp0s17f6"),
    ]
    nodes.append(n1)

    # Node 2
    n2 = _gen_node("pve-2", "21", 2, cpu_cores=8, cpu_sockets=1,
                   mem_gb=32, rootfs_gb=100, swap_gb=8)
    n2["vms"] = [
        _gen_vm(100, "ubuntu-app-1", 2, 4, 50, tags="production,app"),
        _gen_vm(101, "ubuntu-app-2", 2, 4, 50, tags="production,app"),
        _gen_vm(102, "test-runner", 4, 8, 80, status="stopped", tags="ci"),
    ]
    n2["vm_configs"] = {
        str(v): _gen_vm_config(v, 2, 4) for v in [100, 101]
    }
    n2["vm_configs"]["102"] = _gen_vm_config(102, 4, 8)
    n2["containers"] = [
        _gen_lxc(200, "redis-2", 1, 1.0, 4, tags="cache"),
        _gen_lxc(201, "nginx-2", 1, 0.5, 2, tags="web"),
        _gen_lxc(202, "mariadb", 2, 2.0, 20, tags="database"),
        _gen_lxc(203, "nextcloud", 2, 2.0, 30, tags="web"),
        _gen_lxc(204, "jellyfin", 2, 4.0, 50, tags="media"),
        _gen_lxc(205, "wireguard", 1, 0.25, 1, tags="vpn"),
        _gen_lxc(206, "pihole", 1, 0.25, 2, tags="dns"),
        _gen_lxc(207, "gitlab-runner", 2, 2.0, 10, tags="ci"),
    ]
    n2["lxc_configs"] = {
        str(v): _gen_lxc_config(v, 1, 1) for v in [200, 201, 202, 203, 204, 205, 206, 207]
    }
    n2["storages"] = [
        _gen_storage("local", "dir", 100, 0.35),
        _gen_storage("local-lvm", "lvmthin", 500, 0.45),
        _gen_storage("nfs-data", "nfs", 2000, 0.30),
    ]
    n2["networks"] = [
        _gen_network("vmbr0", "bridge", "192.168.20.11/24", bridge_ports="enp0s31f6"),
        _gen_network("vmbr1", "bridge", "10.0.0.11/24", bridge_ports="enp0s17f6"),
    ]
    nodes.append(n2)

    return {
        "name": "双节点小集群",
        "desc": "2节点 / 6VM / 13容器 / NFS共享存储 / 无Ceph",
        "pve_version": "8.3.2",
        "nodes": nodes, "ceph": None, "ha_resources": [],
    }


def level_3_triple_node():
    """Level 3 — 三节点标准集群: 3节点, 无Ceph, 无HA, 多存储"""
    nodes = []
    node_specs = [
        ("pve-1", "30", 0, 16, 2, 64, 120, 16),
        ("pve-2", "31", 3, 16, 2, 64, 120, 16),
        ("pve-3", "32", 1, 24, 2, 128, 120, 16),
    ]
    vm_base = 100
    lxc_base = 200
    for i, (name, ip, cpu_idx, cores, sock, mem, rootfs, swap) in enumerate(node_specs):
        n = _gen_node(name, ip, cpu_idx, cpu_cores=cores, cpu_sockets=sock,
                      mem_gb=mem, rootfs_gb=rootfs, swap_gb=swap)

        # 每节点 5~8 个 VM
        n["vms"] = []
        n["vm_configs"] = {}
        vm_names = [
            ("web-prod-{}", 2, 4, 50, "production,web"),
            ("db-master-{}", 4, 16, 200, "production,database"),
            ("app-node-{}", 2, 4, 50, "production,app"),
            ("monitor-{}", 2, 8, 80, "monitoring"),
            ("ci-runner-{}", 4, 8, 100, "ci"),
            ("dev-sandbox-{}", 2, 4, 40, "development"),
        ]
        if i == 0:
            vm_names.append(("gateway-{}", 2, 2, 30, "infra"))
            vm_names.append(("logstash-{}", 2, 4, 60, "monitoring"))
        for j, (vname_pattern, vc, vd, vdsk, vtags) in enumerate(vm_names):
            vid = vm_base + j + 1
            status = "running" if random.random() > 0.1 else "stopped"
            vm = _gen_vm(vid, vname_pattern.format(i + 1), vc, vd, vdsk,
                         status=status, tags=vtags,
                         snapshot_count=random.randint(0, 3))
            n["vms"].append(vm)
            n["vm_configs"][str(vid)] = _gen_vm_config(vid, vc, vd)

        # 每节点 8~15 个 LXC
        n["containers"] = []
        n["lxc_configs"] = {}
        lxc_pool = [
            ("nginx-{}", 1, 0.5, 2, "web"),
            ("redis-{}", 1, 1.0, 4, "cache"),
            ("postgres-{}", 2, 4.0, 30, "database"),
            ("elasticsearch-{}", 2, 4.0, 40, "search"),
            ("grafana-{}", 2, 2.0, 10, "monitoring"),
            ("prometheus-{}", 2, 4.0, 20, "monitoring"),
            ("portainer-{}", 1, 0.5, 2, "docker"),
            ("minio-{}", 2, 2.0, 50, "storage"),
            ("rabbitmq-{}", 1, 2.0, 10, "mq"),
            ("consul-{}", 1, 1.0, 4, "infra"),
            ("vault-{}", 1, 1.0, 4, "security"),
            ("traefik-{}", 1, 0.5, 2, "web"),
            ("wikijs-{}", 1, 1.0, 8, "docs"),
        ]
        num_lxc = random.randint(8, 13)
        for j in range(num_lxc):
            tmpl = lxc_pool[j % len(lxc_pool)]
            cid = lxc_base + j + 1
            status = "running" if random.random() > 0.05 else "stopped"
            ct = _gen_lxc(cid, tmpl[0].format(i + 1), tmpl[1], tmpl[2], tmpl[3],
                          status=status, tags=tmpl[4])
            n["containers"].append(ct)
            n["lxc_configs"][str(cid)] = _gen_lxc_config(cid, tmpl[1], tmpl[2])

        n["storages"] = [
            _gen_storage("local", "dir", 120, 0.3),
            _gen_storage("local-lvm", "lvmthin", 800, random.uniform(0.3, 0.6)),
            _gen_storage("nfs-backup", "nfs", 4000, random.uniform(0.2, 0.5)),
            _gen_storage("iscsi-data", "lvmthin", 2000, random.uniform(0.4, 0.7)),
        ]

        n["networks"] = [
            _gen_network("vmbr0", "bridge", f"192.168.3{i}.10/24",
                         bridge_ports="enp0s31f6", speed=10000),
            _gen_network("bond0", "bond", f"10.0.{i}.10/24", speed=25000,
                         bond_mode="802.3ad", bond_slaves="enp0s31f6 enp0s17f6"),
        ]
        vm_base += len(n["vms"])
        lxc_base += num_lxc
        nodes.append(n)

    return {
        "name": "三节点标准集群",
        "desc": "3节点 / ~20VM / ~35容器 / 多存储类型 / Bond网络",
        "pve_version": "8.3.2",
        "nodes": nodes, "ceph": None, "ha_resources": [],
    }


def level_4_ceph_cluster():
    """Level 4 — 三节点 + Ceph + 基础 HA"""
    nodes = []
    node_specs = [
        ("ceph-1", "40", 0, 24, 2, 128, 100, 32),
        ("ceph-2", "41", 3, 24, 2, 128, 100, 32),
        ("ceph-3", "42", 2, 24, 2, 128, 100, 32),
    ]
    vm_base = 100
    lxc_base = 200
    for i, (name, ip, cpu_idx, cores, sock, mem, rootfs, swap) in enumerate(node_specs):
        n = _gen_node(name, ip, cpu_idx, cpu_cores=cores, cpu_sockets=sock,
                      mem_gb=mem, rootfs_gb=rootfs, swap_gb=swap,
                      ceph_node=True, ha_node=True,
                      disk_devices=[
                          {"dev": "sda", "read": random.randint(10000000, 50000000000),
                           "write": random.randint(50000000, 100000000000),
                           "read_ios": random.randint(5000, 200000),
                           "write_ios": random.randint(10000, 500000),
                           "io_ms": round(random.uniform(1, 15), 1)},
                          {"dev": "sdb", "read": random.randint(50000000, 200000000000),
                           "write": random.randint(20000000, 80000000000),
                           "read_ios": random.randint(10000, 500000),
                           "write_ios": random.randint(50000, 300000),
                           "io_ms": round(random.uniform(2, 20), 1)},
                          {"dev": "nvme0n1", "read": random.randint(100000000, 500000000000),
                           "write": random.randint(50000000, 200000000000),
                           "read_ios": random.randint(50000, 500000),
                           "write_ios": random.randint(50000, 500000),
                           "io_ms": round(random.uniform(0.1, 2), 1)},
                      ])

        n["vms"] = []
        n["vm_configs"] = {}
        vm_pool = [
            ("k8s-master-{}", 4, 16, 100, "production,k8s,master"),
            ("k8s-worker-{}", 4, 16, 100, "production,k8s,worker"),
            ("db-primary-{}", 4, 32, 200, "production,database,ha-enabled"),
            ("db-replica-{}", 4, 16, 200, "production,database"),
            ("redis-cluster-{}", 2, 8, 50, "production,cache,ha-enabled"),
            ("api-server-{}", 2, 8, 80, "production,app"),
            ("web-frontend-{}", 2, 4, 50, "production,web"),
            ("monitoring-{}", 2, 8, 100, "monitoring"),
            ("ci-runner-{}", 4, 8, 100, "ci"),
            ("dev-vm-{}", 2, 4, 40, "development"),
            ("log-collector-{}", 2, 4, 80, "monitoring,logging"),
            ("backup-server-{}", 2, 4, 500, "infra,backup"),
        ]
        for j, (vname_pattern, vc, vd, vdsk, vtags) in enumerate(vm_pool):
            vid = vm_base + j + 1
            status = "running" if random.random() > 0.05 else "stopped"
            vm = _gen_vm(vid, vname_pattern.format(i + 1), vc, vd, vdsk,
                         status=status, tags=vtags,
                         snapshot_count=random.randint(0, 5))
            n["vms"].append(vm)
            n["vm_configs"][str(vid)] = _gen_vm_config(vid, vc, vd)

        n["containers"] = []
        n["lxc_configs"] = {}
        lxc_pool = [
            ("nginx-lb-{}", 1, 0.5, 2, "web,loadbalancer"),
            ("coredns-{}", 1, 0.5, 2, "infra,dns"),
            ("cert-manager-{}", 1, 1.0, 4, "security"),
            ("redis-sidecar-{}", 1, 1.0, 4, "cache"),
            ("prometheus-node-{}", 1, 1.0, 8, "monitoring"),
            ("alertmanager-{}", 1, 0.5, 4, "monitoring"),
            ("loki-{}", 2, 2.0, 20, "monitoring,logging"),
            ("harbor-registry-{}", 2, 2.0, 50, "docker,registry"),
            ("argocd-{}", 2, 2.0, 10, "ci,gitops"),
            ("minio-rgw-{}", 2, 2.0, 30, "storage"),
        ]
        num_lxc = random.randint(8, 10)
        for j in range(num_lxc):
            tmpl = lxc_pool[j % len(lxc_pool)]
            cid = lxc_base + j + 1
            ct = _gen_lxc(cid, tmpl[0].format(i + 1), tmpl[1], tmpl[2], tmpl[3],
                          tags=tmpl[4])
            n["containers"].append(ct)
            n["lxc_configs"][str(cid)] = _gen_lxc_config(cid, tmpl[1], tmpl[2])

        n["storages"] = [
            _gen_storage("local", "dir", 100, 0.25),
            _gen_storage("ceph-ssd", "rbd", 5000, random.uniform(0.3, 0.5)),
            _gen_storage("ceph-hdd", "rbd", 15000, random.uniform(0.4, 0.6)),
        ]
        n["networks"] = [
            _gen_network("vmbr0", "bridge", f"192.168.4{i}.10/24",
                         bridge_ports="enp0s31f6"),
            _gen_network("bond0", "bond", f"10.10.{i}.10/24", speed=25000,
                         bond_mode="802.3ad", bond_slaves="enp0s31f6 enp0s17f6"),
        ]
        vm_base += len(n["vms"])
        lxc_base += num_lxc
        nodes.append(n)

    # Ceph: HEALTH_OK, 12 OSD (每节点 4)
    ceph = {
        "health": "HEALTH_OK",
        "total_osds": 12, "up_osds": 12, "in_osds": 12,
        "pool_count": 4,
        "total_used_gb": 8192.0, "total_avail_gb": 16384.0, "total_space_gb": 24576.0,
    }

    ha_resources = [
        {"sid": "ha:db-primary", "type": "vm", "vmid": 103,
         "node": "ceph-1", "state": "started", "ha_group": "ha-group-db",
         "ha_status": "active", "crm_state": "started",
         "max_restarts": 3, "max_shutdown": 120,
         "raw": {}},
        {"sid": "ha:redis-1", "type": "vm", "vmid": 105,
         "node": "ceph-2", "state": "started", "ha_group": "ha-group-cache",
         "ha_status": "active", "crm_state": "started",
         "max_restarts": 3, "max_shutdown": 60,
         "raw": {}},
    ]

    return {
        "name": "Ceph 三节点集群",
        "desc": "3节点 / ~36VM / ~30容器 / Ceph OK(12OSD) / 2 HA资源",
        "pve_version": "8.3.2",
        "nodes": nodes, "ceph": ceph, "ha_resources": ha_resources,
    }


def level_5_enterprise():
    """Level 5 — 多节点企业集群: 5节点 + Ceph WARN + 大规模"""
    nodes = []
    node_specs = [
        ("prod-1", "50", 0, 32, 2, 256, 100, 64, True, True),
        ("prod-2", "51", 3, 32, 2, 256, 100, 64, True, True),
        ("prod-3", "52", 2, 64, 2, 512, 100, 64, True, True),
        ("prod-4", "53", 5, 64, 2, 512, 100, 64, True, False),
        ("prod-5", "54", 4, 48, 2, 384, 100, 64, True, True),
    ]
    vm_base = 100
    lxc_base = 200
    for i, spec in enumerate(node_specs):
        (name, ip, cpu_idx, cores, sock, mem, rootfs, swap,
         ceph_node, ha_node) = spec
        n = _gen_node(name, ip, cpu_idx, cpu_cores=cores, cpu_sockets=sock,
                      mem_gb=mem, rootfs_gb=rootfs, swap_gb=swap,
                      ceph_node=ceph_node, ha_node=ha_node,
                      disk_devices=[
                          {"dev": "sda", "read": random.randint(50000000, 200000000000),
                           "write": random.randint(100000000, 500000000000),
                           "read_ios": random.randint(20000, 800000),
                           "write_ios": random.randint(50000, 1000000),
                           "io_ms": round(random.uniform(1, 30), 1)},
                          {"dev": "sdb", "read": random.randint(100000000, 800000000000),
                           "write": random.randint(50000000, 300000000000),
                           "read_ios": random.randint(30000, 1000000),
                           "write_ios": random.randint(100000, 800000),
                           "io_ms": round(random.uniform(2, 25), 1)},
                          {"dev": "nvme0n1", "read": random.randint(500000000, 2000000000000),
                           "write": random.randint(200000000, 1000000000000),
                           "read_ios": random.randint(100000, 2000000),
                           "write_ios": random.randint(100000, 2000000),
                           "io_ms": round(random.uniform(0.05, 1.5), 2)},
                          {"dev": "nvme1n1", "read": random.randint(500000000, 2000000000000),
                           "write": random.randint(200000000, 1000000000000),
                           "read_ios": random.randint(100000, 2000000),
                           "write_ios": random.randint(100000, 2000000),
                           "io_ms": round(random.uniform(0.05, 1.5), 2)},
                      ])

        # 每节点 10~15 个 VM
        n["vms"] = []
        n["vm_configs"] = {}
        vm_pool = [
            ("k8s-master-{}", 8, 32, 100, "production,k8s,master,ha-enabled"),
            ("k8s-worker-{}", 8, 32, 100, "production,k8s,worker"),
            ("k8s-worker-{}", 8, 32, 100, "production,k8s,worker"),
            ("db-mysql-primary-{}", 8, 64, 500, "production,database,ha-enabled"),
            ("db-mysql-replica-{}", 4, 32, 300, "production,database"),
            ("db-pgsql-{}", 8, 32, 200, "production,database"),
            ("redis-sentinel-{}", 2, 8, 50, "production,cache,ha-enabled"),
            ("api-gateway-{}", 4, 16, 80, "production,app,gateway"),
            ("api-service-{}", 4, 16, 80, "production,app"),
            ("api-service-{}", 4, 16, 80, "production,app"),
            ("web-frontend-{}", 2, 8, 50, "production,web"),
            ("kafka-broker-{}", 4, 32, 200, "production,mq"),
            ("elasticsearch-{}", 4, 32, 300, "production,search"),
            ("monitoring-stack-{}", 4, 16, 200, "monitoring"),
            ("ci-gitlab-{}", 4, 16, 500, "ci"),
        ]
        num_vm = random.randint(10, 15)
        for j in range(num_vm):
            tmpl = vm_pool[j % len(vm_pool)]
            vid = vm_base + j + 1
            status = "running" if random.random() > 0.03 else "stopped"
            vm = _gen_vm(vid, tmpl[0].format(i + 1), tmpl[1], tmpl[2], tmpl[3],
                         status=status, tags=tmpl[4],
                         snapshot_count=random.randint(0, 8))
            n["vms"].append(vm)
            n["vm_configs"][str(vid)] = _gen_vm_config(vid, tmpl[1], tmpl[2])

        # 每节点 10~15 个 LXC
        n["containers"] = []
        n["lxc_configs"] = {}
        lxc_pool = [
            ("nginx-ingress-{}", 2, 1.0, 2, "web,loadbalancer"),
            ("coredns-{}", 1, 0.5, 2, "infra,dns"),
            ("etcd-{}", 2, 4.0, 10, "infra,etcd"),
            ("harbor-registry-{}", 2, 4.0, 50, "docker,registry"),
            ("argocd-{}", 2, 2.0, 10, "ci,gitops"),
            ("prometheus-{}", 2, 4.0, 40, "monitoring"),
            ("grafana-{}", 2, 2.0, 10, "monitoring"),
            ("loki-{}", 2, 4.0, 50, "monitoring,logging"),
            ("minio-{}", 4, 4.0, 100, "storage"),
            ("vault-{}", 2, 2.0, 4, "security"),
            ("consul-{}", 1, 1.0, 4, "infra"),
            ("rabbitmq-{}", 2, 2.0, 10, "mq"),
            ("cert-manager-{}", 1, 1.0, 4, "security"),
            ("zabbix-{}", 2, 4.0, 30, "monitoring"),
        ]
        num_lxc = random.randint(10, 14)
        for j in range(num_lxc):
            tmpl = lxc_pool[j % len(lxc_pool)]
            cid = lxc_base + j + 1
            ct = _gen_lxc(cid, tmpl[0].format(i + 1), tmpl[1], tmpl[2], tmpl[3],
                          tags=tmpl[4])
            n["containers"].append(ct)
            n["lxc_configs"][str(cid)] = _gen_lxc_config(cid, tmpl[1], tmpl[2])

        n["storages"] = [
            _gen_storage("local", "dir", 100, 0.2),
            _gen_storage("ceph-ssd", "rbd", 10000, random.uniform(0.3, 0.6)),
            _gen_storage("ceph-hdd", "rbd", 40000, random.uniform(0.4, 0.7)),
            _gen_storage("local-zfs", "zfspool", 2000, random.uniform(0.2, 0.5)),
        ]
        n["networks"] = [
            _gen_network("vmbr0", "bridge", f"192.168.5{i}.10/24",
                         bridge_ports="enp0s31f6"),
            _gen_network("vmbr1", "bridge", f"10.10.0.{10 + i}/24",
                         bridge_ports="enp0s17f6"),
            _gen_network("bond0", "bond", f"172.16.{i}.10/24", speed=25000,
                         bond_mode="802.3ad",
                         bond_slaves="enp3s0f0 enp3s0f1"),
        ]
        vm_base += len(n["vms"])
        lxc_base += num_lxc
        nodes.append(n)

    # Ceph: HEALTH_WARN — 2 个 OSD down
    ceph = {
        "health": "HEALTH_WARN",
        "total_osds": 24, "up_osds": 22, "in_osds": 23,
        "pool_count": 8,
        "total_used_gb": 32768.0, "total_avail_gb": 49152.0, "total_space_gb": 81920.0,
    }

    ha_resources = [
        {"sid": "ha:mysql-primary", "type": "vm", "vmid": 104,
         "node": "prod-1", "state": "started", "ha_group": "ha-group-db",
         "ha_status": "active", "crm_state": "started",
         "max_restarts": 5, "max_shutdown": 300, "raw": {}},
        {"sid": "ha:redis-sentinel", "type": "vm", "vmid": 107,
         "node": "prod-2", "state": "started", "ha_group": "ha-group-cache",
         "ha_status": "active", "crm_state": "started",
         "max_restarts": 3, "max_shutdown": 60, "raw": {}},
        {"sid": "ha:api-gw-1", "type": "vm", "vmid": 108,
         "node": "prod-3", "state": "started", "ha_group": "ha-group-app",
         "ha_status": "active", "crm_state": "started",
         "max_restarts": 5, "max_shutdown": 30, "raw": {}},
        {"sid": "ha:api-gw-2", "type": "vm", "vmid": 109,
         "node": "prod-4", "state": "started", "ha_group": "ha-group-app",
         "ha_status": "active", "crm_state": "started",
         "max_restarts": 5, "max_shutdown": 30, "raw": {}},
        {"sid": "ha:kafka-1", "type": "vm", "vmid": 112,
         "node": "prod-5", "state": "started", "ha_group": "ha-group-mq",
         "ha_status": "active", "crm_state": "started",
         "max_restarts": 3, "max_shutdown": 120, "raw": {}},
    ]

    return {
        "name": "企业生产集群",
        "desc": "5节点 / ~65VM / ~60容器 / Ceph WARN(24OSD, 2down) / 5 HA资源 / 复杂网络",
        "pve_version": "8.3.2",
        "nodes": nodes, "ceph": ceph, "ha_resources": ha_resources,
    }


# 数据生成器注册表
LEVELS = {
    1: level_1_single_node,
    2: level_2_dual_node,
    3: level_3_triple_node,
    4: level_4_ceph_cluster,
    5: level_5_enterprise,
}


# ============================================================
# 核心操作
# ============================================================

def do_detect(token):
    """检测现有测试数据"""
    status, data = api_request("/api/clusters/", token=token)
    if status != 200:
        print(f"[错误] 查询集群列表失败: {status} {data}")
        return []

    clusters = data.get("results", data) if isinstance(data, dict) else data
    test_clusters = [c for c in clusters if c.get("name", "").startswith(TEST_CLUSTER_PREFIX)]

    print(f"\n{'='*60}")
    print(f"  现有集群总数: {len(clusters)}")
    print(f"  测试集群数量: {len(test_clusters)}")
    print(f"{'='*60}")

    if not test_clusters:
        print("  (无测试数据)\n")
        return []

    print(f"\n  {'ID':<6} {'名称':<30} {'节点':<6} {'VM':<6} {'容器':<6} {'最后扫描':<20}")
    print(f"  {'-'*54}")
    for c in test_clusters:
        last_scan = c.get("last_scanned_at", "")[:19] or "从未扫描"
        print(f"  {c['id']:<6} {c['name']:<30} {c.get('total_nodes',0):<6} "
              f"{c.get('total_vms',0):<6} {c.get('total_lxc',0):<6} {last_scan:<20}")

    # 查询每个测试集群的 Agent 数量
    print()
    for c in test_clusters:
        detail_status, detail = api_request(f"/api/clusters/{c['id']}/", token=token)
        if detail_status == 200:
            agents = detail.get("agents", [])
            print(f"  集群 [{c['name']}] ({c['id']})")
            for a in agents:
                print(f"    Agent: {a.get('hostname', '?')} | "
                      f"ID: {a.get('agent_id', '?')[:16]}... | "
                      f"状态: {a.get('status', '?')} | "
                      f"扫描次数: {a.get('total_scans', 0)}")
            if not agents:
                print(f"    (无 Agent)")
    print()
    return test_clusters


def do_delete(token):
    """删除所有测试集群"""
    test_clusters = do_detect(token)
    if not test_clusters:
        print("[完成] 无需清理\n")
        return

    print(f"[删除] 正在删除 {len(test_clusters)} 个测试集群...")
    for c in test_clusters:
        status, _ = api_request(f"/api/clusters/{c['id']}/", "DELETE", token=token)
        if status in (200, 204):
            print(f"  ✓ 已删除: {c['name']} (ID={c['id']})")
        else:
            print(f"  ✗ 删除失败: {c['name']} (ID={c['id']}) — {status}")
    print("[完成] 清理完毕\n")


def do_upload(token, levels=None, num_scans=7):
    """生成并上传模拟数据"""
    if levels is None:
        levels = [1, 2, 3, 4, 5]

    now = datetime.now(timezone.utc)
    results = []

    for level in levels:
        if level not in LEVELS:
            print(f"[跳过] Level {level} 不存在")
            continue

        gen_func = LEVELS[level]
        data = gen_func()
        print(f"\n{'='*60}")
        print(f"  Level {level}: {data['name']}")
        print(f"  {data['desc']}")
        print(f"{'='*60}")

        # 1. 创建集群
        cluster_name = f"{TEST_CLUSTER_PREFIX} L{level} — {data['name']}"
        cluster_resp_status, cluster_resp = api_request("/api/clusters/", "POST", {
            "name": cluster_name,
            "description": f"[自动化测试] Level {level} 模拟集群 — {data['desc']}",
            "pve_endpoint": f"https://192.168.1.{10 + level * 10}:8006",
            "pve_token": f"root@pam!test:fake-token-{uuid.uuid4().hex[:16]}",
        }, token=token)

        if cluster_resp_status not in (200, 201):
            print(f"  [错误] 创建集群失败: {cluster_resp_status} {cluster_resp}")
            continue

        cluster_id = cluster_resp["id"]
        agent_token = cluster_resp["agent_token"]
        print(f"  集群已创建: ID={cluster_id}, token={agent_token[:16]}...")

        # 2. 注册 Agent（每个节点一个 Agent）
        agent_ids = []
        for node in data["nodes"]:
            reg_status, reg_resp = api_request("/api/agent/register/", "POST", {
                "agent_token": agent_token,
                "pve_api_endpoint": f"https://192.168.1.{10 + level * 10}:8006",
                "pve_username": "root@pam",
                "pve_password": f"fake-password-{node['name']}",
                "hostname": node["name"],
                "scan_interval": 300,
                "version": f"0.5.11",
            })
            if reg_status == 201:
                aid = reg_resp["agent_id"]
                agent_ids.append(aid)
                print(f"  Agent 已注册: {node['name']} → {aid[:16]}...")
            else:
                print(f"  [错误] Agent 注册失败: {node['name']} — {reg_status} {reg_resp}")

        # 3. 发送心跳
        for aid in agent_ids:
            api_request("/api/agent/heartbeat/", "POST", {
                "agent_id": aid, "status": "online", "version": "0.5.11"
            })

        # 4. 上传扫描数据（多轮，模拟历史趋势）
        print(f"  上传 {num_scans} 轮扫描数据...")
        for scan_idx in range(num_scans):
            # 扫描时间：从 (num_scans-1) 天前到现在，每轮间隔约 num_scans 小时
            scan_time = now - timedelta(
                days=(num_scans - 1 - scan_idx),
                hours=random.randint(0, 6),
                minutes=random.randint(0, 59),
            )

            # 为每轮扫描添加随机波动
            scan_payload = _build_scan_payload(
                cluster_id, agent_ids, data, scan_time, scan_idx, num_scans
            )

            # 选择第一个 Agent 上传（模拟单 Agent 上报）
            upload_status, upload_resp = api_request(
                "/api/agent/scan/upload/", "POST", scan_payload
            )

            scan_label = scan_time.strftime("%m-%d %H:%M")
            if upload_status == 200 and isinstance(upload_resp, dict) and upload_resp.get("ok"):
                print(f"    [{scan_idx+1}/{num_scans}] {scan_label} ✓ "
                      f"(task_id={upload_resp.get('scan_task_id')})")
            else:
                print(f"    [{scan_idx+1}/{num_scans}] {scan_label} ✗ "
                      f"— {upload_status} {upload_resp}")

        results.append({
            "level": level, "name": data["name"],
            "cluster_id": cluster_id, "cluster_name": cluster_name,
            "agents": len(agent_ids),
        })

    # 汇总
    print(f"\n{'='*60}")
    print(f"  上传完成 — 共 {len(results)} 个层级")
    print(f"{'='*60}")
    for r in results:
        print(f"  Level {r['level']}: {r['cluster_name']}")
        print(f"    Cluster ID={r['cluster_id']}, Agents={r['agents']}")
    print()


def _build_scan_payload(cluster_id, agent_ids, data, scan_time, scan_idx, total_scans):
    """构建扫描上传 payload，带随机波动"""
    nodes_out = []
    for i, node_template in enumerate(data["nodes"]):
        # 深拷贝节点数据并添加波动
        node = json.loads(json.dumps(node_template))

        # CPU/内存随时间波动
        drift = random.uniform(-0.15, 0.15)
        node["cpu_load"] = max(0, min(100,
            round(node["cpu_load"] + drift * node["cpu_load"], 1)))
        mem_drift = int(node["memory_total_mb"] * drift * 0.3)
        node["memory_used_mb"] = max(0,
            node["memory_used_mb"] + mem_drift)
        node["memory_free_mb"] = node["memory_total_mb"] - node["memory_used_mb"]
        node["memory_usage_pct"] = round(
            node["memory_used_mb"] / node["memory_total_mb"] * 100, 1)

        # 磁盘 I/O 波动
        for disk in node.get("diskstat", []):
            disk["io_ms"] = round(max(0, disk["io_ms"] + random.uniform(-3, 3)), 1)
        node["disk_io_delay_ms"] = round(
            sum(d["io_ms"] for d in node.get("diskstat", [])), 1)

        # VM 状态微调
        for vm in node.get("vms", []):
            if vm["status"] == "running":
                vm["cpu_usage"] = round(max(0, min(100,
                    vm["cpu_usage"] + random.uniform(-10, 10))), 1)
                vm["memory_used_mb"] = max(0,
                    vm["memory_used_mb"] + int(vm["memory_mb"] * random.uniform(-0.1, 0.1)))
                vm["net_in_bps"] = max(0, vm["net_in_bps"] + random.randint(-5000000, 5000000))
                vm["net_out_bps"] = max(0, vm["net_out_bps"] + random.randint(-5000000, 5000000))

        # LXC 状态微调
        for ct in node.get("containers", []):
            if ct["status"] == "running":
                ct["cpu_usage"] = round(max(0, min(100,
                    ct["cpu_usage"] + random.uniform(-5, 5))), 1)

        nodes_out.append(node)

    payload = {
        "agent_id": agent_ids[0] if agent_ids else "unknown",
        "cluster_id": str(cluster_id),
        "scanned_at": scan_time.isoformat(),
        "version": data["pve_version"],
        "nodes": nodes_out,
        "ceph": data.get("ceph"),
        "ha_resources": data.get("ha_resources", []),
    }
    return payload


# ============================================================
# CLI 入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="PVE 集群模拟测试数据种子脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
架构层级:
  Level 1  单节点入门   (1节点 / 0VM / 3容器 / 无Ceph / 无HA)
  Level 2  双节点小集群  (2节点 / 6VM / 13容器 / NFS存储 / 无Ceph)
  Level 3  三节点标准集群 (3节点 / ~20VM / ~35容器 / 多存储 / Bond网络)
  Level 4  Ceph三节点    (3节点 / ~36VM / ~30容器 / Ceph OK / 2 HA资源)
  Level 5  企业生产集群   (5节点 / ~65VM / ~60容器 / Ceph WARN / 5 HA资源)

示例:
  python scripts/seed_test_data.py detect
  python scripts/seed_test_data.py delete
  python scripts/seed_test_data.py upload
  python scripts/seed_test_data.py upload --levels 1,2
  python scripts/seed_test_data.py upload --scans 14
  python scripts/seed_test_data.py reset
  python scripts/seed_test_data.py reset --levels 3,4,5 --scans 10
        """,
    )
    parser.add_argument("action", choices=["detect", "delete", "upload", "reset"],
                        help="操作: detect=检测 delete=删除 upload=上传 reset=删除后重新上传")
    parser.add_argument("--levels", default="1,2,3,4,5",
                        help="层级 (逗号分隔, 默认: 1,2,3,4,5)")
    parser.add_argument("--scans", type=int, default=7,
                        help="每层级扫描轮数 (默认: 7, 模拟7天趋势)")
    parser.add_argument("--base-url", default=None, help="服务地址 (默认: http://127.0.0.1:8000)")
    parser.add_argument("--username", default=None, help="登录用户名")
    parser.add_argument("--password", default=None, help="登录密码")

    args = parser.parse_args()

    # 覆盖全局配置
    if args.base_url is not None:
        _set_config("BASE_URL", args.base_url)
    if args.username is not None:
        _set_config("USERNAME", args.username)
    if args.password is not None:
        _set_config("PASSWORD", args.password)

    levels = [int(x.strip()) for x in args.levels.split(",") if x.strip()]

    # 登录
    print(f"[认证] 登录 {_cfg('BASE_URL')} ...")
    token = login()
    print(f"[认证] 成功\n")

    # 执行操作
    if args.action == "detect":
        do_detect(token)

    elif args.action == "delete":
        do_delete(token)

    elif args.action == "upload":
        do_upload(token, levels=levels, num_scans=args.scans)

    elif args.action == "reset":
        do_delete(token)
        do_upload(token, levels=levels, num_scans=args.scans)


if __name__ == "__main__":
    main()
