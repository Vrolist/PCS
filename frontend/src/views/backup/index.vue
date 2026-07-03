<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ t('advanced.backup.title') }}</h2>
        <p class="page-desc">{{ t('advanced.backup.subtitle') }}</p>
      </div>
    </div>

    <div class="stats-row">
      <div class="el-card is-never-shadow stat-card">
        <div class="el-card__body">
          <div class="stat-label">{{ t('advanced.backup.totalStorages') }}</div>
          <div class="stat-value">{{ stats.total_storages }}</div>
        </div>
      </div>
      <div class="el-card is-never-shadow stat-card">
        <div class="el-card__body">
          <div class="stat-label">{{ t('advanced.backup.enabledJobs') }}</div>
          <div class="stat-value">{{ stats.enabled_jobs }}<span class="stat-sub">/{{ stats.total_jobs }}</span></div>
        </div>
      </div>
      <div class="el-card is-never-shadow stat-card">
        <div class="el-card__body">
          <div class="stat-label">{{ t('advanced.backup.successRate') }}</div>
          <div class="stat-value" :class="stats.success_rate >= 90 ? 'text-success' : stats.success_rate >= 70 ? 'text-warning' : 'text-danger'">{{ stats.success_rate }}%</div>
        </div>
      </div>
      <div class="el-card is-never-shadow stat-card">
        <div class="el-card__body">
          <div class="stat-label">{{ t('advanced.backup.totalBackupSize') }}</div>
          <div class="stat-value">{{ stats.total_backup_size_gb }}<span class="stat-sub"> GB</span></div>
        </div>
      </div>
    </div>

    <el-card shadow="hover" class="table-card">
      <el-tabs v-model="activeTab">
        <el-tab-pane :label="t('advanced.backup.storages')" name="storages">
          <el-table :data="storages" stripe style="width: 100%" v-loading="loading" :empty-text="t('advanced.backup.noData')">
            <el-table-column prop="storage_name" :label="t('advanced.backup.storageName')" min-width="140" />
            <el-table-column prop="storage_type" :label="t('advanced.backup.storageType')" min-width="100" align="center">
              <template #default="{ row }">
                <el-tag size="small" effect="plain">{{ row.storage_type }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="cluster_name" :label="t('advanced.backup.cluster')" min-width="120" />
            <el-table-column prop="node_name" :label="t('advanced.backup.node')" min-width="100" />
            <el-table-column :label="t('advanced.backup.capacity')" min-width="180">
              <template #default="{ row }">
                <div class="capacity-bar">
                  <el-progress :percentage="Math.round((row.used_fraction || 0) * 100)" :stroke-width="8" :color="getCapacityColor(row.used_fraction)" />
                  <span class="capacity-text">{{ row.used_gb }} / {{ row.total_gb }} GB</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="active" :label="t('advanced.backup.status')" min-width="80" align="center">
              <template #default="{ row }">
                <el-tag :type="row.active ? 'success' : 'info'" size="small">{{ row.active ? t('advanced.backup.active') : t('advanced.backup.inactive') }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="shared" :label="t('advanced.backup.shared')" min-width="80" align="center">
              <template #default="{ row }">
                <el-tag v-if="row.shared" type="warning" size="small">{{ t('advanced.backup.yes') }}</el-tag>
                <span v-else class="text-muted">-</span>
              </template>
            </el-table-column>
            <el-table-column prop="scanned_at" :label="t('advanced.backup.scannedAt')" min-width="160">
              <template #default="{ row }">{{ formatTime(row.scanned_at) }}</template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane :label="t('advanced.backup.jobs')" name="jobs">
          <el-table :data="jobs" stripe style="width: 100%" v-loading="loading" :empty-text="t('advanced.backup.noData')">
            <el-table-column prop="job_id" :label="t('advanced.backup.jobId')" min-width="180" show-overflow-tooltip />
            <el-table-column prop="vmid" :label="t('advanced.backup.vmid')" min-width="80" align="center">
              <template #default="{ row }">
                <span v-if="row.vmid != null">{{ row.vmid }}</span>
                <span v-else class="text-muted">-</span>
              </template>
            </el-table-column>
            <el-table-column prop="resource_type" :label="t('advanced.backup.resourceType')" min-width="80" align="center">
              <template #default="{ row }">
                <el-tag v-if="row.resource_type === 'vm'" size="small" type="primary">VM</el-tag>
                <el-tag v-else-if="row.resource_type === 'ct'" size="small" type="success">CT</el-tag>
                <el-tag v-else size="small" effect="plain">{{ row.resource_type || '-' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="cluster_name" :label="t('advanced.backup.cluster')" min-width="120" />
            <el-table-column prop="node_name" :label="t('advanced.backup.node')" min-width="100" />
            <el-table-column prop="mode" :label="t('advanced.backup.mode')" min-width="100" align="center">
              <template #default="{ row }">
                <el-tag size="small" effect="plain">{{ row.mode || '-' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="storage_name" :label="t('advanced.backup.storageName')" min-width="120" />
            <el-table-column prop="schedule" :label="t('advanced.backup.schedule')" min-width="100" />
            <el-table-column prop="retention" :label="t('advanced.backup.retention')" min-width="120" show-overflow-tooltip />
            <el-table-column prop="enabled" :label="t('advanced.backup.enabled')" min-width="80" align="center">
              <template #default="{ row }">
                <el-tag :type="row.enabled ? 'success' : 'info'" size="small">{{ row.enabled ? t('advanced.backup.yes') : t('advanced.backup.no') }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="last_status" :label="t('advanced.backup.lastStatus')" min-width="100" align="center">
              <template #default="{ row }">
                <el-tag v-if="row.last_status === 'ok'" type="success" size="small">OK</el-tag>
                <el-tag v-else-if="row.last_status === 'error'" type="danger" size="small">{{ t('advanced.backup.error') }}</el-tag>
                <span v-else class="text-muted">{{ row.last_status || '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="last_run" :label="t('advanced.backup.lastRun')" min-width="160">
              <template #default="{ row }">{{ formatTime(row.last_run) }}</template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane :label="t('advanced.backup.history')" name="history">
          <div class="filter-bar">
            <el-select v-model="historyFilter.status" :placeholder="t('advanced.backup.status')" clearable size="small" style="width: 120px" @change="fetchHistory">
              <el-option label="OK" value="ok" />
              <el-option :label="t('advanced.backup.error')" value="error" />
              <el-option :label="t('advanced.backup.running')" value="running" />
            </el-select>
            <el-input v-model="historyFilter.search" :placeholder="t('advanced.backup.searchPlaceholder')" clearable size="small" style="width: 240px; margin-left: 8px" @keyup.enter="fetchHistory" @clear="fetchHistory" />
          </div>
          <el-table :data="history" stripe style="width: 100%" v-loading="loading" :empty-text="t('advanced.backup.noData')">
            <el-table-column prop="task_id" :label="t('advanced.backup.taskId')" min-width="200" show-overflow-tooltip />
            <el-table-column prop="vmid" :label="t('advanced.backup.vmid')" min-width="80" align="center">
              <template #default="{ row }">
                <span v-if="row.vmid != null">{{ row.vmid }}</span>
                <span v-else class="text-muted">-</span>
              </template>
            </el-table-column>
            <el-table-column prop="resource_type" :label="t('advanced.backup.resourceType')" min-width="80" align="center">
              <template #default="{ row }">
                <el-tag v-if="row.resource_type === 'vm'" size="small" type="primary">VM</el-tag>
                <el-tag v-else-if="row.resource_type === 'ct'" size="small" type="success">CT</el-tag>
                <span v-else class="text-muted">-</span>
              </template>
            </el-table-column>
            <el-table-column prop="cluster_name" :label="t('advanced.backup.cluster')" min-width="120" />
            <el-table-column prop="node_name" :label="t('advanced.backup.node')" min-width="100" />
            <el-table-column prop="status" :label="t('advanced.backup.status')" min-width="90" align="center">
              <template #default="{ row }">
                <el-tag v-if="row.status === 'ok'" type="success" size="small">OK</el-tag>
                <el-tag v-else-if="row.status === 'error'" type="danger" size="small">{{ t('advanced.backup.error') }}</el-tag>
                <el-tag v-else type="warning" size="small">{{ t('advanced.backup.running') }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column :label="t('advanced.backup.duration')" min-width="100" align="center">
              <template #default="{ row }">
                <span v-if="row.duration_seconds != null">{{ formatDuration(row.duration_seconds) }}</span>
                <span v-else class="text-muted">-</span>
              </template>
            </el-table-column>
            <el-table-column :label="t('advanced.backup.backupSize')" min-width="100" align="right">
              <template #default="{ row }">
                <span v-if="row.size_bytes">{{ formatSize(row.size_bytes) }}</span>
                <span v-else class="text-muted">-</span>
              </template>
            </el-table-column>
            <el-table-column prop="mode" :label="t('advanced.backup.mode')" min-width="100" align="center">
              <template #default="{ row }">
                <el-tag size="small" effect="plain">{{ row.mode || '-' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="error_message" :label="t('advanced.backup.errorMessage')" min-width="200" show-overflow-tooltip>
              <template #default="{ row }">
                <span v-if="row.error_message" class="text-danger">{{ row.error_message }}</span>
                <span v-else class="text-muted">-</span>
              </template>
            </el-table-column>
            <el-table-column prop="started_at" :label="t('advanced.backup.startedAt')" min-width="160">
              <template #default="{ row }">{{ formatTime(row.started_at) }}</template>
            </el-table-column>
          </el-table>
          <div class="pagination-wrap" v-if="historyTotal > historyPageSize">
            <el-pagination
              v-model:current-page="historyPage"
              :page-size="historyPageSize"
              :total="historyTotal"
              layout="prev, pager, next"
              @current-change="fetchHistory"
            />
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, reactive } from 'vue'
import { useI18n } from 'vue-i18n'
import { useClusterStore } from '@/stores/cluster'
import {
  getBackupStorages, getBackupJobs, getBackupHistory, getBackupStats,
  type BackupStorage, type BackupJob, type BackupHistoryItem, type BackupStats,
} from '@/api/backup'

const { t } = useI18n()
const clusterStore = useClusterStore()

const loading = ref(false)
const activeTab = ref('storages')
const storages = ref<BackupStorage[]>([])
const jobs = ref<BackupJob[]>([])
const history = ref<BackupHistoryItem[]>([])
const historyTotal = ref(0)
const historyPage = ref(1)
const historyPageSize = 20
const historyFilter = reactive({ status: '', search: '' })

const stats = reactive<BackupStats>({
  total_storages: 0, total_storages_gb: 0, used_storages_gb: 0,
  total_jobs: 0, enabled_jobs: 0,
  total_backups: 0, success_backups: 0, failed_backups: 0,
  success_rate: 0, total_backup_size_gb: 0,
})

function formatTime(iso: string | null) {
  if (!iso) return '-'
  const d = new Date(iso)
  return `${d.getFullYear()}/${String(d.getMonth() + 1).padStart(2, '0')}/${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

function formatDuration(seconds: number) {
  if (seconds < 60) return `${seconds}s`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`
  return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`
}

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1073741824) return `${(bytes / 1048576).toFixed(1)} MB`
  return `${(bytes / 1073741824).toFixed(2)} GB`
}

function getCapacityColor(fraction: number | null) {
  const pct = (fraction || 0) * 100
  if (pct > 90) return '#f56c6c'
  if (pct > 70) return '#e6a23c'
  return '#67c23a'
}

async function fetchData() {
  if (!clusterStore.currentClusterId) return
  loading.value = true
  try {
    const params = { cluster_id: clusterStore.currentClusterId }
    const [s, j, st] = await Promise.all([
      getBackupStorages(params),
      getBackupJobs(params),
      getBackupStats(params),
    ])
    storages.value = s
    jobs.value = j
    Object.assign(stats, st)
    await fetchHistory()
  } catch { /* ignore */ } finally {
    loading.value = false
  }
}

async function fetchHistory() {
  if (!clusterStore.currentClusterId) return
  try {
    const resp = await getBackupHistory({
      cluster_id: clusterStore.currentClusterId,
      status: historyFilter.status || undefined,
      search: historyFilter.search || undefined,
      page: historyPage.value,
      page_size: historyPageSize,
    })
    history.value = resp.results
    historyTotal.value = resp.count
  } catch { /* ignore */ }
}

onMounted(async () => {
  if (!clusterStore.clusterList.length) await clusterStore.fetchClusters()
  fetchData()
})

watch(() => clusterStore.currentClusterId, () => {
  historyPage.value = 1
  historyFilter.status = ''
  historyFilter.search = ''
  fetchData()
})
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
.stat-sub { font-size: 14px; font-weight: 400; color: var(--text-muted); }
.table-card { margin-top: 0; }
.text-muted { color: var(--text-muted); }
.text-success { color: #67c23a; }
.text-warning { color: #e6a23c; }
.text-danger { color: #f56c6c; }
.filter-bar { display: flex; align-items: center; margin-bottom: 12px; }
.capacity-bar { display: flex; flex-direction: column; gap: 2px; }
.capacity-text { font-size: 12px; color: var(--text-muted); }
.pagination-wrap { display: flex; justify-content: flex-end; margin-top: 16px; }
</style>
