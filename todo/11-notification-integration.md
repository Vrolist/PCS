# 11 — 告警通知集成

> 优先级：P1 | 预估工期：2-3天 | 依赖：DetectionResult + 通知渠道

## 功能描述

告警不只在 Web 页面展示，推送到运维人员常用的通知渠道：邮件、企业微信、钉钉、Telegram，支持分级推送策略。

## 核心价值

- 告警即时到达，不漏不过
- 运维人员不需要一直盯着页面
- 分级推送，重要告警电话/短信，一般告警消息

## 支持的通知渠道

| 渠道 | 实现方式 | 优先级 |
|------|---------|--------|
| 邮件 | SMTP | P0 |
| 企业微信 Webhook | Webhook URL | P0 |
| 钉钉机器人 | Webhook URL | P1 |
| Telegram Bot | Bot API | P1 |
| 浏览器推送 | WebSocket | P2 |

## 推送策略

### 分级推送

| 告警级别 | 邮件 | 企业微信 | 钉钉 | Telegram |
|---------|------|---------|------|----------|
| critical | ✅ 立即 | ✅ 立即 | ✅ 立即 | ✅ 立即 |
| warning | ✅ 汇总(每小时) | ✅ 立即 | ✅ 立即 | ❌ |
| info | ✅ 每日汇总 | ❌ | ❌ | ❌ |

### 去重策略

- 同一告警 10 分钟内不重复推送
- 告警恢复时推送"恢复通知"
- 支持静默时段（如 00:00-07:00 不推送 info）

## 数据模型

```python
class NotificationChannel(models.Model):
    """通知渠道配置"""
    class ChannelType(models.TextChoices):
        EMAIL = "email", "邮件"
        WECHAT_WORK = "wechat_work", "企业微信"
        DINGTALK = "dingtalk", "钉钉"
        TELEGRAM = "telegram", "Telegram"
    
    name = models.CharField("渠道名称", max_length=128)
    channel_type = models.CharField("类型", choices=ChannelType.choices)
    
    # 邮件配置
    smtp_host = models.CharField("SMTP 主机", max_length=128, blank=True)
    smtp_port = models.IntegerField("SMTP 端口", default=587)
    smtp_user = models.CharField("SMTP 用户", max_length=128, blank=True)
    smtp_password = models.CharField("SMTP 密码", max_length=128, blank=True)
    
    # Webhook 配置
    webhook_url = models.URLField("Webhook URL", blank=True)
    
    # Telegram 配置
    bot_token = models.CharField("Bot Token", max_length=128, blank=True)
    chat_id = models.CharField("Chat ID", max_length=64, blank=True)
    
    # 推送策略
    notify_critical = models.BooleanField("推送 Critical", default=True)
    notify_warning = models.BooleanField("推送 Warning", default=True)
    notify_info = models.BooleanField("推送 Info", default=False)
    
    # 静默时段
    quiet_start = models.TimeField("静默开始", null=True, blank=True)
    quiet_end = models.TimeField("静默结束", null=True, blank=True)
    
    is_enabled = models.BooleanField("启用", default=True)
    
    class Meta:
        verbose_name = "通知渠道"


class NotificationLog(models.Model):
    """通知发送日志"""
    channel = models.ForeignKey(NotificationChannel, on_delete=models.CASCADE)
    alert = models.ForeignKey("DetectionResult", on_delete=models.CASCADE)
    status = models.CharField("状态", max_length=16,
                              help_text="sent / failed / skipped")
    error_message = models.TextField("错误信息", blank=True)
    sent_at = models.DateTimeField("发送时间", auto_now_add=True)
    
    class Meta:
        verbose_name = "通知日志"
        ordering = ["-sent_at"]
```

## 后端实现

### 通知发送服务

```python
class NotificationService:
    """统一通知发送服务"""
    
    def send_alert(self, alert: DetectionResult):
        channels = NotificationChannel.objects.filter(is_enabled=True)
        for channel in channels:
            if not self._should_notify(channel, alert):
                continue
            
            try:
                content = self._format_message(alert, channel.channel_type)
                self._send(channel, content)
                NotificationLog.objects.create(
                    channel=channel, alert=alert, status="sent"
                )
            except Exception as e:
                NotificationLog.objects.create(
                    channel=channel, alert=alert,
                    status="failed", error_message=str(e)
                )
    
    def _format_message(self, alert, channel_type):
        """根据渠道类型格式化消息"""
        if channel_type == "wechat_work":
            return self._format_wechat_markdown(alert)
        elif channel_type == "dingtalk":
            return self._format_dingtalk_markdown(alert)
        elif channel_type == "email":
            return self._format_html_email(alert)
        elif channel_type == "telegram":
            return self._format_telegram_html(alert)
```

### 企业微信消息模板

```json
{
    "msgtype": "markdown",
    "markdown": {
        "content": "## ⚠️ PVE 告警通知\n> **集群**: 生产环境\n> **级别**: 🔴 严重\n> **告警**: VM 199 CPU 使用率 95%\n> **节点**: firstbox\n> **时间**: 2026-07-03 14:00\n\n请及时处理！"
    }
}
```

## 前端实现

### 通知设置页面

扩展 `views/user-notifications/index.vue`：

```
┌──────────────────────────────────────┐
│ 🔔 通知设置                          │
├──────────────────────────────────────┤
│ 已配置的通知渠道:                     │
│                                      │
│ ✅ 企业微信  webhook.wechat.com/...  │
│    Critical ✅  Warning ✅  Info ❌  │
│    [编辑] [删除] [测试]              │
│                                      │
│ ✅ 邮件  ops@example.com             │
│    Critical ✅  Warning ✅  Info ✅  │
│    [编辑] [删除] [测试]              │
│                                      │
│ [+ 添加通知渠道]                     │
├──────────────────────────────────────┤
│ 静默时段:                            │
│ [00:00] - [07:00] (info 级别静默)    │
│                                      │
│ 去重间隔: [10] 分钟                   │
│ 恢复通知: [✅ 启用]                   │
└──────────────────────────────────────┘
```

## 注意事项

- 企业微信 Webhook 有频率限制（20条/分钟），需要做速率控制
- 钉钉 Webhook 需要加签（sign 参数）
- 邮件通知建议用平台已有的 SMTP 配置（QQ 邮箱 1121031509@qq.com）
- 敏感信息（Webhook URL、Token）在数据库中需加密存储
- 通知日志需定期清理（保留 30 天）
