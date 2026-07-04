"""灾备就绪评分 API (DR Score)"""
from collections import defaultdict

from django.db.models import Q, Max
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.clusters.models import Cluster
from apps.scanner.models import (
    VM, LXC, VMConfig, LXCConfig, VMSnapshot,
    HAResource, NetworkInterface, BackupJob, BackupStorage, Storage,
)


def _user_cluster_ids(user):
    return list(Cluster.objects.filter(user=user).values_list("id", flat=True))


# ── 评分权重 ──────────────────────────────────────────────
VM_WEIGHTS = {
    "ha": 30,
    "snapshot": 20,
    "backup": 20,
    "agent": 15,
    "network": 15,
}
LXC_WEIGHTS = {
    "ha": 30,
    "snapshot": 20,
    "backup": 20,
    "agent": 0,  # LXC 无 QEMU Agent
    "network": 15,
}
# Agent 权重为 0 时，将 15 分摊到其他维度（按比例）
_LXC_REDIST = {k: v / 85 * 100 for k, v in LXC_WEIGHTS.items() if k != "agent"}


def _grade(score):
    if score >= 80:
        return "excellent"
    if score >= 60:
        return "good"
    if score >= 40:
        return "fair"
    return "danger"


def _get_latest_vms(cluster_ids):
    """获取每个集群每个 VM 的最新记录"""
    from apps.scanner.models import ClusterNode
    nodes = ClusterNode.objects.filter(cluster_id__in=cluster_ids)
    vms = VM.objects.filter(node__in=nodes).select_related("node")
    # 使用 update_or_create 策略，每条 VM 只有一条记录
    return list(vms)


def _get_latest_lxcs(cluster_ids):
    from apps.scanner.models import ClusterNode
    nodes = ClusterNode.objects.filter(cluster_id__in=cluster_ids)
    return list(LXC.objects.filter(node__in=nodes).select_related("node"))


def _score_vm(vm, ha_set, snapshot_count_map, backup_vmids, backup_storages_set, network_map):
    """对单个 VM 评分"""
    breakdown = {"ha": 0, "snapshot": 0, "backup": 0, "agent": 0, "network": 0}
    missing = []

    # 1. HA 保护
    if vm.id in ha_set:
        breakdown["ha"] = VM_WEIGHTS["ha"]
    else:
        missing.append("HA保护")

    # 2. 快照保护
    snap_count = snapshot_count_map.get(vm.id, vm.snapshot_count or 0)
    if snap_count > 0:
        breakdown["snapshot"] = VM_WEIGHTS["snapshot"]
    else:
        missing.append("快照")

    # 3. 备份存储
    if vm.vmid in backup_vmids:
        breakdown["backup"] = VM_WEIGHTS["backup"]
    else:
        missing.append("备份存储")

    # 4. QEMU Agent
    if hasattr(vm, '_agent_enabled') and vm._agent_enabled:
        breakdown["agent"] = VM_WEIGHTS["agent"]
    else:
        missing.append("QEMU Agent")

    # 5. 网络冗余
    iface_count, has_bond = network_map.get(vm.node_id, (0, False))
    if iface_count >= 2 and has_bond:
        breakdown["network"] = VM_WEIGHTS["network"]
    elif iface_count >= 2:
        breakdown["network"] = 8
    else:
        missing.append("网络冗余")

    total = sum(breakdown.values())
    return total, breakdown, missing


def _score_lxc(lxc, ha_set, backup_vmids, network_map):
    """对单个 LXC 容器评分"""
    breakdown = {"ha": 0, "snapshot": 0, "backup": 0, "agent": 0, "network": 0}
    missing = []

    # 1. HA 保护
    if lxc.id in ha_set:
        breakdown["ha"] = LXC_WEIGHTS["ha"]
    else:
        missing.append("HA保护")

    # 2. 快照保护 — LXC 无快照数据，给默认 0
    missing.append("快照")

    # 3. 备份存储
    if lxc.vmid in backup_vmids:
        breakdown["backup"] = LXC_WEIGHTS["backup"]
    else:
        missing.append("备份存储")

    # 4. Agent — LXC 无 QEMU Agent，分值重分配
    breakdown["agent"] = 0

    # 5. 网络冗余
    iface_count, has_bond = network_map.get(lxc.node_id, (0, False))
    if iface_count >= 2 and has_bond:
        breakdown["network"] = LXC_WEIGHTS["network"]
    elif iface_count >= 2:
        breakdown["network"] = 8
    else:
        missing.append("网络冗余")

    total = sum(breakdown.values())
    return total, breakdown, missing


def _build_network_map(cluster_ids):
    """构建 node_id → (iface_count, has_bond) 映射"""
    from apps.scanner.models import ClusterNode
    nodes = ClusterNode.objects.filter(cluster_id__in=cluster_ids)
    ifaces = NetworkInterface.objects.filter(node__in=nodes).values(
        "node_id", "type", "bond_mode"
    )

    result = defaultdict(lambda: (0, False))
    node_ifaces = defaultdict(lambda: {"count": 0, "has_bond": False})
    for iface in ifaces:
        nid = iface["node_id"]
        node_ifaces[nid]["count"] += 1
        if iface["type"] == "bond" or iface.get("bond_mode"):
            node_ifaces[nid]["has_bond"] = True

    for nid, info in node_ifaces.items():
        result[nid] = (info["count"], info["has_bond"])
    return result


def _build_ha_sets(cluster_ids):
    """构建 VM/LXC 的 HA 启用集合"""
    vm_configs = VMConfig.objects.filter(
        vm__node__cluster_id__in=cluster_ids, ha_enabled=True
    ).values_list("vm_id", flat=True)

    lxc_configs = LXCConfig.objects.filter(
        container__node__cluster_id__in=cluster_ids, ha_enabled=True
    ).values_list("container_id", flat=True)

    return set(vm_configs), set(lxc_configs)


def _build_snapshot_map(cluster_ids):
    """构建 vm_id → 快照数 映射"""
    snapshots = VMSnapshot.objects.filter(
        vm__node__cluster_id__in=cluster_ids
    ).values("vm_id").annotate(count=Max("id"))
    # 用 distinct vm_id 计数
    snap_counts = defaultdict(int)
    for s in VMSnapshot.objects.filter(
        vm__node__cluster_id__in=cluster_ids
    ).values_list("vm_id", flat=True):
        snap_counts[s] += 1
    return snap_counts


def _build_backup_sets(cluster_ids):
    """构建有备份任务的 VMID 集合 + 备份存储名集合"""
    jobs = BackupJob.objects.filter(cluster_id__in=cluster_ids, enabled=True)
    backup_vmids = set(jobs.values_list("vmid", flat=True))

    backup_storages = set(
        BackupStorage.objects.filter(cluster_id__in=cluster_ids).values_list("storage_name", flat=True)
    )
    return backup_vmids, backup_storages


def _build_agent_map(cluster_ids):
    """构建 vm_id → agent_enabled 映射"""
    configs = VMConfig.objects.filter(
        vm__node__cluster_id__in=cluster_ids
    ).values_list("vm_id", "agent_enabled")
    return {vm_id: enabled for vm_id, enabled in configs}


class DRScoreView(APIView):
    """GET /api/dashboard/dr-score/?cluster_id=X"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cluster_filter = request.query_params.get("cluster_id")
        cluster_ids = _user_cluster_ids(request.user)

        if cluster_filter:
            cluster_ids = [int(cluster_filter)]

        if not cluster_ids:
            return Response({"error": "no_cluster"}, status=400)

        # ── 预加载数据 ──
        vms = _get_latest_vms(cluster_ids)
        lxcs = _get_latest_lxcs(cluster_ids)
        ha_vm_set, ha_lxc_set = _build_ha_sets(cluster_ids)
        snapshot_map = _build_snapshot_map(cluster_ids)
        backup_vmids, backup_storages = _build_backup_sets(cluster_ids)
        network_map = _build_network_map(cluster_ids)
        agent_map = _build_agent_map(cluster_ids)

        # ── 逐资源评分 ──
        resources = []
        vm_scores = []
        lxc_scores = []

        for vm in vms:
            vm._agent_enabled = agent_map.get(vm.id, False)
            score, breakdown, missing = _score_vm(
                vm, ha_vm_set, snapshot_map, backup_vmids, backup_storages, network_map
            )
            weight = 2 if vm.status == "running" else (1.5 if vm.has_template else 1)
            resources.append({
                "type": "vm",
                "vmid": vm.vmid,
                "name": vm.name,
                "node": vm.node.node_name,
                "status": vm.status,
                "score": score,
                "grade": _grade(score),
                "breakdown": breakdown,
                "missing": missing,
                "_weight": weight,
            })
            vm_scores.append((score, weight))

        for lxc in lxcs:
            score, breakdown, missing = _score_lxc(
                lxc, ha_lxc_set, backup_vmids, network_map
            )
            weight = 2 if lxc.status == "running" else (1.5 if lxc.has_template else 1)
            resources.append({
                "type": "lxc",
                "vmid": lxc.vmid,
                "name": lxc.name,
                "node": lxc.node.node_name,
                "status": lxc.status,
                "score": score,
                "grade": _grade(score),
                "breakdown": breakdown,
                "missing": missing,
                "_weight": weight,
            })
            lxc_scores.append((score, weight))

        # ── 集群总分：加权平均 ──
        all_scores = vm_scores + lxc_scores
        if all_scores:
            total_weighted = sum(s * w for s, w in all_scores)
            total_weight = sum(w for _, w in all_scores)
            cluster_score = round(total_weighted / total_weight) if total_weight else 0
        else:
            cluster_score = 0

        cluster_grade = _grade(cluster_score)

        # ── 统计 ──
        summary_counts = {"excellent": 0, "good": 0, "fair": 0, "danger": 0}
        for r in resources:
            summary_counts[r["grade"]] += 1

        # ── 建议 ──
        recommendations = []
        danger_resources = [r for r in resources if r["grade"] == "danger"]
        if danger_resources:
            names = ", ".join(
                f"{r['type'].upper()} {r['vmid']} ({r['name']})" for r in danger_resources[:5]
            )
            recommendations.append(f"以下资源无任何保护，建议立即配置 HA 或至少添加快照：{names}")

        no_backup = [r for r in resources if "备份存储" in r["missing"]]
        if no_backup:
            recommendations.append(f"{len(no_backup)} 个资源无备份存储，建议挂载备份目录并配置备份任务")

        no_ha = [r for r in resources if "HA保护" in r["missing"] and r["status"] == "running"]
        if no_ha:
            recommendations.append(f"{len(no_ha)} 个运行中的资源未启用 HA，建议配置高可用保护")

        no_snapshot = [r for r in resources if "快照" in r["missing"]]
        if no_snapshot:
            recommendations.append(f"{len(no_snapshot)} 个资源无快照，建议定期创建快照作为快速恢复手段")

        no_agent = [r for r in resources if "QEMU Agent" in r["missing"] and r["type"] == "vm"]
        if no_agent:
            recommendations.append(f"{len(no_agent)} 台 VM 未启用 QEMU Agent，建议在 VM 配置中启用以支持文件系统冻结备份")

        # ── 清理内部字段 ──
        for r in resources:
            del r["_weight"]

        # 按分数升序排列（最差的排前面）
        resources.sort(key=lambda r: r["score"])

        return Response({
            "cluster_score": cluster_score,
            "cluster_grade": cluster_grade,
            "summary": {
                "total_resources": len(resources),
                "excellent": summary_counts["excellent"],
                "good": summary_counts["good"],
                "fair": summary_counts["fair"],
                "danger": summary_counts["danger"],
            },
            "resources": resources,
            "recommendations": recommendations,
        })
