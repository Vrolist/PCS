from django.urls import path

from . import views

app_name = "agent_api"

urlpatterns = [
    # Agent 通信
    path("register/", views.AgentRegisterView.as_view(), name="register"),
    path("heartbeat/", views.AgentHeartbeatView.as_view(), name="heartbeat"),
    path("scan/upload/", views.ScanUploadView.as_view(), name="scan-upload"),
    path("tasks/", views.AgentTasksView.as_view(), name="tasks"),
    path("unregister/", views.AgentUnregisterView.as_view(), name="unregister"),
    # 版本与安装
    path("version/", views.AgentVersionView.as_view(), name="version"),
    path("pve-info/", views.AgentPVEInfoView.as_view(), name="pve-info"),
    path("install.sh", views.AgentInstallScriptView.as_view(), name="install-script"),
    # Agent 事件与实例管理
    path("events/", views.AgentEventListView.as_view(), name="events"),
    path("instances/", views.AgentInstanceListView.as_view(), name="instances"),
]
