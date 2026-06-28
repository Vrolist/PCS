from django.contrib.auth.models import AbstractUser
from django.db import models


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


class Plan(models.Model):
    """套餐/价格体系"""
    name = models.CharField("套餐名称", max_length=64)
    code = models.SlugField("标识符", unique=True, help_text="free / pro / enterprise")
    price_monthly = models.DecimalField("月费(元)", max_digits=8, decimal_places=2, default=0)
    price_yearly = models.DecimalField("年费(元)", max_digits=8, decimal_places=2, default=0)

    # 功能限制
    max_clusters = models.IntegerField("最大集群数", default=1)
    max_nodes_per_cluster = models.IntegerField("每集群最大节点数", default=10)
    scan_interval_minutes = models.IntegerField("Agent扫描间隔(分钟)", default=60)
    retention_days = models.IntegerField("数据保留天数", default=30)
    max_agents_per_cluster = models.IntegerField("每集群最大Agent数", default=1)

    # 功能开关
    features = models.JSONField("功能开关", default=dict, blank=True,
        help_text='{"ceph_monitor": true, "security_scan": false, "auto_repair": false}')
    is_active = models.BooleanField("启用", default=True)

    sort_order = models.IntegerField("排序", default=0)
    description = models.TextField("描述", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "套餐"
        verbose_name_plural = "套餐"
        ordering = ["sort_order"]

    def __str__(self):
        return f"{self.name} ({self.code})"


class UserPlan(models.Model):
    """用户订阅"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="用户",
                             related_name="plans")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, verbose_name="套餐")
    start_date = models.DateField("开始日期", auto_now_add=True)
    end_date = models.DateField("结束日期")
    is_active = models.BooleanField("有效", default=True)
    auto_renew = models.BooleanField("自动续费", default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "用户订阅"
        verbose_name_plural = "用户订阅"

    def __str__(self):
        return f"{self.user.username} - {self.plan.name}"
