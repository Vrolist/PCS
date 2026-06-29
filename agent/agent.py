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
import signal
import socket
import ssl
import sys
import time
import threading
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

VERSION = "0.2.0"

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
        self.scan_interval = 300
        self.heartbeat_interval = 300

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

    return {
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "version": version,
        "nodes": nodes_data,
        "ceph": ceph,
        "ha_resources": ha_resources,
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
        }
        try:
            config = pve.get_vm_config(node, vmid)
            data["os_type"] = config.get("ostype", "")
            data["description"] = config.get("description", "")
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
    except Exception:
        return []

    return [{
        "name": net.get("iface", ""),
        "type": net.get("type", ""),
        "active": bool(net.get("active", 0)),
        "method": net.get("method", ""),
        "address": net.get("address", ""),
        "gateway": net.get("gateway", ""),
        "speed_mbps": net.get("speed"),
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
            "state": r.get("status", ""),
            "ha_group": ha_data.get("group", ""),
            "ha_status": ha_data.get("status", ""),
            "crm_state": ha_data.get("crm_state", ""),
            "max_restarts": ha_data.get("max_restart"),
            "max_shutdown": ha_data.get("max_shutdown"),
            "raw": r,
        })
    return result


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

    def heartbeat(self, agent_id, status="online", current_task="", error_message=""):
        payload = {
            "agent_id": agent_id,
            "status": status,
            "current_task": current_task,
        }
        if error_message:
            payload["error_message"] = error_message
        return http_post(f"{self.base_url}/api/agent/heartbeat/", payload)

    def upload_scan(self, agent_id, cluster_id, scan_data):
        return http_post(f"{self.base_url}/api/agent/scan/upload/", {
            "agent_id": agent_id,
            "cluster_id": cluster_id,
            **scan_data,
        })

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

    def _signal_handler(self, signum, frame):
        logger.info(f"收到信号 {signum}，停止 agent...")
        self._running = False
        sys.exit(0)

    def _heartbeat_loop(self):
        while self._running:
            try:
                self.platform.heartbeat(self.config.agent_id, status="online")
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
            self.platform.heartbeat(self.config.agent_id, status="online", current_task="scanning")
        except Exception:
            pass

        try:
            # 如果之前认证失败，尝试重新认证
            if not self.pve._is_token and not self.pve.ticket:
                logger.info("尝试重新认证 PVE...")
                self.pve.authenticate()

            scan_data = scan_full(self.pve)
            logger.info(f"扫描完成: {len(scan_data['nodes'])} 个节点")

            result = self.platform.upload_scan(self.config.agent_id, self.config.cluster_id, scan_data)
            logger.info(f"上传成功: {result}")

            # 扫描成功，恢复在线状态
            try:
                self.platform.heartbeat(self.config.agent_id, status="online", current_task="")
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
    cfg.platform_url = input("平台地址 (如 http://192.168.1.100:8000): ").strip()
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
