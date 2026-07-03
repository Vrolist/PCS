# 12 — 定期健康报告自动生成

> 优先级：P2 | 预估工期：2-3天 | 依赖：ScanHistory + DetectionResult + 通知集成

## 功能描述

每周/每月自动生成集群健康报告并邮件发送，包含资源概览、告警统计、趋势变化、风险建议，运维人员不需要手动查看就能掌握集群状态。

## 核心价值

- 管理层周报自动化
- 历史趋势沉淀
- 运维工作量量化展示

## 报告内容

### 周报模板

```
# PVE 集群周报 — 生产环境
## 2026-06-28 ~ 2026-07-03

### 📊 资源概览
| 指标 | 本周均值 | 上周均值 | 变化 |
|------|---------|---------|------|
| CPU 使用率 | 65.2% | 62.1% | ↑ +3.1% |
| 内存使用率 | 72.5% | 70.0% | ↑ +2.5% |
| 磁盘使用率 | 58.3% | 57.8% | ↑ +0.5% |
| 存储总量 | 2000GB | 2000GB | — |

### ⚠️ 告警统计
- 严重告警: 2 次 (↓ 减少 1 次)
- 警告告警: 12 次 (↑ 增加 3 次)
- 信息告警: 8 次

#### 严重告警详情
1. 06-30 14:00 VM 199 CPU 过载 (95%) → 已修复
2. 07-02 09:00 firstbox 磁盘空间不足 (92%) → 已修复

### 📈 趋势分析
- CPU: 近7天平均 65.2%，峰值 89% (07-01 15:00)
- 内存: 近7天平均 72.5%，峰值 85% (07-02 10:00)
- 存储: 线性增长，预计 696 天后满

### 🛡️ DR Score 变化
- 本周: 78 分 (良好) ↑ +2 分
- 新增 HA 保护: VM 205 (new-webapp)

### 💡 建议
1. VM 7711 (Win11-P620) 无任何保护，建议配置 HA
2. 5 台 VM 无快照保护
3. Ceph 存储池 health 需关注 (HEALTH_WARN)

### 📦 运维操作
| 时间 | 操作 | 操作人 |
|------|------|--------|
| 06-29 | VM 205 创建 | admin |
| 07-01 | firstbox 磁盘扩容 | admin |
```

## 后端实现

### 报告生成引擎

```python
class HealthReportGenerator:
    """集群健康报告生成器"""
    
    def generate_weekly(self, cluster_id):
        cluster = Cluster.objects.get(id=cluster_id)
        end_date = timezone.now()
        start_date = end_date - timedelta(days=7)
        
        report = {
            "cluster": cluster.name,
            "period": f"{start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}",
            "resource_overview": self._resource_summary(cluster, start_date, end_date),
            "alert_stats": self._alert_statistics(cluster, start_date, end_date),
            "trend_analysis": self._trend_analysis(cluster, start_date, end_date),
            "dr_score": self._dr_score_summary(cluster),
            "recommendations": self._generate_recommendations(cluster),
            "operations": self._recent_operations(cluster, start_date, end_date),
        }
        
        return report
    
    def _resource_summary(self, cluster, start, end):
        histories = ScanHistory.objects.filter(
            cluster=cluster, scanned_at__range=(start, end)
        )
        # 按天聚合 CPU/内存/磁盘平均值
        daily_data = defaultdict(list)
        for h in histories:
            day = h.scanned_at.date()
            daily_data[day].append(h.snapshot_data)
        
        # 计算周均值、峰值
        ...
    
    def render_html(self, report):
        """渲染为 HTML 邮件"""
        template = loader.get_template('emails/health_report.html')
        return template.render(report)
    
    def render_markdown(self, report):
        """渲染为 Markdown（用于存档）"""
        ...
```

### 定时任务

通过平台 Cron 调度：

```python
# 每周一早上 9:00 生成周报
CRON_SCHEDULE = "0 1 * * 1"  # UTC，北京时间 09:00

# 每月 1 号早上 9:00 生成月报
CRON_SCHEDULE_MONTHLY = "0 1 1 * *"
```

## 前端实现

### 报告管理页面

新增 `views/reports/index.vue`：

```
┌──────────────────────────────────────┐
│ 📊 健康报告                          │
├──────────────────────────────────────┤
│ 最新报告:                            │
│                                      │
│ 📄 周报 2026-06-28 ~ 07-03          │
│    集群: 生产环境 | 评分: 78 🟡       │
│    [查看] [下载] [重新生成]           │
│                                      │
│ 📄 周报 2026-06-21 ~ 06-27          │
│    集群: 生产环境 | 评分: 76 🟡       │
│    [查看] [下载]                      │
│                                      │
│ 📄 月报 2026-06                      │
│    集群: 生产环境 | 评分: 75 🟡       │
│    [查看] [下载]                      │
├──────────────────────────────────────┤
│ 定时设置:                            │
│ 周报: 每周一 09:00                   │
│ 月报: 每月 1 日 09:00                │
│ 收件人: admin@company.com            │
│ [编辑设置]                           │
└──────────────────────────────────────┘
```

### 报告预览

- HTML 渲染在 iframe 中展示
- 支持导出为 PDF
- 历史报告存档可检索

## 注意事项

- 报告生成需要查询大量历史数据，建议异步生成
- HTML 邮件模板需要兼容各邮件客户端（Outlook/Gmail/QQ邮箱）
- 月报相比周报增加：容量预测、DR Score 趋势、月度对比
- 报告存档在数据库或文件系统均可，建议两者都存
- 首次使用时数据不足 7 天，显示"数据积累中"提示
