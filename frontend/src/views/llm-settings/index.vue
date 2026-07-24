<template>
  <div class="llm-settings-page">
    <div class="page-header">
      <div>
        <h2 class="page-title">AI 助手配置</h2>
        <p class="page-desc">配置大语言模型服务，用于集群智能分析与运维建议</p>
      </div>
    </div>

    <div class="settings-grid">
      <!-- 左侧：配置表单 -->
      <div class="settings-form-wrap">
        <el-card shadow="hover" class="config-card">
          <template #header>
            <div class="card-header">
              <el-icon :size="18"><Setting /></el-icon>
              <span>模型配置</span>
            </div>
          </template>

          <el-form :model="form" label-position="top" class="llm-form">
            <el-form-item label="服务提供商">
              <el-segmented v-model="form.provider" :options="providers" @change="onProviderChange" />
            </el-form-item>

            <el-form-item label="API Key" required>
              <el-input
                v-model="form.apiKey"
                :type="showKey ? 'text' : 'password'"
                placeholder="输入 API Key"
              >
                <template #suffix>
                  <el-icon class="key-toggle" @click="showKey = !showKey">
                    <View v-if="showKey" />
                    <Hide v-else />
                  </el-icon>
                </template>
              </el-input>
              <div class="form-hint">
                <el-icon :size="12"><InfoFilled /></el-icon>
                <span>API Key 仅存储在浏览器本地，不会上传到服务器</span>
              </div>
            </el-form-item>

            <el-form-item label="模型">
              <el-select v-model="form.model" filterable allow-create class="w-full">
                <el-option v-for="m in availableModels" :key="m" :label="m" :value="m" />
              </el-select>
            </el-form-item>

            <el-form-item v-if="form.provider === 'custom'" label="API 地址">
              <el-input v-model="form.baseUrl" placeholder="https://api.example.com" />
              <div class="form-hint">兼容 OpenAI API 格式的服务地址，无需加 /v1</div>
            </el-form-item>

            <el-form-item label="Temperature">
              <div class="slider-row">
                <el-slider
                  v-model="form.temperature"
                  :min="0"
                  :max="2"
                  :step="0.1"
                  :show-tooltip="false"
                  class="flex-1"
                />
                <span class="slider-val">{{ form.temperature.toFixed(1) }}</span>
              </div>
              <div class="form-hint">低值 = 精确稳定，高值 = 创意多样。建议 0.3~0.7</div>
            </el-form-item>

            <el-form-item label="Max Tokens">
              <el-input-number v-model="form.maxTokens" :min="256" :max="32768" :step="256" />
              <div class="form-hint">单次回复最大长度，长分析建议 4096+</div>
            </el-form-item>

            <el-form-item>
              <div class="form-actions">
                <el-button type="primary" :loading="saving" @click="handleSave">
                  保存配置
                </el-button>
                <el-button :loading="testing" @click="handleTest">
                  测试连接
                </el-button>
              </div>
            </el-form-item>
          </el-form>
        </el-card>
      </div>

      <!-- 右侧：说明 + 预置 -->
      <div class="settings-info-wrap">
        <!-- 连接状态 -->
        <el-card shadow="hover" class="info-card">
          <template #header>
            <div class="card-header">
              <el-icon :size="18"><Connection /></el-icon>
              <span>连接状态</span>
            </div>
          </template>
          <div v-if="testResult" class="test-result" :class="testResult.ok ? 'success' : 'error'">
            <el-icon :size="20">
              <CircleCheckFilled v-if="testResult.ok" />
              <CircleCloseFilled v-else />
            </el-icon>
            <div>
              <div class="test-title">{{ testResult.ok ? '连接成功' : '连接失败' }}</div>
              <div class="test-detail">{{ testResult.message }}</div>
            </div>
          </div>
          <div v-else class="test-placeholder">
            <el-icon :size="24" color="var(--text-muted)"><InfoFilled /></el-icon>
            <span>点击「测试连接」验证 API 配置</span>
          </div>
        </el-card>

        <!-- 预置提供商 -->
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
              @click="applyPreset(p)"
            >
              <div class="provider-icon" :style="{ background: p.color }">
                <span>{{ p.icon }}</span>
              </div>
              <div class="provider-info">
                <div class="provider-name">{{ p.name }}</div>
                <div class="provider-desc">{{ p.desc }}</div>
              </div>
              <el-icon class="provider-arrow"><ArrowRight /></el-icon>
            </div>
          </div>
        </el-card>

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
              <span>选择服务商并填入 API Key</span>
            </div>
            <div class="tip-item">
              <span class="tip-num">2</span>
              <span>点击测试连接验证配置是否正确</span>
            </div>
            <div class="tip-item">
              <span class="tip-num">3</span>
              <span>右下角气泡打开 AI 助手开始对话</span>
            </div>
            <div class="tip-item">
              <span class="tip-num">4</span>
              <span>AI 会自动结合当前选中集群的数据进行分析</span>
            </div>
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
import { ElMessage } from 'element-plus'
import {
  Setting, Connection, Promotion, Document, View, Hide,
  InfoFilled, CircleCheckFilled, CircleCloseFilled, ArrowRight,
} from '@element-plus/icons-vue'

const chatStore = useChatStore()

const showKey = ref(false)
const saving = ref(false)
const testing = ref(false)
const testResult = ref<{ ok: boolean; message: string } | null>(null)

const form = reactive<LLMConfig>({
  provider: 'deepseek',
  apiKey: '',
  model: 'deepseek-chat',
  baseUrl: 'https://api.deepseek.com',
  temperature: 0.7,
  maxTokens: 4096,
})

const providers = [
  { label: 'DeepSeek', value: 'deepseek' },
  { label: 'OpenAI', value: 'openai' },
  { label: '自定义', value: 'custom' },
]

const modelMap: Record<string, string[]> = {
  deepseek: ['deepseek-chat', 'deepseek-reasoner'],
  openai: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-3.5-turbo'],
  custom: ['custom-model'],
}

const baseUrlMap: Record<string, string> = {
  deepseek: 'https://api.deepseek.com',
  openai: 'https://api.openai.com',
  custom: '',
}

const availableModels = computed(() => modelMap[form.provider] || [])

const presets = [
  {
    key: 'deepseek',
    name: 'DeepSeek',
    desc: '国产大模型，性价比高，中文能力强',
    color: 'linear-gradient(135deg, #409eff, #36d399)',
    icon: 'DS',
    provider: 'deepseek' as const,
    baseUrl: 'https://api.deepseek.com',
    model: 'deepseek-chat',
  },
  {
    key: 'openai',
    name: 'OpenAI GPT-4o',
    desc: '全球领先的多模态大模型',
    color: 'linear-gradient(135deg, #10a37f, #1a7f5a)',
    icon: 'AI',
    provider: 'openai' as const,
    baseUrl: 'https://api.openai.com',
    model: 'gpt-4o',
  },
  {
    key: 'custom',
    name: '自定义服务',
    desc: '兼容 OpenAI API 格式的其他服务',
    color: 'linear-gradient(135deg, #8b5cf6, #6366f1)',
    icon: '...',
    provider: 'custom' as const,
    baseUrl: '',
    model: 'custom-model',
  },
]

onMounted(() => {
  const cfg = chatStore.config
  form.provider = cfg.provider
  form.apiKey = cfg.apiKey
  form.model = cfg.model
  form.baseUrl = cfg.baseUrl
  form.temperature = cfg.temperature
  form.maxTokens = cfg.maxTokens
})

function onProviderChange(val: string) {
  form.baseUrl = baseUrlMap[val] || ''
  const models = modelMap[val]
  if (models?.length) form.model = models[0]
}

function applyPreset(p: typeof presets[0]) {
  form.provider = p.provider
  form.baseUrl = p.baseUrl
  form.model = p.model
}

async function handleSave() {
  if (!form.apiKey) {
    ElMessage.warning('请输入 API Key')
    return
  }
  saving.value = true
  try {
    chatStore.updateConfig({ ...form })
    ElMessage.success('配置已保存')
  } finally {
    saving.value = false
  }
}

async function handleTest() {
  if (!form.apiKey) {
    ElMessage.warning('请先输入 API Key')
    return
  }
  testing.value = true
  testResult.value = null

  const url = `${form.baseUrl}/v1/chat/completions`

  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${form.apiKey}`,
      },
      body: JSON.stringify({
        model: form.model,
        messages: [{ role: 'user', content: 'Hi, reply with one word: OK' }],
        max_tokens: 10,
      }),
    })

    if (res.ok) {
      const data = await res.json()
      const reply = data.choices?.[0]?.message?.content || ''
      testResult.value = { ok: true, message: `模型响应: "${reply.trim()}"` }
    } else {
      const body = await res.text()
      testResult.value = { ok: false, message: `HTTP ${res.status}: ${body.slice(0, 150)}` }
    }
  } catch (err: any) {
    testResult.value = { ok: false, message: `连接失败: ${err.message}` }
  } finally {
    testing.value = false
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
  grid-template-columns: 520px 1fr;
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

/* 表单 */
.llm-form {
  padding: 4px 0;
}
.w-full {
  width: 100%;
}
.form-hint {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 4px;
}
.slider-row {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
}
.flex-1 {
  flex: 1;
}
.slider-val {
  font-size: 14px;
  font-weight: 600;
  color: var(--primary-color);
  min-width: 32px;
  text-align: center;
}
.form-actions {
  display: flex;
  gap: 12px;
}
.key-toggle {
  cursor: pointer;
  color: var(--text-muted);
  transition: color 0.15s;
}
.key-toggle:hover {
  color: var(--primary-color);
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
  padding: 12px;
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
  width: 36px;
  height: 36px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 13px;
  font-weight: 700;
  flex-shrink: 0;
}
.provider-info {
  flex: 1;
  min-width: 0;
}
.provider-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-heading);
}
.provider-desc {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 2px;
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
</style>
