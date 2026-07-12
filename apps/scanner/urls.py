from django.urls import path

from . import views

urlpatterns = [
    path("nodes/", views.NodeListView.as_view(), name="scanner-nodes"),
    path("nodes/<int:node_id>/detail/", views.NodeDetailView.as_view(), name="scanner-node-detail"),
    path("vms/", views.VMListView.as_view(), name="scanner-vms"),
    path("vms/<int:vm_id>/detail/", views.VMDetailView.as_view(), name="scanner-vm-detail"),
    path("containers/", views.LXCListView.as_view(), name="scanner-containers"),
    path("containers/<int:ct_id>/detail/", views.LXCDetailView.as_view(), name="scanner-ct-detail"),
    path("storage/", views.StorageListView.as_view(), name="scanner-storage"),
    path("networks/", views.NetworkInterfaceListView.as_view(), name="scanner-networks"),
    path("ceph/", views.CephStatusView.as_view(), name="scanner-ceph"),
    path("ha/", views.HAListView.as_view(), name="scanner-ha"),
    path("sdn/zones/", views.SDNZoneListView.as_view(), name="scanner-sdn-zones"),
    path("sdn/vnets/", views.SDNVNetListView.as_view(), name="scanner-sdn-vnets"),
    path("sdn/subnets/", views.SDNSubnetListView.as_view(), name="scanner-sdn-subnets"),
    path("snapshots/", views.SnapshotListView.as_view(), name="scanner-snapshots"),
    path("backup/storages/", views.BackupStorageListView.as_view(), name="scanner-backup-storages"),
    path("backup/jobs/", views.BackupJobListView.as_view(), name="scanner-backup-jobs"),
    path("backup/history/", views.BackupHistoryListView.as_view(), name="scanner-backup-history"),
    path("backup/stats/", views.BackupStatsView.as_view(), name="scanner-backup-stats"),
    path("replication/", views.ReplicationJobListView.as_view(), name="scanner-replication"),
    path("firewall/summary/", views.FirewallSummaryView.as_view(), name="scanner-firewall-summary"),
    path("firewall/rules/", views.FirewallRulesView.as_view(), name="scanner-firewall-rules"),
    path("firewall/ipsets/", views.FirewallIPSetsView.as_view(), name="scanner-firewall-ipsets"),
    path("firewall/aliases/", views.FirewallAliasesView.as_view(), name="scanner-firewall-aliases"),
    path("firewall/options/", views.FirewallOptionsView.as_view(), name="scanner-firewall-options"),
    path("firewall/security-groups/", views.FirewallSecurityGroupsView.as_view(), name="scanner-firewall-security-groups"),
    path("dependency/", views.DependencyGraphView.as_view(), name="scanner-dependency"),
    path("changes/", views.ChangeTrackingView.as_view(), name="scanner-changes"),
]
