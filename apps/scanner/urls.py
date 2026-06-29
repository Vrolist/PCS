from django.urls import path

from . import views

urlpatterns = [
    path("nodes/", views.NodeListView.as_view(), name="scanner-nodes"),
    path("vms/", views.VMListView.as_view(), name="scanner-vms"),
    path("vms/<int:vm_id>/detail/", views.VMDetailView.as_view(), name="scanner-vm-detail"),
    path("containers/", views.LXCListView.as_view(), name="scanner-containers"),
    path("containers/<int:ct_id>/detail/", views.LXCDetailView.as_view(), name="scanner-ct-detail"),
    path("ha/", views.HAListView.as_view(), name="scanner-ha"),
]
