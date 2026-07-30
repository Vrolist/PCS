"""
ASGI config for config project.

SSE 流式端点通过拦截 send() 绕过 Django 缓冲，
直接写入 transport 并强制 flush，实现真正的逐 token 推送。
同时保留 Django 的全部中间件（CORS、Session、CSRF 等）。
"""

import os
import logging

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

logger = logging.getLogger(__name__)

_django_app = None


async def application(scope, receive, send):
    """ASGI 入口"""
    global _django_app

    if _django_app is None:
        from django.core.asgi import get_asgi_application
        _django_app = get_asgi_application()

    # SSE 流式端点：拦截 send() 绕过缓冲
    if scope.get("type") == "http" and scope.get("path") == "/api/auth/chat/stream/":
        return await _sse_app(scope, receive, send, _django_app)

    return await _django_app(scope, receive, send)


async def _sse_app(scope, receive, send, django_app):
    """
    SSE 端点包装器：
    1. 让 Django 正常处理（中间件、鉴权、view 执行）
    2. http.response.start → 通过 send() 让 uvicorn 正确处理（状态码+头）
    3. http.response.body → 直接写入 transport 绕过 uvicorn 缓冲
    4. 完成后抑制 Django 的重复 send() 调用
    """
    transport = scope.get("transport")
    headers_sent = False
    done = False

    async def send_wrapper(message):
        nonlocal headers_sent, done

        if message.get("type") == "http.response.start":
            if done:
                return  # 已完成，抑制
            # 让 uvicorn 正确处理响应头（设置状态码、Content-Type 等）
            await send(message)
            headers_sent = True
            return

        if message.get("type") == "http.response.body":
            body = message.get("body", b"")
            more_body = message.get("more_body", True)

            if done:
                return  # 已完成，抑制

            if body:
                if transport:
                    # 直接写入 HTTP chunked 编码到 transport，绕过 uvicorn 缓冲
                    chunk_line = f"{len(body):x}\r\n".encode()
                    transport.write(chunk_line + body + b"\r\n")
                    if hasattr(transport, 'flush'):
                        try:
                            await transport.flush()
                        except Exception:
                            pass
                else:
                    # fallback：通过 uvicorn 发送（有缓冲但至少能工作）
                    await send(message)

            if not more_body:
                # 发送 chunked 终止符
                if transport:
                    transport.write(b"0\r\n\r\n")
                    if hasattr(transport, 'flush'):
                        try:
                            await transport.flush()
                        except Exception:
                            pass
                done = True
            return

        # 其他消息类型正常传递
        await send(message)

    # 运行 Django 应用，使用包装后的 send
    await django_app(scope, receive, send_wrapper)
