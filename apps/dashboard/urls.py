from django.urls import path

from . import views
from .predictions import PredictionsView

urlpatterns = [
    path("stats/", views.StatsView.as_view(), name="dashboard-stats"),
    path("alerts/", views.AlertsView.as_view(), name="dashboard-alerts"),
    path("trends/", views.TrendsView.as_view(), name="dashboard-trends"),
    path("nodes/", views.NodesView.as_view(), name="dashboard-nodes"),
    path("predictions/", PredictionsView.as_view(), name="dashboard-predictions"),
]
