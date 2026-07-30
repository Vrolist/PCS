"""
LangChain LLM 服务封装
统一管理 LLM 实例构建、消息转换、流式调用。
"""

import logging
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)


def build_llm(config):
    """
    从 UserLLMConfig 构建 LangChain ChatOpenAI 实例。

    所有 OpenAI 兼容 API（DeepSeek / Kimi / GLM / Ollama 等）均通过
    ChatOpenAI 统一接入，只需配置 base_url + api_key + model。
    """
    base_url = config.base_url.rstrip('/')
    # ChatOpenAI 自动拼接 /v1/chat/completions，所以传入的 base_url
    # 应该是域名根路径（如 https://api.deepseek.com）。
    # 如果用户配置了 https://xxx/v1，去掉末尾的 /v1。
    if base_url.endswith('/v1'):
        base_url = base_url[:-3]

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

    用法：
        async for token in stream_chat(llm, messages):
            print(token)
    """
    async for chunk in llm.astream(messages):
        if chunk.content:
            yield chunk.content
