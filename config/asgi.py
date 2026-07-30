"""
ASGI config for config project.

SSE 流式端点通过独立的 ASGI handler 实现，绕过 Django 主应用，
避免 uvicorn 缓冲 StreamingHttpResponse。
"""

import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

_django_app = None


async def application(scope, receive, send):
    """ASGI 入口"""
    global _django_app

    if _django_app is None:
        from django.core.asgi import get_asgi_application
        _django_app = get_asgi_application()

    # SSE 流式端点由独立的 ASGI handler 处理
    if scope.get("type") == "http" and scope.get("path") == "/api/auth/chat/stream/":
        from .sse_handler import sse_chat_stream
        return await sse_chat_stream(scope, receive, send)

    return await _django_app(scope, receive, send)
