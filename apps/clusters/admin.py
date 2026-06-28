from django.contrib import admin

from .models import Cluster


@admin.register(Cluster)
class ClusterAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'status', 'total_nodes', 'total_vms',
                    'last_scanned_at', 'is_active', 'created_at']
    list_filter = ['status', 'is_active']
    search_fields = ['name', 'user__username']
    readonly_fields = ['agent_token', 'cluster_id']
