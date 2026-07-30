"""
独立的 ASGI SSE 流式处理器。

绕过 Django 的 StreamingHttpResponse，直接通过 transport 写入数据并 flush，
确保每个 token 立即推送到浏览器，不受任何中间层缓冲影响。
"""

import asyncio
import json
import logging
import time

from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)


async def sse_chat_stream(scope, receive, send):
    """
    ASGI 应用：处理 /api/auth/chat/stream/ 的 SSE 流式响应。

    直接写入 transport，绕过 Django 和 uvicorn 的所有缓冲层。
    """

    # 只处理 POST
    if scope.get("method") != "POST":
        await _send_json(send, 405, {"detail": "Method not allowed"})
        return

    # 读取请求体
    body = b""
    while True:
        message = await receive()
        if message.get("type") == "http.disconnect":
            return
        if "body" in message:
            body += message["body"]
        if not message.get("more_body", False):
            break

    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        await _send_json(send, 400, {"detail": "无效的 JSON"})
        return


    # JWT 鉴权
    headers = dict(scope.get("headers", []))
    auth = headers.get(b"authorization", b"").decode()
    if not auth.startswith("Bearer "):
        await _send_json(send, 401, {"detail": "未授权"})
        return

    try:
        from rest_framework_simplejwt.tokens import AccessToken
        from apps.accounts.models import User, UserLLMConfig
        token = AccessToken(auth[7:])
        user = await sync_to_async(User.objects.get, thread_sensitive=True)(id=token["user_id"])
    except Exception as e:
        logger.warning(f"sse: token 解析失败: {e}")
        await _send_json(send, 401, {"detail": "token 无效"})
        return


    config_id = data.get("config_id")
    messages = data.get("messages", [])
    cluster_id = data.get("cluster_id")
    user_message = data.get("user_message", "")

    if not config_id or not messages:
        await _send_json(send, 400, {"detail": "缺少必要参数"})
        return

    try:
        config = await sync_to_async(UserLLMConfig.objects.get, thread_sensitive=True)(pk=config_id, user=user)
    except UserLLMConfig.DoesNotExist:
        await _send_json(send, 404, {"detail": "配置不存在"})
        return

    if not config.api_key:
        await _send_json(send, 400, {"detail": "未配置 API Key"})
        return

    # 构建 LLM
    from apps.accounts.chat_context import build_pve_context
    from apps.accounts.llm_service import build_llm, build_langchain_messages, stream_chat

    pve_context = await sync_to_async(build_pve_context, thread_sensitive=True)(cluster_id, user_message) if cluster_id else ""
    langchain_msgs = build_langchain_messages(messages, pve_context)
    llm = build_llm(config)

    # 发送 HTTP 响应头（SSE）
    await send({
        "type": "http.response.start",
        "status": 200,
        "headers": [
            [b"content-type", b"text/event-stream"],
            [b"cache-control", b"no-cache, no-store, must-revalidate"],
            [b"x-accel-buffering", b"no"],
            [b"access-control-allow-origin", b"*"],
            [b"connection", b"keep-alive"],
        ],
    })


    # 发送初始连接消息
    await _send_sse(send, ": connected\n\n")

    # 流式输出 LLM 响应（并发监听客户端断连）
    t0 = time.monotonic()
    token_count = 0
    disconnected = False
    stream_error = None

    async def _listen_disconnect():
        nonlocal disconnected
        while True:
            msg = await receive()
            if msg.get("type") == "http.disconnect":
                disconnected = True
                return

    async def _stream():
        nonlocal token_count, stream_error
        try:
            async for token in stream_chat(llm, langchain_msgs):
                if disconnected:
                    break
                token_count += 1
                elapsed = time.monotonic() - t0
                logger.debug(f"sse: token#{token_count} +{elapsed:.2f}s len={len(token)}")
                chunk = json.dumps(
                    {"choices": [{"delta": {"content": token}}]},
                    ensure_ascii=False,
                )
                await _send_sse(send, f"data: {chunk}\n\n")
        except Exception as e:
            stream_error = e
            logger.warning(f"sse: stream 异常 user={user.id} tokens={token_count} err={e}")
            err_chunk = json.dumps(
                {"choices": [{"delta": {"content": f"\n\n[错误: {e}]"}}]},
                ensure_ascii=False,
            )
            await _send_sse(send, f"data: {err_chunk}\n\n")

    try:
        # 并发运行：流式输出 + 监听断连
        stream_task = asyncio.ensure_future(_stream())
        disconnect_task = asyncio.ensure_future(_listen_disconnect())
        await asyncio.wait(
            [stream_task, disconnect_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        # 取消未完成的任务
        if not stream_task.done():
            stream_task.cancel()
            try:
                await stream_task
            except asyncio.CancelledError:
                pass
        if not disconnect_task.done():
            disconnect_task.cancel()
            try:
                await disconnect_task
            except asyncio.CancelledError:
                pass

        # 始终发送 [DONE] 保证 chunked 编码正常结束（more_body=False 终止流）
        try:
            await _send_sse_done(send, b"data: [DONE]\n\n")
        except Exception:
            pass

        elapsed = time.monotonic() - t0
        if disconnected:
            logger.info(f"sse: 客户端断连 user={user.id} tokens={token_count}")
        else:
            if stream_error:
                logger.warning(f"sse: 完成(有错误) user={user.id} tokens={token_count} elapsed={elapsed:.2f}s")
            else:
                logger.info(f"sse: 完成 user={user.id} tokens={token_count} elapsed={elapsed:.2f}s")
    except Exception as e:
        elapsed = time.monotonic() - t0
        logger.warning(f"sse: 失败 user={user.id} tokens={token_count} elapsed={elapsed:.2f}s err={e}")
        try:
            err_chunk = json.dumps(
                {"choices": [{"delta": {"content": f"\n\n[错误: {e}]"}}]},
                ensure_ascii=False,
            )
            await _send_sse(send, f"data: {err_chunk}\n\n")
            await _send_sse_done(send, b"data: [DONE]\n\n")
        except Exception:
            pass


async def _send_sse(send, data):
    """发送一个 SSE 数据块（流式中间帧）。"""
    body = data.encode("utf-8") if isinstance(data, str) else data
    await send({
        "type": "http.response.body",
        "body": body,
        "more_body": True,
    })


async def _send_sse_done(send, data=b""):
    """发送最后一帧并关闭 chunked 编码流（more_body=False）。"""
    await send({
        "type": "http.response.body",
        "body": data,
        "more_body": False,
    })


async def _send_json(send, status, data):
    """发送 JSON 响应（非流式）。"""
    body = json.dumps(data, ensure_ascii=False).encode()
    await send({
        "type": "http.response.start",
        "status": status,
        "headers": [
            [b"content-type", b"application/json"],
        ],
    })
    await send({
        "type": "http.response.body",
        "body": body,
        "more_body": False,
    })
