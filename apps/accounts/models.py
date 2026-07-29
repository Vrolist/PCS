from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from cryptography.fernet import Fernet
from django.conf import settings
import base64
import hashlib
import secrets


def _get_fernet():
    """用 Django SECRET_KEY 派生加密密钥"""
    key = base64.urlsafe_b64encode(
        hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    )
    return Fernet(key)


class User(AbstractUser):
    """自定义用户模型"""
    phone = models.CharField("手机号", max_length=20, blank=True)
    company = models.CharField("公司", max_length=128, blank=True)
    avatar = models.URLField("头像", max_length=256, blank=True)

    class Meta:
        verbose_name = "用户"
        verbose_name_plural = "用户"

    def __str__(self):
        return self.username


class PasswordResetCode(models.Model):
    """密码重置验证码"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="用户")
    code = models.CharField("验证码", max_length=64, unique=True)
    email = models.EmailField("邮箱")
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    expires_at = models.DateTimeField("过期时间")
    is_used = models.BooleanField("已使用", default=False)

    class Meta:
        verbose_name = "密码重置码"
        verbose_name_plural = "密码重置码"

    def __str__(self):
        return f"{self.user.username} - {self.code[:8]}..."

    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at

    @classmethod
    def generate_for_user(cls, user, email, expiry_minutes=30):
        code = secrets.token_urlsafe(32)
        expires_at = timezone.now() + timezone.timedelta(minutes=expiry_minutes)
        return cls.objects.create(
            user=user,
            code=code,
            email=email,
            expires_at=expires_at,
        )


class UserLog(models.Model):
    """用户操作日志"""
    ACTION_CHOICES = [
        ("login", "登录"),
        ("logout", "退出登录"),
        ("create", "创建"),
        ("update", "更新"),
        ("delete", "删除"),
        ("change_password", "修改密码"),
        ("reset_password", "重置密码"),
        ("register", "注册"),
        ("other", "其他"),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="用户")
    username = models.CharField("用户名", max_length=150, blank=True)
    action = models.CharField("操作类型", max_length=32, choices=ACTION_CHOICES, db_index=True)
    resource_type = models.CharField("资源类型", max_length=64, blank=True, db_index=True)
    resource_id = models.CharField("资源 ID", max_length=64, blank=True)
    detail = models.TextField("操作详情", blank=True)
    ip_address = models.GenericIPAddressField("IP 地址", blank=True, null=True)
    user_agent = models.CharField("User-Agent", max_length=512, blank=True)
    created_at = models.DateTimeField("操作时间", auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "操作日志"
        verbose_name_plural = "操作日志"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.username} - {self.get_action_display()} - {self.created_at:%Y-%m-%d %H:%M}"


class SystemConfig(models.Model):
    """系统配置（键值对，运行时动态修改）"""
    key = models.CharField("配置键", max_length=128, unique=True)
    value = models.TextField("配置值", blank=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "系统配置"
        verbose_name_plural = "系统配置"

    def __str__(self):
        return f"{self.key} = {self.value}"

    @classmethod
    def get(cls, key, default=None):
        try:
            return cls.objects.get(key=key).value
        except cls.DoesNotExist:
            return default

    @classmethod
    def set(cls, key, value):
        obj, _ = cls.objects.update_or_create(key=key, defaults={"value": str(value)})
        return obj


class UserLLMConfig(models.Model):
    """用户的大模型配置"""
    PROVIDER_CHOICES = [
        ('deepseek', 'DeepSeek'),
        ('kimi', 'Kimi'),
        ('glm', 'GLM'),
        ('openai', 'OpenAI'),
        ('mimo', 'MiMo（小米）'),
        ('custom', '自定义'),
    ]

    BILLING_MODE_CHOICES = [
        ('payg', '余额计费'),
        ('plan', 'Token Plan（套餐）'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='llm_configs')
    name = models.CharField('配置名称', max_length=64, default='')
    provider = models.CharField('服务提供商', max_length=16, choices=PROVIDER_CHOICES, default='deepseek')
    billing_mode = models.CharField('计费方式', max_length=8, choices=BILLING_MODE_CHOICES, blank=True, default='')
    api_key_encrypted = models.TextField('API Key（加密）', blank=True, default='')
    model = models.CharField('模型', max_length=128, default='')
    base_url = models.CharField('API 地址', max_length=256, blank=True, default='')
    is_active = models.BooleanField('当前选中', default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_active', 'created_at']
        verbose_name = '用户模型配置'
        verbose_name_plural = '用户模型配置'

    def __str__(self):
        return f'{self.user.username} - {self.name}'

    @property
    def api_key(self):
        if not self.api_key_encrypted:
            return ''
        try:
            return _get_fernet().decrypt(self.api_key_encrypted.encode()).decode()
        except Exception:
            return ''

    @api_key.setter
    def api_key(self, value):
        if value:
            self.api_key_encrypted = _get_fernet().encrypt(value.encode()).decode()
        else:
            self.api_key_encrypted = ''

    @property
    def has_key(self) -> bool:
        return bool(self.api_key_encrypted)


class ChatConversation(models.Model):
    """AI 助手对话会话"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_conversations')
    title = models.CharField('对话标题', max_length=256, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = '对话会话'
        verbose_name_plural = '对话会话'

    def __str__(self):
        return f'{self.user.username} - {self.title or "未命名对话"}'


class ChatMessage(models.Model):
    """AI 助手对话消息"""
    conversation = models.ForeignKey(ChatConversation, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField('角色', max_length=16)  # 'user' or 'assistant'
    content = models.TextField('内容')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = '对话消息'
        verbose_name_plural = '对话消息'

    def __str__(self):
        return f'[{self.role}] {self.content[:50]}'


DEFAULT_SYSTEM_PROMPT = """# 角色定义

你是 PCS (PveClusterScan) 平台的 AI 运维助手，专为 Proxmox VE 集群监控与管理设计。你的核心职责是帮助用户分析 PVE 集群的运行状况，发现潜在问题，并提供可操作的运维建议。

# 能力范围

你可以基于以下类型的实时数据进行分析：

1. **节点状态** — CPU 使用率、内存使用率、根分区磁盘使用率、磁盘 I/O 延迟、运行时长
2. **虚拟机 (VM)** — 运行状态、CPU/内存/磁盘分配、网络流量、快照数量
3. **LXC 容器** — 运行状态、CPU/内存/交换分区使用、IP 地址
4. **存储** — 类型、容量、使用率、共享状态
5. **网络接口** — 类型、IP 地址、网卡速率
6. **Ceph 集群** — 健康状态、OSD 数量与状态、存储用量
7. **HA 资源** — 资源组状态、CRM 状态、故障转移配置
8. **SDN 虚拟网络** — 区域、虚拟网络、子网配置

# 回答规范

## 语言要求
- 使用中文回复，保持简洁清晰
- 对技术术语保留英文原文，首次出现时加中文说明

## 格式要求
- 使用 Markdown 结构化回答，善用标题、列表、表格
- 对比性数据使用表格展示，表格包含表头
- 异常数据使用 **加粗** 或 `行内代码` 突出

## 分析深度
- 分析问题时遵循：**现象 → 原因 → 影响 → 建议** 的逻辑链路
- 给出具体数值，不只是"过高/过低"等定性描述
- 建议要可操作，包含具体的排查步骤或优化方向

# 异常处理规范

对不同类型的异常采用不同的处理策略：

| 异常级别 | 判断标准 | 处理方式 |
|---------|---------|---------|
| 严重 | CPU > 90% / 磁盘 > 90% / 节点离线 | 立即预警，给出紧急应对方案 |
| 警告 | CPU > 75% / 磁盘 > 80% / 内存 > 85% | 建议关注，给出优化方案 |
| 提示 | 资源使用趋势上升 / 配置非最佳实践 | 提供优化建议，防患未然 |

对于 Ceph 集群：
- HEALTH_OK → 正常，可不做处理
- HEALTH_WARN → 分析降级原因，给出修复步骤
- HEALTH_ERR → 紧急处理建议，可能导致数据不可用

# 边界限制

- **只回答与 PVE 集群运维相关的问题**。对于超出范围的提问（编程、日常聊天等），礼貌地表示无法回答，并引导回到运维话题
- **不执行任何命令或操作**。所有建议仅为指导性文字建议，不涉及登录执行 shell 命令或 API 调用
- **不确定时不编造**。当数据不足以作出判断时，明确告知用户缺少哪些信息
- **不提供安全敏感的配置建议**。对于涉及生产环境的关键配置变更，建议查阅官方文档或在测试环境验证
"""


class UserSystemPrompt(models.Model):
    """用户自定义角色约束"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='system_prompts')
    name = models.CharField('约束名称', max_length=64, default='PVE 运维助手')
    content = models.TextField('约束内容', default=DEFAULT_SYSTEM_PROMPT)
    is_default = models.BooleanField('默认约束', default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_default', '-updated_at']
        verbose_name = '角色约束'
        verbose_name_plural = '角色约束'

    def __str__(self):
        return self.name
