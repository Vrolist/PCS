from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User, PasswordResetCode, UserLog, SystemConfig, UserLLMConfig


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'phone', 'company', 'is_staff', 'date_joined']
    list_filter = ['is_staff', 'is_active']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('额外信息', {'fields': ('phone', 'company', 'avatar')}),
    )


@admin.register(PasswordResetCode)
class PasswordResetCodeAdmin(admin.ModelAdmin):
    list_display = ['user', 'email', 'created_at', 'expires_at', 'is_used']
    list_filter = ['is_used']


@admin.register(UserLog)
class UserLogAdmin(admin.ModelAdmin):
    list_display = ['username', 'action', 'resource_type', 'resource_id', 'ip_address', 'created_at']
    list_filter = ['action', 'created_at']
    search_fields = ['username', 'detail']
    date_hierarchy = 'created_at'
    readonly_fields = ['username', 'action', 'resource_type', 'resource_id', 'detail', 'ip_address', 'user_agent', 'created_at']


@admin.register(SystemConfig)
class SystemConfigAdmin(admin.ModelAdmin):
    list_display = ['key', 'value', 'updated_at']
    search_fields = ['key']


@admin.register(UserLLMConfig)
class UserLLMConfigAdmin(admin.ModelAdmin):
    list_display = ['user', 'name', 'provider', 'model', 'is_active', 'has_key', 'created_at']
    list_filter = ['provider', 'is_active']
    search_fields = ['user__username', 'name']
    readonly_fields = ['api_key_encrypted']
