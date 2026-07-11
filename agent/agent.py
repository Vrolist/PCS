#!/usr/bin/env python3
"""
PVE Cluster Scan Agent — 单文件版，无外部依赖

功能：
  1. 注册到管理平台（获取 agent_id）
  2. 定时心跳（每 300s / 5 分钟）
  3. 定时扫描 PVE 集群（每 300s / 5 分钟）
  4. 上传数据到管理平台

用法：
  # 安装模式（交互式，配置 + 注册 + 安装 systemd 服务）
  python3 agent.py install

  # 直接运行（已配置过）
  python3 agent.py run

  # 查看状态
  python3 agent.py status

  # 卸载
  python3 agent.py uninstall
"""
import json
import logging
import os
import shutil
import signal
import socket
import ssl
import subprocess
import sys
import time
import threading
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

VERSION = "0.10.2"

# 路径常量
INSTALL_DIR = Path("/opt/pcs-agent")
CONFIG_FILE = INSTALL_DIR / "config.env"
SERVICE_FILE = Path("/etc/systemd/system/pcs-agent.service")
LOG_FILE = INSTALL_DIR / "agent.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(str(LOG_FILE)) if LOG_FILE.parent.exists() else logging.StreamHandler(),
    ],
)
logger = logging.getLogger("pcs-agent")

# 忽略 SSL 验证（PVE 默认自签证书）
ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

# 自定义 opener：跟随重定向 + 忽略 SSL 验证
_http_opener = urllib.request.build_opener(
    urllib.request.HTTPRedirectHandler,
    urllib.request.HTTPSHandler(context=ssl_ctx),
)


# ============================================================
# 配置管理 (KEY=VALUE 文本文件)
# ============================================================

class Config:
    def __init__(self):
        self.platform_url = ""
        self.agent_token = ""
        self.agent_id = ""
        self.cluster_id = ""
        self.pve_endpoint = ""
        self.pve_username = "root@pam"
        self.pve_password = ""
        self.pve_version = ""
        self.scan_interval = 300
        self.heartbeat_interval = 120

    def load(self):
        if not CONFIG_FILE.exists():
            return False
        for line in CONFIG_FILE.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if hasattr(self, key):
                    # 数字类型转换
                    if key in ("scan_interval", "heartbeat_interval"):
                        value = int(value)
                    setattr(self, key, value)
        return True

    def save(self):
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            f'platform_url="{self.platform_url}"',
            f'agent_token="{self.agent_token}"',
            f'agent_id="{self.agent_id}"',
            f'cluster_id="{self.cluster_id}"',
            f'pve_endpoint="{self.pve_endpoint}"',
            f'pve_username="{self.pve_username}"',
            f'pve_password="{self.pve_password}"',
            f'pve_version="{self.pve_version}"',
            f'scan_interval={self.scan_interval}',
            f'heartbeat_interval={self.heartbeat_interval}',
        ]
        CONFIG_FILE.write_text("\n".join(lines) + "\n")
        CONFIG_FILE.chmod(0o600)  # 仅 owner 可读写

    @property
    def is_registered(self):
        return bool(self.agent_id)


# ============================================================
# HTTP 工具（纯 stdlib）
# ============================================================

def http_post(url, data, timeout=30):
    """发送 JSON POST 请求（自动跟随重定向）"""
    payload = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with _http_opener.open(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def http_get(url, timeout=30):
    """发送 GET 请求（自动跟随重定向）"""
    req = urllib.request.Request(url)
    with _http_opener.open(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ============================================================
# PVE API 客户端
# ============================================================

class PVEClient:
    def __init__(self, endpoint, username, password):
        self.endpoint = endpoint.rstrip("/")
        self.username = username
        self.password = password
        self.ticket = ""
        self.csrf = ""
        # 判断是 API Token 还是密码
        # Token 格式: user@realm!tokenid=uuid  或  user@realm!tokenid=uuid（含=号）
        self._is_token = "!" in password and "=" in password

    def authenticate(self):
        if self._is_token:
            # API Token 认证：无需调用 /access/ticket，直接在请求 header 中携带
            logger.info("PVE API Token 认证模式")
        else:
            # 密码认证：调用 /access/ticket 获取 ticket
            url = f"{self.endpoint}/api2/json/access/ticket"
            data = json.dumps({"username": self.username, "password": self.password}).encode()
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
            with _http_opener.open(req) as resp:
                result = json.loads(resp.read())["data"]
            self.ticket = result["ticket"]
            self.csrf = result["CSRFPreventionToken"]
            logger.info("PVE 认证成功")

    def get(self, path):
        url = f"{self.endpoint}/api2/json{path}"
        req = urllib.request.Request(url)
        if self._is_token:
            # API Token 认证
            req.add_header("Authorization", f"PVEAPIToken={self.password}")
        else:
            # Ticket 认证
            req.add_header("Cookie", f"PVEAuthCookie={self.ticket}")
        with _http_opener.open(req) as resp:
            return json.loads(resp.read())["data"]

    def get_version(self):
        return self.get("/version").get("version", "")

    def get_cluster_status(self):
        return self.get("/cluster/status")

    def get_node_status(self, node):
        return self.get(f"/nodes/{node}/status")

    def get_node_qemu(self, node):
        return self.get(f"/nodes/{node}/qemu")

    def get_node_lxc(self, node):
        return self.get(f"/nodes/{node}/lxc")

    def get_node_storage(self, node):
        return self.get(f"/nodes/{node}/storage")

    def get_node_network(self, node):
        return self.get(f"/nodes/{node}/network")

    def get_ceph_status(self):
        try:
            return self.get("/cluster/ceph/status")
        except Exception:
            return None

    def get_vm_config(self, node, vmid):
        return self.get(f"/nodes/{node}/qemu/{vmid}/config")

    def get_lxc_config(self, node, vmid):
        return self.get(f"/nodes/{node}/lxc/{vmid}/config")

    def get_ha_resources(self):
        try:
            return self.get("/cluster/ha/resources")
        except Exception:
            return []

    def get_vm_snapshots(self, node, vmid):
        try:
            return self.get(f"/nodes/{node}/qemu/{vmid}/snapshot")
        except Exception:
            return []

    def get_sdn_zones(self):
        try:
            return self.get("/cluster/sdn/zones")
        except Exception:
            return []

    def get_sdn_vnets(self):
        try:
            return self.get("/cluster/sdn/vnets")
        except Exception:
            return []

    def get_sdn_subnets(self):
        try:
            return self.get("/cluster/sdn/subnets")
        except Exception:
            return []

    def get_backup_jobs(self, node):
        """获取节点备份任务配置"""
        try:
            return self.get(f"/nodes/{node}/vzdump")
        except Exception:
            return []

    def get_backup_history(self, node, limit=50):
        """获取备份历史任务"""
        try:
            return self.get(f"/nodes/{node}/tasks?limit={limit}&typefilter=vzdump")
        except Exception:
            return []

    def get_backup_content(self, node, storage):
        """获取备份存储内容"""
        try:
            return self.get(f"/nodes/{node}/storage/{storage}/content?content=backup")
        except Exception:
            return []

    def get_node_replication(self, node):
        """获取节点的复制任务列表"""
        try:
            return self.get(f"/nodes/{node}/replication")
        except Exception:
            return []

    # ---- 防火墙 API ----
    def get_cluster_fw_options(self):
        try:
            return self.get("/cluster/firewall/options")
        except Exception:
            return {}

    def get_cluster_fw_rules(self):
        try:
            return self.get("/cluster/firewall/rules")
        except Exception:
            return []

    def get_cluster_fw_groups(self):
        try:
            return self.get("/cluster/firewall/groups")
        except Exception:
            return []

    def get_cluster_fw_group_rules(self, group):
        try:
            return self.get(f"/cluster/firewall/groups/{group}")
        except Exception:
            return []

    def get_cluster_fw_ipsets(self):
        try:
            return self.get("/cluster/firewall/ipset")
        except Exception:
            return []

    def get_cluster_fw_ipset(self, name):
        try:
            return self.get(f"/cluster/firewall/ipset/{name}")
        except Exception:
            return []

    def get_cluster_fw_aliases(self):
        try:
            return self.get("/cluster/firewall/aliases")
        except Exception:
            return []

    def get_node_fw_options(self, node):
        try:
            return self.get(f"/nodes/{node}/firewall/options")
        except Exception:
            return {}

    def get_node_fw_rules(self, node):
        try:
            return self.get(f"/nodes/{node}/firewall/rules")
        except Exception:
            return []

    def get_vm_fw_options(self, node, vmid):
        try:
            return self.get(f"/nodes/{node}/qemu/{vmid}/firewall/options")
        except Exception:
            return {}

    def get_vm_fw_rules(self, node, vmid):
        try:
            return self.get(f"/nodes/{node}/qemu/{vmid}/firewall/rules")
        except Exception:
            return []

    def get_ct_fw_options(self, node, vmid):
        try:
            return self.get(f"/nodes/{node}/lxc/{vmid}/firewall/options")
        except Exception:
            return {}

    def get_ct_fw_rules(self, node, vmid):
        try:
            return self.get(f"/nodes/{node}/lxc/{vmid}/firewall/rules")
        except Exception:
            return []


# ============================================================
# 数据采集
# ============================================================

def _bytes_to_mb(b):
    return int(b // 1048576)

def _bytes_to_gb(b):
    return round(b / 1073741824, 2)

def _cpu_pct(v):
    return round(v * 100, 1)


def scan_full(pve):
    """执行一次完整扫描"""
    version = pve.get_version()
    cluster_status = pve.get_cluster_status()
    nodes_info = [s for s in cluster_status if s.get("type") == "node"]

    nodes_data = []
    for info in nodes_info:
        name = info["name"]
        try:
            nodes_data.append(_scan_node(pve, name, info))
        except Exception as e:
            logger.error(f"扫描节点 {name} 失败: {e}")
            nodes_data.append({"name": name, "status": "offline", "error": str(e)})

    ceph = pve.get_ceph_status()
    ha_resources = _scan_ha(pve)
    sdn = _scan_sdn(pve)
    replication = _scan_replication(pve, nodes_data)
    firewall = _scan_firewall(pve, nodes_data)

    backups = {}
    try:
        # Collect backup data from first node that has data
        for nd in nodes_data:
            if nd.get("status") != "offline" and not nd.get("error"):
                backups = _scan_backups(pve, nd["name"])
                break
    except Exception as e:
        logger.error(f"扫描备份数据失败: {e}")

    return {
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "version": version,
        "nodes": nodes_data,
        "ceph": ceph,
        "ha_resources": ha_resources,
        "sdn": sdn,
        "replication": replication,
        "backups": backups,
        "firewall": firewall,
    }


def _scan_node(pve, name, info):
    status = pve.get_node_status(name)
    cpuinfo = status.get("cpuinfo", {})
    mem = status.get("memory", {})
    rootfs = status.get("rootfs", {})
    swap = status.get("swap", {})
    diskstat = status.get("diskstat", [])

    mem_total = _bytes_to_mb(mem.get("total", 0))
    mem_used = _bytes_to_mb(mem.get("used", 0))

    # 扫描子资源
    vm_list = _scan_vms(pve, name)
    lxc_list = _scan_lxc(pve, name)

    # 状态判断：有内存数据或有 VM/容器 → 在线；否则 → 未知
    node_status = status.get("status", "") or info.get("status", "")
    if not node_status:
        if mem_total > 0 or vm_list or lxc_list:
            node_status = "online"
        else:
            node_status = "unknown"

    return {
        "name": name,
        "status": node_status,
        "pve_version": status.get("pveversion", ""),
        "kernel_version": status.get("kversion", ""),
        "cpu_model": cpuinfo.get("model", ""),
        "cpu_cores": cpuinfo.get("cpus"),
        "cpu_sockets": cpuinfo.get("sockets"),
        "cpu_load": _cpu_pct(status.get("cpu", 0)),
        "memory_total_mb": mem_total,
        "memory_used_mb": mem_used,
        "memory_free_mb": _bytes_to_mb(mem.get("free", 0)),
        "memory_usage_pct": round(mem_used / mem_total * 100, 1) if mem_total else 0,
        "rootfs_total_gb": _bytes_to_gb(rootfs.get("total", 0)),
        "rootfs_used_gb": _bytes_to_gb(rootfs.get("used", 0)),
        "rootfs_avail_gb": _bytes_to_gb(rootfs.get("avail", 0)),
        "swap_total_mb": _bytes_to_mb(swap.get("total", 0)),
        "swap_used_mb": _bytes_to_mb(swap.get("used", 0)),
        "disk_io_delay_ms": sum(d.get("io_ms", 0) for d in diskstat),
        "diskstat": diskstat,
        "ip_address": info.get("ip"),
        "is_ceph_node": False,
        "is_ha_node": False,
        "uptime_seconds": status.get("uptime", 0),
        "vms": vm_list,
        "containers": lxc_list,
        "storages": _scan_storages(pve, name),
        "networks": _scan_networks(pve, name),
        "vm_configs": _scan_vm_configs(pve, name, vm_list),
        "lxc_configs": _scan_lxc_configs(pve, name, lxc_list),
    }


def _scan_vms(pve, node):
    try:
        qemu_list = pve.get_node_qemu(node)
    except Exception:
        return []

    vms = []
    for vm in qemu_list:
        vmid = vm.get("vmid")
        data = {
            "vmid": vmid,
            "name": vm.get("name", ""),
            "status": vm.get("status", "unknown"),
            "cpu_cores": vm.get("cpus") or vm.get("maxcpu"),
            "cpu_usage": _cpu_pct(vm.get("cpu", 0)),
            "memory_mb": _bytes_to_mb(vm.get("maxmem", 0)),
            "memory_used_mb": _bytes_to_mb(vm.get("mem", 0)),
            "disk_gb": _bytes_to_gb(vm.get("maxdisk", 0)),  # PVE API 不返回 QEMU 实际磁盘使用量
            "max_disk_gb": _bytes_to_gb(vm.get("maxdisk", 0)),
            "disk_write_iops": vm.get("diskwrite"),
            "disk_read_iops": vm.get("diskread"),
            "net_in_bps": vm.get("netin"),
            "net_out_bps": vm.get("netout"),
            "uptime_seconds": vm.get("uptime", 0),
            "os_type": "",
            "snapshot_count": 0,
            "has_template": bool(vm.get("template", 0)),
            "tags": vm.get("tags", ""),
            "description": "",
            "config": {},
            "snapshots": [],
        }
        try:
            config = pve.get_vm_config(node, vmid)
            data["os_type"] = config.get("ostype", "")
            data["description"] = config.get("description", "")
        except Exception:
            pass
        # 扫描快照
        try:
            snapshots = pve.get_vm_snapshots(node, vmid)
            data["snapshot_count"] = len(snapshots)
            data["snapshots"] = _parse_snapshots(snapshots)
        except Exception:
            pass
        vms.append(data)
    return vms


def _scan_vm_configs(pve, node, vm_list):
    """扫描每个 VM 的详细配置"""
    configs = {}
    for vm in vm_list:
        vmid = vm.get("vmid")
        if not vmid:
            continue
        try:
            cfg = pve.get_vm_config(node, vmid)
            configs[str(vmid)] = _parse_vm_config(cfg)
        except Exception as e:
            logger.warning(f"获取 VM {vmid} 配置失败: {e}")
    return configs


def _parse_vm_config(cfg):
    """解析 VM 配置"""
    result = {
        "cpu_type": cfg.get("cpu", ""),
        "cpu_cores": cfg.get("cores"),
        "cpu_sockets": cfg.get("sockets"),
        "memory_mb": cfg.get("memory"),
        "balloon_min_mb": cfg.get("balloon"),
        "os_type": cfg.get("ostype", ""),
        "boot_order": cfg.get("boot", ""),
        "agent_enabled": cfg.get("agent", "").startswith("1"),
        "description": cfg.get("description", ""),
        "tags": cfg.get("tags", ""),
        "scsi_disks": [],
        "ide_disks": [],
        "net_devices": [],
    }

    # Parse storage devices
    for key, val in cfg.items():
        if key.startswith("scsi") and isinstance(val, str):
            parts = val.split(",", 1)
            storage_file = parts[0]
            storage = storage_file.split(":")[0] if ":" in storage_file else ""
            result["scsi_disks"].append({"slot": key, "storage": storage, "raw": val})
        elif key.startswith("ide") and isinstance(val, str):
            parts = val.split(",", 1)
            storage_file = parts[0]
            media = "cdrom" if "media=cdrom" in val else "disk"
            storage = storage_file.split(":")[0] if ":" in storage_file else ""
            result["ide_disks"].append({"slot": key, "storage": storage, "media": media, "raw": val})
        elif key.startswith("net") and isinstance(val, str):
            net_info = {}
            for item in val.split(","):
                if "=" in item:
                    k, v = item.split("=", 1)
                    net_info[k] = v
            net_info["slot"] = key
            result["net_devices"].append(net_info)

    return result


def _parse_snapshots(snapshots):
    """解析 PVE 快照列表"""
    result = []
    for snap in snapshots:
        snap_time = None
        ts = snap.get("snaptime", 0)
        if ts:
            try:
                snap_time = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
            except Exception:
                pass
        result.append({
            "snapid": snap.get("name", ""),
            "name": snap.get("name", ""),
            "description": snap.get("description", ""),
            "snap_time": snap_time,
            "parent": snap.get("parent", ""),
            "ram": bool(snap.get("ram", 0)),
            "vmstate": bool(snap.get("vmstate", 0)),
            "snap_type": snap.get("type", ""),
            "size_mb": None,
        })
    return result


def _scan_lxc(pve, node):
    try:
        lxc_list = pve.get_node_lxc(node)
    except Exception:
        return []

    containers = []
    for ct in lxc_list:
        containers.append({
            "vmid": ct.get("vmid"),
            "name": ct.get("name", ""),
            "status": ct.get("status", "unknown"),
            "cpu_cores": ct.get("cpus") or ct.get("maxcpu"),
            "cpu_usage": _cpu_pct(ct.get("cpu", 0)),
            "memory_mb": _bytes_to_mb(ct.get("maxmem", 0)),
            "memory_used_mb": _bytes_to_mb(ct.get("mem", 0)),
            "swap_mb": _bytes_to_mb(ct.get("maxswap", 0)),
            "swap_used_mb": _bytes_to_mb(ct.get("swap", 0)),
            "disk_gb": _bytes_to_gb(ct.get("maxdisk", 0)),
            "uptime_seconds": ct.get("uptime", 0),
            "tags": ct.get("tags", ""),
            "description": "",
            "has_template": bool(ct.get("template", 0)),
        })
    return containers


def _scan_lxc_configs(pve, node, lxc_list):
    """扫描每个容器的详细配置"""
    configs = {}
    for ct in lxc_list:
        vmid = ct.get("vmid")
        if not vmid:
            continue
        try:
            cfg = pve.get_lxc_config(node, vmid)
            configs[str(vmid)] = _parse_lxc_config(cfg)
        except Exception as e:
            logger.warning(f"获取 LXC {vmid} 配置失败: {e}")
    return configs


def _parse_lxc_config(cfg):
    """解析 LXC 配置"""
    result = {
        "hostname": cfg.get("hostname", ""),
        "cpu_cores": cfg.get("cores"),
        "memory_mb": cfg.get("memory"),
        "swap_mb": cfg.get("swap"),
        "os_type": cfg.get("ostype", ""),
        "description": cfg.get("description", ""),
        "tags": cfg.get("tags", ""),
        "startup_order": cfg.get("startup", ""),
        "rootfs": {},
        "mount_points": [],
        "net_devices": [],
    }

    # Parse rootfs
    rootfs_val = cfg.get("rootfs", "")
    if isinstance(rootfs_val, str) and rootfs_val:
        parts = rootfs_val.split(",", 1)
        storage = parts[0].split(":")[0] if ":" in parts[0] else ""
        result["rootfs"] = {"storage": storage, "raw": rootfs_val}

    # Parse mount points (mp0, mp1, ...)
    for key, val in cfg.items():
        if key.startswith("mp") and isinstance(val, str):
            result["mount_points"].append({"slot": key, "raw": val})

    # Parse network
    for key, val in cfg.items():
        if key.startswith("net") and isinstance(val, str):
            net_info = {}
            for item in val.split(","):
                if "=" in item:
                    k, v = item.split("=", 1)
                    net_info[k] = v
            net_info["slot"] = key
            result["net_devices"].append(net_info)

    return result


def _scan_storages(pve, node):
    try:
        storage_list = pve.get_node_storage(node)
    except Exception:
        return []

    return [{
        "name": st.get("storage", ""),
        "type": st.get("type", ""),
        "active": bool(st.get("active", 0)),
        "used_gb": _bytes_to_gb(st.get("used", 0)),
        "avail_gb": _bytes_to_gb(st.get("available", 0)),
        "total_gb": _bytes_to_gb(st.get("total", 0)),
        "used_fraction": st.get("used_fraction"),
        "content_types": st.get("content", ""),
        "shared": bool(st.get("shared", 0)),
    } for st in storage_list]


def _scan_networks(pve, node):
    try:
        net_list = pve.get_node_network(node)
    except Exception as e:
        logger.error(f"扫描网络失败 {node}: {e}")
        return []

    return [{
        "name": net.get("iface", ""),
        "type": net.get("type", ""),
        "active": bool(net.get("active", 0)),
        "method": net.get("method", ""),
        "address": net.get("address", ""),
        "netmask": net.get("netmask", ""),
        "gateway": net.get("gateway", ""),
        "speed_mbps": net.get("speed"),
        "bridge_ports": net.get("bridge_ports", ""),
        "bond_mode": net.get("bond_mode", ""),
        "bond_slaves": net.get("bond_slaves", ""),
        "vlan_id": net.get("vlan_id"),
        "mtu": net.get("mtu"),
    } for net in net_list]


def _scan_ha(pve):
    """扫描 HA 高可用资源"""
    try:
        resources = pve.get_ha_resources()
    except Exception:
        return []

    result = []
    for r in resources:
        sid = r.get("sid", "")
        rtype = "vm" if sid.startswith("vm:") else "ct" if sid.startswith("ct:") else "unknown"
        vmid = None
        if ":" in sid:
            try:
                vmid = int(sid.split(":")[1])
            except (ValueError, IndexError):
                pass
        ha_data = r.get("ha", {})
        result.append({
            "sid": sid,
            "type": rtype,
            "vmid": vmid,
            "node": r.get("node", ""),
            "state": r.get("state", "") or r.get("status", ""),
            "ha_group": r.get("group", "") or ha_data.get("group", ""),
            "ha_status": ha_data.get("status", ""),
            "crm_state": ha_data.get("crm_state", ""),
            "max_restarts": ha_data.get("max_restart"),
            "max_shutdown": ha_data.get("max_shutdown"),
            "raw": r,
        })
    return result


def _scan_sdn(pve):
    """扫描 SDN 虚拟网络"""
    return {
        "zones": pve.get_sdn_zones() or [],
        "vnets": pve.get_sdn_vnets() or [],
        "subnets": pve.get_sdn_subnets() or [],
    }


def _scan_replication(pve, nodes_data):
    """扫描所有节点的复制任务"""
    jobs = []
    for nd in nodes_data:
        if nd.get("status") == "offline" or nd.get("error"):
            continue
        name = nd["name"]
        try:
            node_jobs = pve.get_node_replication(name)
            for job in node_jobs:
                job_id = str(job.get("id", ""))
                guest = job.get("guest", 0)
                rtype = "vm" if job.get("type", "") == "local" else "ct"
                # 从 guest 字段推断类型: < 1000 通常为 VM，>= 1000 可能为 CT
                # PVE replication type 字段: local 表示同集群复制
                last_sync_ts = job.get("last_sync", 0)
                last_try_ts = job.get("last_try", 0)
                last_sync = None
                last_try = None
                if last_sync_ts and last_sync_ts > 0:
                    try:
                        last_sync = datetime.fromtimestamp(last_sync_ts, tz=timezone.utc).isoformat()
                    except Exception:
                        pass
                if last_try_ts and last_try_ts > 0:
                    try:
                        last_try = datetime.fromtimestamp(last_try_ts, tz=timezone.utc).isoformat()
                    except Exception:
                        pass
                jobs.append({
                    "job_id": job_id,
                    "vmid": guest,
                    "resource_type": rtype,
                    "source_node": name,
                    "target_node": job.get("target", ""),
                    "schedule": job.get("schedule", ""),
                    "rate_limit": job.get("rate"),
                    "comment": job.get("comment", ""),
                    "enabled": not bool(job.get("disable", 0)),
                    "state": job.get("state", ""),
                    "last_sync": last_sync,
                    "last_try": last_try,
                    "last_duration": job.get("duration"),
                    "error_message": job.get("error", ""),
                    "sync_count": job.get("sync_count", 0),
                    "raw": job,
                })
        except Exception as e:
            logger.warning(f"扫描节点 {name} 复制任务失败: {e}")
    return jobs


def _parse_fw_rules(rules):
    """解析防火墙规则列表，提取结构化字段"""
    result = []
    for i, r in enumerate(rules):
        if not isinstance(r, dict):
            continue
        result.append({
            "pos": r.get("pos", i),
            "action": r.get("action", ""),
            "type": r.get("type", ""),
            "direction": r.get("direction", r.get("type", "")),
            "proto": r.get("proto", ""),
            "source": r.get("source", ""),
            "dest": r.get("dest", ""),
            "dport": r.get("dport", ""),
            "sport": r.get("sport", ""),
            "comment": r.get("comment", ""),
            "enabled": not bool(r.get("disable", 0)),
            "log": r.get("log", ""),
            "iface": r.get("iface", ""),
            "macro": r.get("macro", ""),
            "raw": r,
        })
    return result


def _scan_firewall(pve, nodes_data):
    """扫描集群级 + 节点级 + VM/CT 级防火墙配置"""
    fw = {
        "cluster_options": {},
        "cluster_rules": [],
        "security_groups": {},
        "ipsets": {},
        "aliases": [],
        "nodes": {},
    }

    try:
        # 集群级选项
        fw["cluster_options"] = pve.get_cluster_fw_options()

        # 集群级规则
        fw["cluster_rules"] = _parse_fw_rules(pve.get_cluster_fw_rules())

        # 安全组
        groups = pve.get_cluster_fw_groups()
        for g in groups:
            gname = g.get("name", g) if isinstance(g, dict) else str(g)
            group_rules = pve.get_cluster_fw_group_rules(gname)
            fw["security_groups"][gname] = _parse_fw_rules(group_rules)

        # IPSet
        ipset_list = pve.get_cluster_fw_ipsets()
        for ip in ipset_list:
            ipname = ip.get("name", ip) if isinstance(ip, dict) else str(ip)
            entries = pve.get_cluster_fw_ipset(ipname)
            fw["ipsets"][ipname] = {
                "name": ipname,
                "comment": ip.get("comment", "") if isinstance(ip, dict) else "",
                "entries": [{
                    "cidr": e.get("cidr", ""),
                    "comment": e.get("comment", ""),
                    "nomatch": bool(e.get("nomatch", 0)),
                    "raw": e,
                } for e in entries if isinstance(e, dict)],
            }

        # 别名
        aliases = pve.get_cluster_fw_aliases()
        fw["aliases"] = [{
            "name": a.get("name", ""),
            "cidr": a.get("cidr", ""),
            "alias_type": a.get("type", ""),
            "comment": a.get("comment", ""),
            "raw": a,
        } for a in aliases if isinstance(a, dict)]

        # 节点级 + VM/CT 级
        for nd in nodes_data:
            if nd.get("status") == "offline" or nd.get("error"):
                continue
            node_name = nd["name"]
            try:
                node_opts = pve.get_node_fw_options(node_name)
                node_rules = pve.get_node_fw_rules(node_name)
                node_fw = {
                    "options": node_opts,
                    "rules": _parse_fw_rules(node_rules),
                    "vms": {},
                    "cts": {},
                }

                # VM 防火墙
                for vm in nd.get("vms", []):
                    vmid = vm.get("vmid")
                    if not vmid:
                        continue
                    vm_opts = pve.get_vm_fw_options(node_name, vmid)
                    # 只采集启用防火墙的 VM
                    if vm_opts.get("enable"):
                        vm_rules = pve.get_vm_fw_rules(node_name, vmid)
                        node_fw["vms"][str(vmid)] = {
                            "options": vm_opts,
                            "rules": _parse_fw_rules(vm_rules),
                        }

                # 容器防火墙
                for ct in nd.get("containers", []):
                    vmid = ct.get("vmid")
                    if not vmid:
                        continue
                    ct_opts = pve.get_ct_fw_options(node_name, vmid)
                    if ct_opts.get("enable"):
                        ct_rules = pve.get_ct_fw_rules(node_name, vmid)
                        node_fw["cts"][str(vmid)] = {
                            "options": ct_opts,
                            "rules": _parse_fw_rules(ct_rules),
                        }

                fw["nodes"][node_name] = node_fw
            except Exception as e:
                logger.warning(f"扫描节点 {node_name} 防火墙失败: {e}")

    except Exception as e:
        logger.error(f"扫描防火墙数据失败: {e}")

    return fw


def _scan_backups(pve, node):
    """扫描节点备份数据"""
    jobs = pve.get_backup_jobs(node)
    history = pve.get_backup_history(node)

    # Find backup storages
    backup_storages = []
    try:
        all_storages = pve.get_node_storage(node)
        for st in all_storages:
            content = st.get("content", "")
            if "backup" in content:
                backup_storages.append({
                    "storage_name": st.get("storage", ""),
                    "storage_type": st.get("type", ""),
                    "path": st.get("path", ""),
                    "content_types": content,
                    "active": bool(st.get("active", 0)),
                    "shared": bool(st.get("shared", 0)),
                    "total_gb": _bytes_to_gb(st.get("total", 0)),
                    "used_gb": _bytes_to_gb(st.get("used", 0)),
                    "avail_gb": _bytes_to_gb(st.get("available", 0)),
                    "used_fraction": st.get("used_fraction"),
                })
    except Exception:
        pass

    # Parse backup jobs
    parsed_jobs = []
    for job in jobs:
        vmid_val = job.get("vmid")
        if isinstance(vmid_val, list):
            vmid_val = ",".join(str(v) for v in vmid_val)
        storage_val = job.get("storage", "")
        if isinstance(storage_val, list):
            storage_val = ",".join(str(v) for v in storage_val)
        parsed_jobs.append({
            "job_id": job.get("id", ""),
            "vmid": job.get("vmid") if isinstance(job.get("vmid"), int) else None,
            "resource_type": "vm" if str(job.get("vmid", "")).isdigit() else "all",
            "storage_name": storage_val if isinstance(storage_val, str) else "",
            "mode": job.get("mode", ""),
            "schedule": job.get("schedule", ""),
            "retention": job.get("retention", "") or job.get("keep-all", ""),
            "enabled": not bool(job.get("disabled", 0)),
            "compress": job.get("compress", ""),
            "notes": job.get("notes", ""),
            "last_run": job.get("last-run"),
            "last_status": "ok" if job.get("last-status") == "OK" else job.get("last-status", ""),
            "raw": job,
        })

    # Parse backup history (from tasks)
    parsed_history = []
    for task in history:
        upid = task.get("upid", "")
        status = task.get("status", "")
        if isinstance(status, str) and status.startswith("OK"):
            status = "ok"
        elif status:
            status = "error"
        else:
            status = "running"

        start_ts = task.get("starttime", 0)
        end_ts = task.get("endtime", 0)
        start_time = None
        end_time = None
        duration = None
        if start_ts:
            try:
                start_time = datetime.fromtimestamp(start_ts, tz=timezone.utc).isoformat()
            except Exception:
                pass
        if end_ts and start_ts:
            try:
                end_time = datetime.fromtimestamp(end_ts, tz=timezone.utc).isoformat()
                duration = int(end_ts - start_ts)
            except Exception:
                pass

        # Extract vmid from UPID: "UPID:node:PID:TYPE:VMID:..."
        type_val = task.get("type", "")
        vmid = None
        rtype = ""
        if type_val == "vzdump":
            # Parse from description or type
            desc = task.get("description", "")
            # Try to extract VMID from description like "VM 100"
            import re
            m = re.search(r'(?:VM|CT)\s+(\d+)', desc)
            if m:
                vmid = int(m.group(1))
                rtype = "vm" if "VM" in desc else "ct"

        parsed_history.append({
            "task_id": upid,
            "vmid": vmid,
            "resource_type": rtype,
            "status": status,
            "started_at": start_time,
            "finished_at": end_time,
            "duration_seconds": duration,
            "raw": task,
        })

    return {
        "backup_storages": backup_storages,
        "backup_jobs": parsed_jobs,
        "backup_history": parsed_history,
    }


# ============================================================
# 平台通信
# ============================================================

class PlatformClient:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/")

    def register(self, token, pve_endpoint, pve_username, pve_password, hostname, scan_interval):
        return http_post(f"{self.base_url}/api/agent/register/", {
            "agent_token": token,
            "pve_api_endpoint": pve_endpoint,
            "pve_username": pve_username,
            "pve_password": pve_password,
            "hostname": hostname,
            "scan_interval": scan_interval,
            "version": VERSION,
        })

    def unregister(self, agent_id):
        return http_post(f"{self.base_url}/api/agent/unregister/", {"agent_id": agent_id})

    def heartbeat(self, agent_id, status="online", current_task="", error_message="", version="", pve_version=""):
        payload = {
            "agent_id": agent_id,
            "status": status,
            "current_task": current_task,
            "version": version,
            "pve_version": pve_version,
        }
        if error_message:
            payload["error_message"] = error_message
        try:
            return http_post(f"{self.base_url}/api/agent/heartbeat/", payload)
        except urllib.error.HTTPError as e:
            if e.code == 410:
                return {"_deleted": True}
            raise

    def upload_scan(self, agent_id, cluster_id, scan_data):
        try:
            return http_post(f"{self.base_url}/api/agent/scan/upload/", {
                "agent_id": agent_id,
                "cluster_id": cluster_id,
                **scan_data,
            })
        except urllib.error.HTTPError as e:
            if e.code == 423:
                return {"_deactivated": True}
            if e.code == 410:
                return {"_deleted": True}
            raise

    def get_tasks(self, agent_id):
        return http_get(f"{self.base_url}/api/agent/tasks/?agent_id={agent_id}")


# ============================================================
# 主循环
# ============================================================

class Agent:
    def __init__(self, config):
        self.config = config
        self.platform = PlatformClient(config.platform_url)
        self.pve = PVEClient(config.pve_endpoint, config.pve_username, config.pve_password)
        self._running = True

    def start(self):
        """启动 agent（心跳 + 扫描循环）"""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        logger.info(f"Agent 启动中 (id={self.config.agent_id})")
        logger.info(f"PVE: {self.config.pve_endpoint}")
        logger.info(f"平台: {self.config.platform_url}")
        logger.info(f"扫描间隔: {self.config.scan_interval}s | 心跳间隔: {self.config.heartbeat_interval}s")

        # PVE 认证（失败不崩溃，上报错误状态）
        pve_auth_ok = False
        try:
            self.pve.authenticate()
            pve_auth_ok = True
        except Exception as e:
            logger.error(f"PVE 认证失败: {e}")
            # 上报错误到平台
            try:
                self.platform.heartbeat(
                    self.config.agent_id,
                    status="error",
                    version=VERSION,
                    error_message=f"PVE 认证失败: {e}",
                )
            except Exception:
                pass

        # 心跳线程
        t = threading.Thread(target=self._heartbeat_loop, daemon=True)
        t.start()

        # 启动后立即执行一次扫描
        try:
            self._do_scan()
        except Exception as e:
            logger.error(f"首次扫描失败: {e}")
            try:
                self.platform.heartbeat(
                    self.config.agent_id,
                    status="error",
                    version=VERSION,
                    error_message=f"扫描失败: {e}",
                )
            except Exception:
                pass

        # 扫描主循环
        self._scan_loop()

    def run_once(self):
        """单次扫描"""
        self.pve.authenticate()
        self._do_scan()

    def _stop_permanently(self, reason="集群已删除"):
        """永久停止 Agent，禁止 systemd 重启"""
        logger.warning(f"{reason}，停止 Agent 并禁用自动重启")
        self._running = False
        try:
            os.system("systemctl disable pcs-agent 2>/dev/null")
        except Exception:
            pass
        sys.exit(0)

    def _signal_handler(self, signum, frame):
        logger.info(f"收到信号 {signum}，停止 agent...")
        self._running = False
        sys.exit(0)

    def _handle_update(self, update_info):
        """处理平台下发的更新指令"""
        download_url = update_info.get("download_url")
        latest_version = update_info.get("latest_version")
        changelog = update_info.get("changelog", "")

        if not download_url:
            return

        logger.info(f"检测到新版本 {latest_version}，changelog: {changelog}")
        logger.info(f"开始下载: {download_url}")

        # 1. 下载新版本到临时文件
        tmp_path = str(INSTALL_DIR / "agent.py.new")
        try:
            urllib.request.urlretrieve(download_url, tmp_path)
        except Exception as e:
            logger.error(f"下载失败: {e}")
            return

        # 2. 校验文件完整性 & 版本比较
        try:
            with open(tmp_path, "r") as f:
                content = f.read()
            if 'VERSION = "' not in content:
                logger.error("下载文件校验失败：非有效 agent 文件")
                os.remove(tmp_path)
                return

            # 提取下载文件的版本号
            import re as _re
            m = _re.search(r'VERSION\s*=\s*"([^"]+)"', content)
            downloaded_version = m.group(1) if m else ""

            if downloaded_version == VERSION:
                logger.info(f"下载版本 {downloaded_version} 与当前版本一致，无需更新")
                os.remove(tmp_path)
                return
        except Exception as e:
            logger.error(f"文件校验异常: {e}")
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            return

        # 3. 备份当前版本
        backup_path = str(INSTALL_DIR / "agent.py.bak")
        try:
            shutil.copy2(str(INSTALL_DIR / "agent.py"), backup_path)
        except Exception as e:
            logger.warning(f"备份失败: {e}")

        # 4. 替换当前文件
        try:
            os.replace(tmp_path, str(INSTALL_DIR / "agent.py"))
            logger.info("文件替换完成")
        except Exception as e:
            logger.error(f"替换文件失败: {e}")
            return

        # 4.5 更新配置文件中的间隔参数
        try:
            self._update_config_intervals()
        except Exception as e:
            logger.warning(f"更新配置间隔失败: {e}")

        # 5. 重启服务
        logger.info("正在重启服务...")
        self._running = False
        try:
            # 使用 Popen 创建独立子进程，避免 systemctl 与当前进程冲突
            subprocess.Popen(
                ["systemctl", "restart", "pcs-agent"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            logger.info("正在退出当前进程...")
            os._exit(0)
        except Exception as e:
            logger.error(f"重启服务失败: {e}，请手动重启")
            os._exit(1)

    def _update_config_intervals(self):
        """更新配置文件中的间隔参数为新版默认值"""
        config_path = INSTALL_DIR / "config.env"
        if not config_path.exists():
            return

        content = config_path.read_text()
        lines = content.splitlines()
        new_lines = []
        found_heartbeat = False
        found_scan = False

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("heartbeat_interval="):
                new_lines.append("heartbeat_interval=120")
                found_heartbeat = True
            elif stripped.startswith("scan_interval="):
                new_lines.append("scan_interval=300")
                found_scan = True
            else:
                new_lines.append(line)

        if not found_heartbeat:
            new_lines.append("heartbeat_interval=120")
        if not found_scan:
            new_lines.append("scan_interval=300")

        config_path.write_text("\n".join(new_lines) + "\n")
        config_path.chmod(0o600)
        logger.info("配置间隔已更新: heartbeat=120s, scan=300s")

    def _heartbeat_loop(self):
        while self._running:
            try:
                result = self.platform.heartbeat(
                    self.config.agent_id, status="online",
                    version=VERSION,
                    pve_version=self.config.pve_version,
                )
                if isinstance(result, dict) and result.get("_deleted"):
                    self._stop_permanently("集群已被删除（心跳检测）")
                    return
                # 检测更新指令
                if isinstance(result, dict) and result.get("update", {}).get("available"):
                    self._handle_update(result["update"])
                    return  # 更新后重启，退出当前循环
            except Exception as e:
                logger.warning(f"心跳失败: {e}")
            time.sleep(self.config.heartbeat_interval)

    def _scan_loop(self):
        while self._running:
            try:
                self._do_scan()
            except Exception as e:
                logger.error(f"扫描失败: {e}")
            time.sleep(self.config.scan_interval)

    def _do_scan(self):
        logger.info("=== 开始扫描 ===")
        try:
            self.platform.heartbeat(
                self.config.agent_id, status="online", current_task="scanning",
                version=VERSION,
                pve_version=self.config.pve_version,
            )
        except Exception:
            pass

        try:
            # 如果之前认证失败，尝试重新认证
            if not self.pve._is_token and not self.pve.ticket:
                logger.info("尝试重新认证 PVE...")
                self.pve.authenticate()

            scan_data = scan_full(self.pve)
            logger.info(f"扫描完成: {len(scan_data['nodes'])} 个节点")

            # 保存 PVE 版本到配置（首次扫描后）
            if scan_data.get("version") and not self.config.pve_version:
                self.config.pve_version = scan_data["version"]
                self.config.save()
                logger.info(f"PVE 版本已记录: {self.config.pve_version}")

            result = self.platform.upload_scan(self.config.agent_id, self.config.cluster_id, scan_data)

            # 集群已被删除，永久停止
            if isinstance(result, dict) and result.get("_deleted"):
                self._stop_permanently("集群已被删除（上传检测）")
                return

            # 集群已停用，不上报数据，保持心跳等待恢复
            if isinstance(result, dict) and result.get("_deactivated"):
                logger.warning("集群已停用，暂停数据上报，继续心跳等待恢复...")
                try:
                    self.platform.heartbeat(
                        self.config.agent_id,
                        status="paused",
                        version=VERSION,
                        pve_version=self.config.pve_version,
                        current_task="deactivated",
                        error_message="集群已停用，等待恢复",
                    )
                except Exception:
                    pass
                return

            logger.info(f"上传成功: {result}")

            # 扫描成功，恢复在线状态
            try:
                self.platform.heartbeat(
                    self.config.agent_id, status="online", current_task="",
                    version=VERSION,
                    pve_version=self.config.pve_version,
                )
            except Exception:
                pass

        except Exception as e:
            error_msg = f"扫描失败: {e}"
            logger.error(error_msg)
            # 上报扫描失败到平台
            try:
                self.platform.heartbeat(
                    self.config.agent_id,
                    status="error",
                    version=VERSION,
                    error_message=error_msg,
                )
            except Exception:
                pass

        # 检查任务
        try:
            tasks = self.platform.get_tasks(self.config.agent_id)
            if tasks:
                logger.info(f"收到 {len(tasks)} 个任务")
        except Exception:
            pass

        logger.info("=== 扫描结束 ===")


# ============================================================
# 安装 / 卸载
# ============================================================

def cmd_install():
    """交互式安装"""
    print("=" * 50)
    print("  PVE Cluster Scan Agent  安装程序")
    print(f"  版本: v{VERSION}")
    print("=" * 50)
    print()

    # 检查 root
    if os.geteuid() != 0:
        print("错误: 需要 root 权限运行。请使用 sudo 或 root 用户。")
        sys.exit(1)

    # 交互式收集配置
    cfg = Config()
    cfg.platform_url = input("平台地址 (如 http://192.168.1.100:8066): ").strip()
    cfg.agent_token = input("Agent Token: ").strip()
    cfg.pve_endpoint = input("PVE API 地址 (如 https://192.168.1.200:8006): ").strip()
    cfg.pve_username = input("PVE 用户名 [root@pam]: ").strip() or "root@pam"
    cfg.pve_password = input("PVE 密码: ").strip()

    if not all([cfg.platform_url, cfg.agent_token, cfg.pve_endpoint, cfg.pve_password]):
        print("错误: 所有字段都是必填的。")
        sys.exit(1)

    # 创建目录
    INSTALL_DIR.mkdir(parents=True, exist_ok=True)

    # 注册到平台
    print("\n正在注册到平台...")
    platform = PlatformClient(cfg.platform_url)
    try:
        hostname = socket.gethostname()
        result = platform.register(
            token=cfg.agent_token,
            pve_endpoint=cfg.pve_endpoint,
            pve_username=cfg.pve_username,
            pve_password=cfg.pve_password,
            hostname=hostname,
            scan_interval=cfg.scan_interval,
        )
        cfg.agent_id = result["agent_id"]
        cfg.cluster_id = str(result.get("cluster_id", ""))
        logger.info(f"注册成功, agent_id={cfg.agent_id}")
    except Exception as e:
        print(f"注册失败: {e}")
        sys.exit(1)

    # 保存配置
    cfg.save()
    print(f"配置已保存: {CONFIG_FILE}")

    # 复制 agent.py 到安装目录
    agent_src = Path(__file__).resolve()
    agent_dst = INSTALL_DIR / "agent.py"
    if agent_src != agent_dst:
        import shutil
        shutil.copy2(str(agent_src), str(agent_dst))
        print(f"Agent 已复制: {agent_dst}")

    # 创建 systemd 服务
    service_content = f"""[Unit]
Description=PVE Cluster Scan Agent
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 {agent_dst} run
Restart=always
RestartSec=10
WorkingDirectory={INSTALL_DIR}

[Install]
WantedBy=multi-user.target
"""
    SERVICE_FILE.write_text(service_content)
    print(f"systemd 服务: {SERVICE_FILE}")

    # 启动服务
    os.system("systemctl daemon-reload")
    os.system("systemctl enable pcs-agent")
    os.system("systemctl start pcs-agent")

    time.sleep(2)
    status = os.popen("systemctl is-active pcs-agent").read().strip()

    print()
    print("=" * 50)
    print("  安装完成!")
    print()
    if status == "active":
        print(f"  状态:     运行中")
    else:
        print(f"  状态:     {status}")
        print(f"  排查:     journalctl -u pcs-agent -n 20")
    print()
    print(f"  Agent ID: {cfg.agent_id}")
    print(f"  配置文件: {CONFIG_FILE}")
    print(f"  日志:     {LOG_FILE}")
    print()
    print("  管理命令:")
    print("    systemctl status pcs-agent    # 查看状态")
    print("    systemctl restart pcs-agent   # 重启")
    print("    systemctl stop pcs-agent      # 停止")
    print("    journalctl -u pcs-agent -f    # 实时日志")
    print("    python3 agent.py uninstall    # 卸载")
    print("=" * 50)


def cmd_status():
    """查看状态"""
    cfg = Config()
    if not cfg.load():
        print("Agent 未安装或配置文件不存在。")
        return

    status = os.popen("systemctl is-active pcs-agent 2>/dev/null").read().strip() or "unknown"

    print()
    print("PVE Agent 状态")
    print("=" * 40)
    print(f"  版本:     v{VERSION}")
    print(f"  Agent ID: {cfg.agent_id or '未注册'}")
    print(f"  平台:     {cfg.platform_url}")
    print(f"  PVE:      {cfg.pve_endpoint}")
    print(f"  扫描间隔: {cfg.scan_interval}s")
    print()
    print(f"  服务状态: {status}")
    print(f"  配置文件: {CONFIG_FILE}")
    print(f"  日志:     {LOG_FILE}")
    print()


def cmd_uninstall():
    """卸载"""
    if os.geteuid() != 0:
        print("错误: 需要 root 权限。")
        sys.exit(1)

    cfg = Config()
    cfg.load()

    print("即将卸载 PVE Agent:")
    print(f"  Agent ID: {cfg.agent_id or '未知'}")
    confirm = input("确认卸载? [y/N] ").strip().lower()
    if confirm != "y":
        print("已取消。")
        return

    # 1. 通知平台
    if cfg.agent_id:
        print("1. 通知平台...")
        try:
            PlatformClient(cfg.platform_url).unregister(cfg.agent_id)
        except Exception:
            pass

    # 2. 停止并删除服务
    print("2. 停止服务...")
    os.system("systemctl stop pcs-agent 2>/dev/null")
    os.system("systemctl disable pcs-agent 2>/dev/null")
    if SERVICE_FILE.exists():
        SERVICE_FILE.unlink()
    os.system("systemctl daemon-reload")

    # 3. 删除文件
    print("3. 清理文件...")
    import shutil
    if INSTALL_DIR.exists():
        shutil.rmtree(INSTALL_DIR)

    print()
    print("Agent 已卸载。")


# ============================================================
# CLI 入口
# ============================================================

def main():
    if len(sys.argv) < 2:
        print(f"PVE Cluster Scan Agent v{VERSION}")
        print("用法: python3 agent.py <command>")
        print()
        print("命令:")
        print("  install    安装 Agent（交互式配置 + systemd 服务）")
        print("  run        运行 Agent（心跳 + 扫描循环）")
        print("  once       执行单次扫描")
        print("  status     查看运行状态")
        print("  uninstall  卸载 Agent")
        print("  version    查看版本")
        sys.exit(0)

    cmd = sys.argv[1].lower()

    if cmd == "install":
        cmd_install()
    elif cmd == "run":
        cfg = Config()
        if not cfg.load():
            print("配置文件不存在，请先运行: python3 agent.py install")
            sys.exit(1)
        Agent(cfg).start()
    elif cmd == "once":
        cfg = Config()
        if not cfg.load():
            print("配置文件不存在，请先运行: python3 agent.py install")
            sys.exit(1)
        Agent(cfg).run_once()
    elif cmd == "status":
        cmd_status()
    elif cmd == "uninstall":
        cmd_uninstall()
    elif cmd in ("version", "-v", "--version"):
        print(f"pcs-agent v{VERSION}")
    else:
        print(f"未知命令: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
