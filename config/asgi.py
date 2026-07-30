"""
ASGI config for config project.

SSE 流式端点通过拦截 send() 绕过 uvicorn 缓冲：
- 通过 receive.__self__.transport 获取真正的 transport 对象
- body chunk 直接写入 transport 并 flush，绕过 uvicorn 的 Response 缓冲
- 保留 Django 全部中间件
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

    if scope.get("type") == "http" and scope.get("path") == "/api/auth/chat/stream/":
        return await _sse_app(scope, receive, send, _django_app)

    return await _django_app(scope, receive, send)


def _get_transport(receive):
    """
    从 uvicorn 的 receive() 绑定方法获取 transport。
    receive.__self__ = RequestResponseCycle 实例，它持有 self.transport。
    """
    try:
        return receive.__self__.transport
    except AttributeError:
        return None


async def _sse_app(scope, receive, send, django_app):
    """
    SSE 端点包装器：
    1. Django 正常处理（中间件 + 鉴权 + view）
    2. http.response.start → 通过 send() 让 uvicorn 处理（状态码 + 头）
    3. http.response.body → 直接写入 transport 并 flush（绕过缓冲）
    """
    transport = _get_transport(receive)
    done = False

    async def send_wrapper(message):
        nonlocal done

        if message.get("type") == "http.response.start":
            if done:
                return
            # 让 uvicorn 处理响应头（状态码、Content-Type 等）
            await send(message)
            return

        if message.get("type") == "http.response.body":
            body = message.get("body", b"")
            more_body = message.get("more_body", True)

            if done:
                return

            if body and transport:
                # 直接写入 HTTP chunked 编码到 transport，绕过 uvicorn 缓冲
                chunk_line = f"{len(body):x}\r\n".encode()
                transport.write(chunk_line + body + b"\r\n")
                try:
                    await transport.flush()
                except Exception:
                    pass
            elif body:
                # transport 不可用时 fallback
                await send(message)

            if not more_body:
                if transport:
                    transport.write(b"0\r\n\r\n")
                    try:
                        await transport.flush()
                    except Exception:
                        pass
                done = True
            return

        await send(message)

    await django_app(scope, receive, send_wrapper)
