import logging

from django.shortcuts import render
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User, PasswordResetCode, UserLog
from .serializers import (
    LoginSerializer,
    RegisterSerializer,
    UserSerializer,
    PasswordResetSerializer,
    PasswordResetConfirmSerializer,
    ChangePasswordSerializer,
    UserLogSerializer,
)

logger = logging.getLogger(__name__)


def log_user_action(user, action, resource_type="", resource_id="", detail="", request=None):
    """记录用户操作日志"""
    UserLog.objects.create(
        user=user,
        username=user.username,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id else "",
        detail=detail,
        ip_address=request.META.get("REMOTE_ADDR") if request else None,
        user_agent=request.META.get("HTTP_USER_AGENT", "")[:512] if request else "",
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def change_password_view(request):
    """登录用户修改密码"""
    serializer = ChangePasswordSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    request.user.set_password(serializer.validated_data["new_password"])
    request.user.save()
    log_user_action(request.user, "change_password", request=request)
    return Response({"detail": "密码修改成功"})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_admin_session_view(request):
    """超级管理员点击「管理后台」时，创建 Django session 以便免登录进入 /admin/"""
    if not request.user.is_superuser:
        return Response({"detail": "无权限"}, status=status.HTTP_403_FORBIDDEN)
    from django.contrib.auth import login
    login(request, request.user)
    return Response({"detail": "session 已创建"})


def index(request):
    """Vue SPA 入口页"""
    return render(request, "vue_index.html")


@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.validated_data["user"]
    refresh = RefreshToken.for_user(user)
    log_user_action(user, "login", request=request)
    return Response({
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user": UserSerializer(user).data,
    })


@api_view(["POST"])
@permission_classes([AllowAny])
def register_view(request):
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    refresh = RefreshToken.for_user(user)
    log_user_action(user, "register", request=request)
    return Response({
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user": UserSerializer(user).data,
    }, status=status.HTTP_201_CREATED)


@api_view(["GET", "PATCH"])
def user_view(request):
    if request.method == "PATCH":
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
    return Response(UserSerializer(request.user).data)


@api_view(["POST"])
@permission_classes([AllowAny])
def password_reset_view(request):
    serializer = PasswordResetSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    email = serializer.validated_data["email"]
    user = User.objects.get(email=email)

    # 使该用户旧的未使用重置码失效
    PasswordResetCode.objects.filter(user=user, is_used=False).update(is_used=True)

    reset_code = PasswordResetCode.generate_for_user(user, email)

    # 开发环境打印到日志 / 控制台
    logger.info(f"[DEV] 密码重置验证码 for {email}: {reset_code.code}")

    return Response({
        "detail": "重置链接已发送到邮箱",
        # 开发环境直接返回 code，方便测试
        "dev_code": reset_code.code,
    })


@api_view(["POST"])
@permission_classes([AllowAny])
def password_reset_confirm_view(request):
    serializer = PasswordResetConfirmSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    reset_code = serializer.validated_data["reset_code"]
    new_password = serializer.validated_data["new_password"]

    user = reset_code.user
    user.set_password(new_password)
    user.save()

    reset_code.is_used = True
    reset_code.save()

    log_user_action(user, "reset_password", request=request)
    return Response({"detail": "密码重置成功"})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_logs_view(request):
    """获取当前用户的操作日志（分页）"""
    page_size = int(request.GET.get("page_size", 20))
    page = int(request.GET.get("page", 1))
    action = request.GET.get("action", "")

    queryset = UserLog.objects.filter(user=request.user)
    if action:
        queryset = queryset.filter(action=action)

    total = queryset.count()
    start = (page - 1) * page_size
    end = start + page_size
    logs = queryset[start:end]

    serializer = UserLogSerializer(logs, many=True)
    return Response({
        "count": total,
        "page": page,
        "page_size": page_size,
        "results": serializer.data,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def cluster_logs_view(request):
    """获取所有用户的集群操作日志（分页）"""
    page_size = int(request.GET.get("page_size", 20))
    page = int(request.GET.get("page", 1))
    action = request.GET.get("action", "")

    # 只查询集群相关的操作
    queryset = UserLog.objects.filter(resource_type="cluster")
    if action:
        queryset = queryset.filter(action=action)

    total = queryset.count()
    start = (page - 1) * page_size
    end = start + page_size
    logs = queryset[start:end]

    serializer = UserLogSerializer(logs, many=True)
    return Response({
        "count": total,
        "page": page,
        "page_size": page_size,
        "results": serializer.data,
    })
