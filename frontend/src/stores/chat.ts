import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import axios from 'axios'
import { fetchLLMConfigs, createLLMConfig, updateLLMConfig, deleteLLMConfig } from '@/api/llm'
import {
  fetchConversations,
  createConversation,
  fetchConversation,
  deleteConversation as apiDeleteConversation,
  createMessage,
} from '@/api/chat'
import {
  fetchSystemPrompts,
  createSystemPrompt,
  updateSystemPrompt,
  deleteSystemPrompt as apiDeletePrompt,
} from '@/api/system-prompt'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: number
}

export interface LLMConfig {
  id: number
  name: string
  provider: 'openai' | 'deepseek' | 'kimi' | 'glm' | 'mimo' | 'custom'
  billingMode: string
  apiKey: string
  hasKey: boolean
  model: string
  baseUrl: string
}

export interface ConversationItem {
  id: number
  title: string
  message_count: number
  created_at: string
  updated_at: string
}

export interface SystemPromptItem {
  id: number
  name: string
  content: string
  is_default: boolean
}

const LAYOUT_KEY = 'pcs_chat_layout'
const VISIBLE_KEY = 'pcs_chat_visible'


function loadVisible(): boolean {
  try { return localStorage.getItem(VISIBLE_KEY) === 'true' } catch { return false }
}
function saveVisible(v: boolean) { localStorage.setItem(VISIBLE_KEY, String(v)) }

function loadLayoutMode(): 'float' | 'sidebar' {
  try {
    const v = localStorage.getItem(LAYOUT_KEY)
    if (v === 'float' || v === 'sidebar') return v
  } catch { /* ignore */ }
  return 'float'
}

function saveLayoutMode(mode: 'float' | 'sidebar') {
  localStorage.setItem(LAYOUT_KEY, mode)
}

// 用户自定义聊天面板尺寸
const FLOAT_W_KEY = 'pcs_chat_float_w'
const FLOAT_H_KEY = 'pcs_chat_float_h'
const SIDEBAR_W_KEY = 'pcs_chat_sidebar_w'

function loadFloatWidth(): number {
  try { const v = localStorage.getItem(FLOAT_W_KEY); return v ? Number(v) : 420 } catch { return 420 }
}
function saveFloatWidth(v: number) { localStorage.setItem(FLOAT_W_KEY, String(v)) }
function loadFloatHeight(): number {
  try { const v = localStorage.getItem(FLOAT_H_KEY); return v ? Number(v) : 600 } catch { return 600 }
}
function saveFloatHeight(v: number) { localStorage.setItem(FLOAT_H_KEY, String(v)) }
function loadSidebarWidth(): number {
  try { const v = localStorage.getItem(SIDEBAR_W_KEY); return v ? Number(v) : 420 } catch { return 420 }
}
function saveSidebarWidth(v: number) { localStorage.setItem(SIDEBAR_W_KEY, String(v)) }

const BASE_URL_MAP: Record<string, string> = {
  deepseek: 'https://api.deepseek.com',
  kimi: 'https://api.moonshot.cn',
  glm: 'https://open.bigmodel.cn',
  openai: 'https://api.openai.com',
  custom: '',
}

export function createDefaultConfig(provider: LLMConfig['provider'] = 'deepseek'): Omit<LLMConfig, 'id'> {
  return {
    name: provider === 'custom' ? '自定义' : provider === 'mimo' ? 'MiMo' : provider.charAt(0).toUpperCase() + provider.slice(1),
    provider,
    billingMode: provider === 'mimo' ? 'payg' : '',
    apiKey: '',
    hasKey: false,
    model: provider === 'deepseek' ? 'deepseek-v4-pro'
      : provider === 'kimi' ? 'kimi-k3'
      : provider === 'glm' ? 'glm-5.2'
      : provider === 'openai' ? 'gpt-5.6-sol'
      : provider === 'mimo' ? 'mimo-v2.5-pro'
      : 'custom-model',
    baseUrl: BASE_URL_MAP[provider] || '',
  }
}

export const useChatStore = defineStore('chat', () => {
  const visible = ref(loadVisible())
  const messages = ref<ChatMessage[]>([])
  const loading = ref(false)
  const configs = ref<LLMConfig[]>([])
  const currentController = ref<AbortController | null>(null)
  const layoutMode = ref<'float' | 'sidebar'>(loadLayoutMode())
  const floatWidth = ref(loadFloatWidth())
  const floatHeight = ref(loadFloatHeight())
  const sidebarWidth = ref(loadSidebarWidth())
  const configLoading = ref(false)
  const configLoaded = ref(false)

  // 对话管理
  const conversations = ref<ConversationItem[]>([])
  const currentConversationId = ref<number | null>(null)

  // 角色约束管理
  const prompts = ref<SystemPromptItem[]>([])
  const promptsLoaded = ref(false)

  // 本地暂存：AI 助手中用户选择的模型和约束（不保存到后端，仅存 localStorage）
  const CHAT_SELECTED_CONFIG_KEY = 'pcs_chat_selected_config'
  const CHAT_SELECTED_PROMPT_KEY = 'pcs_chat_selected_prompt'
  const chatSelectedConfigId = ref<number | null>(loadChatSelectedConfigId())
  const chatSelectedPromptId = ref<number | null>(loadChatSelectedPromptId())
  function loadChatSelectedConfigId(): number | null {
    try { const v = localStorage.getItem(CHAT_SELECTED_CONFIG_KEY); return v ? Number(v) : null } catch { return null }
  }
  function saveChatSelectedConfigId(id: number | null) {
    chatSelectedConfigId.value = id
    if (id !== null) localStorage.setItem(CHAT_SELECTED_CONFIG_KEY, String(id))
    else localStorage.removeItem(CHAT_SELECTED_CONFIG_KEY)
  }
  function loadChatSelectedPromptId(): number | null {
    try { const v = localStorage.getItem(CHAT_SELECTED_PROMPT_KEY); return v ? Number(v) : null } catch { return null }
  }
  function saveChatSelectedPromptId(id: number | null) {
    chatSelectedPromptId.value = id
    if (id !== null) localStorage.setItem(CHAT_SELECTED_PROMPT_KEY, String(id))
    else localStorage.removeItem(CHAT_SELECTED_PROMPT_KEY)
  }

  // 数据加载后自动默认选择第一项（无 localStorage 记录或记录已失效时）
  watch(configs, (list) => {
    if (list.length > 0 && (chatSelectedConfigId.value === null || !list.find(c => c.id === chatSelectedConfigId.value))) {
      saveChatSelectedConfigId(list[0].id)
    }
  })
  watch(prompts, (list) => {
    if (list.length > 0 && (chatSelectedPromptId.value === null || !list.find(p => p.id === chatSelectedPromptId.value))) {
      saveChatSelectedPromptId(list[0].id)
    }
  })

  // 持久化 AI 助手面板打开/关闭状态
  watch(visible, (v) => saveVisible(v))

  /** 加载角色约束列表 */
  async function loadPrompts() {
    if (promptsLoaded.value) return
    try {
      const data: SystemPromptItem[] = await fetchSystemPrompts()
      prompts.value = data
      promptsLoaded.value = true
    } catch (err) {
      console.error('加载角色约束失败:', err)
    }
  }

  async function addPrompt(data: { name: string; content?: string }) {
    const dto = await createSystemPrompt(data)
    const item: SystemPromptItem = {
      id: dto.id,
      name: dto.name,
      content: dto.content,
      is_default: dto.is_default,
    }
    prompts.value.push(item)
    return item
  }

  async function updatePrompt(id: number, data: { name?: string; content?: string }) {
    const dto = await updateSystemPrompt(id, data)
    const idx = prompts.value.findIndex(p => p.id === id)
    if (idx !== -1) {
      prompts.value[idx] = { ...prompts.value[idx], ...dto }
    }
  }

  async function removePrompt(id: number) {
    await apiDeletePrompt(id)
    prompts.value = prompts.value.filter(p => p.id !== id)
  }

  // 异步从后端加载配置
  async function loadConfigsFromAPI() {
    if (configLoaded.value) return
    configLoading.value = true
    try {
      const data: any[] = await fetchLLMConfigs()
      configs.value = data.map(dto => ({
        id: dto.id,
        name: dto.name,
        provider: dto.provider as LLMConfig['provider'],
        billingMode: dto.billing_mode || '',
        apiKey: dto.api_key || '',
        hasKey: dto.has_key,
        model: dto.model,
        baseUrl: dto.base_url,
      }))
      configLoaded.value = true
    } catch (err) {
      console.error('加载 LLM 配置失败:', err)
    } finally {
      configLoading.value = false
    }
  }

  /** 加载对话列表，并自动加载最近一个对话的消息 */
  async function loadConversations() {
    try {
      const list = await fetchConversations()
      conversations.value = list
      if (list.length > 0) {
        await switchConversation(list[0].id)
      }
    } catch (err) {
      console.error('加载对话列表失败:', err)
    }
  }

  /** 切换对话 */
  async function switchConversation(id: number) {
    currentConversationId.value = id
    try {
      const detail = await fetchConversation(id)
      messages.value = (detail.messages || []).map(m => ({
        id: String(m.id),
        role: m.role,
        content: m.content,
        timestamp: new Date(m.created_at).getTime(),
      }))
    } catch (err) {
      console.error('加载对话消息失败:', err)
      messages.value = []
    }
  }

  /** 创建新对话 */
  async function createNewConversation() {
    try {
      const conv = await createConversation()
      conversations.value.unshift({
        id: conv.id,
        title: conv.title,
        message_count: 0,
        created_at: conv.created_at,
        updated_at: conv.updated_at,
      })
      currentConversationId.value = conv.id
      messages.value = []
      return conv
    } catch (err) {
      console.error('创建对话失败:', err)
    }
  }

  /** 删除对话 */
  async function removeConversation(id: number) {
    try {
      await apiDeleteConversation(id)
      conversations.value = conversations.value.filter(c => c.id !== id)
      if (currentConversationId.value === id) {
        if (conversations.value.length > 0) {
          await switchConversation(conversations.value[0].id)
        } else {
          currentConversationId.value = null
          messages.value = []
        }
      }
    } catch (err) {
      console.error('删除对话失败:', err)
    }
  }

  const activeConfig = computed(() => {
    const id = chatSelectedConfigId.value
    // 如果已选中的配置存在且有效，使用它
    if (id && configs.value.find(c => c.id === id)) {
      return configs.value.find(c => c.id === id)!
    }
    // 否则默认使用第一个
    return configs.value[0] || null
  })

  const hasApiKey = computed(() => {
    const cfg = activeConfig.value
    return cfg ? cfg.hasKey || !!cfg.apiKey : false
  })

  async function addConfig(data?: Partial<LLMConfig>) {
    const defaults = createDefaultConfig()
    const payload = {
      name: data?.name ?? defaults.name,
      provider: data?.provider ?? defaults.provider,
      api_key: data?.apiKey ?? '',
      model: data?.model ?? defaults.model,
      base_url: data?.baseUrl ?? defaults.baseUrl,
    }
    try {
      const dto = await createLLMConfig(payload)
      const newCfg: LLMConfig = {
        id: dto.id,
        name: dto.name,
        provider: dto.provider as LLMConfig['provider'],
        billingMode: dto.billing_mode || '',
        apiKey: dto.api_key || '',
        hasKey: dto.has_key,
        model: dto.model,
        baseUrl: dto.base_url,
      }
      configs.value.push(newCfg)
      return newCfg
    } catch (err: any) {
      throw new Error(err.response?.data?.detail || '创建配置失败')
    }
  }

  async function updateConfig(id: number, data: Partial<LLMConfig>) {
    const payload: Record<string, any> = {}
    if (data.name !== undefined) payload.name = data.name
    if (data.provider !== undefined) payload.provider = data.provider
    if (data.apiKey !== undefined) payload.api_key = data.apiKey
    if (data.model !== undefined) payload.model = data.model
    if (data.baseUrl !== undefined) payload.base_url = data.baseUrl

    try {
      const dto = await updateLLMConfig(id, payload)
      const idx = configs.value.findIndex(c => c.id === id)
      if (idx !== -1) {
        configs.value[idx] = {
          ...configs.value[idx],
          name: dto.name,
          provider: dto.provider as LLMConfig['provider'],
          hasKey: dto.has_key,
          model: dto.model,
          baseUrl: dto.base_url,
          apiKey: data.apiKey !== undefined ? data.apiKey : configs.value[idx].apiKey,
        }
      }
    } catch (err: any) {
      throw new Error(err.response?.data?.detail || '更新配置失败')
    }
  }

  async function removeConfig(id: number) {
    try {
      await deleteLLMConfig(id)
      const idx = configs.value.findIndex(c => c.id === id)
      if (idx === -1) return
      configs.value.splice(idx, 1)
    } catch (err: any) {
      throw new Error(err.response?.data?.detail || '删除配置失败')
    }
  }

  function openChat() {
    visible.value = true
  }

  function toggleChat() {
    visible.value = !visible.value
  }

  function toggleLayoutMode() {
    layoutMode.value = layoutMode.value === 'float' ? 'sidebar' : 'float'
    saveLayoutMode(layoutMode.value)
    visible.value = true
  }

  /**
   * 带自动 token 刷新的 fetch 封装。
   * fetch 不走 axios 拦截器，所以需要手动处理 401 → refresh → retry。
   */
  async function fetchWithAuth(url: string, init: RequestInit, retryOnce = true): Promise<Response> {
    const token = localStorage.getItem('token') || ''
    const headers = new Headers(init.headers)
    headers.set('Authorization', `Bearer ${token}`)

    const response = await fetch(url, { ...init, headers })

    if (response.status === 401 && retryOnce) {
      const refreshToken = localStorage.getItem('refreshToken')
      if (refreshToken) {
        try {
          const res = await axios.post('/api/auth/token/refresh/', { refresh: refreshToken })
          const { access, refresh: newRefresh } = res.data
          localStorage.setItem('token', access)
          if (newRefresh) localStorage.setItem('refreshToken', newRefresh)
          // 用新 token 重试
          headers.set('Authorization', `Bearer ${access}`)
          return fetch(url, { ...init, headers })
        } catch {
          // refresh token 也过期 → 跳登录
          localStorage.removeItem('token')
          localStorage.removeItem('refreshToken')
          window.location.href = '/login'
          return response
        }
      }
    }
    return response
  }

  async function sendMessage(content: string, clusterId?: number) {
    if (!content.trim() || loading.value) return
    const cfg = activeConfig.value
    if (!cfg) return

    // 如果没有对话，自动创建
    let convId = currentConversationId.value
    if (!convId) {
      try {
        const conv = await createConversation()
        conversations.value.unshift({
          id: conv.id,
          title: conv.title,
          message_count: 0,
          created_at: conv.created_at,
          updated_at: conv.updated_at,
        })
        convId = conv.id
        currentConversationId.value = convId
      } catch {
        return
      }
    }

    // 用户消息
    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: content.trim(),
      timestamp: Date.now(),
    }
    messages.value.push(userMsg)
    loading.value = true

    // 保存用户消息到后端
    createMessage(convId, 'user', content.trim()).catch(() => {})

    // 历史消息（排除当前用户消息）
    const history = messages.value.slice(0, -1).map(m => ({
      role: m.role,
      content: m.content,
    }))

    // 使用选中的角色约束作为 system prompt
    const activePrompt = prompts.value.find(p => p.id === chatSelectedPromptId.value)
    const systemPrompt = activePrompt ? activePrompt.content : buildSystemPrompt(clusterId)
    const controller = new AbortController()
    currentController.value = controller

    let fullReply = ''
    let assistantMsg: ChatMessage | null = null

    try {
      // 通过后端代理调用 LLM（注入 PVE 数据 + 流式返回）
      const response = await fetchWithAuth('/api/auth/chat/stream/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          config_id: cfg.id,
          cluster_id: clusterId,
          user_message: content.trim(),
          messages: [
            { role: 'system', content: systemPrompt },
            ...history,
            { role: 'user', content: content.trim() },
          ],
        }),
        signal: controller.signal,
      })

      if (!response.ok) {
        const errBody = await response.text()
        // 错误时直接添加带内容的 assistant 消息
        assistantMsg = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: `请求失败 (${response.status})：${errBody.slice(0, 200)}`,
          timestamp: Date.now(),
        }
        messages.value.push(assistantMsg)
        return
      }

      const reader = response.body!.getReader()
      const decoder = new TextDecoder()
      let lineBuffer = ''  // 跨 chunk 行缓冲，防止 SSE 行被截断

      let chunkCount = 0
      while (true) {
        const { done, value } = await reader.read()
        chunkCount += 1
        if (done) break

        lineBuffer += decoder.decode(value, { stream: true })
        const lines = lineBuffer.split('\n')
        // 最后一个元素可能是不完整的行，保留到下一次
        lineBuffer = lines.pop() || ''

        for (const line of lines) {
          const trimmed = line.trim()
          if (!trimmed || !trimmed.startsWith('data: ')) continue
          const data = trimmed.slice(6)
          if (data === '[DONE]') break
          try {
            const parsed = JSON.parse(data)
            const delta = parsed.choices?.[0]?.delta?.content
            if (delta) {
              fullReply += delta
              // 首次收到内容时创建 assistant 消息
              if (!assistantMsg) {
                const newMsg: ChatMessage = {
                  id: (Date.now() + 1).toString(),
                  role: 'assistant',
                  content: '',
                  timestamp: Date.now(),
                }
                messages.value.push(newMsg)
                // 必须引用数组中的响应式代理，修改 content 才能触发 UI 更新
                assistantMsg = messages.value[messages.value.length - 1]
              }
              assistantMsg.content = fullReply
            }
          } catch { /* skip */ }
        }
      }
    } catch (err: any) {
      const errText = err.name === 'AbortError'
        ? '\n\n*[已停止]*'
        : `连接失败：${err.message}。请检查 API 配置。`
      if (assistantMsg) {
        assistantMsg.content += errText
      } else {
        assistantMsg = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: errText,
          timestamp: Date.now(),
        }
        messages.value.push(assistantMsg)
      }
    } finally {
      loading.value = false
      currentController.value = null
    }

    // 保存助手回复到后端
    if (fullReply && convId) {
      createMessage(convId, 'assistant', fullReply).catch(() => {})
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
    layoutMode,
    floatWidth,
    floatHeight,
    sidebarWidth,
    saveFloatWidth,
    saveFloatHeight,
    saveSidebarWidth,
    configLoading,
    configLoaded,
    conversations,
    currentConversationId,
    prompts,
    promptsLoaded,
    activeConfig,
    hasApiKey,
    chatSelectedConfigId,
    chatSelectedPromptId,
    saveChatSelectedConfigId,
    saveChatSelectedPromptId,
    loadConfigsFromAPI,
    loadConversations,
    loadPrompts,
    switchConversation,
    createNewConversation,
    removeConversation,
    addPrompt,
    updatePrompt,
    removePrompt,
    addConfig,
    updateConfig,
    removeConfig,
    openChat,
    toggleChat,
    toggleLayoutMode,
    sendMessage,
    stopGeneration,
  }
})
