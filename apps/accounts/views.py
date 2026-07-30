import logging
import json
import time

import requests as http_requests
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import StreamingHttpResponse, JsonResponse
from django.shortcuts import render
from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken

from .models import User, PasswordResetCode, UserLog, SystemConfig, UserLLMConfig, ChatConversation, ChatMessage, UserSystemPrompt, DEFAULT_SYSTEM_PROMPT
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
    UserLLMConfigSerializer,
    ChatConversationSerializer,
    ChatConversationListSerializer,
    ChatMessageSerializer,
    UserSystemPromptSerializer,
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


# ---- LLM 配置 CRUD ----

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def llm_config_list_view(request):
    """GET/POST /api/auth/llm-configs/"""
    if request.method == "GET":
        qs = UserLLMConfig.objects.filter(user=request.user)
        serializer = UserLLMConfigSerializer(qs, many=True)
        return Response(serializer.data)

    # POST
    serializer = UserLLMConfigSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    serializer.save(user=request.user)
    log_user_action(request.user, "create", "llm_config", "", f"新增 LLM 配置: {serializer.data.get('name')}", request)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def llm_config_detail_view(request, pk):
    """PATCH/DELETE /api/auth/llm-configs/:id/"""
    try:
        config = UserLLMConfig.objects.get(pk=pk, user=request.user)
    except UserLLMConfig.DoesNotExist:
        return Response({"detail": "配置不存在"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "DELETE":
        config.delete()
        log_user_action(request.user, "delete", "llm_config", str(pk), "删除 LLM 配置", request)
        return Response(status=status.HTTP_204_NO_CONTENT)

    # PATCH
    serializer = UserLLMConfigSerializer(config, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    log_user_action(request.user, "update", "llm_config", str(pk), f"更新 LLM 配置: {serializer.data.get('name')}", request)
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def llm_config_set_active_view(request, pk):
    """POST /api/auth/llm-configs/:id/set-active/ - 设为当前选中"""
    try:
        config = UserLLMConfig.objects.get(pk=pk, user=request.user)
    except UserLLMConfig.DoesNotExist:
        return Response({"detail": "配置不存在"}, status=status.HTTP_404_NOT_FOUND)

    # 该用户所有配置 is_active 设为 False
    UserLLMConfig.objects.filter(user=request.user).update(is_active=False)
    config.is_active = True
    config.save(update_fields=["is_active"])
    return Response({"detail": "已设为当前配置", "id": config.pk})


# ---- AI 助手对话 CRUD ----

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def chat_conversation_list_view(request):
    """GET/POST /api/auth/chat/conversations/"""
    if request.method == "GET":
        qs = ChatConversation.objects.filter(user=request.user)
        serializer = ChatConversationListSerializer(qs, many=True)
        return Response(serializer.data)

    # POST - 创建新对话
    serializer = ChatConversationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    serializer.save(user=request.user)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def chat_conversation_detail_view(request, pk):
    """GET/PATCH/DELETE /api/auth/chat/conversations/:id/"""
    try:
        conv = ChatConversation.objects.get(pk=pk, user=request.user)
    except ChatConversation.DoesNotExist:
        return Response({"detail": "对话不存在"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        serializer = ChatConversationSerializer(conv)
        return Response(serializer.data)

    if request.method == "DELETE":
        conv.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # PATCH - 重命名
    serializer = ChatConversationSerializer(conv, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def chat_message_create_view(request, pk):
    """POST /api/auth/chat/conversations/:id/messages/ - 添加消息"""
    try:
        conv = ChatConversation.objects.get(pk=pk, user=request.user)
    except ChatConversation.DoesNotExist:
        return Response({"detail": "对话不存在"}, status=status.HTTP_404_NOT_FOUND)

    serializer = ChatMessageSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    serializer.save(conversation=conv)

    # 如果是第一条用户消息，自动用其内容生成标题
    if conv.messages.count() == 1 and not conv.title:
        content = serializer.validated_data.get('content', '')
        conv.title = content[:50]
        conv.save(update_fields=['title'])

    return Response(serializer.data, status=status.HTTP_201_CREATED)


# ---- 角色约束 CRUD ----

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def system_prompt_list_view(request):
    """GET/POST /api/auth/system-prompts/"""
    if request.method == "GET":
        # 如果没有约束，自动创建默认约束
        qs = UserSystemPrompt.objects.filter(user=request.user)
        if not qs.exists():
            UserSystemPrompt.objects.create(
                user=request.user,
                name="PVE 运维助手",
                content=DEFAULT_SYSTEM_PROMPT,
                is_default=True,
            )
            qs = UserSystemPrompt.objects.filter(user=request.user)
        serializer = UserSystemPromptSerializer(qs, many=True)
        return Response(serializer.data)

    # POST
    serializer = UserSystemPromptSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    serializer.save(user=request.user)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def system_prompt_detail_view(request, pk):
    """PATCH/DELETE /api/auth/system-prompts/:id/"""
    try:
        prompt = UserSystemPrompt.objects.get(pk=pk, user=request.user)
    except UserSystemPrompt.DoesNotExist:
        return Response({"detail": "约束不存在"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "DELETE":
        prompt.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # PATCH
    serializer = UserSystemPromptSerializer(prompt, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


# ============================================================
# LLM 流式代理
# ============================================================

@csrf_exempt
@require_http_methods(["POST"])
def chat_stream_view(request):
    """
    POST /api/auth/chat/stream/
    纯 Django 视图（无 DRF 装饰器），避免 DRF + ASGI 下的 StreamingHttpResponse 兼容问题。
    后端代理 LLM 请求，注入 PVE 数据上下文，流式返回响应。
    """
    # 手动解析 JSON 请求体
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"detail": "无效的 JSON"}, status=400)

    # 手动 JWT 鉴权
    auth = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth.startswith('Bearer '):
        return JsonResponse({"detail": "未授权"}, status=401)
    try:
        token = AccessToken(auth[7:])
        user = User.objects.get(id=token['user_id'])
    except Exception:
        return JsonResponse({"detail": "token 无效"}, status=401)

    config_id = data.get('config_id')
    messages = data.get('messages', [])
    cluster_id = data.get('cluster_id')
    user_message = data.get('user_message', '')

    if not config_id or not messages:
        return JsonResponse({"detail": "缺少必要参数"}, status=400)

    # 获取 LLM 配置
    try:
        config = UserLLMConfig.objects.get(pk=config_id, user=user)
    except UserLLMConfig.DoesNotExist:
        return JsonResponse({"detail": "配置不存在"}, status=404)

    api_key = config.api_key
    if not api_key:
        return JsonResponse({"detail": "未配置 API Key"}, status=400)

    # 注入 PVE 数据上下文到 system prompt
    from .chat_context import build_pve_context
    pve_context = build_pve_context(cluster_id, user_message) if cluster_id else ''

    if pve_context:
        enhanced_messages = _inject_context(messages, pve_context)
    else:
        enhanced_messages = messages

    # 构建 LLM API URL
    base_url = config.base_url.rstrip('/')
    api_path = '/chat/completions' if base_url.endswith('/v1') else '/v1/chat/completions'
    llm_url = f"{base_url}{api_path}"

    # 转发请求到 LLM API（流式）
    try:
        llm_response = http_requests.post(
            llm_url,
            json={
                "model": config.model,
                "messages": enhanced_messages,
                "stream": True,
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            stream=True,
            timeout=120,
        )
    except http_requests.exceptions.RequestException as e:
        logger.warning(f"chat stream: LLM 连接失败 (user {user.id}): {e}")
        return JsonResponse({"detail": f"连接 LLM 失败: {str(e)}"}, status=502)

    if llm_response.status_code != 200:
        err_body = llm_response.text[:500]
        logger.warning(f"chat stream: LLM 返回错误 (user {user.id}): {llm_response.status_code}")
        return JsonResponse(
            {"detail": f"LLM 返回错误 ({llm_response.status_code}): {err_body}"},
            status=llm_response.status_code,
        )

    # 流式透传 — 使用 iter_lines() 高效按行读取 + 心跳保活
    KEEPALIVE_INTERVAL = 15  # 每 15 秒发送一次心跳

    def generate():
        try:
            # 立即 yield → 发送 HTTP 200 + 建立 SSE 连接
            yield ": connected\n\n"

            last_yield = time.time()
            line_iter = llm_response.iter_lines(decode_unicode=True)

            while True:
                # 带超时的行读取（用 time 模拟非阻塞）
                try:
                    line = next(line_iter)
                except StopIteration:
                    break

                if not line:
                    # 心跳保活：如果距上次发送数据超过 KEEPALIVE_INTERVAL 秒，发送注释行
                    now = time.time()
                    if now - last_yield >= KEEPALIVE_INTERVAL:
                        yield ": keepalive\n\n"
                        last_yield = now
                    continue

                # SSE data 行 → 直接透传
                yield f"{line}\n\n"
                last_yield = time.time()

            yield "data: [DONE]\n\n"
            logger.info(f"chat stream: 完成 (user {user.id})")
        except GeneratorExit:
            logger.warning(f"chat stream: 客户端断开 (user {user.id})")
        except Exception:
            logger.exception(f"chat stream: 流式处理异常 (user {user.id})")
            try:
                yield "data: [DONE]\n\n"
            except GeneratorExit:
                pass

    response = StreamingHttpResponse(generate(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['X-Accel-Buffering'] = 'no'
    response['Access-Control-Allow-Origin'] = '*'
    return response


def _inject_context(messages, pve_context):
    """将 PVE 数据上下文注入到 system prompt 中"""
    enhanced = []
    context_block = f"\n\n--- 当前集群实时数据 ---\n{pve_context}\n--- 数据结束 ---\n"

    for msg in messages:
        if msg.get('role') == 'system':
            enhanced.append({
                'role': 'system',
                'content': msg['content'] + context_block,
            })
        else:
            enhanced.append(msg)

    # 如果没有 system message，在最前面插入
    if not any(m.get('role') == 'system' for m in enhanced):
        enhanced.insert(0, {
            'role': 'system',
            'content': f"你是 PCS 平台的 AI 运维助手。{context_block}",
        })

    return enhanced
