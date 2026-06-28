from django.contrib import admin

from .models import AgentInstance, ScanTask


@admin.register(AgentInstance)
class AgentInstanceAdmin(admin.ModelAdmin):
    list_display = ['hostname', 'agent_id', 'cluster', 'version', 'status',
                    'last_heartbeat_at', 'total_scans']
    list_filter = ['status', 'version']
    search_fields = ['hostname', 'agent_id', 'cluster__name']


@admin.register(ScanTask)
class ScanTaskAdmin(admin.ModelAdmin):
    list_display = ['cluster', 'agent', 'task_type', 'status', 'total_nodes',
                    'total_vms', 'started_at', 'duration_seconds']
    list_filter = ['status', 'task_type']
    search_fields = ['cluster__name']
