"""扫描器 — 从 PVE API 采集数据并转换格式"""
import logging
from datetime import datetime, timezone

from .pve_client import PVEClient

logger = logging.getLogger(__name__)

BYTES_TO_MB = 1048576
BYTES_TO_GB = 1073741824


def _bytes_to_mb(b: int | float) -> int:
    return int(b // BYTES_TO_MB)


def _bytes_to_gb(b: int | float) -> float:
    return round(b / BYTES_TO_GB, 2)


def _cpu_to_pct(v: float) -> float:
    return round(v * 100, 1)


def scan_full(pve: PVEClient) -> dict:
    """执行一次完整扫描，返回上报格式的 dict"""
    logger.info("Starting full scan...")

    # 集群版本
    version = pve.get_version()

    # 集群状态 → 节点列表
    cluster_status = pve.get_cluster_status()
    nodes_info = [s for s in cluster_status if s.get("type") == "node"]

    nodes_data = []
    for node_info in nodes_info:
        node_name = node_info["name"]
        logger.info(f"Scanning node: {node_name}")
        try:
            node_data = _scan_node(pve, node_name, node_info)
            nodes_data.append(node_data)
        except Exception as e:
            logger.error(f"Failed to scan node {node_name}: {e}")
            # 记录一个最小化的节点信息
            nodes_data.append({
                "name": node_name,
                "status": "offline",
                "error": str(e),
            })

    # Ceph 状态
    ceph = pve.get_ceph_status()

    result = {
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "version": version,
        "nodes": nodes_data,
        "ceph": ceph,
    }
    logger.info(f"Scan complete: {len(nodes_data)} nodes")
    return result


def _scan_node(pve: PVEClient, node_name: str, node_info: dict) -> dict:
    """扫描单个节点"""
    status = pve.get_node_status(node_name)

    # CPU
    cpu_load = _cpu_to_pct(status.get("cpu", 0))
    cpuinfo = status.get("cpuinfo", {})

    # 内存
    mem = status.get("memory", {})
    mem_total = _bytes_to_mb(mem.get("total", 0))
    mem_used = _bytes_to_mb(mem.get("used", 0))
    mem_free = _bytes_to_mb(mem.get("free", 0))
    mem_pct = round(mem_used / mem_total * 100, 1) if mem_total > 0 else 0

    # 根分区
    rootfs = status.get("rootfs", {})

    # Swap
    swap = status.get("swap", {})

    # I/O 延迟
    diskstat = status.get("diskstat", [])
    io_delay_ms = sum(d.get("io_ms", 0) for d in diskstat)

    # IP
    ip_address = node_info.get("ip")

    # 运行时长
    uptime = status.get("uptime", 0)

    # VM 列表
    vms = _scan_vms(pve, node_name)

    # LXC 列表
    containers = _scan_lxc(pve, node_name)

    # 存储列表
    storages = _scan_storages(pve, node_name)

    # 网络列表
    networks = _scan_networks(pve, node_name)

    return {
        "name": node_name,
        "status": status.get("status", "unknown"),
        "pve_version": status.get("pveversion", ""),
        "kernel_version": status.get("kversion", ""),
        "cpu_model": cpuinfo.get("model", ""),
        "cpu_cores": cpuinfo.get("cpus"),
        "cpu_sockets": cpuinfo.get("sockets"),
        "cpu_load": cpu_load,
        "memory_total_mb": mem_total,
        "memory_used_mb": mem_used,
        "memory_free_mb": mem_free,
        "memory_usage_pct": mem_pct,
        "rootfs_total_gb": _bytes_to_gb(rootfs.get("total", 0)),
        "rootfs_used_gb": _bytes_to_gb(rootfs.get("used", 0)),
        "rootfs_avail_gb": _bytes_to_gb(rootfs.get("avail", 0)),
        "swap_total_mb": _bytes_to_mb(swap.get("total", 0)),
        "swap_used_mb": _bytes_to_mb(swap.get("used", 0)),
        "disk_io_delay_ms": io_delay_ms,
        "diskstat": diskstat,
        "ip_address": ip_address,
        "is_ceph_node": False,  # 后续可从 /nodes/{node}/ceph 检查
        "is_ha_node": False,
        "uptime_seconds": uptime,
        "vms": vms,
        "containers": containers,
        "storages": storages,
        "networks": networks,
    }


def _scan_vms(pve: PVEClient, node_name: str) -> list:
    """扫描节点上的 QEMU 虚拟机"""
    try:
        qemu_list = pve.get_node_qemu(node_name)
    except Exception as e:
        logger.warning(f"Failed to get VMs for {node_name}: {e}")
        return []

    vms = []
    for vm in qemu_list:
        vmid = vm.get("vmid")
        vm_data = {
            "vmid": vmid,
            "name": vm.get("name", ""),
            "status": vm.get("status", "unknown"),
            "cpu_cores": vm.get("maxcpu"),
            "cpu_usage": _cpu_to_pct(vm.get("cpu", 0)),
            "memory_mb": _bytes_to_mb(vm.get("maxmem", 0)),
            "memory_used_mb": _bytes_to_mb(vm.get("mem", 0)),
            "disk_gb": _bytes_to_gb(vm.get("disk", 0)),
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
        }

        # 获取详细配置
        try:
            config = pve.get_vm_config(node_name, vmid)
            vm_data["os_type"] = config.get("ostype", "")
            vm_data["description"] = config.get("description", "")
            vm_data["cpu_sockets"] = config.get("sockets")
        except Exception:
            pass

        # 快照数
        try:
            snapshots = pve.get_vm_snapshots(node_name, vmid)
            vm_data["snapshot_count"] = len(snapshots)
        except Exception:
            pass

        vms.append(vm_data)

    return vms


def _scan_lxc(pve: PVEClient, node_name: str) -> list:
    """扫描节点上的 LXC 容器"""
    try:
        lxc_list = pve.get_node_lxc(node_name)
    except Exception as e:
        logger.warning(f"Failed to get LXC for {node_name}: {e}")
        return []

    containers = []
    for ct in lxc_list:
        ct_data = {
            "vmid": ct.get("vmid"),
            "name": ct.get("name", ""),
            "status": ct.get("status", "unknown"),
            "cpu_cores": ct.get("maxcpu"),
            "cpu_usage": _cpu_to_pct(ct.get("cpu", 0)),
            "memory_mb": _bytes_to_mb(ct.get("maxmem", 0)),
            "memory_used_mb": _bytes_to_mb(ct.get("mem", 0)),
            "swap_mb": _bytes_to_mb(ct.get("maxswap", 0)),
            "swap_used_mb": _bytes_to_mb(ct.get("swap", 0)),
            "disk_gb": _bytes_to_gb(ct.get("maxdisk", 0)),
            "uptime_seconds": ct.get("uptime", 0),
            "tags": ct.get("tags", ""),
            "description": "",
        }
        containers.append(ct_data)

    return containers


def _scan_storages(pve: PVEClient, node_name: str) -> list:
    """扫描节点存储"""
    try:
        storage_list = pve.get_node_storage(node_name)
    except Exception as e:
        logger.warning(f"Failed to get storage for {node_name}: {e}")
        return []

    storages = []
    for st in storage_list:
        storages.append({
            "name": st.get("storage", ""),
            "type": st.get("type", ""),
            "active": bool(st.get("active", 0)),
            "used_gb": _bytes_to_gb(st.get("used", 0)),
            "avail_gb": _bytes_to_gb(st.get("available", 0)),
            "total_gb": _bytes_to_gb(st.get("total", 0)),
            "used_fraction": st.get("used_fraction"),
            "content_types": st.get("content", ""),
            "shared": bool(st.get("shared", 0)),
        })

    return storages


def _scan_networks(pve: PVEClient, node_name: str) -> list:
    """扫描节点网络接口"""
    try:
        net_list = pve.get_node_network(node_name)
    except Exception as e:
        logger.warning(f"Failed to get network for {node_name}: {e}")
        return []

    networks = []
    for net in net_list:
        networks.append({
            "name": net.get("iface", ""),
            "type": net.get("type", ""),
            "active": bool(net.get("active", 0)),
            "method": net.get("method", ""),
            "address": net.get("address", ""),
            "gateway": net.get("gateway", ""),
            "speed_mbps": net.get("speed"),
        })

    return networks
