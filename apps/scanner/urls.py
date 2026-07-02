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
]
