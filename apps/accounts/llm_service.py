"""
LangChain LLM 服务封装
统一管理 LLM 实例构建、消息转换、流式调用。
"""

import logging
import time

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)


def build_llm(config):
    """
    从 UserLLMConfig 构建 LangChain ChatOpenAI 实例。

    所有 OpenAI 兼容 API（DeepSeek / Kimi / GLM / Ollama / MiMo 等）均通过
    ChatOpenAI 统一接入，只需配置 base_url + api_key + model。

    OpenAI 客户端会在 base_url 后拼接 /chat/completions，因此 base_url
    需要以 /v1 结尾（例如 https://api.xxx.com/v1）。如果用户只填了域名，
    自动补全 /v1，与前端的连接测试保持一致。
    """
    base_url = config.base_url.rstrip('/')
    if base_url and not base_url.endswith('/v1'):
        base_url = base_url + '/v1'

    return ChatOpenAI(
        api_key=config.api_key,
        base_url=base_url,
        model=config.model,
        streaming=True,
        timeout=120,
        max_retries=1,
    )


def build_langchain_messages(raw_messages, pve_context=''):
    """
    将前端传来的 dict 列表转为 LangChain 消息对象列表。
    如果有 pve_context，注入到 system message 末尾。
    """
    messages = []
    context_block = f"\n\n--- 当前集群实时数据 ---\n{pve_context}\n--- 数据结束 ---\n" if pve_context else ''

    for msg in raw_messages:
        role = msg.get('role', '')
        content = msg.get('content', '')

        if role == 'system':
            if pve_context:
                content += context_block
            messages.append(SystemMessage(content=content))
        elif role == 'assistant':
            messages.append(AIMessage(content=content))
        elif role == 'user':
            messages.append(HumanMessage(content=content))

    # 如果没有 system message 且有 PVE 上下文，在最前面插入
    if not any(isinstance(m, SystemMessage) for m in messages) and pve_context:
        messages.insert(0, SystemMessage(
            content=f"你是 PCS 平台的 AI 运维助手。{context_block}"
        ))

    return messages


async def stream_chat(llm, messages):
    """
    异步流式调用 LLM，yield 每个 token 字符串。

    支持 DeepSeek 等推理模型的 reasoning_content，实时透传思考过程，
    避免用户在前 N 秒看不到任何输出而产生"卡住"错觉。

    用法：
        async for token in stream_chat(llm, messages):
            print(token)
    """
    _t0 = time.monotonic()
    chunk_index = 0
    try:
        async for chunk in llm.astream(messages):
            chunk_index += 1
            elapsed = time.monotonic() - _t0
            content = getattr(chunk, "content", "") or ""

            # DeepSeek / 部分 OpenAI 兼容接口会在 additional_kwargs 或
            # response_metadata 中返回 reasoning_content。
            reasoning_content = ""
            additional_kwargs = getattr(chunk, "additional_kwargs", None)
            if isinstance(additional_kwargs, dict):
                reasoning_content = additional_kwargs.get("reasoning_content", "") or ""
            if not reasoning_content:
                response_metadata = getattr(chunk, "response_metadata", None)
                if isinstance(response_metadata, dict):
                    reasoning_content = response_metadata.get("reasoning_content", "") or ""


            if reasoning_content:
                # 用 <think> 标记包裹思考过程，前端会渲染为可折叠区块
                yield f"<think>{reasoning_content}</think>"
            if content:
                yield content
    except Exception as e:
        raise


async def stream_chat_with_tools(llm, messages, cluster_id):
    """
    流式调用 LLM，支持 Tool Calling 按需查询 PVE 数据。

    两轮制：
    - Round 1: 非流式 invoke，LLM 决定是否调用工具
    - Round 2: 流式输出最终回答（含工具执行结果）

    如果 LLM 不支持 tool calling 或调用失败，自动降级为普通流式。
    """
    if not cluster_id:
        logger.info("tool calling: 无 cluster_id，降级为普通流式")
        async for token in stream_chat(llm, messages):
            yield token
        return

    from .llm_tools import make_pve_tools
    from langchain_core.messages import ToolMessage

    tools = make_pve_tools(cluster_id)
    llm_with_tools = llm.bind_tools(tools)

    # Round 1: LLM 决定是否调用工具
    try:
        response = await llm_with_tools.ainvoke(messages)
    except Exception as e:
        logger.warning(f"tool calling round 1 失败，降级为普通流式: {e}")
        async for token in stream_chat(llm, messages):
            yield token
        return

    if not response.tool_calls:
        # 没有工具调用，直接输出 LLM 的回答
        if response.content:
            yield response.content
        return

    # 将包含 tool_calls 的 assistant 回复加入消息历史
    messages.append(response)

    # 执行工具调用
    tool_names = [t.name for t in tools]
    for tc in response.tool_calls:
        tool_fn = next((t for t in tools if t.name == tc["name"]), None)
        if not tool_fn:
            logger.warning(f"tool calling: 未知工具 {tc['name']}，可用工具: {tool_names}")
            messages.append(ToolMessage(
                content=f"[工具不存在: {tc['name']}。可用工具: {', '.join(tool_names)}]",
                tool_call_id=tc["id"],
            ))
            continue

        try:
            logger.info(f"tool calling: 执行 {tc['name']}({tc['args']})")
            result = await tool_fn.ainvoke(tc["args"])
            messages.append(ToolMessage(content=result, tool_call_id=tc["id"]))
        except Exception as e:
            logger.warning(f"tool calling: {tc['name']} 执行失败: {e}")
            messages.append(ToolMessage(
                content=f"[工具执行错误: {e}]",
                tool_call_id=tc["id"],
            ))

    # Round 2: 流式输出最终回答
    try:
        async for chunk in llm.astream(messages):
            # 同样支持 reasoning_content 透传
            content = getattr(chunk, "content", "") or ""
            reasoning_content = ""
            additional_kwargs = getattr(chunk, "additional_kwargs", None)
            if isinstance(additional_kwargs, dict):
                reasoning_content = additional_kwargs.get("reasoning_content", "") or ""
            if not reasoning_content:
                response_metadata = getattr(chunk, "response_metadata", None)
                if isinstance(response_metadata, dict):
                    reasoning_content = response_metadata.get("reasoning_content", "") or ""

            if reasoning_content:
                yield f" thinking{reasoning_content} response"
            if content:
                yield content
    except Exception as e:
        logger.warning(f"tool calling round 2 流式失败: {e}")
        yield f"\n\n[错误: {e}]"
