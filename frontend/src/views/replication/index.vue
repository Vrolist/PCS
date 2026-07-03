<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ t('advanced.replication.title') }}</h2>
        <p class="page-desc">{{ t('advanced.replication.subtitle') }}</p>
      </div>
    </div>

    <div class="stats-row">
      <div class="el-card is-never-shadow stat-card">
        <div class="el-card__body">
          <div class="stat-label">{{ t('advanced.replication.totalJobs') }}</div>
          <div class="stat-value">{{ jobs.length }}</div>
        </div>
      </div>
      <div class="el-card is-never-shadow stat-card">
        <div class="el-card__body">
          <div class="stat-label">{{ t('advanced.replication.activeJobs') }}</div>
          <div class="stat-value stat-active">{{ activeCount }}</div>
        </div>
      </div>
      <div class="el-card is-never-shadow stat-card">
        <div class="el-card__body">
          <div class="stat-label">{{ t('advanced.replication.syncSuccess') }}</div>
          <div class="stat-value stat-success">{{ totalSyncCount }}</div>
        </div>
      </div>
      <div class="el-card is-never-shadow stat-card">
        <div class="el-card__body">
          <div class="stat-label">{{ t('advanced.replication.lastSyncTime') }}</div>
          <div class="stat-value stat-time">{{ latestSyncDisplay }}</div>
        </div>
      </div>
    </div>

    <el-card shadow="hover" class="table-card">
      <div class="table-toolbar">
        <el-input
          v-model="searchText"
          :placeholder="t('advanced.replication.searchPlaceholder')"
          clearable
          style="width: 280px"
          @input="onSearch"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-select v-model="statusFilter" :placeholder="t('common.status')" clearable style="width: 140px" @change="fetchData">
          <el-option :label="t('advanced.replication.active')" value="active" />
          <el-option :label="t('advanced.replication.disabled')" value="disabled" />
          <el-option :label="t('advanced.replication.error')" value="error" />
          <el-option :label="t('advanced.replication.syncing')" value="syncing" />
        </el-select>
      </div>

      <el-table :data="filteredJobs" stripe style="width: 100%" v-loading="loading" :empty-text="t('advanced.replication.noData')">
        <el-table-column prop="job_id" :label="t('advanced.replication.jobId')" min-width="90" />
        <el-table-column prop="vmid" :label="t('advanced.replication.vmid')" min-width="80" align="center">
          <template #default="{ row }">
            <span v-if="row.vmid != null">{{ row.vmid }}</span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="resource_type" :label="t('advanced.replication.resourceType')" min-width="80" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="row.resource_type === 'vm' ? 'primary' : 'success'" effect="plain">
              {{ row.resource_type === 'vm' ? 'VM' : 'CT' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="source_node" :label="t('advanced.replication.sourceNode')" min-width="120" />
        <el-table-column prop="target_node" :label="t('advanced.replication.targetNode')" min-width="120">
          <template #default="{ row }">
            <div class="target-cell">
              <el-icon class="arrow-icon"><Right /></el-icon>
              <span>{{ row.target_node }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="schedule" :label="t('advanced.replication.schedule')" min-width="90" align="center" />
        <el-table-column prop="enabled" :label="t('advanced.replication.enabled')" min-width="80" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="row.enabled ? 'success' : 'info'" effect="plain">
              {{ row.enabled ? t('advanced.replication.yes') : t('advanced.replication.no') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="state" :label="t('advanced.replication.state')" min-width="90" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="stateTagType(row.state)" effect="plain">
              {{ stateDisplay(row.state) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="last_sync" :label="t('advanced.replication.lastSync')" min-width="150">
          <template #default="{ row }">{{ formatTime(row.last_sync) }}</template>
        </el-table-column>
        <el-table-column prop="last_duration" :label="t('advanced.replication.lastDuration')" min-width="80" align="center">
          <template #default="{ row }">
            <span v-if="row.last_duration != null">{{ formatDuration(row.last_duration) }}</span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="sync_count" :label="t('advanced.replication.syncCount')" min-width="90" align="center" />
        <el-table-column prop="error_message" :label="t('advanced.replication.errorMessage')" min-width="200">
          <template #default="{ row }">
            <span v-if="row.error_message" class="error-text">{{ row.error_message }}</span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="cluster_name" :label="t('common.cluster')" min-width="120" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useClusterStore } from '@/stores/cluster'
import { getReplicationJobs, type ReplicationJob } from '@/api/replication'
import { Search, Right } from '@element-plus/icons-vue'

const { t } = useI18n()
const clusterStore = useClusterStore()

const loading = ref(false)
const searchText = ref('')
const statusFilter = ref('')
const jobs = ref<ReplicationJob[]>([])
let searchTimer: ReturnType<typeof setTimeout> | null = null

const activeCount = computed(() => jobs.value.filter(j => j.state === 'active' && j.enabled).length)
const totalSyncCount = computed(() => jobs.value.reduce((sum, j) => sum + (j.sync_count || 0), 0))
const latestSyncDisplay = computed(() => {
  const times = jobs.value.map(j => j.last_sync).filter(Boolean) as string[]
  if (!times.length) return '-'
  return formatTime(times.sort().reverse()[0])
})

const filteredJobs = computed(() => {
  if (!searchText.value) return jobs.value
  const q = searchText.value.toLowerCase()
  return jobs.value.filter(j =>
    j.job_id.toLowerCase().includes(q) ||
    j.source_node.toLowerCase().includes(q) ||
    j.target_node.toLowerCase().includes(q) ||
    j.comment.toLowerCase().includes(q)
  )
})

function stateTagType(state: string) {
  if (state === 'active') return 'success'
  if (state === 'error') return 'danger'
  if (state === 'syncing') return 'warning'
  return 'info'
}

function stateDisplay(state: string) {
  const map: Record<string, string> = {
    active: t('advanced.replication.active'),
    disabled: t('advanced.replication.disabled'),
    error: t('advanced.replication.error'),
    syncing: t('advanced.replication.syncing'),
  }
  return map[state] || state || '-'
}

function formatTime(iso: string | null) {
  if (!iso) return '-'
  const d = new Date(iso)
  return `${d.getFullYear()}/${String(d.getMonth() + 1).padStart(2, '0')}/${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

function formatDuration(seconds: number | null) {
  if (seconds == null) return '-'
  if (seconds < 60) return `${seconds}s`
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return s > 0 ? `${m}m${s}s` : `${m}m`
}

function onSearch() {
  // local filter via computed, no API call needed
}

async function fetchData() {
  if (!clusterStore.currentClusterId) return
  loading.value = true
  try {
    const params: Record<string, any> = { cluster_id: clusterStore.currentClusterId }
    if (statusFilter.value) params.status = statusFilter.value
    jobs.value = await getReplicationJobs(params)
  } catch { /* ignore */ } finally {
    loading.value = false
  }
}

onMounted(async () => {
  if (!clusterStore.clusterList.length) await clusterStore.fetchClusters()
  fetchData()
})

watch(() => clusterStore.currentClusterId, () => fetchData())
</script>

<style scoped>
.page-container { max-width: 1400px; margin: 0 auto; }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.page-title { font-size: 24px; font-weight: 700; color: var(--text-heading); margin: 0; }
.page-desc { font-size: 14px; color: var(--text-muted); margin: 4px 0 0; }
.stats-row { display: flex; gap: 16px; margin-bottom: 16px; }
.stat-card { flex: 1; }
.stat-card .el-card__body { padding: 20px 24px; display: flex; flex-direction: column; gap: 4px; }
.stat-label { font-size: 13px; color: var(--text-muted); }
.stat-value { font-size: 28px; font-weight: 700; color: var(--text-heading); }
.stat-active { color: #67c23a; }
.stat-success { color: #409eff; }
.stat-time { font-size: 18px; }
.table-card { margin-top: 0; }
.table-toolbar { display: flex; gap: 12px; margin-bottom: 16px; align-items: center; }
.text-muted { color: var(--text-muted); }
.error-text { color: #f56c6c; font-size: 12px; word-break: break-all; }
.target-cell { display: flex; align-items: center; gap: 4px; }
.arrow-icon { color: var(--text-muted); font-size: 14px; }
</style>
