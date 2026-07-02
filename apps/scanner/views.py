from django.db.models import Max, Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.clusters.models import Cluster
from .models import ClusterNode, VM, LXC, VMConfig, LXCConfig, VMSnapshot, HAResource, Storage, NetworkInterface, CephStatus, SDNZone, SDNVNet, SDNSubnet


def _user_cluster_ids(user):
    return Cluster.objects.filter(user=user).values_list("id", flat=True)


def _latest_node_ids(user):
    """获取每个物理节点最新扫描的 ClusterNode ID 列表"""
    cluster_ids = _user_cluster_ids(user)
    latest = (
        ClusterNode.objects
        .filter(cluster_id__in=cluster_ids)
        .values("cluster_id", "node_name")
        .annotate(last_scan=Max("scanned_at"))
    )
    node_ids = []
    for item in latest:
        pk = (
            ClusterNode.objects
            .filter(
                cluster_id=item["cluster_id"],
                node_name=item["node_name"],
                scanned_at=item["last_scan"],
            )
            .values_list("pk", flat=True)
            .first()
        )
        if pk:
            node_ids.append(pk)
    return node_ids


class NodeListView(APIView):
    """GET /api/scanner/nodes/ — 节点列表（最新扫描数据）"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cluster_filter = request.query_params.get("cluster_id")
        node_ids = _latest_node_ids(request.user)
        nodes = ClusterNode.objects.filter(pk__in=node_ids).select_related("cluster")
        if cluster_filter:
            nodes = nodes.filter(cluster_id=cluster_filter)
        data = [{
            "id": n.id,
            "cluster_id": n.cluster_id,
            "cluster_name": n.cluster.name,
            "node_name": n.node_name,
            "status": n.status,
            "cpu_model": n.cpu_model,
            "cpu_cores": n.cpu_cores,
            "cpu_sockets": n.cpu_sockets,
            "cpu_load": n.cpu_load,
            "memory_total_mb": n.memory_total_mb,
            "memory_used_mb": n.memory_used_mb,
            "memory_usage_pct": n.memory_usage_pct,
            "rootfs_total_gb": n.rootfs_total_gb,
            "rootfs_used_gb": n.rootfs_used_gb,
            "rootfs_avail_gb": n.rootfs_avail_gb,
            "disk_io_delay_ms": n.disk_io_delay_ms,
            "ip_address": n.ip_address,
            "pve_version": n.pve_version,
            "kernel_version": n.kernel_version,
            "uptime_seconds": n.uptime_seconds,
            "is_ceph_node": n.is_ceph_node,
            "is_ha_node": n.is_ha_node,
            "scanned_at": n.scanned_at,
        } for n in nodes]
        return Response(data)


class SDNZoneListView(APIView):
    """GET /api/scanner/sdn/zones/ — SDN 区域列表"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cluster_ids = _user_cluster_ids(request.user)
        cluster_filter = request.query_params.get("cluster_id")
        if cluster_filter:
            cluster_ids = cluster_ids.filter(id=cluster_filter)
        zones = SDNZone.objects.filter(cluster_id__in=cluster_ids).select_related("cluster")
        data = [{
            "id": z.id,
            "zone": z.zone,
            "zone_type": z.zone_type,
            "nodes": z.nodes,
            "cluster_name": z.cluster.name,
            "scanned_at": z.scanned_at,
        } for z in zones]
        return Response(data)


class SDNVNetListView(APIView):
    """GET /api/scanner/sdn/vnets/ — SDN 虚拟网络列表"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cluster_ids = _user_cluster_ids(request.user)
        cluster_filter = request.query_params.get("cluster_id")
        if cluster_filter:
            cluster_ids = cluster_ids.filter(id=cluster_filter)
        vnets = SDNVNet.objects.filter(cluster_id__in=cluster_ids).select_related("cluster", "zone")
        data = [{
            "id": v.id,
            "vnet": v.vnet,
            "vnet_type": v.vnet_type,
            "vlan": v.vlan,
            "zone_name": v.zone_name,
            "zone": v.zone.zone if v.zone else "",
            "cluster_name": v.cluster.name,
            "scanned_at": v.scanned_at,
        } for v in vnets]
        return Response(data)


class SDNSubnetListView(APIView):
    """GET /api/scanner/sdn/subnets/ — SDN 子网列表"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cluster_ids = _user_cluster_ids(request.user)
        cluster_filter = request.query_params.get("cluster_id")
        if cluster_filter:
            cluster_ids = cluster_ids.filter(id=cluster_filter)
        subnets = SDNSubnet.objects.filter(cluster_id__in=cluster_ids).select_related("cluster", "vnet")
        data = [{
            "id": s.id,
            "subnet": s.subnet,
            "vnet_name": s.vnet_name,
            "vnet": s.vnet.vnet if s.vnet else "",
            "gateway": s.gateway,
            "dns_server": s.dns_server,
            "dns_zone_prefix": s.dns_zone_prefix,
            "cluster_name": s.cluster.name,
            "scanned_at": s.scanned_at,
        } for s in subnets]
        return Response(data)


class NodeDetailView(APIView):
    """GET /api/scanner/nodes/<id>/detail/ — 节点详情（含存储/网络/VM/容器）"""
    permission_classes = [IsAuthenticated]

    def get(self, request, node_id):
        try:
            node = ClusterNode.objects.select_related("cluster").get(pk=node_id)
        except ClusterNode.DoesNotExist:
            return Response({"error": "Node not found"}, status=404)

        # 基本信息
        data = {
            "node": {
                "id": node.id,
                "cluster_id": node.cluster_id,
                "cluster_name": node.cluster.name,
                "node_name": node.node_name,
                "status": node.status,
                "cpu_model": node.cpu_model,
                "cpu_cores": node.cpu_cores,
                "cpu_sockets": node.cpu_sockets,
                "cpu_load": node.cpu_load,
                "memory_total_mb": node.memory_total_mb,
                "memory_used_mb": node.memory_used_mb,
                "memory_free_mb": node.memory_free_mb,
                "memory_usage_pct": node.memory_usage_pct,
                "rootfs_total_gb": node.rootfs_total_gb,
                "rootfs_used_gb": node.rootfs_used_gb,
                "rootfs_avail_gb": node.rootfs_avail_gb,
                "swap_total_mb": node.swap_total_mb,
                "swap_used_mb": node.swap_used_mb,
                "disk_io_delay_ms": node.disk_io_delay_ms,
                "diskstat": node.diskstat,
                "ip_address": node.ip_address,
                "mac_address": node.mac_address,
                "pve_version": node.pve_version,
                "kernel_version": node.kernel_version,
                "uptime_seconds": node.uptime_seconds,
                "is_ceph_node": node.is_ceph_node,
                "is_ha_node": node.is_ha_node,
                "scanned_at": node.scanned_at,
            },
            "storages": [],
            "networks": [],
            "vms": [],
            "containers": [],
        }

        # 该节点的最新存储
        storage_latest = (
            Storage.objects
            .filter(node=node)
            .values("storage_name")
            .annotate(last_scan=Max("scanned_at"))
        )
        storages = []
        for item in storage_latest:
            s = Storage.objects.filter(
                node=node, storage_name=item["storage_name"],
                scanned_at=item["last_scan"]
            ).first()
            if s:
                storages.append({
                    "name": s.storage_name, "type": s.type, "status": s.status,
                    "active": s.active, "total_gb": s.total_gb, "used_gb": s.used_gb,
                    "avail_gb": s.avail_gb, "content_types": s.content_types, "shared": s.shared,
                })
        data["storages"] = storages

        # 该节点的最新网络接口
        net_latest = (
            NetworkInterface.objects
            .filter(node=node)
            .values("name")
            .annotate(last_scan=Max("scanned_at"))
        )
        networks = []
        for item in net_latest:
            ni = NetworkInterface.objects.filter(
                node=node, name=item["name"],
                scanned_at=item["last_scan"]
            ).first()
            if ni:
                networks.append({
                    "name": ni.name, "type": ni.type, "active": ni.active,
                    "method": ni.method, "address": ni.address,
                    "gateway": ni.gateway, "speed_mbps": ni.speed_mbps,
                    "bridge_ports": ni.bridge_ports,
                    "bond_mode": ni.bond_mode, "bond_slaves": ni.bond_slaves,
                    "vlan_id": ni.vlan_id, "mtu": ni.mtu,
                })
        data["networks"] = networks

        # 该节点最新扫描的 VM
        vm_latest = (
            VM.objects
            .filter(node=node)
            .values("vmid")
            .annotate(last_scan=Max("scanned_at"))
        )
        vms = []
        for item in vm_latest:
            vm = VM.objects.filter(
                node=node, vmid=item["vmid"],
                scanned_at=item["last_scan"]
            ).first()
            if vm:
                vms.append({
                    "vmid": vm.vmid, "name": vm.name, "status": vm.status,
                    "cpu_cores": vm.cpu_cores, "cpu_usage": vm.cpu_usage,
                    "memory_mb": vm.memory_mb, "memory_used_mb": vm.memory_used_mb,
                    "disk_gb": vm.max_disk_gb, "uptime_seconds": vm.uptime_seconds,
                })
        data["vms"] = vms

        # 该节点最新扫描的 LXC
        lxc_latest = (
            LXC.objects
            .filter(node=node)
            .values("vmid")
            .annotate(last_scan=Max("scanned_at"))
        )
        containers = []
        for item in lxc_latest:
            ct = LXC.objects.filter(
                node=node, vmid=item["vmid"],
                scanned_at=item["last_scan"]
            ).first()
            if ct:
                containers.append({
                    "vmid": ct.vmid, "name": ct.name, "status": ct.status,
                    "cpu_cores": ct.cpu_cores, "cpu_usage": ct.cpu_usage,
                    "memory_mb": ct.memory_mb, "memory_used_mb": ct.memory_used_mb,
                    "swap_mb": ct.swap_mb, "swap_used_mb": ct.swap_used_mb,
                    "disk_gb": ct.disk_gb, "uptime_seconds": ct.uptime_seconds,
                    "has_template": ct.has_template,
                })
        data["containers"] = containers

        return Response(data)


class StorageListView(APIView):
    """GET /api/scanner/storage/ — 存储列表"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cluster_filter = request.query_params.get("cluster_id")
        cluster_ids = _user_cluster_ids(request.user)
        nodes = ClusterNode.objects.filter(cluster_id__in=cluster_ids)
        if cluster_filter:
            nodes = nodes.filter(cluster_id=cluster_filter)
        storages = Storage.objects.filter(node__in=nodes).select_related("node__cluster")

        # 只取每个存储的最新记录
        latest = (
            storages.values("node__node_name", "storage_name")
            .annotate(last_scan=Max("scanned_at"))
        )
        q = Q()
        for item in latest:
            q |= Q(node__node_name=item["node__node_name"],
                   storage_name=item["storage_name"],
                   scanned_at=item["last_scan"])

        if q:
            storages = Storage.objects.filter(q, node__in=nodes).select_related("node__cluster")
        else:
            storages = Storage.objects.none()

        data = [{
            "id": s.id,
            "node_name": s.node.node_name,
            "cluster_name": s.node.cluster.name,
            "name": s.storage_name,
            "type": s.type,
            "status": s.status,
            "total_gb": s.total_gb,
            "used_gb": s.used_gb,
            "available_gb": s.avail_gb,
            "content": s.content_types,
            "shared": s.shared,
            "scanned_at": s.scanned_at,
        } for s in storages]
        return Response(data)


class NetworkInterfaceListView(APIView):
    """GET /api/scanner/networks/ — 网络接口列表"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cluster_filter = request.query_params.get("cluster_id")
        cluster_ids = _user_cluster_ids(request.user)
        nodes = ClusterNode.objects.filter(cluster_id__in=cluster_ids)
        if cluster_filter:
            nodes = nodes.filter(cluster_id=cluster_filter)
        ifaces = NetworkInterface.objects.filter(node__in=nodes).select_related("node__cluster")

        latest = (
            ifaces.values("node__node_name", "name")
            .annotate(last_scan=Max("scanned_at"))
        )
        q = Q()
        for item in latest:
            q |= Q(node__node_name=item["node__node_name"],
                   name=item["name"],
                   scanned_at=item["last_scan"])

        if q:
            ifaces = NetworkInterface.objects.filter(q, node__in=nodes).select_related("node__cluster")
        else:
            ifaces = NetworkInterface.objects.none()

        data = [{
            "id": i.id,
            "node_name": i.node.node_name,
            "cluster_name": i.node.cluster.name,
            "name": i.name,
            "type": i.type,
            "address": i.address,
            "gateway": i.gateway,
            "mac_address": "",
            "speed": i.speed_mbps,
            "status": "up" if i.active else "down",
            "bridge_ports": i.bridge_ports,
            "bond_mode": i.bond_mode,
            "bond_slaves": i.bond_slaves,
            "vlan_id": i.vlan_id,
            "mtu": i.mtu,
            "scanned_at": i.scanned_at,
        } for i in ifaces]
        return Response(data)


class CephStatusView(APIView):
    """GET /api/scanner/ceph/ — Ceph 状态"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cluster_filter = request.query_params.get("cluster_id")
        cluster_ids = _user_cluster_ids(request.user)
        latest = (
            CephStatus.objects.filter(cluster_id__in=cluster_ids)
            .values("cluster_id")
            .annotate(last_scan=Max("scanned_at"))
        )
        q = Q()
        for item in latest:
            q |= Q(cluster_id=item["cluster_id"], scanned_at=item["last_scan"])

        if q:
            ceph_statuses = CephStatus.objects.filter(q).order_by("-scanned_at")
        else:
            ceph_statuses = CephStatus.objects.none()

        if cluster_filter:
            ceph_statuses = ceph_statuses.filter(cluster_id=cluster_filter)

        if not ceph_statuses:
            return Response(None)

        s = ceph_statuses.first()
        data = {
            "id": s.id,
            "cluster_name": s.cluster.name if hasattr(s, "cluster") else "",
            "health": s.health,
            "total_osds": s.total_osds,
            "up_osds": s.up_osds,
            "in_osds": s.in_osds,
            "total_pgs": s.pool_count,
            "bytes_used_gb": s.total_used_gb,
            "bytes_total_gb": s.total_avail_gb,
            "version": "",
            "uptime": "",
            "scanned_at": s.scanned_at,
        }
        return Response(data)


class VMListView(APIView):
    """GET /api/scanner/vms/ — 虚拟机列表（每个 VM 只展示最新一条）"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cluster_ids = _user_cluster_ids(request.user)
        cluster_filter = request.query_params.get("cluster_id")
        node_filter = request.query_params.get("node_id")
        status_filter = request.query_params.get("status")
        search = request.query_params.get("search", "").strip()

        # 只取最新扫描的节点 ID
        node_ids = _latest_node_ids(request.user)

        # 在最新节点中，按 (node_name, vmid) 去重取最新
        latest = (
            VM.objects
            .filter(node_id__in=node_ids)
            .values("node__node_name", "vmid")
            .annotate(last_scan=Max("scanned_at"))
        )
        q = Q()
        for item in latest:
            q |= Q(
                node__node_name=item["node__node_name"],
                vmid=item["vmid"],
                scanned_at=item["last_scan"],
            )
        if not q:
            return Response([])

        vms = VM.objects.filter(q).select_related("node", "node__cluster")

        if cluster_filter:
            vms = vms.filter(node__cluster_id=cluster_filter)
        if node_filter:
            vms = vms.filter(node_id=node_filter)
        if status_filter:
            vms = vms.filter(status=status_filter)
        if search:
            vms = vms.filter(Q(name__icontains=search) | Q(vmid__icontains=search))

        data = [{
            "id": vm.id,
            "node_id": vm.node_id,
            "node_name": vm.node.node_name,
            "cluster_id": vm.node.cluster_id,
            "cluster_name": vm.node.cluster.name,
            "vmid": vm.vmid,
            "name": vm.name,
            "status": vm.status,
            "cpu_cores": vm.cpu_cores,
            "cpu_usage": vm.cpu_usage,
            "memory_mb": vm.memory_mb,
            "memory_used_mb": vm.memory_used_mb,
            "disk_gb": vm.disk_gb,
            "max_disk_gb": vm.max_disk_gb,
            "net_in_bps": vm.net_in_bps,
            "net_out_bps": vm.net_out_bps,
            "disk_read_iops": vm.disk_read_iops,
            "disk_write_iops": vm.disk_write_iops,
            "uptime_seconds": vm.uptime_seconds,
            "os_type": vm.os_type,
            "tags": vm.tags,
            "scanned_at": vm.scanned_at,
        } for vm in vms]
        return Response(data)


class LXCListView(APIView):
    """GET /api/scanner/containers/ — 容器列表（每个容器只展示最新一条）"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cluster_filter = request.query_params.get("cluster_id")
        node_filter = request.query_params.get("node_id")
        status_filter = request.query_params.get("status")
        search = request.query_params.get("search", "").strip()

        node_ids = _latest_node_ids(request.user)

        latest = (
            LXC.objects
            .filter(node_id__in=node_ids)
            .values("node__node_name", "vmid")
            .annotate(last_scan=Max("scanned_at"))
        )
        q = Q()
        for item in latest:
            q |= Q(
                node__node_name=item["node__node_name"],
                vmid=item["vmid"],
                scanned_at=item["last_scan"],
            )
        if not q:
            return Response([])

        containers = LXC.objects.filter(q).select_related("node", "node__cluster")

        if cluster_filter:
            containers = containers.filter(node__cluster_id=cluster_filter)
        if node_filter:
            containers = containers.filter(node_id=node_filter)
        if status_filter:
            containers = containers.filter(status=status_filter)
        if search:
            containers = containers.filter(Q(name__icontains=search) | Q(vmid__icontains=search))

        # 预加载最新 LXCConfig 以提取 IP
        from .models import LXCConfig
        container_ids = [ct.id for ct in containers]
        latest_configs = {}
        if container_ids:
            configs = (
                LXCConfig.objects
                .filter(container_id__in=container_ids)
                .values("container_id")
                .annotate(last_scan=Max("scanned_at"))
            )
            for cfg in configs:
                lc = LXCConfig.objects.filter(
                    container_id=cfg["container_id"],
                    scanned_at=cfg["last_scan"]
                ).first()
                if lc:
                    latest_configs[cfg["container_id"]] = lc

        def _extract_ip(ct):
            """从 LXCConfig.net_devices 提取第一个 IPv4 地址"""
            cfg = latest_configs.get(ct.id)
            if not cfg:
                return ""
            for net in (cfg.net_devices or []):
                ip_val = net.get("ip", "")
                if ip_val and ip_val != "dhcp" and "/" in ip_val:
                    return ip_val.split("/")[0]
            return ""

        data = [{
            "id": ct.id,
            "node_id": ct.node_id,
            "node_name": ct.node.node_name,
            "cluster_id": ct.node.cluster_id,
            "cluster_name": ct.node.cluster.name,
            "vmid": ct.vmid,
            "name": ct.name,
            "status": ct.status,
            "ip_address": _extract_ip(ct),
            "cpu_cores": ct.cpu_cores,
            "cpu_usage": ct.cpu_usage,
            "memory_mb": ct.memory_mb,
            "memory_used_mb": ct.memory_used_mb,
            "swap_mb": ct.swap_mb,
            "swap_used_mb": ct.swap_used_mb,
            "disk_gb": ct.disk_gb,
            "uptime_seconds": ct.uptime_seconds,
            "tags": ct.tags,
            "has_template": ct.has_template,
            "scanned_at": ct.scanned_at,
        } for ct in containers]
        return Response(data)


class VMDetailView(APIView):
    """GET /api/scanner/vms/<id>/detail/ — VM 详情（含配置）"""
    permission_classes = [IsAuthenticated]

    def get(self, request, vm_id):
        try:
            vm = VM.objects.select_related("node", "node__cluster").get(pk=vm_id)
        except VM.DoesNotExist:
            return Response({"error": "VM not found"}, status=404)

        config = (
            VMConfig.objects
            .filter(vm=vm)
            .order_by("-scanned_at")
            .first()
        )

        data = {
            "vm": {
                "id": vm.id,
                "vmid": vm.vmid,
                "name": vm.name,
                "status": vm.status,
                "node_name": vm.node.node_name,
                "cluster_name": vm.node.cluster.name,
                "cpu_cores": vm.cpu_cores,
                "cpu_sockets": vm.cpu_sockets,
                "cpu_usage": vm.cpu_usage,
                "memory_mb": vm.memory_mb,
                "memory_used_mb": vm.memory_used_mb,
                "balloon_min_mb": vm.balloon_min_mb,
                "balloon_max_mb": vm.balloon_max_mb,
                "disk_gb": vm.disk_gb,
                "max_disk_gb": vm.max_disk_gb,
                "disk_read_iops": vm.disk_read_iops,
                "disk_write_iops": vm.disk_write_iops,
                "net_in_bps": vm.net_in_bps,
                "net_out_bps": vm.net_out_bps,
                "uptime_seconds": vm.uptime_seconds,
                "os_type": vm.os_type,
                "snapshot_count": vm.snapshot_count,
                "has_template": vm.has_template,
                "tags": vm.tags,
                "description": vm.description,
                "scanned_at": vm.scanned_at,
            },
            "config": None,
        }

        if config:
            data["config"] = {
                "cpu_type": config.cpu_type,
                "cpu_cores": config.cpu_cores,
                "cpu_sockets": config.cpu_sockets,
                "memory_mb": config.memory_mb,
                "balloon_min_mb": config.balloon_min_mb,
                "os_type": config.os_type,
                "boot_order": config.boot_order,
                "scsi_disks": config.scsi_disks,
                "ide_disks": config.ide_disks,
                "net_devices": config.net_devices,
                "agent_enabled": config.agent_enabled,
                "ha_enabled": config.ha_enabled,
                "ha_group": config.ha_group,
                "description": config.description,
                "tags": config.tags,
            }

        return Response(data)


class LXCDetailView(APIView):
    """GET /api/scanner/containers/<id>/detail/ — LXC 详情（含配置）"""
    permission_classes = [IsAuthenticated]

    def get(self, request, ct_id):
        try:
            ct = LXC.objects.select_related("node", "node__cluster").get(pk=ct_id)
        except LXC.DoesNotExist:
            return Response({"error": "Container not found"}, status=404)

        config = (
            LXCConfig.objects
            .filter(container=ct)
            .order_by("-scanned_at")
            .first()
        )

        # 从 net_devices 提取 IP
        ip_address = ""
        if config:
            for net in (config.net_devices or []):
                ip_val = net.get("ip", "")
                if ip_val and ip_val != "dhcp" and "/" in ip_val:
                    ip_address = ip_val.split("/")[0]
                    break

        data = {
            "container": {
                "id": ct.id,
                "vmid": ct.vmid,
                "name": ct.name,
                "status": ct.status,
                "node_name": ct.node.node_name,
                "cluster_name": ct.node.cluster.name,
                "ip_address": ip_address,
                "cpu_cores": ct.cpu_cores,
                "cpu_usage": ct.cpu_usage,
                "memory_mb": ct.memory_mb,
                "memory_used_mb": ct.memory_used_mb,
                "swap_mb": ct.swap_mb,
                "swap_used_mb": ct.swap_used_mb,
                "disk_gb": ct.disk_gb,
                "uptime_seconds": ct.uptime_seconds,
                "tags": ct.tags,
                "has_template": ct.has_template,
                "scanned_at": ct.scanned_at,
            },
            "config": None,
        }

        if config:
            data["config"] = {
                "hostname": config.hostname,
                "cpu_cores": config.cpu_cores,
                "memory_mb": config.memory_mb,
                "swap_mb": config.swap_mb,
                "os_type": config.os_type,
                "rootfs": config.rootfs,
                "mount_points": config.mount_points,
                "net_devices": config.net_devices,
                "ha_enabled": config.ha_enabled,
                "ha_group": config.ha_group,
                "description": config.description,
                "tags": config.tags,
                "startup_order": config.startup_order,
            }

        return Response(data)


class HAListView(APIView):
    """GET /api/scanner/ha/ — HA 高可用资源列表"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cluster_filter = request.query_params.get("cluster_id")
        cluster_ids = _user_cluster_ids(request.user)

        # 只取每个 sid 的最新记录
        base_qs = HAResource.objects.filter(cluster_id__in=cluster_ids)
        if cluster_filter:
            base_qs = base_qs.filter(cluster_id=cluster_filter)
        latest = (
            base_qs
            .values("sid")
            .annotate(last_scan=Max("scanned_at"))
        )
        q = Q()
        for item in latest:
            q |= Q(sid=item["sid"], scanned_at=item["last_scan"])

        if q:
            resources = HAResource.objects.filter(q).select_related("cluster")
        else:
            resources = HAResource.objects.none()

        data = [{
            "id": r.id,
            "sid": r.sid,
            "resource_type": r.resource_type,
            "vmid": r.vmid,
            "node_name": r.node_name,
            "cluster_name": r.cluster.name,
            "state": r.state,
            "ha_group": r.ha_group,
            "ha_status": r.ha_status,
            "crm_state": r.crm_state,
            "max_restarts": r.max_restarts,
            "max_shutdown": r.max_shutdown,
            "scanned_at": r.scanned_at,
        } for r in resources]
        return Response(data)


class SnapshotListView(APIView):
    """GET /api/scanner/snapshots/ — VM 快照列表（每个快照只展示最新一条）"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cluster_ids = _user_cluster_ids(request.user)
        cluster_filter = request.query_params.get("cluster_id")
        node_filter = request.query_params.get("node_id")
        vmid_filter = request.query_params.get("vmid")
        search = request.query_params.get("search", "").strip()

        node_ids = _latest_node_ids(request.user)

        # 在最新节点中，按 (vm, snapid) 去重取最新
        latest = (
            VMSnapshot.objects
            .filter(vm__node_id__in=node_ids)
            .values("vm_id", "snapid")
            .annotate(last_scan=Max("scanned_at"))
        )
        q = Q()
        for item in latest:
            q |= Q(
                vm_id=item["vm_id"],
                snapid=item["snapid"],
                scanned_at=item["last_scan"],
            )
        if not q:
            return Response([])

        snaps = VMSnapshot.objects.filter(q).select_related("vm", "vm__node", "vm__node__cluster")

        if cluster_filter:
            snaps = snaps.filter(vm__node__cluster_id=cluster_filter)
        if node_filter:
            snaps = snaps.filter(vm__node_id=node_filter)
        if vmid_filter:
            snaps = snaps.filter(vm__vmid=vmid_filter)
        if search:
            snaps = snaps.filter(
                Q(name__icontains=search) | Q(description__icontains=search) |
                Q(vm__name__icontains=search) | Q(snapid__icontains=search)
            )

        data = [{
            "id": s.id,
            "snapid": s.snapid,
            "name": s.name,
            "description": s.description,
            "snap_time": s.snap_time,
            "parent": s.parent,
            "ram": s.ram,
            "vmstate": s.vmstate,
            "snap_type": s.snap_type,
            "size_mb": s.size_mb,
            "vm_id": s.vm_id,
            "vm_vmid": s.vm.vmid,
            "vm_name": s.vm.name,
            "vm_status": s.vm.status,
            "node_name": s.vm.node.node_name,
            "cluster_id": s.vm.node.cluster_id,
            "cluster_name": s.vm.node.cluster.name,
            "scanned_at": s.scanned_at,
        } for s in snaps]
        return Response(data)
