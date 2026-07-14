from django.urls import path

from . import views

urlpatterns = [
    path("login/", views.login_view, name="auth-login"),
    path("register/", views.register_view, name="auth-register"),
    path("user/", views.user_view, name="auth-user"),
    path("password-reset/", views.password_reset_view, name="auth-password-reset"),
    path("password-reset/confirm/", views.password_reset_confirm_view, name="auth-password-reset-confirm"),
    path("change-password/", views.change_password_view, name="auth-change-password"),
    path("create-admin-session/", views.create_admin_session_view, name="auth-create-admin-session"),
    path("logs/", views.user_logs_view, name="auth-user-logs"),
    path("cluster-logs/", views.cluster_logs_view, name="auth-cluster-logs"),
    path("registration-status/", views.registration_status_view, name="auth-registration-status"),
    
    # 管理员专用API
    path("admin/users/", views.AdminUserListView.as_view(), name="admin-user-list"),
    path("admin/users/<int:pk>/", views.AdminUserDetailView.as_view(), name="admin-user-detail"),
    path("admin/users/<int:user_id>/change-password/", views.admin_change_password_view, name="admin-change-password"),
    path("admin/users/<int:user_id>/toggle-active/", views.admin_toggle_user_active_view, name="admin-toggle-active"),
]
