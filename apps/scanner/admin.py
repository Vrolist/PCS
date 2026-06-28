from django.contrib import admin

from .models import (ClusterNode, VM, LXC, Storage, NetworkInterface,
                     CephStatus, ScanHistory, DetectionRule, DetectionResult)


@admin.register(ClusterNode)
class ClusterNodeAdmin(admin.ModelAdmin):
    list_display = ['node_name', 'cluster', 'status', 'cpu_cores',
                    'memory_usage_pct', 'cpu_load', 'scanned_at']
    list_filter = ['status', 'is_ceph_node']
    search_fields = ['node_name', 'cluster__name']


@admin.register(VM)
class VMAdmin(admin.ModelAdmin):
    list_display = ['name', 'vmid', 'node', 'status', 'cpu_cores',
                    'memory_mb', 'scanned_at']
    list_filter = ['status', 'has_template']
    search_fields = ['name', 'vmid']


@admin.register(LXC)
class LXCAdmin(admin.ModelAdmin):
    list_display = ['name', 'vmid', 'node', 'status', 'cpu_cores', 'memory_mb', 'scanned_at']
    list_filter = ['status']
    search_fields = ['name', 'vmid']


@admin.register(Storage)
class StorageAdmin(admin.ModelAdmin):
    list_display = ['storage_name', 'node', 'type', 'status', 'total_gb',
                    'used_fraction', 'shared']
    list_filter = ['type', 'status', 'shared']


@admin.register(NetworkInterface)
class NetworkInterfaceAdmin(admin.ModelAdmin):
    list_display = ['name', 'node', 'type', 'active', 'address', 'speed_mbps']
    list_filter = ['type', 'active']


@admin.register(CephStatus)
class CephStatusAdmin(admin.ModelAdmin):
    list_display = ['cluster', 'health', 'total_osds', 'up_osds', 'total_space_gb', 'scanned_at']
    list_filter = ['health']


@admin.register(ScanHistory)
class ScanHistoryAdmin(admin.ModelAdmin):
    list_display = ['cluster', 'scanned_at']
    list_filter = ['scanned_at']


@admin.register(DetectionRule)
class DetectionRuleAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'severity', 'is_enabled', 'cluster']
    list_filter = ['category', 'severity', 'is_enabled']


@admin.register(DetectionResult)
class DetectionResultAdmin(admin.ModelAdmin):
    list_display = ['title', 'cluster', 'category', 'severity',
                    'affected_resource', 'is_resolved', 'created_at']
    list_filter = ['category', 'severity', 'is_resolved']
