import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: number
}

export interface LLMConfig {
  id: string
  name: string
  provider: 'openai' | 'deepseek' | 'kimi' | 'glm' | 'custom'
  apiKey: string
  model: string
  baseUrl: string
}

function genId(): string {
  return Math.random().toString(36).slice(2, 10)
}

const STORAGE_KEY = 'pcs_llm_configs'
const ACTIVE_KEY = 'pcs_llm_active_id'

function loadConfigs(): LLMConfig[] {
  try {
    // 兼容旧版单配置格式
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const parsed = JSON.parse(raw)
      if (Array.isArray(parsed)) return parsed
      // 旧版单对象 → 迁移
      if (parsed.provider) {
        const migrated: LLMConfig = {
          id: genId(),
          name: parsed.provider === 'custom' ? '自定义' : parsed.provider.charAt(0).toUpperCase() + parsed.provider.slice(1),
          provider: parsed.provider,
          apiKey: parsed.apiKey || '',
          model: parsed.model || 'deepseek-v4-pro',
          baseUrl: parsed.baseUrl || 'https://api.deepseek.com',
        }
        saveConfigs([migrated])
        return [migrated]
      }
    }
  } catch { /* ignore */ }
  return [defaultConfig()]
}

function saveConfigs(configs: LLMConfig[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(configs))
}

function loadActiveId(): string {
  try {
    return localStorage.getItem(ACTIVE_KEY) || ''
  } catch {
    return ''
  }
}

function saveActiveId(id: string) {
  localStorage.setItem(ACTIVE_KEY, id)
}

function defaultConfig(): LLMConfig {
  return {
    id: genId(),
    name: 'DeepSeek',
    provider: 'deepseek',
    apiKey: '',
    model: 'deepseek-v4-pro',
    baseUrl: 'https://api.deepseek.com',
  }
}

const BASE_URL_MAP: Record<string, string> = {
  deepseek: 'https://api.deepseek.com',
  kimi: 'https://api.moonshot.cn',
  glm: 'https://open.bigmodel.cn',
  openai: 'https://api.openai.com',
  custom: '',
}

export function createDefaultConfig(provider: LLMConfig['provider'] = 'deepseek'): LLMConfig {
  return {
    id: genId(),
    name: provider === 'custom' ? '自定义' : provider.charAt(0).toUpperCase() + provider.slice(1),
    provider,
    apiKey: '',
    model: provider === 'deepseek' ? 'deepseek-v4-pro'
      : provider === 'kimi' ? 'kimi-k3'
      : provider === 'glm' ? 'glm-5.2'
      : provider === 'openai' ? 'gpt-5.6-sol'
      : 'custom-model',
    baseUrl: BASE_URL_MAP[provider] || '',
  }
}

export const useChatStore = defineStore('chat', () => {
  const visible = ref(false)
  const messages = ref<ChatMessage[]>([])
  const loading = ref(false)
  const configs = ref<LLMConfig[]>(loadConfigs())
  const activeConfigId = ref(loadActiveId())
  const currentController = ref<AbortController | null>(null)

  // 如果没有有效的 activeConfigId，默认选中第一个
  if (!configs.value.find(c => c.id === activeConfigId.value) && configs.value.length > 0) {
    activeConfigId.value = configs.value[0].id
    saveActiveId(activeConfigId.value)
  }

  // 自动保存配置变更到 localStorage
  watch(configs, () => {
    saveConfigs(configs.value)
  }, { deep: true })

  const activeConfig = computed(() => {
    return configs.value.find(c => c.id === activeConfigId.value) || configs.value[0] || null
  })

  const hasApiKey = computed(() => !!activeConfig.value?.apiKey)

  function setActiveConfig(id: string) {
    if (configs.value.find(c => c.id === id)) {
      activeConfigId.value = id
      saveActiveId(id)
    }
  }

  function addConfig(config?: Partial<LLMConfig>) {
    const cfg = config
      ? { ...defaultConfig(), ...config, id: genId() }
      : defaultConfig()
    configs.value.push(cfg)
    saveConfigs(configs.value)
    return cfg
  }

  function updateConfig(id: string, data: Partial<LLMConfig>) {
    const idx = configs.value.findIndex(c => c.id === id)
    if (idx === -1) return
    configs.value[idx] = { ...configs.value[idx], ...data }
    saveConfigs(configs.value)
  }

  function removeConfig(id: string) {
    const idx = configs.value.findIndex(c => c.id === id)
    if (idx === -1) return
    configs.value.splice(idx, 1)
    if (activeConfigId.value === id) {
      activeConfigId.value = configs.value[0]?.id || ''
      if (activeConfigId.value) saveActiveId(activeConfigId.value)
      else localStorage.removeItem(ACTIVE_KEY)
    }
    saveConfigs(configs.value)
  }

  function openChat() {
    visible.value = true
  }

  function toggleChat() {
    visible.value = !visible.value
  }

  function clearMessages() {
    messages.value = []
  }

  async function sendMessage(content: string, clusterId?: number) {
    if (!content.trim() || loading.value) return
    const cfg = activeConfig.value
    if (!cfg || !cfg.apiKey) return

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
      const response = await fetch(`${cfg.baseUrl}/v1/chat/completions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${cfg.apiKey}`,
        },
        body: JSON.stringify({
          model: cfg.model,
          messages: [
            { role: 'system', content: systemPrompt },
            ...history,
            { role: 'user', content: content.trim() },
          ],
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
    configs,
    activeConfigId,
    activeConfig,
    hasApiKey,
    setActiveConfig,
    addConfig,
    updateConfig,
    removeConfig,
    openChat,
    toggleChat,
    clearMessages,
    sendMessage,
    stopGeneration,
  }
})
