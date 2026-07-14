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

    <!-- 筛选栏 -->
    <el-card shadow="hover" class="filter-card">
      <div class="filter-row">
        <el-select v-model="filterStatus" :placeholder="t('agents.filterStatus')" clearable @change="loadAgents">
          <el-option value="online" :label="t('agents.online')" />
          <el-option value="offline" :label="t('agents.offline')" />
          <el-option value="error" :label="t('agents.error')" />
          <el-option value="paused" :label="t('agents.paused')" />
        </el-select>
        <el-button @click="loadAgents" :icon="Refresh">{{ t('common.search') }}</el-button>
      </div>
    </el-card>

    <!-- Agent 列表 -->
    <el-card shadow="hover" class="table-card">
      <el-table :data="agents" stripe v-loading="loading" @row-click="viewAgentEvents">
        <el-table-column :label="t('clusters.hostname')" width="120" prop="hostname" />
        <el-table-column label="Agent ID" width="150">
          <template #default="{ row }">
            <code class="agent-id">{{ row.agent_id.slice(0, 12) }}...</code>
          </template>
        </el-table-column>
        <el-table-column :label="t('common.status')" width="90">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ row.status_display }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="t('common.version')" width="120">
          <template #default="{ row }">
            <span>{{ row.version }}</span>
            <el-tag v-if="isOutdated(row.version)" type="warning" size="small" class="version-tag">
              {{ t('clusters.updateAvailable') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="t('clusters.scanCount')" width="90" prop="total_scans" />
        <el-table-column :label="t('agents.ipAddress')" width="130" prop="ip_address" />
        <el-table-column :label="t('agents.platform')" min-width="120" prop="platform" show-overflow-tooltip />
        <el-table-column :label="t('clusters.lastHeartbeat')" width="140">
          <template #default="{ row }">
            {{ row.last_heartbeat_at ? formatTime(row.last_heartbeat_at) : t('clusters.never') }}
          </template>
        </el-table-column>
        <el-table-column :label="t('agents.lastScan')" width="140">
          <template #default="{ row }">
            {{ row.last_scan_at ? formatTime(row.last_scan_at) : t('clusters.never') }}
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper" v-if="total > 0">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="loadAgents"
        />
      </div>
    </el-card>

    <!-- Agent 事件弹窗 -->
    <el-dialog v-model="showEvents" :title="t('agents.agentEvents')" width="900px">
      <template v-if="selectedAgent">
        <div class="events-header">
          <span class="events-agent-info">
            {{ selectedAgent.hostname }} ({{ selectedAgent.cluster_name }})
          </span>
        </div>

        <div class="events-filter">
          <el-select v-model="eventFilter" :placeholder="t('clusters.eventTypeFilter')" clearable size="small" @change="loadEvents">
            <el-option value="register" :label="t('clusters.eventRegister')" />
            <el-option value="scan_upload" :label="t('clusters.eventScanUpload')" />
            <el-option value="scan_failed" :label="t('clusters.eventScanFailed')" />
            <el-option value="version_upgrade" :label="t('clusters.eventVersionUpgrade')" />
            <el-option value="status_change" :label="t('clusters.eventStatusChange')" />
            <el-option value="error" :label="t('clusters.eventError')" />
            <el-option value="unregister" :label="t('clusters.eventUnregister')" />
          </el-select>
        </div>

        <el-table :data="events" stripe v-loading="eventsLoading">
          <el-table-column :label="t('common.time')" width="140">
            <template #default="{ row }">
              {{ formatTime(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column :label="t('clusters.eventType')" width="120">
            <template #default="{ row }">
              <el-tag :type="eventTypeTagType(row.event_type)" size="small">
                {{ row.event_type_display }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column :label="t('common.version')" width="140">
            <template #default="{ row }">
              <span v-if="row.old_version">{{ row.old_version }} → </span>
              <span>{{ row.version }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="detail" :label="t('common.detail')" min-width="250" show-overflow-tooltip />
        </el-table>

        <div class="pagination-wrapper" v-if="eventsTotal > 0">
          <el-pagination
            v-model:current-page="eventsPage"
            :page-size="20"
            :total="eventsTotal"
            layout="prev, pager, next"
            @current-change="loadEvents"
          />
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { Refresh } from '@element-plus/icons-vue'
import { useClusterStore } from '@/stores/cluster'
import { getAgentInstances, getAgentEvents, getLatestAgentVersion } from '@/api/clusters'
import type { AgentInstance, AgentEvent } from '@/api/clusters'

const { t } = useI18n()
const clusterStore = useClusterStore()

const loading = ref(false)
const agents = ref<AgentInstance[]>([])
const latestVersion = ref('')
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)

// 筛选
const filterStatus = ref('')

// Agent 事件弹窗
const showEvents = ref(false)
const selectedAgent = ref<AgentInstance | null>(null)
const events = ref<AgentEvent[]>([])
const eventsLoading = ref(false)
const eventsPage = ref(1)
const eventsTotal = ref(0)
const eventFilter = ref('')

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
    const params: any = {
      page: currentPage.value,
      page_size: pageSize.value,
    }
    if (clusterStore.currentClusterId) {
      params.cluster_id = clusterStore.currentClusterId
    }
    if (filterStatus.value) {
      params.status = filterStatus.value
    }
    const res = await getAgentInstances(params)
    agents.value = res.results || []
    total.value = res.count || 0
  } catch {
    // error handled by interceptor
  } finally {
    loading.value = false
  }
}

function viewAgentEvents(row: AgentInstance) {
  selectedAgent.value = row
  showEvents.value = true
  events.value = []
  eventsPage.value = 1
  eventsTotal.value = 0
  eventFilter.value = ''
  loadEvents()
}

async function loadEvents() {
  if (!selectedAgent.value) return
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
    events.value = res.results || []
    eventsTotal.value = res.count || 0
  } catch {
    // error handled by interceptor
  } finally {
    eventsLoading.value = false
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

// 监听集群变化
watch(() => clusterStore.currentClusterId, () => {
  currentPage.value = 1
  loadAgents()
})

onMounted(() => {
  loadLatestVersion()
  loadAgents()
})
</script>

<style scoped>
.agents-page {
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
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

.filter-card {
  margin-bottom: 16px;
}

.filter-row {
  display: flex;
  gap: 12px;
  align-items: center;
}

.table-card {
  min-height: 400px;
}

.agent-id {
  font-size: 12px;
  color: var(--text-secondary, #909399);
}

.version-tag {
  margin-left: 4px;
  font-size: 11px;
}

.pagination-wrapper {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.events-header {
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border-light, #ebeef5);
}

.events-agent-info {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary, #303133);
}

.events-filter {
  margin-bottom: 16px;
}

:deep(.el-card__body) {
  padding: 20px 24px;
}

:deep(.el-table) {
  cursor: pointer;
}
</style>
