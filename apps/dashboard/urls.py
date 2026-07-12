from django.urls import path

from . import views
from .predictions import PredictionsView
from .health_report import HealthReportView
from .dr_score import DRScoreView
from .compliance import ComplianceReportView
from .correlation import CorrelationView

urlpatterns = [
    path("stats/", views.StatsView.as_view(), name="dashboard-stats"),
    path("alerts/", views.AlertsView.as_view(), name="dashboard-alerts"),
    path("trends/", views.TrendsView.as_view(), name="dashboard-trends"),
    path("nodes/", views.NodesView.as_view(), name="dashboard-nodes"),
    path("predictions/", PredictionsView.as_view(), name="dashboard-predictions"),
    path("health-report/", HealthReportView.as_view(), name="dashboard-health-report"),
    path("dr-score/", DRScoreView.as_view(), name="dashboard-dr-score"),
    path("compliance/", ComplianceReportView.as_view(), name="dashboard-compliance"),
    path("correlation/", CorrelationView.as_view(), name="dashboard-correlation"),
]
