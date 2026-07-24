import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: number
}

export interface LLMConfig {
  provider: 'openai' | 'deepseek' | 'custom'
  apiKey: string
  model: string
  baseUrl: string
  temperature: number
  maxTokens: number
}

function loadConfig(): LLMConfig {
  try {
    const saved = localStorage.getItem('pcs_llm_config')
    if (saved) return JSON.parse(saved)
  } catch { /* ignore */ }
  return {
    provider: 'deepseek',
    apiKey: '',
    model: 'deepseek-chat',
    baseUrl: 'https://api.deepseek.com',
    temperature: 0.7,
    maxTokens: 2048,
  }
}

function saveConfigLocal(config: LLMConfig) {
  localStorage.setItem('pcs_llm_config', JSON.stringify(config))
}

export const useChatStore = defineStore('chat', () => {
  const visible = ref(false)
  const messages = ref<ChatMessage[]>([])
  const loading = ref(false)
  const config = ref<LLMConfig>(loadConfig())
  const currentController = ref<AbortController | null>(null)

  function openChat() {
    visible.value = true
  }

  function toggleChat() {
    visible.value = !visible.value
  }

  function updateConfig(newConfig: LLMConfig) {
    config.value = newConfig
    saveConfigLocal(newConfig)
  }

  function clearMessages() {
    messages.value = []
  }

  async function sendMessage(content: string, clusterId?: number) {
    if (!content.trim() || loading.value) return

    // 用户消息
    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: content.trim(),
      timestamp: Date.now(),
    }
    messages.value.push(userMsg)

    // 助手占位
    const assistantMsg: ChatMessage = {
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
    }
    messages.value.push(assistantMsg)
    loading.value = true

    // 构建上下文消息
    const history = messages.value.slice(0, -2).map(m => ({
      role: m.role,
      content: m.content,
    }))

    // 系统提示
    const systemPrompt = buildSystemPrompt(clusterId)

    const controller = new AbortController()
    currentController.value = controller

    try {
      const response = await fetch(`${config.value.baseUrl}/v1/chat/completions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${config.value.apiKey}`,
        },
        body: JSON.stringify({
          model: config.value.model,
          messages: [
            { role: 'system', content: systemPrompt },
            ...history,
            { role: 'user', content: content.trim() },
          ],
          temperature: config.value.temperature,
          max_tokens: config.value.maxTokens,
          stream: true,
        }),
        signal: controller.signal,
      })

      if (!response.ok) {
        const errBody = await response.text()
        assistantMsg.content = `请求失败 (${response.status})：${errBody.slice(0, 200)}`
        return
      }

      const reader = response.body!.getReader()
      const decoder = new TextDecoder()

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value, { stream: true })
        const lines = chunk.split('\n')

        for (const line of lines) {
          const trimmed = line.trim()
          if (!trimmed || !trimmed.startsWith('data: ')) continue
          const data = trimmed.slice(6)
          if (data === '[DONE]') return
          try {
            const parsed = JSON.parse(data)
            const delta = parsed.choices?.[0]?.delta?.content
            if (delta) {
              assistantMsg.content += delta
            }
          } catch { /* skip malformed */ }
        }
      }
    } catch (err: any) {
      if (err.name === 'AbortError') {
        assistantMsg.content += '\n\n*[已停止]*'
      } else {
        assistantMsg.content = `连接失败：${err.message}。请检查 API 配置。`
      }
    } finally {
      loading.value = false
      currentController.value = null
    }
  }

  function stopGeneration() {
    currentController.value?.abort()
    currentController.value = null
    loading.value = false
  }

  function buildSystemPrompt(clusterId?: number): string {
    const base = `你是 PCS (PveClusterScan) 平台的 AI 运维助手。你的职责是帮助用户分析 Proxmox VE 集群状态，提供运维建议。

你可以分析以下数据：
- 节点状态（CPU、内存、磁盘、网络）
- 虚拟机和容器的资源使用情况
- 存储容量与性能
- Ceph 分布式存储健康状态
- HA 高可用资源配置
- SDN 软件定义网络配置
- 网络拓扑与接口信息

回答要求：
- 使用中文回复
- 用简洁清晰的语言给出分析和建议
- 对于异常数据，给出可能的原因和解决方案
- 适当使用 Markdown 格式增强可读性
- 如果用户问的问题超出 PVE 运维范围，礼貌告知并引导回到运维话题`

    if (clusterId) {
      return `${base}\n\n当前用户正在查看集群 ID: ${clusterId}。如果有该集群的上下文数据，请结合分析。`
    }
    return base
  }

  return {
    visible,
    messages,
    loading,
    config,
    openChat,
    toggleChat,
    updateConfig,
    clearMessages,
    sendMessage,
    stopGeneration,
  }
})
