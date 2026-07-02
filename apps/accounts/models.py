from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
import secrets


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
