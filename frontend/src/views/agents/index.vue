<template>
  <div class="agents-page">
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ t('nav.agentManagement') }}</h2>
        <p class="page-subtitle">
          {{ clusterStore.currentCluster ? clusterStore.currentCluster.name : t('agents.subtitle') }}
        </p>
      </div>
    </div>

    <div class="agents-layout">
      <!-- 左侧：Agent 列表 -->
      <div class="agents-sidebar">
        <div class="sidebar-header">
          <span class="sidebar-title">{{ t('agents.agentList') }}</span>
          <el-tag size="small" type="info">{{ agents.length }}</el-tag>
        </div>
        <div class="agents-list" v-loading="loading">
          <div
            v-for="agent in agents"
            :key="agent.agent_id"
            class="agent-card"
            :class="{ active: selectedAgent?.agent_id === agent.agent_id }"
            @click="selectAgent(agent)"
          >
            <div class="agent-card-header">
              <span class="agent-hostname">{{ agent.hostname }}</span>
              <el-tag :type="statusType(agent.status)" size="small">{{ agent.status_display }}</el-tag>
            </div>
            <div class="agent-card-meta">
              <span class="meta-item">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>
                </svg>
                {{ agent.version }}
                <el-tag v-if="isOutdated(agent.version)" type="warning" size="small" class="version-mini">
                  {{ t('clusters.updateAvailable') }}
                </el-tag>
              </span>
              <span class="meta-item">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8"/><path d="M12 17v4"/>
                </svg>
                {{ agent.total_scans }} {{ t('clusters.scanCount') }}
              </span>
            </div>
            <div class="agent-card-time">
              {{ agent.last_heartbeat_at ? formatTime(agent.last_heartbeat_at) : t('clusters.never') }}
            </div>
          </div>
          <el-empty v-if="!loading && agents.length === 0" :description="t('clusters.noAgent')" :image-size="60" />
        </div>
      </div>

      <!-- 右侧：详情 + 事件 -->
      <div class="agents-detail">
        <template v-if="selectedAgent">
          <!-- Agent 详情卡片 -->
          <el-card shadow="hover" class="detail-card">
            <div class="detail-header">
              <div class="detail-title-row">
                <h3 class="detail-title">{{ selectedAgent.hostname }}</h3>
                <el-tag :type="statusType(selectedAgent.status)" size="default">
                  {{ selectedAgent.status_display }}
                </el-tag>
                <el-tag v-if="isOutdated(selectedAgent.version)" type="warning" size="default">
                  {{ t('clusters.updateAvailable') }}
                </el-tag>
              </div>
              <code class="agent-id-full">{{ selectedAgent.agent_id }}</code>
            </div>

            <el-descriptions :column="3" border class="detail-descriptions">
              <el-descriptions-item :label="t('common.version')">
                {{ selectedAgent.version }}
              </el-descriptions-item>
              <el-descriptions-item :label="t('agents.ipAddress')">
                {{ selectedAgent.ip_address || '-' }}
              </el-descriptions-item>
              <el-descriptions-item :label="t('agents.platform')">
                {{ selectedAgent.platform || '-' }}
              </el-descriptions-item>
              <el-descriptions-item :label="t('clusters.scanCount')">
                {{ selectedAgent.total_scans }}
              </el-descriptions-item>
              <el-descriptions-item :label="t('agents.failedScans')">
                <span :class="{ 'text-danger': selectedAgent.failed_scans > 0 }">
                  {{ selectedAgent.failed_scans }}
                </span>
              </el-descriptions-item>
              <el-descriptions-item :label="t('agents.startedAt')">
                {{ formatDateTime(selectedAgent.started_at) }}
              </el-descriptions-item>
              <el-descriptions-item :label="t('clusters.lastHeartbeat')">
                {{ selectedAgent.last_heartbeat_at ? formatDateTime(selectedAgent.last_heartbeat_at) : '-' }}
              </el-descriptions-item>
              <el-descriptions-item :label="t('agents.lastScan')">
                {{ selectedAgent.last_scan_at ? formatDateTime(selectedAgent.last_scan_at) : '-' }}
              </el-descriptions-item>
            </el-descriptions>
          </el-card>

          <!-- Agent 事件列表 -->
          <el-card shadow="hover" class="events-card">
            <template #header>
              <div class="events-header-bar">
                <span class="events-title">{{ t('agents.agentEvents') }}</span>
                <el-select v-model="eventFilter" :placeholder="t('clusters.eventTypeFilter')" clearable size="small" @change="resetAndLoadEvents">
                  <el-option value="register" :label="t('clusters.eventRegister')" />
                  <el-option value="scan_upload" :label="t('clusters.eventScanUpload')" />
                  <el-option value="scan_failed" :label="t('clusters.eventScanFailed')" />
                  <el-option value="version_upgrade" :label="t('clusters.eventVersionUpgrade')" />
                  <el-option value="status_change" :label="t('clusters.eventStatusChange')" />
                  <el-option value="error" :label="t('clusters.eventError')" />
                  <el-option value="unregister" :label="t('clusters.eventUnregister')" />
                </el-select>
              </div>
            </template>

            <div class="events-list" ref="eventsListRef" @scroll="handleScroll">
              <div
                v-for="event in events"
                :key="event.id"
                class="event-item"
              >
                <div class="event-time">{{ formatTime(event.created_at) }}</div>
                <div class="event-content">
                  <div class="event-type-row">
                    <el-tag :type="eventTypeTagType(event.event_type)" size="small">
                      {{ event.event_type_display }}
                    </el-tag>
                    <span v-if="event.version" class="event-version">
                      <span v-if="event.old_version">{{ event.old_version }} → </span>
                      {{ event.version }}
                    </span>
                  </div>
                  <div class="event-detail">{{ event.detail }}</div>
                </div>
              </div>

              <div v-if="eventsLoading" class="events-loading">
                <el-icon class="is-loading"><Loading /></el-icon>
                <span>{{ t('common.loading') }}</span>
              </div>

              <div v-if="!eventsLoading && events.length === 0" class="events-empty">
                {{ t('common.noData') }}
              </div>

              <div v-if="!eventsLoading && !hasMore && events.length > 0" class="events-end">
                {{ t('agents.noMoreEvents') }}
              </div>
            </div>
          </el-card>
        </template>

        <div v-else class="no-selection">
          <el-icon :size="48"><User /></el-icon>
          <p>{{ t('agents.selectAgent') }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { Loading, User } from '@element-plus/icons-vue'
import { useClusterStore } from '@/stores/cluster'
import { getAgentInstances, getAgentEvents, getLatestAgentVersion } from '@/api/clusters'
import type { AgentInstance, AgentEvent } from '@/api/clusters'

const { t } = useI18n()
const clusterStore = useClusterStore()

const loading = ref(false)
const agents = ref<AgentInstance[]>([])
const latestVersion = ref('')
const selectedAgent = ref<AgentInstance | null>(null)

// Agent 事件
const events = ref<AgentEvent[]>([])
const eventsLoading = ref(false)
const eventsPage = ref(1)
const hasMore = ref(true)
const eventFilter = ref('')
const eventsListRef = ref<HTMLElement | null>(null)

async function loadLatestVersion() {
  try {
    const res = await getLatestAgentVersion()
    latestVersion.value = res.latest_version
  } catch {
    // non-critical
  }
}

async function loadAgents() {
  loading.value = true
  try {
    const params: any = { page_size: 100 }
    if (clusterStore.currentClusterId) {
      params.cluster_id = clusterStore.currentClusterId
    }
    const res = await getAgentInstances(params)
    agents.value = res.results || []
    // 如果当前选中的 Agent 不在列表中，清空选择
    if (selectedAgent.value) {
      const found = agents.value.find(a => a.agent_id === selectedAgent.value!.agent_id)
      if (!found) {
        selectedAgent.value = null
      }
    }
  } catch {
    // error handled by interceptor
  } finally {
    loading.value = false
  }
}

function selectAgent(agent: AgentInstance) {
  selectedAgent.value = agent
  resetAndLoadEvents()
}

function resetAndLoadEvents() {
  events.value = []
  eventsPage.value = 1
  hasMore.value = true
  loadEvents()
}

async function loadEvents() {
  if (!selectedAgent.value || eventsLoading.value || !hasMore.value) return
  eventsLoading.value = true
  try {
    const params: any = {
      agent_id: selectedAgent.value.agent_id,
      page: eventsPage.value,
      page_size: 20,
    }
    if (eventFilter.value) {
      params.event_type = eventFilter.value
    }
    const res = await getAgentEvents(params)
    const newEvents = res.results || []
    events.value = [...events.value, ...newEvents]
    hasMore.value = newEvents.length >= 20
    eventsPage.value++
  } catch {
    // error handled by interceptor
  } finally {
    eventsLoading.value = false
  }
}

function handleScroll() {
  if (!eventsListRef.value) return
  const { scrollTop, scrollHeight, clientHeight } = eventsListRef.value
  // 距离底部 50px 时加载更多
  if (scrollHeight - scrollTop - clientHeight < 50 && !eventsLoading.value && hasMore.value) {
    loadEvents()
  }
}

function statusType(s: string) {
  return s === 'online' ? 'success' : s === 'error' ? 'danger' : 'info'
}

function isOutdated(version: string) {
  if (!latestVersion.value || !version) return false
  const pa = version.split('.').map(Number)
  const pb = latestVersion.value.split('.').map(Number)
  for (let i = 0; i < Math.max(pa.length, pb.length); i++) {
    const na = pa[i] || 0
    const nb = pb[i] || 0
    if (na < nb) return true
    if (na > nb) return false
  }
  return false
}

function eventTypeTagType(s: string) {
  const map: Record<string, string> = {
    register: 'success',
    scan_upload: '',
    scan_failed: 'danger',
    version_upgrade: 'warning',
    status_change: 'warning',
    error: 'danger',
    unregister: 'info',
  }
  return map[s] || ''
}

function formatTime(iso: string) {
  const d = new Date(iso)
  const now = new Date()
  const diff = (now.getTime() - d.getTime()) / 1000
  if (diff < 60) return t('common.justNow')
  if (diff < 3600) return `${Math.floor(diff / 60)} ${t('common.minutesAgo')}`
  if (diff < 86400) return `${Math.floor(diff / 3600)} ${t('common.hoursAgo')}`
  return d.toLocaleDateString('zh-CN')
}

function formatDateTime(iso: string) {
  if (!iso) return '-'
  const d = new Date(iso)
  return d.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

// 监听集群变化
watch(() => clusterStore.currentClusterId, () => {
  selectedAgent.value = null
  events.value = []
  loadAgents()
})

onMounted(() => {
  loadLatestVersion()
  loadAgents()
})
</script>

<style scoped>
.agents-page {
  max-width: 1600px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 20px;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary, #303133);
  margin: 0;
}

.page-subtitle {
  font-size: 14px;
  color: var(--text-secondary, #909399);
  margin: 4px 0 0;
}

/* 主布局：左右分栏 */
.agents-layout {
  display: flex;
  gap: 20px;
  height: calc(100vh - 180px);
  min-height: 500px;
}

/* 左侧边栏 */
.agents-sidebar {
  width: 280px;
  flex-shrink: 0;
  background: var(--bg-secondary, #fff);
  border-radius: 12px;
  border: 1px solid var(--border-light, #ebeef5);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 16px 12px;
  border-bottom: 1px solid var(--border-light, #ebeef5);
}

.sidebar-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary, #303133);
}

.agents-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.agent-card {
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  margin-bottom: 4px;
}

.agent-card:hover {
  background: rgba(64, 158, 255, 0.08);
}

.agent-card.active {
  background: rgba(64, 158, 255, 0.12);
  box-shadow: inset 3px 0 0 #409eff;
}

.agent-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.agent-hostname {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary, #303133);
}

.agent-card-meta {
  display: flex;
  gap: 12px;
  margin-bottom: 4px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--text-secondary, #909399);
}

.version-mini {
  margin-left: 2px;
  font-size: 10px;
  padding: 0 4px;
  height: 16px;
  line-height: 16px;
}

.agent-card-time {
  font-size: 11px;
  color: var(--text-muted, #c0c4cc);
}

/* 右侧详情区 */
.agents-detail {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow: hidden;
}

/* Agent 详情卡片 */
.detail-card {
  flex-shrink: 0;
}

.detail-header {
  margin-bottom: 16px;
}

.detail-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 4px;
}

.detail-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
  color: var(--text-primary, #303133);
}

.agent-id-full {
  font-size: 12px;
  color: var(--text-secondary, #909399);
  word-break: break-all;
}

.detail-descriptions {
  margin-top: 12px;
}

.text-danger {
  color: #f56c6c;
  font-weight: 600;
}

/* 事件卡片 */
.events-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.events-card :deep(.el-card__body) {
  flex: 1;
  overflow: hidden;
  padding: 0;
}

.events-header-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.events-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary, #303133);
}

.events-list {
  height: 100%;
  max-height: 400px;
  overflow-y: auto;
  padding: 12px 16px;
}

.event-item {
  display: flex;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid var(--border-light, #f0f0f0);
}

.event-item:last-child {
  border-bottom: none;
}

.event-time {
  flex-shrink: 0;
  width: 80px;
  font-size: 12px;
  color: var(--text-secondary, #909399);
  text-align: right;
}

.event-content {
  flex: 1;
  min-width: 0;
}

.event-type-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.event-version {
  font-size: 12px;
  color: var(--text-secondary, #909399);
}

.event-detail {
  font-size: 13px;
  color: var(--text-primary, #303133);
  line-height: 1.5;
  word-break: break-word;
}

.events-loading,
.events-empty,
.events-end {
  text-align: center;
  padding: 16px;
  color: var(--text-secondary, #909399);
  font-size: 13px;
}

.events-loading .el-icon {
  margin-right: 4px;
}

/* 未选择状态 */
.no-selection {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: var(--text-muted, #c0c4cc);
}

.no-selection p {
  font-size: 14px;
  margin: 0;
}

/* 滚动条美化 */
.agents-list::-webkit-scrollbar,
.events-list::-webkit-scrollbar {
  width: 6px;
}

.agents-list::-webkit-scrollbar-thumb,
.events-list::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.1);
  border-radius: 3px;
}

.agents-list::-webkit-scrollbar-thumb:hover,
.events-list::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.2);
}

:deep(.el-card__body) {
  padding: 16px;
}

:deep(.el-descriptions__label) {
  font-weight: 500;
}
</style>
