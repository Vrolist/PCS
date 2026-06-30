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
]
