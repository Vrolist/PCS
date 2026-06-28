from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User, Plan, UserPlan


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'phone', 'company', 'is_staff', 'date_joined']
    list_filter = ['is_staff', 'is_active']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('额外信息', {'fields': ('phone', 'company', 'avatar')}),
    )


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'price_monthly', 'max_clusters', 'is_active', 'sort_order']
    list_filter = ['is_active']
    list_editable = ['sort_order']


@admin.register(UserPlan)
class UserPlanAdmin(admin.ModelAdmin):
    list_display = ['user', 'plan', 'start_date', 'end_date', 'is_active']
    list_filter = ['is_active', 'plan']
