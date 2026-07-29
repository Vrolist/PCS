<template>
  <div class="llm-settings-page">
    <div class="page-header">
      <div>
        <h2 class="page-title">AI 助手配置</h2>
        <p class="page-desc">管理多个大模型配置，AI 助手中可随时切换</p>
      </div>
    </div>

    <div class="settings-grid">
      <!-- 左侧：使用提示 + 快速开始 -->
      <div class="settings-form-wrap">
        <!-- 使用提示 -->
        <el-card shadow="hover" class="info-card">
          <template #header>
            <div class="card-header">
              <el-icon :size="18"><Document /></el-icon>
              <span>使用提示</span>
            </div>
          </template>
          <div class="tips-list">
            <div class="tip-item">
              <span class="tip-num">1</span>
              <span>添加多个大模型配置，每个配置包含 API Key 和模型</span>
            </div>
            <div class="tip-item">
              <span class="tip-num">2</span>
              <span>在 AI 助手中可随时切换模型</span>
            </div>
            <div class="tip-item">
              <span class="tip-num">3</span>
              <span>右下角气泡打开 AI 助手后，可随时切换模型</span>
            </div>
            <div class="tip-item">
              <span class="tip-num">4</span>
              <span>AI 会自动结合当前选中集群的数据进行分析</span>
            </div>
          </div>
        </el-card>

        <!-- 快速开始 -->
        <el-card shadow="hover" class="info-card">
          <template #header>
            <div class="card-header">
              <el-icon :size="18"><Promotion /></el-icon>
              <span>快速开始</span>
            </div>
          </template>
          <div class="provider-list">
            <div
              v-for="p in presets"
              :key="p.key"
              class="provider-item"
              @click="addFromPreset(p)"
            >
              <div class="provider-icon" :style="{ background: p.color }">
                <span>{{ p.icon }}</span>
              </div>
              <div class="provider-info">
                <div class="provider-name">{{ p.name }}</div>
                <div class="provider-desc">{{ p.desc }}</div>
              </div>
              <el-icon class="provider-arrow"><Plus /></el-icon>
            </div>
          </div>
        </el-card>
      </div>

      <!-- 右侧：模型配置列表 -->
      <div class="settings-info-wrap">
        <!-- 模型配置列表 -->
        <el-card shadow="hover" class="config-card">
          <template #header>
            <div class="card-header card-header-between">
              <div class="card-header-left">
                <el-icon :size="18"><Setting /></el-icon>
                <span>模型配置</span>
              </div>
              <el-button size="small" type="primary" :icon="Plus" @click="addNewConfig">添加配置</el-button>
            </div>
          </template>

          <div v-if="chatStore.configs.length === 0" class="empty-configs">
            <el-icon :size="24" color="var(--text-muted)"><InfoFilled /></el-icon>
            <span>暂无配置，点击「添加配置」或从左侧快速开始添加</span>
          </div>

          <div v-for="cfg in chatStore.configs" :key="cfg.id" class="config-item" :class="{ folded: isFolded(cfg.id) }">
            <!-- 折叠态：紧凑展示 -->
            <div v-if="isFolded(cfg.id)" class="folded-view">
              <div class="folded-left">
                <div class="folded-icon" :style="{ background: getProviderStyle(cfg.provider).bg }">
                  <span>{{ getProviderStyle(cfg.provider).icon }}</span>
                </div>
                <div class="folded-info">
                  <div class="folded-name">
                    <span>{{ cfg.name }}</span>
                    <span class="folded-model">{{ cfg.model }}</span>
                  </div>
                  <div class="folded-meta">
                    <span>{{ cfg.provider === 'custom' ? '自定义' : cfg.provider.charAt(0).toUpperCase() + cfg.provider.slice(1) }}</span>
                  </div>
                </div>
              </div>
              <div class="folded-actions">
                <el-button size="small" text type="primary" @click="expandConfig(cfg.id)">编辑</el-button>
                <el-button size="small" text :loading="testingId === cfg.id" @click="handleTest(cfg)">测试</el-button>
                <el-button size="small" text type="danger" :disabled="!isTempId(cfg.id) && chatStore.configs.length <= 1" @click="handleRemove(cfg.id)">删除</el-button>
              </div>
            </div>

            <!-- 展开态：完整编辑表单 -->
            <template v-else>
              <div class="config-item-header">
                <div class="config-item-name">
                  <el-input
                    v-model="cfg.name"
                    size="small"
                    class="name-input"
                    placeholder="配置名称"
                  />
                </div>
                <div class="config-item-actions">
                  <el-button
                    size="small"
                    text
                    type="primary"
                    :loading="testingId === cfg.id"
                    @click="handleSave(cfg)"
                  >保存</el-button>
                  <el-button
                    size="small"
                    text
                    :loading="testingId === cfg.id"
                    @click="handleTest(cfg)"
                  >测试</el-button>
                  <el-button
                    size="small"
                    text
                    type="danger"
                    :disabled="!isTempId(cfg.id) && chatStore.configs.length <= 1"
                    @click="handleRemove(cfg.id)"
                  >删除</el-button>
                </div>
              </div>

              <div class="config-item-body">
                <el-form :model="cfg" label-position="top" class="config-inner-form" size="small">
                  <el-form-item label="服务提供商">
                    <el-select v-model="cfg.provider" @change="(val: string) => onProviderChange(cfg, val)">
                      <el-option v-for="p in providers" :key="p.value" :label="p.label" :value="p.value" />
                    </el-select>
                  </el-form-item>

                  <el-form-item label="API Key">
                    <el-input
                      v-model="cfg.apiKey"
                      :type="showKeyMap[cfg.id] ? 'text' : 'password'"
                      placeholder="输入 API Key"
                    >
                      <template #suffix>
                        <el-icon class="key-toggle" @click="toggleKey(cfg.id)">
                          <View v-if="showKeyMap[cfg.id]" />
                          <Hide v-else />
                        </el-icon>
                      </template>
                    </el-input>
                  </el-form-item>

                  <el-form-item label="模型">
                    <el-select v-model="cfg.model" filterable allow-create>
                      <el-option v-for="m in getModels(cfg.provider)" :key="m" :label="m" :value="m" />
                    </el-select>
                  </el-form-item>

                  <el-form-item v-if="cfg.provider === 'mimo'" label="计费方式">
                    <el-select v-model="cfg.billingMode" @change="(val: string) => onBillingModeChange(cfg, val)">
                      <el-option label="余额计费" value="payg" />
                      <el-option label="Token Plan（套餐）" value="plan" />
                    </el-select>
                  </el-form-item>

                  <el-form-item v-if="cfg.provider === 'mimo' && cfg.billingMode === 'plan'" label="API 地址">
                    <el-input v-model="cfg.baseUrl" placeholder="请在订阅管理页面获取专属 Base URL" />
                    <div class="form-item-hint">Token Plan 需使用订阅管理页面的专属 Base URL，请前往 platform.xiaomimimo.com 获取</div>
                  </el-form-item>

                  <el-form-item v-if="cfg.provider === 'custom' || (cfg.provider === 'mimo' && cfg.billingMode !== 'plan')" label="API 地址">
                    <el-input v-model="cfg.baseUrl" placeholder="https://api.example.com" />
                  </el-form-item>
                </el-form>
              </div>
            </template>
          </div>
        </el-card>

        <!-- 角色约束管理 -->
        <el-card shadow="hover" class="config-card" style="margin-top: 20px;">
          <template #header>
            <div class="card-header card-header-between">
              <div class="card-header-left">
                <el-icon :size="18"><Document /></el-icon>
                <span>角色约束</span>
              </div>
              <div class="card-header-actions">
                <span class="prompt-hint">约束仅在发送消息时生效，修改后需保存</span>
                <el-button size="small" type="primary" :icon="Plus" @click="handleAddPrompt">添加约束</el-button>
              </div>
            </div>
          </template>

          <div v-if="chatStore.prompts.length === 0" class="empty-configs">
            <el-icon :size="24" color="var(--text-muted)"><InfoFilled /></el-icon>
            <span>暂无约束</span>
          </div>

          <div v-for="p in chatStore.prompts" :key="p.id" class="config-item" :class="{ folded: isPromptFolded(p.id) }">
            <!-- 折叠态 -->
            <div v-if="isPromptFolded(p.id)" class="folded-view" @click="expandPrompt(p.id)">
              <div class="folded-left">
                <div class="folded-info">
                  <div class="folded-name">
                    <span>{{ p.name }}</span>
                  </div>
                </div>
              </div>
              <div class="folded-actions" @click.stop>
                <el-button size="small" text type="primary" @click="expandPrompt(p.id)">编辑</el-button>
                <el-button size="small" text type="primary" @click="handleSavePrompt(p)">保存</el-button>
                <el-button size="small" text type="danger" :disabled="chatStore.prompts.length <= 1" @click="handleDeletePrompt(p.id)">删除</el-button>
              </div>
            </div>

            <!-- 展开态 -->
            <template v-else>
              <div class="config-item-header">
                <div class="config-item-name">
                  <el-input v-model="p.name" size="small" class="name-input" placeholder="约束名称" />
                </div>
                <div class="config-item-actions">
                  <el-button size="small" text type="primary" @click="handleSavePrompt(p)">保存</el-button>
                  <el-button size="small" text type="danger" :disabled="chatStore.prompts.length <= 1" @click="handleDeletePrompt(p.id)">删除</el-button>
                </div>
              </div>
              <div class="config-item-body">
                <el-input
                  v-model="p.content"
                  type="textarea"
                  :rows="10"
                  placeholder="输入角色约束内容..."
                />
              </div>
            </template>
          </div>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useChatStore } from '@/stores/chat'
import type { LLMConfig } from '@/stores/chat'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Setting, Promotion, Document, View, Hide,
  InfoFilled, Plus,
} from '@element-plus/icons-vue'

const chatStore = useChatStore()

const testingId = ref<number | null>(null)
const showKeyMap = reactive<Record<number, boolean>>({})
const foldedIds = reactive<Set<number>>(new Set())

// 约束折叠：一次只能展开一个
const activePromptEditId = ref<number | null>(null)

// 临时配置管理：未保存到后端的配置用负 id 标识
let tempIdCounter = 0
function isTempId(id: number) {
  return id < 0
}
const hasPending = computed(() => chatStore.configs.some(c => isTempId(c.id)))

// 页面加载时从后端拉取配置和约束
onMounted(async () => {
  await chatStore.loadConfigsFromAPI()
  // 已有 key 的配置默认折叠
  chatStore.configs.forEach(cfg => {
    if (cfg.hasKey) {
      foldedIds.add(cfg.id)
    }
  })
  // 加载角色约束
  await chatStore.loadPrompts()
})

function isFolded(id: number) {
  return foldedIds.has(id)
}

function expandConfig(id: number) {
  foldedIds.delete(id)
}

function foldConfig(id: number) {
  foldedIds.add(id)
}

// 约束折叠
function isPromptFolded(id: number) {
  return activePromptEditId.value !== id
}

function expandPrompt(id: number) {
  // 切换展开/折叠
  if (activePromptEditId.value === id) {
    activePromptEditId.value = null
  } else {
    activePromptEditId.value = id
  }
}

const providerStyles: Record<string, { bg: string; icon: string }> = {
  deepseek: { bg: 'linear-gradient(135deg, #409eff, #36d399)', icon: 'DS' },
  kimi: { bg: 'linear-gradient(135deg, #6366f1, #8b5cf6)', icon: 'Ki' },
  glm: { bg: 'linear-gradient(135deg, #f59e0b, #ef4444)', icon: 'GL' },
  openai: { bg: 'linear-gradient(135deg, #10a37f, #1a7f5a)', icon: 'AI' },
  mimo: { bg: 'linear-gradient(135deg, #ff6900, #ff9500)', icon: 'XM' },
  custom: { bg: 'linear-gradient(135deg, #8b5cf6, #6366f1)', icon: '...' },
}

function getProviderStyle(provider: string) {
  return providerStyles[provider] || providerStyles.custom
}

function maskKey(key: string): string {
  if (!key) return '未配置'
  if (key.length <= 6) return key.slice(0, 2) + '****'
  return key.slice(0, 4) + '****' + key.slice(-4)
}

function toggleKey(id: number) {
  showKeyMap[id] = !showKeyMap[id]
}

const providers = [
  { label: 'DeepSeek', value: 'deepseek' },
  { label: 'Kimi', value: 'kimi' },
  { label: 'GLM', value: 'glm' },
  { label: 'OpenAI', value: 'openai' },
  { label: 'MiMo（小米）', value: 'mimo' },
  { label: '自定义', value: 'custom' },
]

const modelMap: Record<string, string[]> = {
  deepseek: ['deepseek-v4-pro', 'deepseek-v4-flash'],
  kimi: ['kimi-k3', 'kimi-k2.7-code', 'kimi-k2.7-code-highspeed', 'kimi-k2.6'],
  glm: ['glm-5.2', 'glm-5.2-fast-preview'],
  openai: ['gpt-5.6-sol', 'gpt-5.6-terra', 'gpt-5.6-luna', 'gpt-5.5'],
  mimo: ['mimo-v2.5-pro', 'mimo-v2.5', 'mimo-v2.5-asr', 'mimo-v2.5-tts'],
  custom: ['custom-model'],
}

function getModels(provider: string) {
  return modelMap[provider] || []
}

const presets = [
  {
    key: 'deepseek',
    name: 'DeepSeek',
    desc: 'V4-Pro 旗舰推理模型，1M 上下文，极致性价比',
    color: 'linear-gradient(135deg, #409eff, #36d399)',
    icon: 'DS',
    provider: 'deepseek' as const,
  },
  {
    key: 'kimi',
    name: 'Kimi (月之暗面)',
    desc: 'K3 旗舰模型，2.8T 参数，1M 超长上下文',
    color: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
    icon: 'Ki',
    provider: 'kimi' as const,
  },
  {
    key: 'glm',
    name: 'GLM (智谱)',
    desc: 'GLM-5.2 旗舰模型，744B MoE，1M 上下文',
    color: 'linear-gradient(135deg, #f59e0b, #ef4444)',
    icon: 'GL',
    provider: 'glm' as const,
  },
  {
    key: 'openai',
    name: 'OpenAI',
    desc: 'GPT-5.6 Sol 最新旗舰，编程与研究领先',
    color: 'linear-gradient(135deg, #10a37f, #1a7f5a)',
    icon: 'AI',
    provider: 'openai' as const,
  },
  {
    key: 'mimo',
    name: 'MiMo (小米)',
    desc: 'V2.5-Pro 万亿参数旗舰，1M 超长上下文，极致性价比',
    color: 'linear-gradient(135deg, #ff6900, #ff9500)',
    icon: 'XM',
    provider: 'mimo' as const,
  },
  {
    key: 'custom',
    name: '自定义服务',
    desc: '兼容 OpenAI API 格式的其他服务',
    color: 'linear-gradient(135deg, #8b5cf6, #6366f1)',
    icon: '...',
    provider: 'custom' as const,
  },
]

async function addFromPreset(p: typeof presets[0]) {
  // 移除已有临时配置，一次只能保留一个待添加模型
  removePendingConfigs()
  // 本地创建临时配置，不调 API
  tempIdCounter++
  const tempId = -tempIdCounter
  const defaults = {
    name: p.name,
    provider: p.provider,
    billingMode: p.provider === 'mimo' ? 'payg' : '',
    apiKey: '',
    hasKey: false,
    model: p.provider === 'mimo' ? 'mimo-v2.5-pro' : p.provider,
    baseUrl: p.provider === 'mimo' ? 'https://api.xiaomimimo.com/v1' : '',
  }
  const cfg: LLMConfig = { id: tempId, ...defaults }
  chatStore.configs.push(cfg)
  showKeyMap[tempId] = false
  // 自动展开该配置
  foldedIds.delete(tempId)
  // 不弹提示，等测试通过保存时再提示
}

async function addNewConfig() {
  // 移除已有临时配置，一次只能保留一个待添加模型
  removePendingConfigs()
  // 本地创建临时配置，不调 API
  tempIdCounter++
  const tempId = -tempIdCounter
  const defaults = {
    name: '新配置',
    provider: 'deepseek' as const,
    billingMode: '',
    apiKey: '',
    hasKey: false,
    model: 'deepseek-v4-pro',
    baseUrl: 'https://api.deepseek.com',
  }
  const cfg: LLMConfig = { id: tempId, ...defaults }
  chatStore.configs.push(cfg)
  showKeyMap[tempId] = false
  foldedIds.delete(tempId)
  // 不弹提示，等测试通过保存时再提示
}

/** 移除所有临时配置（负 id），并将清理相关的内部状态 */
function removePendingConfigs() {
  const pendingIds = chatStore.configs.filter(c => isTempId(c.id)).map(c => c.id)
  pendingIds.forEach(id => {
    const idx = chatStore.configs.findIndex(x => x.id === id)
    if (idx >= 0) chatStore.configs.splice(idx, 1)
    delete showKeyMap[id]
    foldedIds.delete(id)
  })
}

// ---- 角色约束操作 ----

async function handleAddPrompt() {
  try {
    const p = await chatStore.addPrompt({ name: '新约束' })
    activePromptEditId.value = p.id  // 展开新添加的约束
    ElMessage.success('已添加新约束')
  } catch (err: any) {
    ElMessage.error(err.message || '添加失败')
  }
}

async function handleSavePrompt(p: { id: number; name: string; content: string }) {
  try {
    await chatStore.updatePrompt(p.id, { name: p.name, content: p.content })
    activePromptEditId.value = null  // 保存后折叠
    ElMessage.success('已保存')
  } catch (err: any) {
    ElMessage.error(err.message || '保存失败')
  }
}

async function handleDeletePrompt(id: number) {
  if (chatStore.prompts.length <= 1) {
    ElMessage.warning('至少保留一个约束')
    return
  }
  try {
    await ElMessageBox.confirm('确定删除此约束？', '提示', { type: 'warning' })
    await chatStore.removePrompt(id)
    ElMessage.success('已删除')
  } catch { /* canceled */ }
}

async function onProviderChange(cfg: LLMConfig, val: string) {
  const baseUrlMap: Record<string, string> = {
    deepseek: 'https://api.deepseek.com',
    kimi: 'https://api.moonshot.cn',
    glm: 'https://open.bigmodel.cn',
    openai: 'https://api.openai.com',
    mimo: 'https://api.xiaomimimo.com/v1',
    custom: '',
  }
  const models = modelMap[val] || []
  // 更新本地对象
  cfg.provider = val as LLMConfig['provider']
  cfg.billingMode = val === 'mimo' ? 'payg' : ''
  cfg.baseUrl = baseUrlMap[val] || ''
  cfg.model = models[0] || cfg.model
  // 非临时配置 → 同步到后端
  if (!isTempId(cfg.id)) {
    try {
      await chatStore.updateConfig(cfg.id, {
        provider: val as LLMConfig['provider'],
        billingMode: val === 'mimo' ? 'payg' : '',
        baseUrl: baseUrlMap[val] || '',
        model: models[0] || cfg.model,
      })
    } catch (err: any) {
      ElMessage.error(err.message)
    }
  }
}

async function onBillingModeChange(cfg: LLMConfig, val: string) {
  const baseUrl = val === 'plan' ? 'https://token-plan-cn.xiaomimimo.com/v1' : 'https://api.xiaomimimo.com/v1'
  cfg.billingMode = val
  cfg.baseUrl = baseUrl
  // 非临时配置 → 同步到后端
  if (!isTempId(cfg.id)) {
    try {
      await chatStore.updateConfig(cfg.id, { billingMode: val, baseUrl })
    } catch (err: any) {
      ElMessage.error(err.message)
    }
  }
}

async function handleRemove(id: number) {
  if (chatStore.configs.length <= 1) {
    ElMessage.warning('至少保留一个配置')
    return
  }
  try {
    await ElMessageBox.confirm('确定删除此配置？', '提示', { type: 'warning' })
    if (isTempId(id)) {
      // 临时配置：直接从本地移除
      const idx = chatStore.configs.findIndex(c => c.id === id)
      if (idx >= 0) chatStore.configs.splice(idx, 1)
    } else {
      await chatStore.removeConfig(id)
    }
    foldedIds.delete(id)
    ElMessage.success('已删除')
  } catch { /* canceled */ }
}

async function handleTest(cfg: LLMConfig) {
  if (!cfg.apiKey) {
    ElMessage.warning('请先输入 API Key')
    return
  }
  testingId.value = cfg.id

  try {
    const apiPath = cfg.baseUrl.endsWith('/v1') ? '/chat/completions' : '/v1/chat/completions'
    const res = await fetch(`${cfg.baseUrl}${apiPath}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${cfg.apiKey}`,
      },
      body: JSON.stringify({
        model: cfg.model,
        messages: [{ role: 'user', content: 'Hi, reply with one word: OK' }],
      }),
    })

    if (res.ok) {
      const data = await res.json()
      const reply = data.choices?.[0]?.message?.content || ''
      ElMessage.success(`[${cfg.name}] 连接成功: "${reply.trim()}"`)
    } else {
      const body = await res.text()
      ElMessage.error(`[${cfg.name}] HTTP ${res.status}: ${body.slice(0, 150)}`)
    }
  } catch (err: any) {
    ElMessage.error(`[${cfg.name}] 连接失败: ${err.message}`)
  } finally {
    testingId.value = null
  }
}

/** 保存配置到后端，非临时配置直接更新，临时配置先创建再替换 */
async function handleSave(cfg: LLMConfig) {
  if (!cfg.apiKey) {
    ElMessage.warning('请先输入 API Key')
    return
  }
  testingId.value = cfg.id
  try {
    if (isTempId(cfg.id)) {
      const dto = await chatStore.addConfig({
        name: cfg.name,
        provider: cfg.provider,
        apiKey: cfg.apiKey,
        model: cfg.model,
        baseUrl: cfg.baseUrl,
      })
      // addConfig 已在末尾 push 新配置，移除旧的临时配置
      const idx = chatStore.configs.findIndex(c => c.id === cfg.id)
      if (idx >= 0) {
        chatStore.configs.splice(idx, 1)
      }
      foldConfig(dto.id)
      ElMessage.success(`已添加 ${cfg.name} 配置`)
    } else {
      await chatStore.updateConfig(cfg.id, {
        name: cfg.name,
        provider: cfg.provider,
        model: cfg.model,
        baseUrl: cfg.baseUrl,
        apiKey: cfg.apiKey,
      })
      foldConfig(cfg.id)
      ElMessage.success(`已保存 ${cfg.name} 配置`)
    }
  } catch (err: any) {
    ElMessage.error(err.message || '保存失败')
  } finally {
    testingId.value = null
  }
}
</script>

<style scoped>
.llm-settings-page {
  max-width: 1400px;
  margin: 0 auto;
}
.page-header {
  margin-bottom: 28px;
}
.page-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-heading);
  margin: 0;
}
.page-desc {
  font-size: 14px;
  color: var(--text-muted);
  margin: 4px 0 0;
}

.settings-grid {
  display: grid;
  grid-template-columns: 400px 1fr;
  gap: 28px;
  align-items: start;
}
@media (max-width: 1000px) {
  .settings-grid { grid-template-columns: 1fr; }
}

/* 卡片 */
.config-card, .info-card {
  border-radius: 12px;
}
.info-card + .info-card {
  margin-top: 20px;
}
.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: var(--text-heading);
}
.card-header-between {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.card-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 配置列表 */
.empty-configs {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 32px 16px;
  font-size: 13px;
  color: var(--text-muted);
}
.prompt-hint {
  font-size: 12px;
  color: var(--text-muted);
  margin-right: 8px;
}
.card-header-actions {
  display: flex;
  align-items: center;
}
.form-item-hint {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 4px;
  line-height: 1.4;
}
.config-item {
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 16px;
  margin-bottom: 12px;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.config-item.active {
  border-color: var(--primary-color);
  box-shadow: 0 0 0 1px var(--primary-color);
}
.config-item:last-child {
  margin-bottom: 0;
}
.config-item.folded {
  padding: 0;
}
.config-item.folded.active {
  box-shadow: none;
  border-color: var(--border-color);
}
.config-item.folded.active .folded-view {
  border-color: var(--primary-color);
  box-shadow: 0 0 0 1px var(--primary-color);
  border-radius: 10px;
}

/* 折叠态 */
.folded-view {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.folded-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 0;
}
.folded-icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  flex-shrink: 0;
}
.folded-info {
  min-width: 0;
  flex: 1;
}
.folded-name {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-heading);
}
.folded-model {
  font-size: 12px;
  font-weight: 400;
  color: var(--text-muted);
}
.folded-meta {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 2px;
  display: flex;
  align-items: center;
  gap: 4px;
}
.folded-dot {
  opacity: 0.4;
}
.folded-masked {
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: 12px;
  letter-spacing: 0.5px;
}
.folded-actions {
  display: flex;
  align-items: center;
  gap: 2px;
  flex-shrink: 0;
  margin-left: 12px;
}
.folded-actions .el-button {
  font-size: 12px;
}

.config-item-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.config-item-name {
  display: flex;
  align-items: center;
  gap: 8px;
}
.name-input {
  width: 160px;
}
.config-item-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}
.active-tag {
  flex-shrink: 0;
}

/* 内联表单 */
.config-inner-form {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 16px;
}
.config-inner-form .el-form-item {
  margin-bottom: 8px;
}
.config-inner-form .el-form-item:last-child {
  grid-column: 1 / -1;
}

/* 连接状态 */
.test-result {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 10px;
}
.test-result.success {
  background: rgba(103, 194, 58, 0.08);
  color: var(--success-color, #67c23a);
}
.test-result.error {
  background: rgba(245, 108, 108, 0.08);
  color: var(--danger-color, #f56c6c);
}
.test-title {
  font-size: 14px;
  font-weight: 600;
}
.test-detail {
  font-size: 12px;
  opacity: 0.8;
  margin-top: 2px;
  word-break: break-all;
}
.test-placeholder {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  font-size: 13px;
  color: var(--text-muted);
}

/* 提供商列表 */
.provider-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.provider-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid var(--border-color);
  cursor: pointer;
  transition: all 0.15s;
}
.provider-item:hover {
  border-color: var(--primary-color);
  background: rgba(64, 158, 255, 0.04);
}
.provider-icon {
  width: 34px;
  height: 34px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
}
.provider-info {
  flex: 1;
  min-width: 0;
}
.provider-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-heading);
}
.provider-desc {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 1px;
}
.provider-arrow {
  color: var(--text-muted);
  flex-shrink: 0;
  transition: transform 0.15s;
}
.provider-item:hover .provider-arrow {
  transform: translateX(2px);
  color: var(--primary-color);
}

/* 提示列表 */
.tips-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.tip-item {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  color: var(--text-secondary);
}
.tip-num {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: linear-gradient(135deg, #409eff, #8b5cf6);
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.key-toggle {
  cursor: pointer;
  color: var(--text-muted);
  transition: color 0.15s;
}
.key-toggle:hover {
  color: var(--primary-color);
}
</style>
