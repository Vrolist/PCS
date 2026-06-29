from django.urls import path

from . import views

app_name = "agent_api"

urlpatterns = [
    path("register/", views.AgentRegisterView.as_view(), name="register"),
    path("heartbeat/", views.AgentHeartbeatView.as_view(), name="heartbeat"),
    path("scan/upload/", views.ScanUploadView.as_view(), name="scan-upload"),
    path("tasks/", views.AgentTasksView.as_view(), name="tasks"),
]
