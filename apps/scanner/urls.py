from django.urls import path

from . import views

urlpatterns = [
    path("nodes/", views.NodeListView.as_view(), name="scanner-nodes"),
    path("vms/", views.VMListView.as_view(), name="scanner-vms"),
    path("containers/", views.LXCListView.as_view(), name="scanner-containers"),
]
