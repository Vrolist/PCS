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

# CPU 型号池（区分 Intel / AMD，影响 cpu_type 选择）
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

# 网络模型池（按常见度加权）
NET_MODELS_WEIGHTED = ["virtio", "virtio", "virtio", "e1000", "rtl8139"]

# OS 类型池
OS_TYPES = ["l26", "l26", "l26", "l26", "other"]

# 磁盘槽位候选
SCSI_DISKS = ["scsi0", "scsi1", "scsi2", "scsi3"]
IDE_DISKS = ["ide0", "ide1", "ide2", "ide3"]
VIRTIO_DISKS = ["virtio0", "virtio1", "virtio2"]


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
# 数据生成辅助函数
# ============================================================

def _rand_ip(base, suffix):
    return f"{base}.{suffix}"


def _gen_eth(name, speed, ip=None, gateway=None):
    """生成物理网卡 (eth) 网络接口条目"""
    net = {
        "name": name, "type": "eth", "active": True,
        "method": "static" if ip else "manual",
        "address": ip or "",
        "gateway": gateway or "",
        "speed_mbps": speed,
        "mtu": 1500,
    }
    return net


def _gen_mac(base_octets="BC:24:11", offset=0):
    """基于基数 + 偏移生成 MAC 地址"""
    o4 = (base_octets.split(":")[-1] if ":" in base_octets else "00")
    mac_int = int(o4, 16) + offset
    parts = base_octets.split(":")[:3]
    parts.append(f"{mac_int:02X}")
    parts.append(f"{random.randint(0, 255):02X}")
    parts.append(f"{random.randint(0, 255):02X}")
    return ":".join(parts)


def _gen_node(name, ip_suffix, cpu_model_idx, cpu_cores, cpu_sockets,
              mem_gb, rootfs_gb, swap_gb, ceph_node=False, ha_node=False,
              disk_devices=None, networks=None, status="online",
              uptime_days_min=7, uptime_days_max=90, mac_offset=0):
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
             "gateway": "192.168.1.1", "speed_mbps": 1000,
             "bridge_ports": "eno1", "mtu": 1500}
        ]

    # uptime: 在线节点有随机 uptime，离线节点 uptime=0
    if status == "online":
        uptime_sec = random.randint(
            uptime_days_min * 86400, uptime_days_max * 86400
        )
    else:
        uptime_sec = 0

    return {
        "name": name, "status": status,
        "pve_version": PVE_VERSIONS[cpu_model_idx % len(PVE_VERSIONS)],
        "kernel_version": KERNEL_VERSIONS[cpu_model_idx % len(KERNEL_VERSIONS)],
        "cpu_model": CPU_MODELS[cpu_model_idx % len(CPU_MODELS)],
        "cpu_cores": cpu_cores, "cpu_sockets": cpu_sockets,
        "cpu_load": cpu_load if status == "online" else 0,
        "memory_total_mb": mem_total,
        "memory_used_mb": mem_used if status == "online" else 0,
        "memory_free_mb": mem_free if status == "online" else mem_total,
        "memory_usage_pct": round(mem_used / mem_total * 100, 1) if status == "online" else 0.0,
        "rootfs_total_gb": rootfs_total, "rootfs_used_gb": rootfs_used,
        "rootfs_avail_gb": rootfs_avail,
        "swap_total_mb": swap_gb * 1024,
        "swap_used_mb": random.randint(0, int(swap_gb * 1024 * 0.1)) if status == "online" else 0,
        "disk_io_delay_ms": disk_io_delay if status == "online" else 0,
        "diskstat": disk_devices if status == "online" else [],
        "ip_address": f"192.168.{ip_suffix}.10",
        "mac_address": _gen_mac("BC:24:11", mac_offset),
        "uptime_seconds": uptime_sec,
        "is_ceph_node": ceph_node, "is_ha_node": ha_node,
    }


def _gen_vm(vmid, name, cpu_cores, mem_gb, disk_gb, status="running",
            has_template=False, snapshot_count=0, tags="", description="",
            cpu_model_idx=0):
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
        "os_type": random.choice(OS_TYPES),
        "snapshot_count": snapshot_count, "has_template": has_template,
        "tags": tags, "description": description,
        "snapshots": _gen_snapshots(vmid, snapshot_count),
    }


def _gen_snapshots(vmid, count):
    """生成 VM 快照列表"""
    if count <= 0:
        return []
    snap_names = ["pre-update", "pre-migration", "backup-2026", "checkpoint", "before-upgrade",
                  "weekly-auto", "pre-config", "baseline", "gold-image", "stable-v2"]
    snapshots = []
    parent = ""
    for i in range(count):
        name = f"snap{i+1}" if i < len(snap_names) else f"snap{i+1}"
        if i < len(snap_names):
            name = snap_names[i]
        snap_time = datetime.now(timezone.utc) - timedelta(days=random.randint(1, 90), hours=random.randint(0, 23))
        snapshots.append({
            "snapid": name,
            "name": name,
            "description": f"VM {vmid} 快照 {i+1}",
            "snap_time": snap_time.isoformat(),
            "parent": parent,
            "ram": random.choice([True, False]),
            "vmstate": random.choice([True, False, False]),
            "snap_type": random.choice(["snapshot", "snapshot", "qemu"]),
            "size_mb": None,
        })
        parent = name
    return snapshots


def _gen_vm_config(vmid, cpu_cores, mem_gb, cpu_model_idx=0, ha_enabled=False, agent_enabled=None):
    """生成 VM 配置（根据 CPU 型号选择 cpu_type，磁盘和网卡槽位多样化）"""
    cpu_model = CPU_MODELS[cpu_model_idx % len(CPU_MODELS)]
    # Intel 系列用 host / EPYC 系列用 EPYC
    if "AMD" in cpu_model:
        cpu_type = random.choice(["host", "EPYC", "qemu64"])
    else:
        cpu_type = random.choice(["host", "host", "max", "kvm64"])

    # 主磁盘: scsi0
    scsi_disks = [{
        "file": f"local-lvm:vm-{vmid}-disk-0",
        "size_gb": round(mem_gb * 2, 1),
    }]
    # 数据盘: 随机 0~2 块额外 scsi 磁盘
    num_extra_scsi = random.choices([0, 1, 2], weights=[4, 4, 2])[0]
    for k in range(1, 1 + num_extra_scsi):
        scsi_disks.append({
            "file": f"local-lvm:vm-{vmid}-disk-{k}",
            "size_gb": round(random.uniform(10, 200), 1),
        })

    # IDE 光驱: 随机 0~1 个
    ide_disks = []
    if random.random() < 0.4:
        ide_disks.append({"file": "local:iso/ubuntu-22.04-server.iso", "size_gb": 0})

    # 网卡: 1~2 个，模型随机
    net_devices = [{
        "model": random.choice(NET_MODELS_WEIGHTED),
        "bridge": "vmbr0",
        "mac": _gen_mac("BC:24:11", vmid),
    }]
    if random.random() < 0.25:
        net_devices.append({
            "model": "virtio",
            "bridge": "vmbr0" if random.random() < 0.5 else "bond0",
            "mac": _gen_mac("BC:24:11", vmid + 5000),
        })

    boot_parts = []
    if scsi_disks:
        boot_parts.append("scsi0")
    if net_devices:
        boot_parts.append("net0")

    return {
        "cpu_type": cpu_type,
        "cpu_cores": cpu_cores, "cpu_sockets": 1,
        "memory_mb": mem_gb * 1024,
        "balloon_min_mb": mem_gb * 512,
        "os_type": "l26",
        "boot_order": ",".join(boot_parts) if boot_parts else "scsi0",
        "scsi_disks": scsi_disks,
        "ide_disks": ide_disks,
        "net_devices": net_devices,
        "agent_enabled": agent_enabled if agent_enabled is not None else random.random() < 0.8,
        "ha_enabled": ha_enabled,
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


def _gen_lxc_config(vmid, cpu_cores, mem_gb, subnet_base="192.168.1",
                     storage_type=None, has_data_mount=False, mount_gb=0,
                     ha_enabled=False):
    """生成 LXC 配置（rootfs 存储类型多样化，支持数据挂载点）"""
    if storage_type is None:
        storage_type = random.choice(["local-lvm", "local-lvm", "local-zfs", "ceph-ssd"])

    # rootfs 存储类型
    rootfs = {"storage": storage_type, "size_gb": round(random.choice([4, 8, 8, 16, 32]), 1)}

    # 数据挂载点
    mount_points = []
    if has_data_mount:
        mount_points.append({
            "mp": f"mp{random.randint(0, 3)}",
            "storage": random.choice(["nfs-data", "ceph-ssd", "local-zfs"]),
            "size_gb": mount_gb if mount_gb > 0 else round(random.uniform(10, 100), 1),
        })

    # 网卡 IP：同一子网内分配不同 IP，避免冲突
    # vmid 的最后两位用于生成 IP 末位，但限制在 10~254 范围内
    ip_suffix = 10 + (vmid % 200)
    net_devices = [{
        "iface": "eth0",
        "bridge": "vmbr0",
        "ip": f"{subnet_base}.{ip_suffix}/24",
    }]

    return {
        "hostname": f"ct-{vmid}",
        "cpu_cores": cpu_cores,
        "memory_mb": mem_gb * 1024,
        "swap_mb": int(mem_gb * 512),
        "os_type": random.choice(["alpine", "debian", "ubuntu", "centos"]),
        "rootfs": rootfs,
        "mount_points": mount_points,
        "net_devices": net_devices,
        "ha_enabled": ha_enabled,
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
    """生成非 eth 类型网络接口（bridge / bond）"""
    net = {
        "name": name, "type": ntype, "active": True,
        "method": "static", "address": ip, "gateway": gateway,
        "speed_mbps": speed,
    }
    if ntype == "bridge":
        net["bridge_ports"] = extra.get("bridge_ports", "eno1")
    elif ntype == "bond":
        net["bond_mode"] = extra.get("bond_mode", "802.3ad")
        net["bond_slaves"] = extra.get("bond_slaves", "enp0s31f6 enp0s17f6")
    net["mtu"] = extra.get("mtu", 1500)
    return net


def _gen_backup_data(level, nodes, scan_time):
    """根据集群层级生成备份数据

    Level 1: 无备份
    Level 2: 少量备份任务，成功率低
    Level 3: 中等备份覆盖，成功率中等
    Level 4: 较高备份覆盖，成功率高
    Level 5: 几乎全覆盖，成功率很高
    """
    if level <= 1:
        return {"backup_storages": [], "backup_jobs": [], "backup_history": []}

    backup_storages = []
    backup_jobs = []
    backup_history = []

    # 备份存储：L2+ 有备份存储
    if level >= 2:
        node_name = nodes[0]["name"] if nodes else "pve-1"
        total_gb = 500 * level
        used_ratio = 0.2 + level * 0.1
        backup_storages.append({
            "storage_name": "backup-nfs",
            "storage_type": "nfs",
            "node_name": node_name,
            "path": "/mnt/pve/backup-nfs",
            "content_types": "backup",
            "active": True,
            "shared": True,
            "total_gb": total_gb,
            "used_gb": round(total_gb * used_ratio, 2),
            "avail_gb": round(total_gb * (1 - used_ratio), 2),
            "used_fraction": round(used_ratio, 4),
        })

    # 收集所有 VMID
    all_vmids = []
    for node in nodes:
        for vm in node.get("vms", []):
            all_vmids.append((node["name"], vm["vmid"], "qemu"))
        for ct in node.get("containers", []):
            all_vmids.append((node["name"], ct["vmid"], "lxc"))

    if not all_vmids:
        return {"backup_storages": backup_storages, "backup_jobs": [], "backup_history": []}

    # 备份任务覆盖率随等级提升
    coverage_map = {2: 0.2, 3: 0.5, 4: 0.7, 5: 0.9}
    coverage = coverage_map.get(level, 0)
    num_to_backup = max(1, int(len(all_vmids) * coverage))

    # 选择要备份的资源（按 VMID 排序取前 N 个）
    sorted_vmids = sorted(all_vmids, key=lambda x: x[1])
    to_backup = sorted_vmids[:num_to_backup]

    modes = ["snapshot", "suspend", "stop"]
    schedules = ["daily", "daily", "weekly"]

    for idx, (node_name, vmid, rtype) in enumerate(to_backup):
        job_id = f"vzdump-{vmid}"
        mode = modes[idx % len(modes)]
        schedule = schedules[idx % len(schedules)]
        enabled = True
        # L2 部分任务禁用
        if level == 2 and idx > 1:
            enabled = random.random() < 0.5

        backup_jobs.append({
            "job_id": job_id,
            "vmid": vmid,
            "resource_type": rtype,
            "node_name": node_name,
            "storage_name": "backup-nfs",
            "mode": mode,
            "schedule": schedule,
            "retention": f"keep={min(level + 1, 7)}",
            "enabled": enabled,
            "compress": "zstd" if level >= 3 else "lzo",
            "notes": f"自动备份 - {rtype} {vmid}",
            "last_run": (scan_time - timedelta(hours=random.randint(1, 24))).isoformat(),
            "last_status": "ok" if random.random() < (0.5 + level * 0.1) else "error",
        })

    # 备份历史（近 7 天的成功/失败记录）
    # 成功率随等级提升
    success_rate_map = {2: 0.5, 3: 0.7, 4: 0.85, 5: 0.95}
    success_rate = success_rate_map.get(level, 0.5)

    for day_offset in range(7):
        hist_time = scan_time - timedelta(days=day_offset)
        for node_name, vmid, rtype in to_backup:
            if random.random() > 0.9:  # 有些天没有备份
                continue
            status = "ok" if random.random() < success_rate else "failed"
            started = hist_time.replace(
                hour=random.randint(1, 4),
                minute=random.randint(0, 59),
            )
            duration = random.randint(60, 600)
            backup_history.append({
                "task_id": f"UPID:{node_name}:{uuid.uuid4().hex[:16]}",
                "vmid": vmid,
                "resource_type": rtype,
                "node_name": node_name,
                "storage_name": "backup-nfs",
                "mode": "snapshot",
                "status": status,
                "started_at": started.isoformat(),
                "finished_at": (started + timedelta(seconds=duration)).isoformat(),
                "duration_seconds": duration,
                "size_bytes": random.randint(1_000_000_000, 100_000_000_000),
                "filename": f"vzdump-{rtype}-{vmid}-{started.strftime('%Y_%m_%d')}.vma.zst",
                "error_message": "" if status == "ok" else "timeout",
            })

    return {
        "backup_storages": backup_storages,
        "backup_jobs": backup_jobs,
        "backup_history": backup_history,
    }


def _gen_sdn_data(level):
    """根据集群层级生成 SDN 数据

    Level 1-2: 无 SDN
    Level 3: 1 zone + 2 vnets + 2 subnets
    Level 4: 2 zones + 4 vnets + 4 subnets
    Level 5: 3 zones + 6 vnets + 6 subnets
    """
    if level <= 2:
        return {"zones": [], "vnets": [], "subnets": []}

    if level == 3:
        return {
            "zones": [
                {"zone": "zone-mgmt", "type": "vlan", "nodes": "pve-1 pve-2 pve-3"},
            ],
            "vnets": [
                {"vnet": "vnet-app", "zone": "zone-mgmt", "type": "vlan", "vlan": 100},
                {"vnet": "vnet-storage", "zone": "zone-mgmt", "type": "vlan", "vlan": 200},
            ],
            "subnets": [
                {"subnet": "10.100.0.0/24", "vnet": "vnet-app", "gateway": "10.100.0.1", "dnsserver": "8.8.8.8", "dnszoneprefix": "app.internal"},
                {"subnet": "10.200.0.0/24", "vnet": "vnet-storage", "gateway": "10.200.0.1", "dnsserver": "8.8.8.8", "dnszoneprefix": "storage.internal"},
            ],
        }

    if level == 4:
        return {
            "zones": [
                {"zone": "zone-prod", "type": "vlan", "nodes": "ceph-1 ceph-2 ceph-3"},
                {"zone": "zone-storage", "type": "vxlan", "nodes": "ceph-1 ceph-2 ceph-3"},
            ],
            "vnets": [
                {"vnet": "vnet-k8s", "zone": "zone-prod", "type": "vlan", "vlan": 100},
                {"vnet": "vnet-db", "zone": "zone-prod", "type": "vlan", "vlan": 110},
                {"vnet": "vnet-ceph-public", "zone": "zone-storage", "type": "vxlan", "vlan": None},
                {"vnet": "vnet-ceph-cluster", "zone": "zone-storage", "type": "vxlan", "vlan": None},
            ],
            "subnets": [
                {"subnet": "10.100.0.0/24", "vnet": "vnet-k8s", "gateway": "10.100.0.1", "dnsserver": "8.8.8.8", "dnszoneprefix": "k8s.internal"},
                {"subnet": "10.110.0.0/24", "vnet": "vnet-db", "gateway": "10.110.0.1", "dnsserver": "8.8.8.8", "dnszoneprefix": "db.internal"},
                {"subnet": "10.200.0.0/24", "vnet": "vnet-ceph-public", "gateway": "10.200.0.1", "dnsserver": "8.8.8.8", "dnszoneprefix": "ceph-pub.internal"},
                {"subnet": "172.16.0.0/24", "vnet": "vnet-ceph-cluster", "gateway": "172.16.0.1", "dnsserver": "8.8.8.8", "dnszoneprefix": "ceph-cluster.internal"},
            ],
        }

    # Level 5
    return {
        "zones": [
            {"zone": "zone-prod", "type": "vlan", "nodes": "prod-1 prod-2 prod-3 prod-4 prod-5"},
            {"zone": "zone-storage", "type": "vxlan", "nodes": "prod-1 prod-2 prod-3 prod-4 prod-5"},
            {"zone": "zone-mgmt", "type": "vlan", "nodes": "prod-1 prod-2 prod-3 prod-4 prod-5"},
        ],
        "vnets": [
            {"vnet": "vnet-k8s-prod", "zone": "zone-prod", "type": "vlan", "vlan": 100},
            {"vnet": "vnet-db-primary", "zone": "zone-prod", "type": "vlan", "vlan": 110},
            {"vnet": "vnet-db-replica", "zone": "zone-prod", "type": "vlan", "vlan": 111},
            {"vnet": "vnet-app-api", "zone": "zone-prod", "type": "vlan", "vlan": 120},
            {"vnet": "vnet-ceph-public", "zone": "zone-storage", "type": "vxlan", "vlan": None},
            {"vnet": "vnet-mgmt", "zone": "zone-mgmt", "type": "vlan", "vlan": 1},
        ],
        "subnets": [
            {"subnet": "10.100.0.0/24", "vnet": "vnet-k8s-prod", "gateway": "10.100.0.1", "dnsserver": "8.8.8.8", "dnszoneprefix": "k8s-prod.internal"},
            {"subnet": "10.110.0.0/24", "vnet": "vnet-db-primary", "gateway": "10.110.0.1", "dnsserver": "8.8.8.8", "dnszoneprefix": "db-prim.internal"},
            {"subnet": "10.111.0.0/24", "vnet": "vnet-db-replica", "gateway": "10.111.0.1", "dnsserver": "8.8.8.8", "dnszoneprefix": "db-repl.internal"},
            {"subnet": "10.120.0.0/24", "vnet": "vnet-app-api", "gateway": "10.120.0.1", "dnsserver": "8.8.8.8", "dnszoneprefix": "api.internal"},
            {"subnet": "10.200.0.0/24", "vnet": "vnet-ceph-public", "gateway": "10.200.0.1", "dnsserver": "8.8.8.8", "dnszoneprefix": "ceph.internal"},
            {"subnet": "192.168.99.0/24", "vnet": "vnet-mgmt", "gateway": "192.168.99.1", "dnsserver": "8.8.8.8", "dnszoneprefix": "mgmt.internal"},
        ],
    }


def _gen_replication_data(level, nodes):
    """根据集群层级生成复制任务数据

    Level 1-2: 无复制
    Level 3: 2 个复制任务 (节点间)
    Level 4: 3 个复制任务 (含 Ceph 节点)
    Level 5: 5 个复制任务 (企业级)
    """
    if level <= 2:
        return []

    node_names = [n["name"] for n in nodes]
    if len(node_names) < 2:
        return []

    now = datetime.now(timezone.utc)
    schedules = ["*/15", "*/30", "hourly", "*/5", "*/60"]
    states = ["active", "active", "active", "active", "disabled"]

    if level == 3:
        vms = [v for n in nodes for v in n.get("vms", [])[:2]]
        vmids = [v["vmid"] for v in vms[:2]] or [100, 101]
        return [{
            "job_id": f"{i+1}-0",
            "vmid": vmids[i] if i < len(vmids) else 100 + i,
            "resource_type": "vm",
            "source_node": node_names[0],
            "target_node": node_names[min(i + 1, len(node_names) - 1)],
            "schedule": schedules[i % len(schedules)],
            "rate_limit": random.choice([None, 100, 500]),
            "comment": f"VM {vmids[i] if i < len(vmids) else 100 + i} replication",
            "enabled": True,
            "state": states[i % len(states)],
            "last_sync": (now - timedelta(minutes=random.randint(5, 120))).isoformat(),
            "last_try": (now - timedelta(minutes=random.randint(1, 5))).isoformat(),
            "last_duration": random.randint(10, 300),
            "error_message": "",
            "sync_count": random.randint(50, 500),
            "raw": {},
        } for i in range(2)]

    if level == 4:
        vms = [v for n in nodes for v in n.get("vms", [])[:2]]
        vmids = [v["vmid"] for v in vms[:3]] or [100, 101, 102]
        return [{
            "job_id": f"{i+1}-0",
            "vmid": vmids[i] if i < len(vmids) else 100 + i,
            "resource_type": "vm",
            "source_node": node_names[i % len(node_names)],
            "target_node": node_names[(i + 1) % len(node_names)],
            "schedule": schedules[i % len(schedules)],
            "rate_limit": random.choice([None, 100, 500, 1000]),
            "comment": f"VM {vmids[i] if i < len(vmids) else 100 + i} HA replication",
            "enabled": True,
            "state": "active",
            "last_sync": (now - timedelta(minutes=random.randint(5, 60))).isoformat(),
            "last_try": (now - timedelta(minutes=random.randint(1, 5))).isoformat(),
            "last_duration": random.randint(10, 200),
            "error_message": "",
            "sync_count": random.randint(100, 1000),
            "raw": {},
        } for i in range(3)]

    # Level 5
    vms = [v for n in nodes for v in n.get("vms", [])[:2]]
    vmids = [v["vmid"] for v in vms[:5]] or [100, 101, 102, 103, 104]
    result = []
    for i in range(5):
        has_error = i == 3
        result.append({
            "job_id": f"{i+1}-0",
            "vmid": vmids[i] if i < len(vmids) else 100 + i,
            "resource_type": "vm",
            "source_node": node_names[i % len(node_names)],
            "target_node": node_names[(i + 2) % len(node_names)],
            "schedule": schedules[i % len(schedules)],
            "rate_limit": random.choice([None, 100, 500, 1000]),
            "comment": f"VM {vmids[i] if i < len(vmids) else 100 + i} production replication",
            "enabled": not has_error,
            "state": "error" if has_error else "active",
            "last_sync": (now - timedelta(minutes=random.randint(5, 60))).isoformat() if not has_error else None,
            "last_try": (now - timedelta(minutes=random.randint(1, 10))).isoformat(),
            "last_duration": random.randint(10, 300) if not has_error else None,
            "error_message": "ZFS send/receive failed: I/O error" if has_error else "",
            "sync_count": random.randint(200, 2000) if not has_error else random.randint(0, 50),
            "raw": {},
        })
    return result


def _gen_firewall_data(level, nodes):
    """根据集群层级生成防火墙数据

    Level 1-2: 基础防火墙（集群开关 + 几条规则）
    Level 3: 标准防火墙（集群规则 + 节点规则 + 安全组 + IPSet + 别名）
    Level 4: Ceph 集群防火墙（更多规则 + VM 级防火墙）
    Level 5: 企业级防火墙（完整配置 + 多安全组 + VM/CT 级防火墙）
    """
    node_names = [n["name"] for n in nodes]

    # 集群级选项（所有级别都有）
    cluster_options = {
        "enable": 1 if level >= 2 else 0,
        "policy_in": "DROP" if level >= 4 else "ACCEPT",
        "policy_out": "ACCEPT",
        "log_level_in": "info" if level >= 3 else "nolog",
        "log_level_out": "nolog",
        "dhcp": 0,
        "ipfilter": 0,
        "ndp": 0,
        "macfilter": 1 if level >= 3 else 0,
    }

    # 集群级规则
    cluster_rules = [
        {"pos": 0, "action": "ACCEPT", "direction": "in", "proto": "tcp", "dport": "22",
         "source": "", "dest": "", "comment": "SSH 访问", "enabled": True, "log": "", "macro": ""},
        {"pos": 1, "action": "ACCEPT", "direction": "in", "proto": "tcp", "dport": "8006",
         "source": "", "dest": "", "comment": "PVE Web UI", "enabled": True, "log": "", "macro": ""},
        {"pos": 2, "action": "ACCEPT", "direction": "in", "proto": "icmp",
         "source": "", "dest": "", "dport": "", "comment": "ICMP Ping", "enabled": True, "log": "", "macro": ""},
    ]
    if level >= 3:
        cluster_rules.extend([
            {"pos": 3, "action": "ACCEPT", "direction": "in", "proto": "tcp", "dport": "5900-5999",
             "source": "10.0.0.0/8", "dest": "", "comment": "VNC 内网访问", "enabled": True, "log": "", "macro": ""},
            {"pos": 4, "action": "ACCEPT", "direction": "in", "proto": "tcp", "dport": "3128",
             "source": "", "dest": "", "comment": "SPICE proxy", "enabled": True, "log": "", "macro": ""},
            {"pos": 5, "action": "DROP", "direction": "in", "proto": "", "dport": "",
             "source": "", "dest": "", "comment": "默认拒绝入站", "enabled": True, "log": "info", "macro": ""},
        ])
    if level >= 4:
        cluster_rules.extend([
            {"pos": 6, "action": "ACCEPT", "direction": "in", "proto": "tcp", "dport": "6789,3300",
             "source": "", "dest": "", "comment": "Ceph MON/MGR", "enabled": True, "log": "", "macro": ""},
            {"pos": 7, "action": "ACCEPT", "direction": "in", "proto": "tcp", "dport": "6800-7300",
             "source": "", "dest": "", "comment": "Ceph OSD/MDS", "enabled": True, "log": "", "macro": ""},
        ])

    # 安全组
    security_groups = {}
    if level >= 3:
        security_groups["web-servers"] = [
            {"pos": 0, "action": "ACCEPT", "direction": "in", "proto": "tcp", "dport": "80",
             "source": "", "dest": "", "comment": "HTTP", "enabled": True, "log": "", "macro": ""},
            {"pos": 1, "action": "ACCEPT", "direction": "in", "proto": "tcp", "dport": "443",
             "source": "", "dest": "", "comment": "HTTPS", "enabled": True, "log": "", "macro": ""},
            {"pos": 2, "action": "DROP", "direction": "in", "proto": "", "dport": "",
             "source": "", "dest": "", "comment": "拒绝其他", "enabled": True, "log": "warning", "macro": ""},
        ]
        security_groups["db-servers"] = [
            {"pos": 0, "action": "ACCEPT", "direction": "in", "proto": "tcp", "dport": "3306",
             "source": "10.0.0.0/8", "dest": "", "comment": "MySQL 内网", "enabled": True, "log": "", "macro": ""},
            {"pos": 1, "action": "ACCEPT", "direction": "in", "proto": "tcp", "dport": "5432",
             "source": "10.0.0.0/8", "dest": "", "comment": "PostgreSQL 内网", "enabled": True, "log": "", "macro": ""},
            {"pos": 2, "action": "DROP", "direction": "in", "proto": "", "dport": "",
             "source": "", "dest": "", "comment": "拒绝其他", "enabled": True, "log": "", "macro": ""},
        ]
    if level >= 5:
        security_groups["monitoring"] = [
            {"pos": 0, "action": "ACCEPT", "direction": "in", "proto": "tcp", "dport": "9090",
             "source": "192.168.0.0/16", "dest": "", "comment": "Prometheus", "enabled": True, "log": "", "macro": ""},
            {"pos": 1, "action": "ACCEPT", "direction": "in", "proto": "tcp", "dport": "3000",
             "source": "192.168.0.0/16", "dest": "", "comment": "Grafana", "enabled": True, "log": "", "macro": ""},
        ]

    # IPSet
    ipsets = {}
    if level >= 3:
        ipsets["management"] = {
            "name": "management",
            "comment": "管理 IP 白名单",
            "entries": [
                {"cidr": "192.168.1.0/24", "comment": "运维网段", "nomatch": False},
                {"cidr": "10.0.0.1", "comment": "网关", "nomatch": False},
            ],
        }
    if level >= 4:
        ipsets["monitoring-agents"] = {
            "name": "monitoring-agents",
            "comment": "监控 Agent IP",
            "entries": [
                {"cidr": "10.200.0.10", "comment": "Zabbix Server", "nomatch": False},
                {"cidr": "10.200.0.11", "comment": "Prometheus", "nomatch": False},
                {"cidr": "10.200.0.12", "comment": "Grafana", "nomatch": False},
            ],
        }
    if level >= 5:
        ipsets["blacklist"] = {
            "name": "blacklist",
            "comment": "IP 黑名单",
            "entries": [
                {"cidr": "203.0.113.0/24", "comment": "已知攻击源段", "nomatch": False},
                {"cidr": "198.51.100.0/24", "comment": "恶意扫描段", "nomatch": False},
            ],
        }

    # 别名
    aliases = []
    if level >= 3:
        aliases.extend([
            {"name": "internal_net", "cidr": "10.0.0.0/8", "alias_type": "net", "comment": "内网网段"},
            {"name": "pve_api", "cidr": "192.168.10.10", "alias_type": "ip", "comment": "PVE API 地址"},
        ])
    if level >= 4:
        aliases.extend([
            {"name": "ceph_public", "cidr": "10.200.0.0/24", "alias_type": "net", "comment": "Ceph 公网网段"},
            {"name": "ceph_cluster", "cidr": "172.16.0.0/24", "alias_type": "net", "comment": "Ceph 集群网段"},
        ])
    if level >= 5:
        aliases.extend([
            {"name": "ops_team", "cidr": "192.168.1.0/24", "alias_type": "net", "comment": "运维团队网段"},
            {"name": "backup_server", "cidr": "10.0.0.50", "alias_type": "ip", "comment": "备份服务器"},
        ])

    # 节点级防火墙
    nodes_fw = {}
    for n in nodes:
        nname = n["name"]
        node_opts = {
            "enable": 1 if level >= 3 else 0,
            "policy_in": "ACCEPT",
            "policy_out": "ACCEPT",
            "log_level_in": "nolog",
            "log_level_out": "nolog",
            "macfilter": 1 if level >= 3 else 0,
        }
        node_rules = []
        if level >= 3:
            node_rules = [
                {"pos": 0, "action": "ACCEPT", "direction": "in", "proto": "tcp", "dport": "8006",
                 "source": "management", "dest": "", "comment": "PVE Web UI (管理IP)", "enabled": True, "log": "", "macro": ""},
                {"pos": 1, "action": "ACCEPT", "direction": "in", "proto": "tcp", "dport": "22",
                 "source": "management", "dest": "", "comment": "SSH (管理IP)", "enabled": True, "log": "", "macro": ""},
            ]

        # VM 级防火墙（Level 4+ 为部分 VM 开启）
        vms_fw = {}
        if level >= 4:
            vms = n.get("vms", [])
            for vm in vms[:2]:  # 为前 2 个 VM 开启防火墙
                vmid = str(vm["vmid"])
                vms_fw[vmid] = {
                    "options": {"enable": 1, "policy_in": "DROP", "policy_out": "ACCEPT",
                                "dhcp": 0, "ipfilter": 1, "macfilter": 1},
                    "rules": [
                        {"pos": 0, "action": "ACCEPT", "direction": "in", "proto": "tcp", "dport": "22",
                         "source": "", "dest": "", "comment": "SSH", "enabled": True, "log": "", "macro": ""},
                        {"pos": 1, "action": "ACCEPT", "direction": "in", "proto": "tcp", "dport": "80,443",
                         "source": "", "dest": "", "comment": "HTTP/HTTPS", "enabled": True, "log": "", "macro": ""},
                    ],
                }

        # 容器级防火墙（Level 5 为部分 CT 开启）
        cts_fw = {}
        if level >= 5:
            cts = n.get("containers", [])
            for ct in cts[:1]:  # 为第 1 个容器开启防火墙
                vmid = str(ct["vmid"])
                cts_fw[vmid] = {
                    "options": {"enable": 1, "policy_in": "ACCEPT", "policy_out": "ACCEPT",
                                "dhcp": 0, "ipfilter": 0, "macfilter": 0},
                    "rules": [
                        {"pos": 0, "action": "ACCEPT", "direction": "in", "proto": "tcp", "dport": "80,443",
                         "source": "", "dest": "", "comment": "Web 服务", "enabled": True, "log": "", "macro": ""},
                    ],
                }

        nodes_fw[nname] = {
            "options": node_opts,
            "rules": node_rules,
            "vms": vms_fw,
            "cts": cts_fw,
        }

    return {
        "cluster_options": cluster_options,
        "cluster_rules": cluster_rules,
        "security_groups": security_groups,
        "ipsets": ipsets,
        "aliases": aliases,
        "nodes": nodes_fw,
    }


# ============================================================
# 磁盘设备生成器
# ============================================================

def _diskstat_sata(dev, heavy=False):
    """生成 SATA 磁盘的 diskstat 条目"""
    base_read = random.randint(10_000_000, 200_000_000_000) if heavy else random.randint(1_000_000, 50_000_000_000)
    base_write = random.randint(50_000_000, 500_000_000_000) if heavy else random.randint(5_000_000, 100_000_000_000)
    return {
        "dev": dev,
        "read": random.randint(base_read // 2, base_read),
        "write": random.randint(base_write // 2, base_write),
        "read_ios": random.randint(1000, 500_000),
        "write_ios": random.randint(5000, 800_000),
        "io_ms": round(random.uniform(1.0, 25.0) if not heavy else random.uniform(5.0, 40.0), 1),
    }


def _diskstat_nvme(dev):
    """生成 NVMe 磁盘的 diskstat 条目（IO 延迟低）"""
    return {
        "dev": dev,
        "read": random.randint(100_000_000, 2_000_000_000_000),
        "write": random.randint(50_000_000, 1_000_000_000_000),
        "read_ios": random.randint(50_000, 2_000_000),
        "write_ios": random.randint(50_000, 2_000_000),
        "io_ms": round(random.uniform(0.05, 2.0), 2),
    }


# ============================================================
# 五级架构数据
# ============================================================

def level_1_single_node():
    """Level 1 — 单节点入门: 1节点, 无Ceph, 无HA

    网络: vmbr0 (bridge) → eno1 (management, 1G)
    磁盘: sda (SATA OS)
    """
    node = _gen_node("pve-single", "10", 0, cpu_cores=4, cpu_sockets=1,
                     mem_gb=16, rootfs_gb=200, swap_gb=4,
                     uptime_days_min=14, uptime_days_max=180)
    # L1: 高资源压力 (CPU/内存使用率高，健康报告扣分)
    node["cpu_load"] = round(random.uniform(85, 95), 1)
    node["memory_used_mb"] = int(node["memory_total_mb"] * random.uniform(0.85, 0.95))
    node["memory_free_mb"] = node["memory_total_mb"] - node["memory_used_mb"]
    node["memory_usage_pct"] = round(node["memory_used_mb"] / node["memory_total_mb"] * 100, 1)
    # L1 磁盘: 仅 SATA 系统盘
    node["diskstat"] = [_diskstat_sata("sda")]
    node["disk_io_delay_ms"] = round(sum(d["io_ms"] for d in node["diskstat"]), 1)

    # L1: 2 stopped VMs (无HA/无快照/无Agent) + 3 LXCs (无HA/无备份)
    node["vms"] = [
        _gen_vm(100, "old-ubuntu", 1, 2, 20, status="stopped", tags="legacy"),
        _gen_vm(101, "test-box", 1, 1, 10, status="stopped", tags="test"),
    ]
    node["vm_configs"] = {
        str(100): _gen_vm_config(100, 1, 2, ha_enabled=False, agent_enabled=False),
        str(101): _gen_vm_config(101, 1, 1, ha_enabled=False, agent_enabled=False),
    }
    node["containers"] = [
        _gen_lxc(201, "alpine-dns", 1, 0.25, 2, tags="infra"),
        _gen_lxc(202, "nginx-proxy", 1, 0.5, 4, tags="web"),
        _gen_lxc(203, "home-assistant", 2, 1.0, 8, tags="iot"),
    ]
    node["lxc_configs"] = {
        str(201): _gen_lxc_config(201, 1, 0.25, subnet_base="192.168.10"),
        str(202): _gen_lxc_config(202, 1, 0.5, subnet_base="192.168.10"),
        str(203): _gen_lxc_config(203, 2, 1.0, subnet_base="192.168.10"),
    }
    node["storages"] = [
        _gen_storage("local", "dir", 200, 0.22),
        _gen_storage("local-lvm", "lvmthin", 180, 0.35),
    ]
    # L1 网络: vmbr0 (bridge) → eno1 (1G 管理网)
    eth_eno1 = _gen_eth("eno1", 1000, ip="192.168.10.10/24", gateway="192.168.10.1")
    vmbr0 = _gen_network("vmbr0", "bridge", "192.168.10.10/24",
                         gateway="192.168.10.1", speed=1000, bridge_ports="eno1")
    node["networks"] = [eth_eno1, vmbr0]
    node["vm_configs"] = {}
    return {
        "name": "单节点入门集群",
        "desc": "1节点 / 2VM(停机) / 3容器 / 无Ceph / 无HA / 无备份",
        "pve_version": "8.2.4",
        "nodes": [node], "ceph": None, "ha_resources": [],
    }


def level_2_dual_node():
    """Level 2 — 双节点小集群: 2节点, 无Ceph, 无HA

    网络 (每个节点):
      vmbr0 (bridge) → eno1 (management, 1G)
      vmbr1 (bridge) → eno2 (storage/NFS, 1G)
    磁盘: sda (SATA OS) + sdb (SATA data)
    """
    nodes = []
    # Node 1
    n1 = _gen_node("pve-1", "20", 1, cpu_cores=8, cpu_sockets=1,
                   mem_gb=32, rootfs_gb=100, swap_gb=8,
                   uptime_days_min=30, uptime_days_max=120)
    n1["diskstat"] = [_diskstat_sata("sda"), _diskstat_sata("sdb")]
    n1["disk_io_delay_ms"] = round(sum(d["io_ms"] for d in n1["diskstat"]), 1)

    # L2: 6 VMs (snapshot + agent, 无HA), 13 LXCs (无HA)
    n1["vms"] = [
        _gen_vm(100, "ubuntu-web", 2, 4, 50, tags="production,web", snapshot_count=1),
        _gen_vm(101, "centos-db", 4, 16, 200, tags="production,database", snapshot_count=1),
        _gen_vm(102, "dev-vm", 2, 4, 40, tags="development",
                has_template=False, snapshot_count=1),
    ]
    n1["vm_configs"] = {
        str(100): _gen_vm_config(100, 2, 4, cpu_model_idx=1, agent_enabled=True),
        str(101): _gen_vm_config(101, 4, 16, cpu_model_idx=1, agent_enabled=True),
        str(102): _gen_vm_config(102, 2, 4, cpu_model_idx=1, agent_enabled=True),
    }
    n1["containers"] = [
        _gen_lxc(200, "redis-1", 1, 1.0, 4, tags="cache"),
        _gen_lxc(201, "nginx-1", 1, 0.5, 2, tags="web"),
        _gen_lxc(202, "grafana", 2, 2.0, 10, tags="monitoring"),
        _gen_lxc(203, "prometheus", 2, 4.0, 20, tags="monitoring"),
        _gen_lxc(204, "portainer", 1, 0.5, 2, tags="docker"),
    ]
    n1["lxc_configs"] = {
        str(v): _gen_lxc_config(v, 1, 1, subnet_base="192.168.20") for v in [200, 201, 202, 203, 204]
    }
    n1["storages"] = [
        _gen_storage("local", "dir", 100, 0.3),
        _gen_storage("local-lvm", "lvmthin", 500, 0.4),
        _gen_storage("nfs-data", "nfs", 2000, 0.25),
    ]
    # L2 网络: vmbr0→eno1 (管理), vmbr1→eno2 (存储)
    n1["networks"] = [
        _gen_eth("eno1", 1000, ip="192.168.20.10/24", gateway="192.168.20.1"),
        _gen_eth("eno2", 1000, ip="10.0.0.10/24"),
        _gen_network("vmbr0", "bridge", "192.168.20.10/24",
                     gateway="192.168.20.1", speed=1000, bridge_ports="eno1"),
        _gen_network("vmbr1", "bridge", "10.0.0.10/24",
                     speed=1000, bridge_ports="eno2"),
    ]
    nodes.append(n1)

    # Node 2
    n2 = _gen_node("pve-2", "21", 2, cpu_cores=8, cpu_sockets=1,
                   mem_gb=32, rootfs_gb=100, swap_gb=8,
                   uptime_days_min=20, uptime_days_max=100)
    n2["diskstat"] = [_diskstat_sata("sda"), _diskstat_sata("sdb")]
    n2["disk_io_delay_ms"] = round(sum(d["io_ms"] for d in n2["diskstat"]), 1)

    n2["vms"] = [
        _gen_vm(100, "ubuntu-app-1", 2, 4, 50, tags="production,app", snapshot_count=1),
        _gen_vm(101, "ubuntu-app-2", 2, 4, 50, tags="production,app", snapshot_count=1),
        _gen_vm(102, "test-runner", 4, 8, 80, status="stopped", tags="ci"),
    ]
    n2["vm_configs"] = {
        str(v): _gen_vm_config(v, 2, 4, cpu_model_idx=2, agent_enabled=True) for v in [100, 101]
    }
    n2["vm_configs"]["102"] = _gen_vm_config(102, 4, 8, cpu_model_idx=2, agent_enabled=False)
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
        str(v): _gen_lxc_config(v, 1, 1, subnet_base="192.168.21") for v in [200, 201, 202, 203, 204, 205, 206, 207]
    }
    n2["storages"] = [
        _gen_storage("local", "dir", 100, 0.35),
        _gen_storage("local-lvm", "lvmthin", 500, 0.45),
        _gen_storage("nfs-data", "nfs", 2000, 0.30),
    ]
    # L2 网络: vmbr0→eno1 (管理), vmbr1→eno2 (存储)
    n2["networks"] = [
        _gen_eth("eno1", 1000, ip="192.168.20.11/24", gateway="192.168.20.1"),
        _gen_eth("eno2", 1000, ip="10.0.0.11/24"),
        _gen_network("vmbr0", "bridge", "192.168.20.11/24",
                     gateway="192.168.20.1", speed=1000, bridge_ports="eno1"),
        _gen_network("vmbr1", "bridge", "10.0.0.11/24",
                     speed=1000, bridge_ports="eno2"),
    ]
    nodes.append(n2)

    return {
        "name": "双节点小集群",
        "desc": "2节点 / 6VM / 13容器 / NFS共享存储 / 无Ceph",
        "pve_version": "8.3.2",
        "nodes": nodes, "ceph": None, "ha_resources": [],
    }


def level_3_triple_node():
    """Level 3 — 三节点标准集群: 3节点, 无Ceph, 无HA, 多存储

    网络 (每个节点):
      vmbr0 (bridge) → eno1 (management, 1G)
      bond0 (bond, 802.3ad) → enp0s31f6 + enp0s17f6 (app traffic, 2×10G)
    磁盘: sda (SATA OS) + sdb (SATA data) + nvme0n1 (NVMe cache)
    """
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
                      mem_gb=mem, rootfs_gb=rootfs, swap_gb=swap,
                      uptime_days_min=7, uptime_days_max=60,
                      mac_offset=i * 100)

        # L3 磁盘: sda (OS) + sdb (data) + nvme0n1 (cache)
        n["diskstat"] = [
            _diskstat_sata("sda"),
            _diskstat_sata("sdb"),
            _diskstat_nvme("nvme0n1"),
        ]
        n["disk_io_delay_ms"] = round(sum(d["io_ms"] for d in n["diskstat"]), 1)

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
            # L3: 50% VM 有快照
            snap = random.randint(1, 3) if random.random() < 0.5 else 0
            vm = _gen_vm(vid, vname_pattern.format(i + 1), vc, vd, vdsk,
                         status=status, tags=vtags,
                         snapshot_count=snap,
                         cpu_model_idx=cpu_idx)
            n["vms"].append(vm)
            # L3: 25% HA, 80% agent
            ha = random.random() < 0.25
            agent = random.random() < 0.80
            n["vm_configs"][str(vid)] = _gen_vm_config(vid, vc, vd, cpu_model_idx=cpu_idx,
                                                       ha_enabled=ha, agent_enabled=agent)

        # 每节点 8~13 个 LXC
        n["containers"] = []
        n["lxc_configs"] = {}
        lxc_pool = [
            ("nginx-{}", 1, 0.5, 2, "web", False, 0),
            ("redis-{}", 1, 1.0, 4, "cache", False, 0),
            ("postgres-{}", 2, 4.0, 30, "database", True, 50),
            ("elasticsearch-{}", 2, 4.0, 40, "search", True, 80),
            ("grafana-{}", 2, 2.0, 10, "monitoring", False, 0),
            ("prometheus-{}", 2, 4.0, 20, "monitoring", True, 30),
            ("portainer-{}", 1, 0.5, 2, "docker", False, 0),
            ("minio-{}", 2, 2.0, 50, "storage", True, 100),
            ("rabbitmq-{}", 1, 2.0, 10, "mq", False, 0),
            ("consul-{}", 1, 1.0, 4, "infra", False, 0),
            ("vault-{}", 1, 1.0, 4, "security", False, 0),
            ("traefik-{}", 1, 0.5, 2, "web", False, 0),
            ("wikijs-{}", 1, 1.0, 8, "docs", False, 0),
        ]
        num_lxc = random.randint(8, 13)
        for j in range(num_lxc):
            tmpl = lxc_pool[j % len(lxc_pool)]
            cid = lxc_base + j + 1
            status = "running" if random.random() > 0.05 else "stopped"
            ct = _gen_lxc(cid, tmpl[0].format(i + 1), tmpl[1], tmpl[2], tmpl[3],
                          status=status, tags=tmpl[4])
            n["containers"].append(ct)
            ha_lxc = random.random() < 0.25
            n["lxc_configs"][str(cid)] = _gen_lxc_config(
                cid, tmpl[1], tmpl[2], subnet_base=f"192.168.{ip}",
                has_data_mount=tmpl[5], mount_gb=tmpl[6], ha_enabled=ha_lxc,
            )

        n["storages"] = [
            _gen_storage("local", "dir", 120, 0.3),
            _gen_storage("local-lvm", "lvmthin", 800, random.uniform(0.3, 0.6)),
            _gen_storage("nfs-backup", "nfs", 4000, random.uniform(0.2, 0.5)),
            _gen_storage("iscsi-data", "lvmthin", 2000, random.uniform(0.4, 0.7)),
        ]

        # L3 网络: vmbr0→eno1 (1G 管理), bond0→enp0s31f6+enp0s17f6 (2×10G 应用)
        n["networks"] = [
            _gen_eth("eno1", 1000, ip=f"192.168.30.{10 + i}/24", gateway="192.168.30.1"),
            _gen_eth("enp0s31f6", 10000),
            _gen_eth("enp0s17f6", 10000),
            _gen_network("vmbr0", "bridge", f"192.168.30.{10 + i}/24",
                         gateway="192.168.30.1", speed=1000, bridge_ports="eno1"),
            _gen_network("bond0", "bond", f"10.0.0.{10 + i}/24", speed=20000,
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
    """Level 4 — 三节点 Ceph + 基础 HA

    网络 (每个节点):
      vmbr0 (bridge) → eno1 (management, 1G)
      vmbr1 (bridge) → enp0s31f6 (Ceph public network, 10G)
      bond0 (bond, 802.3ad) → enp3s0f0 + enp3s0f1 (Ceph cluster/replication + VM, 2×25G)
    磁盘: sda (SATA OS) + sdb+sdc (SATA OSD) + nvme0n1 (NVMe journal)
    """
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
                      uptime_days_min=14, uptime_days_max=90,
                      mac_offset=1000 + i * 100)

        # L4 磁盘: sda (OS) + sdb+sdc (Ceph OSD) + nvme0n1 (journal)
        n["diskstat"] = [
            _diskstat_sata("sda"),
            _diskstat_sata("sdb", heavy=True),
            _diskstat_sata("sdc", heavy=True),
            _diskstat_nvme("nvme0n1"),
        ]
        n["disk_io_delay_ms"] = round(sum(d["io_ms"] for d in n["diskstat"]), 1)

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
            # L4: 50% VM 有快照 (1-5)
            snap = random.randint(1, 5) if random.random() < 0.5 else 0
            vm = _gen_vm(vid, vname_pattern.format(i + 1), vc, vd, vdsk,
                         status=status, tags=vtags,
                         snapshot_count=snap,
                         cpu_model_idx=cpu_idx)
            n["vms"].append(vm)
            # L4: 50% HA, 90% agent
            ha = random.random() < 0.5
            agent = random.random() < 0.90
            n["vm_configs"][str(vid)] = _gen_vm_config(vid, vc, vd, cpu_model_idx=cpu_idx,
                                                       ha_enabled=ha, agent_enabled=agent)

        n["containers"] = []
        n["lxc_configs"] = {}
        lxc_pool = [
            ("nginx-lb-{}", 1, 0.5, 2, "web,loadbalancer", False, 0),
            ("coredns-{}", 1, 0.5, 2, "infra,dns", False, 0),
            ("cert-manager-{}", 1, 1.0, 4, "security", False, 0),
            ("redis-sidecar-{}", 1, 1.0, 4, "cache", False, 0),
            ("prometheus-node-{}", 1, 1.0, 8, "monitoring", True, 20),
            ("alertmanager-{}", 1, 0.5, 4, "monitoring", False, 0),
            ("loki-{}", 2, 2.0, 20, "monitoring,logging", True, 50),
            ("harbor-registry-{}", 2, 2.0, 50, "docker,registry", True, 100),
            ("argocd-{}", 2, 2.0, 10, "ci,gitops", False, 0),
            ("minio-rgw-{}", 2, 2.0, 30, "storage", True, 80),
        ]
        num_lxc = random.randint(8, 10)
        for j in range(num_lxc):
            tmpl = lxc_pool[j % len(lxc_pool)]
            cid = lxc_base + j + 1
            ct = _gen_lxc(cid, tmpl[0].format(i + 1), tmpl[1], tmpl[2], tmpl[3],
                          tags=tmpl[4])
            n["containers"].append(ct)
            ha_lxc = random.random() < 0.50
            n["lxc_configs"][str(cid)] = _gen_lxc_config(
                cid, tmpl[1], tmpl[2], subnet_base=f"192.168.{ip}",
                storage_type="ceph-ssd", has_data_mount=tmpl[5], mount_gb=tmpl[6],
                ha_enabled=ha_lxc,
            )

        n["storages"] = [
            _gen_storage("local", "dir", 100, 0.25),
            _gen_storage("ceph-ssd", "rbd", 5000, random.uniform(0.3, 0.5)),
            _gen_storage("ceph-hdd", "rbd", 15000, random.uniform(0.4, 0.6)),
        ]
        # L4 网络: vmbr0→eno1 (1G), vmbr1→enp0s31f6 (10G Ceph public),
        #          bond0→enp3s0f0+enp3s0f1 (2×25G Ceph cluster)
        n["networks"] = [
            _gen_eth("eno1", 1000, ip=f"192.168.40.{10 + i}/24", gateway="192.168.40.1"),
            _gen_eth("enp0s31f6", 10000),
            _gen_eth("enp3s0f0", 25000),
            _gen_eth("enp3s0f1", 25000),
            _gen_network("vmbr0", "bridge", f"192.168.40.{10 + i}/24",
                         gateway="192.168.40.1", speed=1000, bridge_ports="eno1"),
            _gen_network("vmbr1", "bridge", f"10.10.0.{10 + i}/24",
                         speed=10000, bridge_ports="enp0s31f6"),
            _gen_network("bond0", "bond", f"172.16.0.{10 + i}/24", speed=50000,
                         bond_mode="802.3ad", bond_slaves="enp3s0f0 enp3s0f1"),
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
    """Level 5 — 多节点企业集群: 5节点 + Ceph WARN + 大规模

    网络 (每个节点):
      vmbr0 (bridge) → eno1 (management, 1G)
      vmbr1 (bridge) → enp0s31f6 (Ceph public network, 10G)
      bond0 (bond, 802.3ad) → enp3s0f0 + enp3s0f1 (VM/应用流量, 2×25G)
    磁盘: sda (SATA OS) + sdb+sdc (SATA OSD) + nvme0n1+nvme1n1 (NVMe journal/wal)
    prod-4 离线测试
    """
    nodes = []
    node_specs = [
        ("prod-1", "50", 0, 32, 2, 256, 100, 64, True, True, "online"),
        ("prod-2", "51", 3, 32, 2, 256, 100, 64, True, True, "online"),
        ("prod-3", "52", 2, 64, 2, 512, 100, 64, True, True, "online"),
        ("prod-4", "53", 5, 64, 2, 512, 100, 64, True, False, "offline"),
        ("prod-5", "54", 4, 48, 2, 384, 100, 64, True, True, "online"),
    ]
    vm_base = 100
    lxc_base = 200
    for i, spec in enumerate(node_specs):
        (name, ip, cpu_idx, cores, sock, mem, rootfs, swap,
         ceph_node, ha_node, node_status) = spec

        # 新节点 uptime 短，老节点长；prod-4 离线所以 uptime=0
        if node_status == "offline":
            uptime_min, uptime_max = 1, 1
        else:
            uptime_min = random.randint(3, 14)
            uptime_max = random.randint(30, 180)

        n = _gen_node(name, ip, cpu_idx, cpu_cores=cores, cpu_sockets=sock,
                      mem_gb=mem, rootfs_gb=rootfs, swap_gb=swap,
                      ceph_node=ceph_node, ha_node=ha_node,
                      status=node_status,
                      uptime_days_min=uptime_min, uptime_days_max=uptime_max,
                      mac_offset=2000 + i * 100)

        # L5 磁盘: sda (OS) + sdb+sdc (OSD) + nvme0n1+nvme1n1 (journal/wal)
        n["diskstat"] = [
            _diskstat_sata("sda"),
            _diskstat_sata("sdb", heavy=True),
            _diskstat_sata("sdc", heavy=True),
            _diskstat_nvme("nvme0n1"),
            _diskstat_nvme("nvme1n1"),
        ]
        n["disk_io_delay_ms"] = round(sum(d["io_ms"] for d in n["diskstat"]), 1)

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
                         snapshot_count=random.randint(2, 8),
                         cpu_model_idx=cpu_idx)
            n["vms"].append(vm)
            ha = random.random() < 0.9
            n["vm_configs"][str(vid)] = _gen_vm_config(vid, tmpl[1], tmpl[2], cpu_model_idx=cpu_idx,
                                                       ha_enabled=ha, agent_enabled=True)

        # 每节点 10~14 个 LXC（prod-4 离线节点仅用 VM，无 LXC）
        n["containers"] = []
        n["lxc_configs"] = {}
        if node_status != "offline":
            lxc_pool = [
                ("nginx-ingress-{}", 2, 1.0, 2, "web,loadbalancer", False, 0),
                ("coredns-{}", 1, 0.5, 2, "infra,dns", False, 0),
                ("etcd-{}", 2, 4.0, 10, "infra,etcd", True, 20),
                ("harbor-registry-{}", 2, 4.0, 50, "docker,registry", True, 100),
                ("argocd-{}", 2, 2.0, 10, "ci,gitops", False, 0),
                ("prometheus-{}", 2, 4.0, 40, "monitoring", True, 50),
                ("grafana-{}", 2, 2.0, 10, "monitoring", False, 0),
                ("loki-{}", 2, 4.0, 50, "monitoring,logging", True, 80),
                ("minio-{}", 4, 4.0, 100, "storage", True, 200),
                ("vault-{}", 2, 2.0, 4, "security", False, 0),
                ("consul-{}", 1, 1.0, 4, "infra", False, 0),
                ("rabbitmq-{}", 2, 2.0, 10, "mq", False, 0),
                ("cert-manager-{}", 1, 1.0, 4, "security", False, 0),
                ("zabbix-{}", 2, 4.0, 30, "monitoring", True, 30),
            ]
            num_lxc = random.randint(10, 14)
            for j in range(num_lxc):
                tmpl = lxc_pool[j % len(lxc_pool)]
                cid = lxc_base + j + 1
                ct = _gen_lxc(cid, tmpl[0].format(i + 1), tmpl[1], tmpl[2], tmpl[3],
                              tags=tmpl[4])
                n["containers"].append(ct)
                ha_lxc = random.random() < 0.9
                n["lxc_configs"][str(cid)] = _gen_lxc_config(
                    cid, tmpl[1], tmpl[2], subnet_base=f"192.168.{ip}",
                    storage_type="ceph-ssd", has_data_mount=tmpl[5], mount_gb=tmpl[6],
                    ha_enabled=ha_lxc,
                )
        else:
            num_lxc = 0

        n["storages"] = [
            _gen_storage("local", "dir", 100, 0.2),
            _gen_storage("ceph-ssd", "rbd", 10000, random.uniform(0.3, 0.6)),
            _gen_storage("ceph-hdd", "rbd", 40000, random.uniform(0.4, 0.7)),
            _gen_storage("local-zfs", "zfspool", 2000, random.uniform(0.2, 0.5)),
        ]
        # L5 网络: vmbr0→eno1 (1G), vmbr1→enp0s31f6 (10G Ceph public),
        #          bond0→enp3s0f0+enp3s0f1 (2×25G 应用)
        n["networks"] = [
            _gen_eth("eno1", 1000, ip=f"192.168.50.{10 + i}/24", gateway="192.168.50.1"),
            _gen_eth("enp0s31f6", 10000),
            _gen_eth("enp3s0f0", 25000),
            _gen_eth("enp3s0f1", 25000),
            _gen_network("vmbr0", "bridge", f"192.168.50.{10 + i}/24",
                         gateway="192.168.50.1", speed=1000, bridge_ports="eno1"),
            _gen_network("vmbr1", "bridge", f"10.10.0.{10 + i}/24",
                         speed=10000, bridge_ports="enp0s31f6"),
            _gen_network("bond0", "bond", f"172.16.0.{10 + i}/24", speed=50000,
                         bond_mode="802.3ad",
                         bond_slaves="enp3s0f0 enp3s0f1"),
        ]
        vm_base += len(n["vms"])
        lxc_base += num_lxc
        nodes.append(n)

    # Ceph: HEALTH_OK — 全部 OSD 正常
    ceph = {
        "health": "HEALTH_OK",
        "total_osds": 24, "up_osds": 24, "in_osds": 24,
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
        "desc": "5节点 / ~65VM / ~60容器 / Ceph OK(24OSD) / 5 HA资源 / 复杂网络 / prod-4离线",
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
        last_scan = (c.get("last_scanned_at") or "")[:19] or "从未扫描"
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
                "version": f"0.6.0",
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
                "agent_id": aid, "status": "online", "version": "0.6.0"
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
                cluster_id, agent_ids, data, scan_time, scan_idx, num_scans, level
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


def _build_scan_payload(cluster_id, agent_ids, data, scan_time, scan_idx, total_scans, level=1):
    """构建扫描上传 payload，带真实波动模式

    波动策略:
      - 一天时段模式: 工作时间 (9-18) CPU 更高，夜间更低
      - 偶发尖刺节点: 随机 1~2 个节点 CPU 冲到 70-95%
      - 部分 VM 内存压力: 随机 ~20% 的运行中 VM 内存使用 80-95%
      - 磁盘 I/O 与运行中 VM 数量正相关
    """
    # 计算工作时段系数 (基于扫描时间)
    scan_hour = scan_time.hour
    if 9 <= scan_hour <= 18:
        hour_factor = 1.3   # 工作时间负载偏高
    elif 19 <= scan_hour <= 23:
        hour_factor = 0.8   # 晚间负载降低
    else:
        hour_factor = 0.5   # 深夜负载最低

    # 随机选择 1~2 个节点作为"尖刺"节点
    spike_nodes = set()
    if len(data["nodes"]) > 1:
        num_spikes = random.choices([0, 1, 2], weights=[5, 3, 2])[0]
        spike_indices = random.sample(range(len(data["nodes"])), min(num_spikes, len(data["nodes"])))
        spike_nodes = set(spike_indices)

    nodes_out = []
    for i, node_template in enumerate(data["nodes"]):
        # 深拷贝节点数据并添加波动
        node = json.loads(json.dumps(node_template))

        # 跳过离线节点的性能数据波动
        if node.get("status") != "online":
            nodes_out.append(node)
            continue

        # 基础波动 + 工作时段系数
        base_drift = random.uniform(-0.15, 0.15)
        effective_drift = base_drift + (hour_factor - 1.0)

        # 尖刺节点: CPU 强制拉高
        if i in spike_nodes:
            node["cpu_load"] = round(random.uniform(70, 95), 1)
        else:
            node["cpu_load"] = max(1, min(100,
                round(node["cpu_load"] + effective_drift * node["cpu_load"], 1)))

        # 内存波动
        mem_drift = int(node["memory_total_mb"] * effective_drift * 0.3)
        node["memory_used_mb"] = max(0, min(
            node["memory_total_mb"],
            node["memory_used_mb"] + mem_drift))
        node["memory_free_mb"] = node["memory_total_mb"] - node["memory_used_mb"]
        node["memory_usage_pct"] = round(
            node["memory_used_mb"] / node["memory_total_mb"] * 100, 1)

        # 磁盘 I/O: 与运行中 VM 数量相关 + 工作时段系数
        running_vm_count = len([v for v in node.get("vms", []) if v["status"] == "running"])
        io_scale = 1.0 + running_vm_count * 0.15 + (hour_factor - 0.5) * 0.5
        for disk in node.get("diskstat", []):
            disk["io_ms"] = round(max(0, disk["io_ms"] * io_scale + random.uniform(-3, 3)), 1)
        node["disk_io_delay_ms"] = round(
            sum(d["io_ms"] for d in node.get("diskstat", [])), 1)

        # VM 状态微调
        for vm in node.get("vms", []):
            if vm["status"] == "running":
                vm["cpu_usage"] = round(max(0, min(100,
                    vm["cpu_usage"] + random.uniform(-10, 10))), 1)

                # 约 20% 的 VM 内存压力大 (80-95%)
                if random.random() < 0.20:
                    vm["memory_used_mb"] = int(vm["memory_mb"] * random.uniform(0.80, 0.95))
                else:
                    vm["memory_used_mb"] = max(0, min(vm["memory_mb"],
                        vm["memory_used_mb"] + int(vm["memory_mb"] * random.uniform(-0.1, 0.1))))

                vm["net_in_bps"] = max(0, vm["net_in_bps"] + int(
                    vm["net_in_bps"] * effective_drift * 0.3) + random.randint(-5000000, 5000000))
                vm["net_out_bps"] = max(0, vm["net_out_bps"] + int(
                    vm["net_out_bps"] * effective_drift * 0.3) + random.randint(-5000000, 5000000))

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
        "sdn": _gen_sdn_data(level),
        "replication": _gen_replication_data(level, nodes_out),
        "firewall": _gen_firewall_data(level, nodes_out),
        "backups": _gen_backup_data(level, nodes_out, scan_time),
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
  Level 1  单节点入门   (1节点 / 2VM停机 / 3容器 / 无Ceph / 无HA / 无备份)
  Level 2  双节点小集群  (2节点 / 6VM / 13容器 / NFS存储 / 无Ceph)
  Level 3  三节点标准集群 (3节点 / ~20VM / ~35容器 / 多存储 / Bond网络 / 25%HA)
  Level 4  Ceph三节点    (3节点 / ~36VM / ~30容器 / Ceph OK / 50%HA)
  Level 5  企业生产集群   (5节点 / ~65VM / ~60容器 / Ceph OK / 90%HA / prod-4离线)

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