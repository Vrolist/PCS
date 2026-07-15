import logging

from django.shortcuts import render
from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User, PasswordResetCode, UserLog, SystemConfig
from .serializers import (
    LoginSerializer,
    RegisterSerializer,
    UserSerializer,
    PasswordResetSerializer,
    PasswordResetConfirmSerializer,
    ChangePasswordSerializer,
    UserLogSerializer,
    AdminUserCreateSerializer,
    AdminUserUpdateSerializer,
    AdminChangePasswordSerializer,
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
    # 检查是否允许注册（从数据库读取，可运行时修改）
    if SystemConfig.get('ALLOW_REGISTRATION', 'True') != 'True':
        return Response({"detail": "注册功能已关闭"}, status=status.HTTP_403_FORBIDDEN)
    
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


class IsSuperUser(IsAuthenticated):
    """仅允许超级管理员"""
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.is_superuser


class AdminUserListView(generics.ListCreateAPIView):
    """GET /api/auth/admin/users/ - 获取用户列表（仅超级管理员）
    POST /api/auth/admin/users/ - 创建用户（仅超级管理员）
    """
    permission_classes = [IsSuperUser]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return AdminUserCreateSerializer
        return UserSerializer

    queryset = User.objects.all().order_by('-date_joined')

    def perform_create(self, serializer):
        user = serializer.save()
        log_user_action(self.request.user, "create", "user", user.id,
                        f"管理员创建用户 {user.username}", self.request)


class AdminUserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET/PUT/PATCH/DELETE /api/auth/admin/users/<id>/ - 用户详情（仅超级管理员）"""
    permission_classes = [IsSuperUser]
    serializer_class = AdminUserUpdateSerializer
    queryset = User.objects.all()

    def perform_destroy(self, instance):
        if instance.is_superuser:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("不能删除超级管理员")
        if instance.id == self.request.user.id:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("不能删除自己")
        log_user_action(self.request.user, "delete", "user", instance.id,
                        f"管理员删除用户 {instance.username}", self.request)
        instance.delete()


@api_view(["POST"])
@permission_classes([IsSuperUser])
def admin_change_password_view(request, user_id):
    """POST /api/auth/admin/users/<id>/change-password/ - 管理员修改用户密码"""
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({"detail": "用户不存在"}, status=status.HTTP_404_NOT_FOUND)
    
    serializer = AdminChangePasswordSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user.set_password(serializer.validated_data["new_password"])
    user.save()
    log_user_action(request.user, "admin_change_password", "user", user_id,
                    f"管理员修改用户 {user.username} 的密码", request)
    return Response({"detail": "密码修改成功"})


@api_view(["POST"])
@permission_classes([IsSuperUser])
def admin_toggle_user_active_view(request, user_id):
    """POST /api/auth/admin/users/<id>/toggle-active/ - 启用/禁用用户"""
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({"detail": "用户不存在"}, status=status.HTTP_404_NOT_FOUND)
    
    if user.is_superuser:
        return Response({"detail": "不能禁用超级管理员"}, status=status.HTTP_400_BAD_REQUEST)
    
    user.is_active = not user.is_active
    user.save()
    action = "启用" if user.is_active else "禁用"
    log_user_action(request.user, "admin_toggle_user", "user", user_id,
                    f"管理员{action}用户 {user.username}", request)
    return Response({"detail": f"用户已{action}", "is_active": user.is_active})


@api_view(["GET"])
@permission_classes([AllowAny])
def registration_status_view(request):
    """GET /api/auth/registration-status/ - 检查是否允许注册"""
    enabled = SystemConfig.get('ALLOW_REGISTRATION', 'True') == 'True'
    return Response({"enabled": enabled})


@api_view(["POST"])
@permission_classes([IsSuperUser])
def toggle_registration_view(request):
    """POST /api/auth/toggle-registration/ - 切换注册开关（立即生效）"""
    current = SystemConfig.get('ALLOW_REGISTRATION', 'True')
    new_value = 'False' if current == 'True' else 'True'
    SystemConfig.set('ALLOW_REGISTRATION', new_value)
    enabled = new_value == 'True'
    log_user_action(request.user, "update", "system", "", f"注册开关已{'开启' if enabled else '关闭'}", request)
    return Response({"detail": f"注册功能已{'开启' if enabled else '关闭'}", "enabled": enabled})
