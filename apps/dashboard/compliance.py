"""合规审计报告 API (Compliance Report)"""
from collections import defaultdict

from django.db.models import Q, Count, Sum
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.clusters.models import Cluster
from apps.scanner.models import (
    ClusterNode, VM, LXC, VMConfig, LXCConfig,
    CephStatus, HAResource, BackupJob, BackupStorage, BackupHistory,
    FirewallOptions, FirewallRule, NetworkInterface, Storage,
    ReplicationJob, DetectionResult,
)


def _user_cluster_ids(user):
    return list(Cluster.objects.filter(user=user).values_list("id", flat=True))


def _grade(score):
    if score >= 90:
        return "compliant"
    if score >= 70:
        return "mostly"
    if score >= 50:
        return "partial"
    return "non_compliant"


def _pct(passed, total):
    return round(passed / total * 100) if total else 100


class ComplianceReportView(APIView):
    """GET /api/dashboard/compliance/?cluster_id=X"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cluster_filter = request.query_params.get("cluster_id")
        cluster_ids = _user_cluster_ids(request.user)

        if cluster_filter:
            cluster_ids = [int(cluster_filter)]

        if not cluster_ids:
            return Response({"error": "no_cluster"}, status=400)

        nodes = ClusterNode.objects.filter(cluster_id__in=cluster_ids)
        node_ids = list(nodes.values_list("id", flat=True))

        categories = []

        # ═══════════════════════════════════════════════════
        # 1. 高可用合规 (HA Compliance) — 权重 25%
        # ═══════════════════════════════════════════════════
        vm_total = VM.objects.filter(node__in=nodes).count()
        lxc_total = LXC.objects.filter(node__in=nodes).count()
        resource_total = vm_total + lxc_total

        ha_vm = VMConfig.objects.filter(
            vm__node__in=nodes, ha_enabled=True
        ).count()
        ha_lxc = LXCConfig.objects.filter(
            container__node__in=nodes, ha_enabled=True
        ).count()
        ha_total = ha_vm + ha_lxc

        ha_pct = _pct(ha_total, resource_total)
        ha_issues = []
        if ha_pct < 100:
            ha_issues.append(f"{resource_total - ha_total} 个资源未启用 HA 高可用保护")
        ha_resources = HAResource.objects.filter(cluster_id__in=cluster_ids)
        ha_errors = ha_resources.filter(~Q(crm_state="started"))
        if ha_errors.exists():
            ha_issues.append(f"{ha_errors.count()} 个 HA 资源 CRM 状态异常")

        categories.append({
            "name": "ha",
            "label": "高可用合规",
            "weight": 25,
            "score": ha_pct,
            "grade": _grade(ha_pct),
            "total_checks": resource_total,
            "passed_checks": ha_total,
            "issues": ha_issues,
            "details": {
                "vm_total": vm_total, "vm_ha": ha_vm,
                "lxc_total": lxc_total, "lxc_ha": ha_lxc,
                "ha_resources_count": ha_resources.count(),
                "ha_errors_count": ha_errors.count(),
            },
        })

        # ═══════════════════════════════════════════════════
        # 2. 备份合规 (Backup Compliance) — 权重 20%
        # ═══════════════════════════════════════════════════
        backup_jobs = BackupJob.objects.filter(cluster_id__in=cluster_ids)
        enabled_jobs = backup_jobs.filter(enabled=True)
        job_count = backup_jobs.count()
        enabled_count = enabled_jobs.count()

        # 最近 7 天备份成功率
        week_ago = timezone.now() - timezone.timedelta(days=7)
        recent_history = BackupHistory.objects.filter(
            cluster_id__in=cluster_ids, started_at__gte=week_ago
        )
        total_runs = recent_history.count()
        success_runs = recent_history.filter(status="ok").count()
        backup_success_pct = _pct(success_runs, total_runs) if total_runs else 0

        # 有备份任务覆盖的 VMID
        backed_up_vmids = set(enabled_jobs.values_list("vmid", flat=True))
        all_vmids = set(VM.objects.filter(node__in=nodes).values_list("vmid", flat=True))
        all_vmids.update(LXC.objects.filter(node__in=nodes).values_list("vmid", flat=True))
        coverage_pct = _pct(len(backed_up_vmids & all_vmids), len(all_vmids))

        # 综合：覆盖率 60% + 成功率 40%
        backup_score = round(coverage_pct * 0.6 + backup_success_pct * 0.4) if job_count > 0 else 0

        backup_issues = []
        uncovered = len(all_vmids - backed_up_vmids)
        if uncovered > 0:
            backup_issues.append(f"{uncovered} 个资源无备份任务覆盖")
        if total_runs > 0 and backup_success_pct < 100:
            backup_issues.append(f"近 7 天备份成功率 {backup_success_pct}%，有 {total_runs - success_runs} 次失败")
        if enabled_count < job_count:
            backup_issues.append(f"{job_count - enabled_count} 个备份任务已禁用")

        categories.append({
            "name": "backup",
            "label": "备份合规",
            "weight": 20,
            "score": backup_score,
            "grade": _grade(backup_score),
            "total_checks": len(all_vmids),
            "passed_checks": len(backed_up_vmids & all_vmids),
            "issues": backup_issues,
            "details": {
                "total_jobs": job_count, "enabled_jobs": enabled_count,
                "coverage_pct": coverage_pct, "success_pct": backup_success_pct,
                "total_runs_7d": total_runs, "success_runs_7d": success_runs,
            },
        })

        # ═══════════════════════════════════════════════════
        # 3. 防火墙合规 (Firewall Compliance) — 权重 20%
        # ═══════════════════════════════════════════════════
        fw_options = FirewallOptions.objects.filter(cluster_id__in=cluster_ids)
        cluster_fw = fw_options.filter(scope="cluster")
        cluster_fw_enabled = cluster_fw.filter(enabled=True).exists()

        fw_rules = FirewallRule.objects.filter(cluster_id__in=cluster_ids)
        rule_count = fw_rules.count()
        enabled_rules = fw_rules.filter(enabled=True).count()

        # 检查默认策略
        default_deny_in = cluster_fw.filter(policy_in="DROP").exists() or cluster_fw.filter(policy_in="REJECT").exists()
        default_deny_out = cluster_fw.filter(policy_out="DROP").exists() or cluster_fw.filter(policy_out="REJECT").exists()

        fw_score = 0
        fw_issues = []
        if cluster_fw_enabled:
            fw_score += 40
        else:
            fw_issues.append("集群级防火墙未启用")

        if rule_count > 0:
            fw_score += 20
        else:
            fw_issues.append("未配置任何防火墙规则")

        if default_deny_in:
            fw_score += 20
        else:
            fw_issues.append("入站默认策略不是 DROP/REJECT")

        if default_deny_out:
            fw_score += 20
        else:
            fw_issues.append("出站默认策略不是 DROP/REJECT")

        categories.append({
            "name": "firewall",
            "label": "防火墙合规",
            "weight": 20,
            "score": fw_score,
            "grade": _grade(fw_score),
            "total_checks": 4,
            "passed_checks": sum([cluster_fw_enabled, rule_count > 0, default_deny_in, default_deny_out]),
            "issues": fw_issues,
            "details": {
                "cluster_fw_enabled": cluster_fw_enabled,
                "total_rules": rule_count, "enabled_rules": enabled_rules,
                "default_deny_in": default_deny_in, "default_deny_out": default_deny_out,
            },
        })

        # ═══════════════════════════════════════════════════
        # 4. 存储合规 (Storage Compliance) — 权重 15%
        # ═══════════════════════════════════════════════════
        # 获取每个存储的最新记录
        storages = Storage.objects.filter(
            node__cluster_id__in=cluster_ids
        ).order_by("node_id", "storage_name", "-scanned_at")
        seen = set()
        latest_storages = []
        for s in storages:
            key = (s.node_id, s.storage_name)
            if key not in seen:
                seen.add(key)
                latest_storages.append(s)

        storage_total = len(latest_storages)
        storage_ok = 0
        storage_issues = []
        ceph_health = None

        for s in latest_storages:
            usage = s.used_fraction or 0
            if usage <= 85:
                storage_ok += 1
            else:
                storage_issues.append(f"存储 {s.storage_name}({s.node.node_name}) 使用率 {usage}% 超过 85%")

        # Ceph 健康检查
        ceph_list = CephStatus.objects.filter(cluster_id__in=cluster_ids).order_by("-scanned_at")
        if ceph_list.exists():
            ceph = ceph_list.first()
            ceph_health = ceph.health
            if ceph.health == "HEALTH_OK":
                storage_ok += 1
                storage_total += 1
            else:
                storage_total += 1
                storage_issues.append(f"Ceph 状态异常: {ceph.health}")

        storage_score = _pct(storage_ok, storage_total)

        categories.append({
            "name": "storage",
            "label": "存储合规",
            "weight": 15,
            "score": storage_score,
            "grade": _grade(storage_score),
            "total_checks": storage_total,
            "passed_checks": storage_ok,
            "issues": storage_issues,
            "details": {
                "total_storages": len(latest_storages),
                "over_85pct": storage_total - storage_ok - (1 if ceph_health and ceph_health != "HEALTH_OK" else 0),
                "ceph_health": ceph_health,
            },
        })

        # ═══════════════════════════════════════════════════
        # 5. 网络合规 (Network Compliance) — 权重 10%
        # ═══════════════════════════════════════════════════
        node_count = nodes.count()
        nodes_with_bond = NetworkInterface.objects.filter(
            node__in=nodes, type="bond"
        ).values("node_id").distinct().count()

        # 每个节点至少 2 个网口
        node_iface_counts = NetworkInterface.objects.filter(
            node__in=nodes
        ).values("node_id").annotate(cnt=Count("id"))
        nodes_multi_iface = sum(1 for n in node_iface_counts if n["cnt"] >= 2)

        net_score = 0
        net_issues = []
        if node_count > 0:
            bond_pct = round(nodes_with_bond / node_count * 100)
            multi_pct = round(nodes_multi_iface / node_count * 100)
            net_score = round(bond_pct * 0.6 + multi_pct * 0.4)
        if nodes_with_bond < node_count:
            net_issues.append(f"{node_count - nodes_with_bond} 个节点未配置 bond 网络冗余")
        if nodes_multi_iface < node_count:
            net_issues.append(f"{node_count - nodes_multi_iface} 个节点网口数不足 2 个")

        categories.append({
            "name": "network",
            "label": "网络合规",
            "weight": 10,
            "score": net_score,
            "grade": _grade(net_score),
            "total_checks": node_count * 2,
            "passed_checks": nodes_with_bond + nodes_multi_iface,
            "issues": net_issues,
            "details": {
                "node_count": node_count,
                "nodes_with_bond": nodes_with_bond,
                "nodes_multi_iface": nodes_multi_iface,
            },
        })

        # ═══════════════════════════════════════════════════
        # 6. 检测告警合规 (Detection Compliance) — 权重 10%
        # ═══════════════════════════════════════════════════
        total_detections = DetectionResult.objects.filter(cluster_id__in=cluster_ids).count()
        unresolved = DetectionResult.objects.filter(
            cluster_id__in=cluster_ids, is_resolved=False
        )
        unresolved_count = unresolved.count()
        critical_unresolved = unresolved.filter(severity="critical").count()
        warning_unresolved = unresolved.filter(severity="warning").count()

        # 无未解决 critical 告警 = 100, 每个 critical -20, 每个 warning -5
        detect_score = max(0, 100 - critical_unresolved * 20 - warning_unresolved * 5)
        detect_issues = []
        if critical_unresolved > 0:
            detect_issues.append(f"{critical_unresolved} 个严重告警未解决")
        if warning_unresolved > 0:
            detect_issues.append(f"{warning_unresolved} 个警告未解决")

        categories.append({
            "name": "detection",
            "label": "告警合规",
            "weight": 10,
            "score": detect_score,
            "grade": _grade(detect_score),
            "total_checks": total_detections,
            "passed_checks": total_detections - unresolved_count,
            "issues": detect_issues,
            "details": {
                "total_detections": total_detections,
                "unresolved": unresolved_count,
                "critical": critical_unresolved,
                "warning": warning_unresolved,
            },
        })

        # ═══════════════════════════════════════════════════
        # 综合评分
        # ═══════════════════════════════════════════════════
        overall_score = round(sum(c["score"] * c["weight"] / 100 for c in categories))
        overall_grade = _grade(overall_score)

        total_checks = sum(c["total_checks"] for c in categories)
        total_passed = sum(c["passed_checks"] for c in categories)

        # 汇总建议
        recommendations = []
        for c in categories:
            if c["score"] < 70 and c["issues"]:
                for issue in c["issues"][:2]:
                    recommendations.append(f"[{c['label']}] {issue}")

        return Response({
            "overall_score": overall_score,
            "overall_grade": overall_grade,
            "summary": {
                "total_checks": total_checks,
                "passed_checks": total_passed,
                "pass_rate": _pct(total_passed, total_checks),
                "categories_count": len(categories),
                "compliant": sum(1 for c in categories if c["grade"] == "compliant"),
                "non_compliant": sum(1 for c in categories if c["grade"] == "non_compliant"),
            },
            "categories": categories,
            "recommendations": recommendations,
            "generated_at": timezone.now().isoformat(),
        })
