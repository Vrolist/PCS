from django.db.models import Max, Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.clusters.models import Cluster
from .models import ClusterNode, VM, LXC


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
        node_ids = _latest_node_ids(request.user)
        nodes = ClusterNode.objects.filter(pk__in=node_ids).select_related("cluster")
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

        data = [{
            "id": ct.id,
            "node_id": ct.node_id,
            "node_name": ct.node.node_name,
            "cluster_id": ct.node.cluster_id,
            "cluster_name": ct.node.cluster.name,
            "vmid": ct.vmid,
            "name": ct.name,
            "status": ct.status,
            "cpu_cores": ct.cpu_cores,
            "cpu_usage": ct.cpu_usage,
            "memory_mb": ct.memory_mb,
            "memory_used_mb": ct.memory_used_mb,
            "swap_mb": ct.swap_mb,
            "swap_used_mb": ct.swap_used_mb,
            "disk_gb": ct.disk_gb,
            "uptime_seconds": ct.uptime_seconds,
            "tags": ct.tags,
            "scanned_at": ct.scanned_at,
        } for ct in containers]
        return Response(data)
