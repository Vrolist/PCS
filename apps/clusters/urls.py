from django.urls import path

from . import views

app_name = "clusters"

urlpatterns = [
    path("", views.ClusterListCreateView.as_view(), name="list-create"),
    path("<int:pk>/", views.ClusterDetailView.as_view(), name="detail"),
]
