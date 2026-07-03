# 05 — ZFS 深度监控

> 优先级：P2 | 预估工期：4-5天 | 依赖：Agent 扩展采集 zpool/arcstat 数据

## 功能描述

扩展 Agent 采集 ZFS 存储池的详细健康指标：scrub 状态、碎片率、ARC 命中率、读写延迟分布等，在前端以专业可视化方式展示，帮助运维人员监控 ZFS 存储健康度。

## 核心价值

- ZFS 是 PVE 最常用的存储后端，健康度直接影响虚拟机性能
- Scrub 状态监控防止数据静默损坏
- ARC 命中率反映内存缓存效率

## Agent 采集扩展

### 新增采集命令

```bash
# 1. ZPool 状态
zpool status -x  # 精简模式
zpool list -o name,size,alloc,free,fragmentation,cap,health

# 2. ZFS 属性
zfs list -o name,used,available,referenced,compression,ratio

# 3. ARC 统计
cat /proc/spl/kstat/zfs/arcstats  # 或 arcstat 工具

# 4. Scrub 历史
zpool history | grep scrub
```

### 新增数据模型

```python
class ZFSPoolStatus(models.Model):
    """ZFS 存储池状态"""
    node = models.ForeignKey(ClusterNode, on_delete=models.CASCADE,
                             related_name='zfs_pools')
    scan = models.ForeignKey(ScanTask, on_delete=models.SET_NULL,
                             null=True, blank=True)

    pool_name = models.CharField("池名称", max_length=128)
    health = models.CharField("健康状态", max_length=32,
                              help_text="ONLINE / DEGRADED / FAULTED")
    size_gb = models.FloatField("总容量(GB)")
    allocated_gb = models.FloatField("已分配(GB)")
    free_gb = models.FloatField("可用(GB)")
    fragmentation_pct = models.FloatField("碎片率(%)", null=True)
    capacity_pct = models.CharField("容量使用率", max_length=8)

    # Scrub 状态
    last_scrub_date = models.DateTimeField("上次 Scrub", null=True, blank=True)
    scrub_status = models.CharField("Scrub 状态", max_length=32,
                                     help_text="completed / in progress / none")
    scrub_errors = models.IntegerField("Scrub 错误数", default=0)

    # VDev 信息
    vdevs = models.JSONField("VDev 列表", default=list,
        help_text='[{"type":"mirror","disks":["sda","sdb"],"state":"ONLINE"}]')

    scanned_at = models.DateTimeField("扫描时间", db_index=True)

    class Meta:
        verbose_name = "ZFS Pool 状态"
        unique_together = ("node", "pool_name")


class ZFSARCCache(models.Model):
    """ZFS ARC 缓存统计"""
    node = models.ForeignKey(ClusterNode, on_delete=models.CASCADE,
                             related_name='arc_stats')
    scan = models.ForeignKey(ScanTask, on_delete=models.SET_NULL,
                             null=True, blank=True)

    # ARC 大小
    size_bytes = models.BigIntegerField("ARC 大小(字节)")
    target_size_bytes = models.BigIntegerField("目标大小(字节)")
    max_size_bytes = models.BigIntegerField("最大大小(字节)")

    # 命中率
    hits = models.BigIntegerField("命中次数")
    misses = models.BigIntegerField("未命中次数")
    hit_ratio = models.FloatField("命中率(%)")

    # 分类
    mru_size = models.BigIntegerField("MRU 大小(字节)", default=0)
    mfu_size = models.BigIntegerField("MFU 大小(字节)", default=0)

    # L2ARC (SSD 缓存)
    l2arc_size = models.BigIntegerField("L2ARC 大小(字节)", default=0)
    l2arc_hits = models.BigIntegerField("L2ARC 命中", default=0)

    scanned_at = models.DateTimeField("扫描时间", db_index=True)

    class Meta:
        verbose_name = "ZFS ARC 缓存"
        ordering = ["-scanned_at"]
```

## 后端 API

```
GET /api/scanner/zfs-pools/?cluster_id=X
GET /api/scanner/zfs-pools/{pool_id}/
GET /api/scanner/arc-stats/?cluster_id=X&hours=24
```

## 前端实现

### ZFS 存储池总览

```
┌──────────────────────────────────────┐
│ 💾 ZFS 存储监控                      │
│                                      │
│ 🟢 nwy-zfs          451GB/512GB 88%  │
│    ████████████████░░ 碎片率 12%     │
│    Scrub: 2026-06-15 ✅ 0 错误       │
│    VDev: raidz1 [nvme0 nvme1 nvme2]  │
│                                      │
│ 🟢 data-pool        180GB/500GB 36%  │
│    ████████░░░░░░░░░░ 碎片率 3%      │
│    Scrub: 2026-06-28 ✅ 0 错误       │
│    VDev: mirror [sda sdb]           │
├──────────────────────────────────────┤
│ 📊 ARC 缓存命中率                    │
│                                      │
│ 命中率: 94.2%                        │
│ ██████████████████████████████░░░░   │
│ MRU: 8GB  MFU: 24GB  L2ARC: 0GB    │
│                                      │
│ [近24小时趋势图]                     │
└──────────────────────────────────────┘
```

### 告警规则

| 指标 | 阈值 | 级别 |
|------|------|------|
| Pool health != ONLINE | 任何异常 | critical |
| Scrub 间隔 >30 天 | 未执行 scrub | warning |
| Scrub 错误数 >0 | 有数据损坏 | critical |
| 碎片率 >30% | 碎片过高 | warning |
| ARC 命中率 <80% | 缓存效率低 | warning |
| 容量 >90% | 空间不足 | critical |

## 注意事项

- Agent 采集需要 root 权限执行 zpool 命令
- ARC 统计需要 `/proc/spl/kstat/zfs/arcstats` 可读（Proxmox 默认支持）
- L2ARC 仅在配置了 SSD 缓存池时有数据
- Scrub 历史通过 `zpool history` 解析，格式可能因版本不同有差异
