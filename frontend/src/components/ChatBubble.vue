<template>
  <!-- 侧边栏模式（固定右侧，始终显示） -->
  <teleport to="body">
    <div v-if="chatStore.layoutMode === 'sidebar' && chatStore.visible" class="chat-panel sidebar">
      <div class="chat-container">
        <!-- 头部 -->
        <div class="chat-header">
          <div class="chat-header-left">
            <div class="chat-avatar-wrap">
              <el-icon :size="18"><Monitor /></el-icon>
            </div>
            <div>
              <h3 class="chat-title">AI 助手</h3>
              <span class="chat-subtitle">PVE 集群运维分析</span>
            </div>
          </div>
          <div class="chat-header-actions">
            <el-popover placement="bottom" :width="240" trigger="click" popper-class="chat-history-popover">
              <template #reference>
                <button class="chat-action-btn" title="历史对话">
                  <el-icon :size="14"><Clock /></el-icon>
                </button>
              </template>
              <div class="history-list">
                <div class="history-list-header">
                  <span class="history-list-title">历史对话</span>
                  <span class="history-list-count">{{ chatStore.conversations.length }} 条</span>
                </div>
                <div v-if="chatStore.conversations.length === 0" class="history-empty">暂无对话记录</div>
                <div
                  v-for="c in chatStore.conversations"
                  :key="c.id"
                  class="history-item"
                  :class="{ active: c.id === chatStore.currentConversationId }"
                  @click="switchToConversation(c.id)"
                >
                  <div class="history-item-info">
                    <div class="history-item-title">{{ c.title || '未命名对话' }}</div>
                    <div class="history-item-meta">{{ c.message_count }} 条消息 · {{ formatDate(c.updated_at) }}</div>
                  </div>
                  <button class="history-item-del" @click.stop="handleRemoveConversation(c.id)" title="删除">
                    <el-icon :size="12"><Close /></el-icon>
                  </button>
                </div>
              </div>
            </el-popover>
            <button class="chat-action-btn" @click="chatStore.toggleLayoutMode" title="切换为浮动模式">
              <el-icon :size="14"><DCaret /></el-icon>
            </button>
            <button class="chat-action-btn" @click="handleNewConversation" title="新对话">
              <el-icon :size="14"><Plus /></el-icon>
            </button>
          </div>
        </div>

        <!-- API 未配置提示 -->
        <div v-if="!hasApiKey" class="chat-no-config">
          <el-icon :size="20"><WarningFilled /></el-icon>
          <span>尚未配置 API Key，请先前往设置</span>
          <el-button size="small" type="primary" link @click="goSettings">去设置</el-button>
        </div>

        <!-- 消息列表 -->
        <div class="chat-messages" ref="messagesRef">
          <!-- 空状态 -->
          <div v-if="chatStore.messages.length === 0" class="chat-empty">
            <div class="chat-empty-icon">
              <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
                <rect width="48" height="48" rx="12" fill="url(#grad1)" />
                <path d="M16 18h16M16 24h12M16 30h8" stroke="#fff" stroke-width="2" stroke-linecap="round"/>
                <defs><linearGradient id="grad1" x1="0" y1="0" x2="48" y2="48"><stop stop-color="#409eff"/><stop offset="1" stop-color="#8b5cf6"/></linearGradient></defs>
              </svg>
            </div>
            <h4 class="chat-empty-title">AI 集群运维助手</h4>
            <p class="chat-empty-desc">我可以帮你分析集群状态、排查问题、给出优化建议</p>
            <div class="chat-quick-actions">
              <button class="quick-btn" @click="sendQuick('帮我分析一下当前集群的整体健康状况')">
                <el-icon><DataAnalysis /></el-icon> 健康分析
              </button>
              <button class="quick-btn" @click="sendQuick('哪些资源的使用率过高？需要关注？')">
                <el-icon><Warning /></el-icon> 资源预警
              </button>
              <button class="quick-btn" @click="sendQuick('请给出集群性能优化建议')">
                <el-icon><MagicStick /></el-icon> 优化建议
              </button>
              <button class="quick-btn" @click="sendQuick('当前集群有哪些潜在风险？')">
                <el-icon><CircleCheck /></el-icon> 风险排查
              </button>
            </div>
          </div>
          <!-- 消息 -->
          <template v-for="msg in chatStore.messages" :key="msg.id">
            <div :class="['chat-msg', msg.role]">
              <div v-if="msg.role === 'assistant'" class="msg-avatar"><el-icon :size="16"><Monitor /></el-icon></div>
              <div class="msg-body">
                <div class="msg-content" v-html="renderMarkdown(msg.content)" />
                <div v-if="msg.role === 'assistant' && msg.content && !chatStore.loading" class="msg-actions">
                  <button class="msg-action-btn" @click="copyMessage(msg.content)" title="复制"><el-icon :size="12"><CopyDocument /></el-icon></button>
                </div>
              </div>
              <div v-if="msg.role === 'user'" class="msg-avatar user-avatar"><el-icon :size="16"><User /></el-icon></div>
            </div>
          </template>
          <!-- 加载中 -->
          <div v-if="chatStore.loading && !streamingContent" class="chat-msg assistant">
            <div class="msg-avatar"><el-icon :size="16"><Monitor /></el-icon></div>
            <div class="msg-body">
              <div class="typing-indicator"><span></span><span></span><span></span></div>
            </div>
          </div>
        </div>

        <!-- 输入区 -->
        <div class="chat-input-area">
          <div v-if="chatStore.configs.length > 0" class="chat-model-row">
            <span class="model-label">模型</span>
            <el-select v-model="chatStore.activeConfigId" size="small" class="model-selector-input" popper-class="model-selector-popper" @change="onModelChange">
              <el-option v-for="cfg in chatStore.configs" :key="cfg.id" :label="cfg.name" :value="cfg.id">
                <span>{{ cfg.name }}</span>
                <span class="model-selector-detail">{{ cfg.model }}</span>
              </el-option>
            </el-select>
          </div>
          <div class="chat-input-wrap">
            <textarea ref="inputRef" v-model="inputText" class="chat-textarea" :placeholder="hasApiKey ? '输入消息，Shift+Enter 换行...' : '请先配置 API Key'" :disabled="!hasApiKey" @keydown.enter.exact.prevent="handleSend" @input="autoResize" />
            <div class="chat-input-actions">
              <button v-if="chatStore.loading" class="input-btn stop-btn" @click="chatStore.stopGeneration" title="停止生成"><el-icon :size="16"><VideoPause /></el-icon></button>
              <button v-else class="input-btn send-btn" :class="{ active: inputText.trim() }" :disabled="!inputText.trim() || !hasApiKey" @click="handleSend" title="发送"><el-icon :size="16"><Promotion /></el-icon></button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </teleport>

  <!-- 侧边栏隐藏时的触发按钮 -->
  <div v-if="chatStore.layoutMode === 'sidebar' && !chatStore.visible" class="sidebar-trigger" @click="chatStore.visible = true" title="打开 AI 助手">
    <el-icon :size="20"><ChatDotRound /></el-icon>
  </div>

  <!-- 浮动模式（悬浮气泡 + 动画面板） -->
  <div v-if="chatStore.layoutMode === 'float'" class="chat-bubble" :class="{ active: chatStore.visible }" @click="chatStore.toggleChat">
    <transition name="bubble-icon" mode="out-in">
      <el-icon v-if="!chatStore.visible" :size="24"><ChatDotRound /></el-icon>
      <el-icon v-else :size="24"><Close /></el-icon>
    </transition>
  </div>
  <teleport to="body">
    <transition name="chat-slide">
      <div v-if="chatStore.visible && chatStore.layoutMode === 'float'" class="chat-panel float">
        <div class="chat-container">
          <!-- 头部 -->
          <div class="chat-header">
            <div class="chat-header-left">
              <div class="chat-avatar-wrap"><el-icon :size="18"><Monitor /></el-icon></div>
              <div>
                <h3 class="chat-title">AI 助手</h3>
                <span class="chat-subtitle">PVE 集群运维分析</span>
              </div>
            </div>
            <div class="chat-header-actions">
              <el-popover placement="bottom" :width="240" trigger="click" popper-class="chat-history-popover">
                <template #reference>
                  <button class="chat-action-btn" title="历史对话"><el-icon :size="14"><Clock /></el-icon></button>
                </template>
                <div class="history-list">
                  <div class="history-list-header">
                    <span class="history-list-title">历史对话</span>
                    <span class="history-list-count">{{ chatStore.conversations.length }} 条</span>
                  </div>
                  <div v-if="chatStore.conversations.length === 0" class="history-empty">暂无对话记录</div>
                  <div
                    v-for="c in chatStore.conversations"
                    :key="c.id"
                    class="history-item"
                    :class="{ active: c.id === chatStore.currentConversationId }"
                    @click="switchToConversation(c.id)"
                  >
                    <div class="history-item-info">
                      <div class="history-item-title">{{ c.title || '未命名对话' }}</div>
                      <div class="history-item-meta">{{ c.message_count }} 条消息 · {{ formatDate(c.updated_at) }}</div>
                    </div>
                    <button class="history-item-del" @click.stop="handleRemoveConversation(c.id)" title="删除">
                      <el-icon :size="12"><Close /></el-icon>
                    </button>
                  </div>
                </div>
              </el-popover>
              <button class="chat-action-btn" @click="chatStore.toggleLayoutMode" title="切换为侧边栏模式"><el-icon :size="14"><FullScreen /></el-icon></button>
              <button class="chat-action-btn" @click="handleNewConversation" title="新对话"><el-icon :size="14"><Plus /></el-icon></button>
            </div>
          </div>
          <!-- API 未配置提示 -->
          <div v-if="!hasApiKey" class="chat-no-config">
            <el-icon :size="20"><WarningFilled /></el-icon>
            <span>尚未配置 API Key，请先前往设置</span>
            <el-button size="small" type="primary" link @click="goSettings">去设置</el-button>
          </div>
          <!-- 消息列表 -->
          <div class="chat-messages" ref="messagesRef">
            <!-- 空状态 -->
            <div v-if="chatStore.messages.length === 0" class="chat-empty">
              <div class="chat-empty-icon">
                <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
                  <rect width="48" height="48" rx="12" fill="url(#grad1)" />
                  <path d="M16 18h16M16 24h12M16 30h8" stroke="#fff" stroke-width="2" stroke-linecap="round"/>
                  <defs><linearGradient id="grad1" x1="0" y1="0" x2="48" y2="48"><stop stop-color="#409eff"/><stop offset="1" stop-color="#8b5cf6"/></linearGradient></defs>
                </svg>
              </div>
              <h4 class="chat-empty-title">AI 集群运维助手</h4>
              <p class="chat-empty-desc">我可以帮你分析集群状态、排查问题、给出优化建议</p>
              <div class="chat-quick-actions">
                <button class="quick-btn" @click="sendQuick('帮我分析一下当前集群的整体健康状况')">
                  <el-icon><DataAnalysis /></el-icon> 健康分析
                </button>
                <button class="quick-btn" @click="sendQuick('哪些资源的使用率过高？需要关注？')">
                  <el-icon><Warning /></el-icon> 资源预警
                </button>
                <button class="quick-btn" @click="sendQuick('请给出集群性能优化建议')">
                  <el-icon><MagicStick /></el-icon> 优化建议
                </button>
                <button class="quick-btn" @click="sendQuick('当前集群有哪些潜在风险？')">
                  <el-icon><CircleCheck /></el-icon> 风险排查
                </button>
              </div>
            </div>
            <!-- 消息 -->
            <template v-for="msg in chatStore.messages" :key="msg.id">
              <div :class="['chat-msg', msg.role]">
                <div v-if="msg.role === 'assistant'" class="msg-avatar"><el-icon :size="16"><Monitor /></el-icon></div>
                <div class="msg-body">
                  <div class="msg-content" v-html="renderMarkdown(msg.content)" />
                  <div v-if="msg.role === 'assistant' && msg.content && !chatStore.loading" class="msg-actions">
                    <button class="msg-action-btn" @click="copyMessage(msg.content)" title="复制"><el-icon :size="12"><CopyDocument /></el-icon></button>
                  </div>
                </div>
                <div v-if="msg.role === 'user'" class="msg-avatar user-avatar"><el-icon :size="16"><User /></el-icon></div>
              </div>
            </template>
            <!-- 加载中 -->
            <div v-if="chatStore.loading && !streamingContent" class="chat-msg assistant">
              <div class="msg-avatar"><el-icon :size="16"><Monitor /></el-icon></div>
              <div class="msg-body">
                <div class="typing-indicator"><span></span><span></span><span></span></div>
              </div>
            </div>
          </div>
          <!-- 输入区 -->
          <div class="chat-input-area">
            <div v-if="chatStore.configs.length > 0" class="chat-model-row">
              <span class="model-label">模型</span>
              <el-select v-model="chatStore.activeConfigId" size="small" class="model-selector-input" popper-class="model-selector-popper" @change="onModelChange">
                <el-option v-for="cfg in chatStore.configs" :key="cfg.id" :label="cfg.name" :value="cfg.id">
                  <span>{{ cfg.name }}</span>
                  <span class="model-selector-detail">{{ cfg.model }}</span>
                </el-option>
              </el-select>
            </div>
            <div class="chat-input-wrap">
              <textarea ref="inputRef" v-model="inputText" class="chat-textarea" :placeholder="hasApiKey ? '输入消息，Shift+Enter 换行...' : '请先配置 API Key'" :disabled="!hasApiKey" @keydown.enter.exact.prevent="handleSend" @input="autoResize" />
              <div class="chat-input-actions">
                <button v-if="chatStore.loading" class="input-btn stop-btn" @click="chatStore.stopGeneration" title="停止生成"><el-icon :size="16"><VideoPause /></el-icon></button>
                <button v-else class="input-btn send-btn" :class="{ active: inputText.trim() }" :disabled="!inputText.trim() || !hasApiKey" @click="handleSend" title="发送"><el-icon :size="16"><Promotion /></el-icon></button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </transition>
  </teleport>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useChatStore } from '@/stores/chat'
import { useClusterStore } from '@/stores/cluster'
import {
  ChatDotRound, Close, Setting, Monitor, User, Promotion,
  DataAnalysis, Warning, MagicStick, CopyDocument, WarningFilled,
  VideoPause, CircleCheck, DCaret, FullScreen, Plus, Clock,
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const router = useRouter()
const chatStore = useChatStore()
const clusterStore = useClusterStore()

const inputText = ref('')
const inputRef = ref<HTMLTextAreaElement>()
const messagesRef = ref<HTMLDivElement>()

const hasApiKey = computed(() => chatStore.hasApiKey)

// 页面加载时从后端拉取 LLM 配置和对话列表
onMounted(() => {
  chatStore.loadConfigsFromAPI()
  chatStore.loadConversations()
})

// 流式内容用于判断是否显示打字指示器
const streamingContent = computed(() => {
  const msgs = chatStore.messages
  if (msgs.length === 0) return false
  const last = msgs[msgs.length - 1]
  return last.role === 'assistant' && last.content.length > 0
})

// 监听消息变化自动滚动到底部
watch(
  () => chatStore.messages.length,
  () => nextTick(scrollToBottom),
)
watch(
  () => {
    const msgs = chatStore.messages
    return msgs.length > 0 ? msgs[msgs.length - 1].content : ''
  },
  () => nextTick(scrollToBottom),
)

function scrollToBottom() {
  if (messagesRef.value) {
    messagesRef.value.scrollTop = messagesRef.value.scrollHeight
  }
}

function autoResize() {
  const el = inputRef.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 120) + 'px'
}

async function handleSend() {
  const text = inputText.value.trim()
  if (!text || !hasApiKey.value) return
  inputText.value = ''
  nextTick(() => autoResize())
  await chatStore.sendMessage(text, clusterStore.currentClusterId || undefined)
}

function sendQuick(text: string) {
  if (!hasApiKey.value) {
    goSettings()
    return
  }
  inputText.value = ''
  chatStore.sendMessage(text, clusterStore.currentClusterId || undefined)
}

function goSettings() {
  chatStore.visible = false
  router.push('/dashboard/llm-settings')
}

async function handleNewConversation() {
  await chatStore.createNewConversation()
}

function formatDate(dateStr: string) {
  const d = new Date(dateStr)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

async function switchToConversation(id: number) {
  if (id === chatStore.currentConversationId) return
  await chatStore.switchConversation(id)
}

async function handleRemoveConversation(id: number) {
  await chatStore.removeConversation(id)
}

function onModelChange(id: string) {
  chatStore.setActiveConfig(id)
}

function copyMessage(content: string) {
  navigator.clipboard.writeText(content).then(
    () => ElMessage.success('已复制'),
    () => ElMessage.error('复制失败'),
  )
}

/** 简易 Markdown → HTML（粗体、行内代码、列表、代码块、标题） */
function renderMarkdown(text: string): string {
  if (!text) return ''
  let html = text
    // 代码块
    .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre class="md-code-block"><code>$2</code></pre>')
    // 行内代码
    .replace(/`([^`]+)`/g, '<code class="md-inline-code">$1</code>')
    // 粗体
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    // 斜体
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    // 标题
    .replace(/^### (.+)$/gm, '<h4 class="md-h">$1</h4>')
    .replace(/^## (.+)$/gm, '<h3 class="md-h">$1</h3>')
    // 无序列表
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    // 有序列表
    .replace(/^\d+\. (.+)$/gm, '<li>$1</li>')
    // 换行
    .replace(/\n/g, '<br/>')

  // 包裹连续 <li>
  html = html.replace(/(<li>.*?<\/li>(<br\/>)?)+/g, (match) => {
    return '<ul class="md-list">' + match.replace(/<br\/>/g, '') + '</ul>'
  })

  return html
}
</script>

<style scoped>
/* ===== 悬浮气泡 ===== */
.chat-bubble {
  position: fixed;
  bottom: 28px;
  right: 28px;
  z-index: 9999;
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: linear-gradient(135deg, #409eff, #8b5cf6);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  cursor: pointer;
  box-shadow: 0 4px 16px rgba(64, 158, 255, 0.4);
  transition: transform 0.2s, box-shadow 0.2s;
  user-select: none;
}
.chat-bubble:hover {
  transform: scale(1.1);
  box-shadow: 0 6px 24px rgba(64, 158, 255, 0.5);
}
.chat-bubble.active {
  background: linear-gradient(135deg, #8b5cf6, #409eff);
}
.bubble-icon-enter-active,
.bubble-icon-leave-active {
  transition: transform 0.15s;
}
.bubble-icon-enter-from,
.bubble-icon-leave-to {
  transform: scale(0.5);
  opacity: 0;
}

/* ===== 侧边栏触发按钮（隐藏时右下角悬浮） ===== */
.sidebar-trigger {
  position: fixed;
  bottom: 28px;
  right: 28px;
  z-index: 9999;
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: linear-gradient(135deg, #409eff, #8b5cf6);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  cursor: pointer;
  box-shadow: 0 4px 16px rgba(64, 158, 255, 0.4);
  transition: transform 0.2s, box-shadow 0.2s;
  user-select: none;
}
.sidebar-trigger:hover {
  transform: scale(1.1);
  box-shadow: 0 6px 24px rgba(64, 158, 255, 0.5);
}

/* ===== 对话面板 ===== */
.chat-panel {
  position: fixed;
  bottom: 92px;
  right: 28px;
  z-index: 9998;
  width: 420px;
  height: 600px;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 12px 48px rgba(0, 0, 0, 0.2), 0 0 0 1px var(--border-color);
  background: var(--bg-secondary);
}
/* 侧边栏模式 */
.chat-panel.sidebar {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  z-index: 100;
  width: 420px;
  height: 100vh;
  border-radius: 0;
  box-shadow: -4px 0 24px rgba(0, 0, 0, 0.1), 0 0 0 1px var(--border-color);
  border-left: 1px solid var(--border-color);
}
.chat-panel.sidebar .chat-container {
  max-height: 100vh;
}
.chat-container {
  display: flex;
  flex-direction: column;
  height: 100%;
}

/* 滑入动画 */
.chat-slide-enter-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}
.chat-slide-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.chat-slide-enter-from {
  opacity: 0;
  transform: translateY(12px) scale(0.96);
}
.chat-slide-leave-to {
  opacity: 0;
  transform: translateY(8px) scale(0.97);
}

/* ===== 头部 ===== */
.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;
}
.chat-header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}
.chat-avatar-wrap {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: linear-gradient(135deg, #409eff, #8b5cf6);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}
.chat-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-heading);
  margin: 0;
  line-height: 1.2;
}
.chat-subtitle {
  font-size: 11px;
  color: var(--text-muted);
}
.chat-header-actions {
  display: flex;
  gap: 4px;
}

/* 模型选择器行 */
.chat-model-row {
  display: flex;
  justify-content: flex-end;
  padding: 0 0 6px 0;
}

/* 输入区模型选择器 */
.chat-model-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
}
.model-label {
  font-size: 11px;
  color: var(--text-muted);
  white-space: nowrap;
}
.model-selector-input {
  width: 140px;
  flex-shrink: 0;
}
.model-selector-input :deep(.el-select__wrapper) {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  box-shadow: none;
  padding: 0 4px;
  font-size: 12px;
  min-height: 28px;
  border-radius: 4px;
}
.model-selector-input :deep(.el-select__wrapper:hover) {
  border-color: #409eff;
}
.model-selector-input :deep(.el-select__placeholder) {
  font-size: 11px;
  color: var(--text-muted);
}
.model-selector-detail {
  font-size: 11px;
  color: var(--text-muted);
  margin-left: 4px;
}
.chat-action-btn {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  border: none;
  background: transparent;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  transition: all 0.15s;
}
.chat-action-btn:hover {
  background: rgba(64, 158, 255, 0.1);
  color: var(--primary-color);
}

/* ===== 未配置提示 ===== */
.chat-no-config {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: rgba(230, 162, 60, 0.1);
  color: var(--warning-color, #e6a23c);
  font-size: 12px;
  flex-shrink: 0;
}

/* ===== 消息列表 ===== */
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.chat-messages::-webkit-scrollbar {
  width: 4px;
}

/* ===== 空状态 ===== */
.chat-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  padding: 24px 16px;
  text-align: center;
}
.chat-empty-icon {
  margin-bottom: 16px;
}
.chat-empty-title {
  font-size: 17px;
  font-weight: 600;
  color: var(--text-heading);
  margin: 0 0 6px;
}
.chat-empty-desc {
  font-size: 13px;
  color: var(--text-muted);
  margin: 0 0 20px;
}
.chat-quick-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  width: 100%;
}
.quick-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid var(--border-color);
  background: var(--bg-card);
  color: var(--text-secondary);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
}
.quick-btn:hover {
  border-color: var(--primary-color);
  color: var(--primary-color);
  background: rgba(64, 158, 255, 0.06);
}

/* ===== 消息气泡 ===== */
.chat-msg {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  max-width: 100%;
}
.chat-msg.user {
  flex-direction: row-reverse;
}
.msg-avatar {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: linear-gradient(135deg, #409eff, #8b5cf6);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
}
.msg-avatar.user-avatar {
  background: var(--primary-color);
}
.msg-body {
  max-width: calc(100% - 40px);
  min-width: 0;
}
.msg-content {
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 13px;
  line-height: 1.6;
  color: var(--text-primary);
  word-break: break-word;
}
.chat-msg.user .msg-content {
  background: var(--primary-color);
  color: #fff;
  border-bottom-right-radius: 4px;
}
.chat-msg.assistant .msg-content {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-bottom-left-radius: 4px;
}
.msg-actions {
  display: flex;
  gap: 4px;
  margin-top: 4px;
  opacity: 0;
  transition: opacity 0.15s;
}
.msg-body:hover .msg-actions {
  opacity: 1;
}
.msg-action-btn {
  padding: 2px 6px;
  border-radius: 4px;
  border: none;
  background: transparent;
  cursor: pointer;
  color: var(--text-muted);
  transition: all 0.15s;
}
.msg-action-btn:hover {
  background: rgba(64, 158, 255, 0.1);
  color: var(--primary-color);
}

/* ===== Markdown 样式 ===== */
.msg-content :deep(.md-code-block) {
  background: rgba(0, 0, 0, 0.06);
  border-radius: 6px;
  padding: 8px 10px;
  margin: 6px 0;
  overflow-x: auto;
  font-size: 12px;
  font-family: 'SF Mono', 'Fira Code', monospace;
}
.msg-content :deep(.md-inline-code) {
  background: rgba(0, 0, 0, 0.06);
  border-radius: 3px;
  padding: 1px 4px;
  font-size: 12px;
  font-family: 'SF Mono', 'Fira Code', monospace;
}
.msg-content :deep(.md-list) {
  margin: 4px 0;
  padding-left: 16px;
  list-style: disc;
}
.msg-content :deep(.md-h) {
  font-size: 14px;
  font-weight: 600;
  margin: 8px 0 4px;
  color: var(--text-heading);
}

/* 暗色代码块 */
:global(.dark) .msg-content :deep(.md-code-block),
:global(.dark) .msg-content :deep(.md-inline-code) {
  background: rgba(255, 255, 255, 0.08);
}

/* ===== 打字指示器 ===== */
.typing-indicator {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 12px 14px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  border-bottom-left-radius: 4px;
}
.typing-indicator span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--text-muted);
  animation: typingBounce 1.2s ease-in-out infinite;
}
.typing-indicator span:nth-child(2) {
  animation-delay: 0.15s;
}
.typing-indicator span:nth-child(3) {
  animation-delay: 0.3s;
}
@keyframes typingBounce {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
  30% { transform: translateY(-4px); opacity: 1; }
}

/* ===== 输入区 ===== */
.chat-input-area {
  padding: 12px 16px;
  border-top: 1px solid var(--border-color);
  background: var(--bg-secondary);
  flex-shrink: 0;
}
.chat-input-wrap {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 12px;
  border: 1px solid var(--border-color);
  background: var(--bg-card);
  transition: border-color 0.2s;
}
.chat-input-wrap:focus-within {
  border-color: var(--primary-color);
}
.chat-textarea {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  color: var(--text-primary);
  font-size: 13px;
  line-height: 1.5;
  resize: none;
  font-family: inherit;
  min-height: 40px;
  max-height: 120px;
}
.chat-textarea::placeholder {
  color: var(--text-muted);
}
.chat-textarea:disabled {
  opacity: 0.5;
}
.chat-input-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}
.input-btn {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.15s;
}
.send-btn {
  background: var(--primary-color);
  color: #fff;
}
.send-btn.active:hover {
  background: #337ecc;
}
.send-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}
.stop-btn {
  background: var(--danger-color, #f56c6c);
  color: #fff;
}
.stop-btn:hover {
  background: #e04b4b;
}

/* ===== 暗色适配 ===== */
:global(.dark) .chat-panel {
  box-shadow: 0 12px 48px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(255, 255, 255, 0.08);
}
:global(.dark) .chat-panel.sidebar {
  box-shadow: -4px 0 24px rgba(0, 0, 0, 0.4), 0 0 0 1px rgba(255, 255, 255, 0.08);
}

/* 模型选择器下拉弹窗 z-index */
:global(.model-selector-popper) {
  z-index: 10001 !important;
}

/* ===== 历史对话弹窗 ===== */
:global(.chat-history-popover) {
  padding: 0 !important;
  max-height: 360px;
  overflow-y: auto;
  z-index: 10002 !important;
}
.history-list {
  padding: 8px 0;
}
.history-list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 14px 10px;
  border-bottom: 1px solid var(--border-color, #eee);
  margin-bottom: 4px;
}
.history-list-title {
  font-weight: 600;
  font-size: 13px;
  color: var(--text-primary, #303133);
}
.history-list-count {
  font-size: 11px;
  color: var(--text-muted, #909399);
}
.history-empty {
  text-align: center;
  padding: 24px 0;
  color: var(--text-muted, #909399);
  font-size: 13px;
}
.history-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 14px;
  cursor: pointer;
  transition: background 0.15s;
  gap: 8px;
}
.history-item:hover {
  background: var(--hover-bg, #f5f7fa);
}
.history-item.active {
  background: var(--primary-bg, #ecf5ff);
}
.history-item-info {
  flex: 1;
  min-width: 0;
}
.history-item-title {
  font-size: 13px;
  color: var(--text-primary, #303133);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.history-item-meta {
  font-size: 11px;
  color: var(--text-muted, #909399);
  margin-top: 2px;
}
.history-item-del {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  border: none;
  background: transparent;
  cursor: pointer;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted, #909399);
  opacity: 0;
  transition: opacity 0.15s;
}
.history-item:hover .history-item-del {
  opacity: 1;
}
.history-item-del:hover {
  background: var(--danger-bg, #fef0f0);
  color: var(--danger-color, #f56c6c);
}
:global(.dark) .history-item:hover {
  background: rgba(255, 255, 255, 0.05);
}
:global(.dark) .history-item.active {
  background: rgba(64, 158, 255, 0.12);
}
:global(.dark) .history-item-del:hover {
  background: rgba(245, 108, 108, 0.15);
}
</style>
