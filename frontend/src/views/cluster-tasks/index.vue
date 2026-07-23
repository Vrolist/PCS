<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ t('clusterTasks.title') }}</h2>
        <p class="page-desc">{{ t('clusterTasks.subtitle') }}</p>
      </div>
    </div>

    <el-card shadow="hover" class="table-card">
      <div class="filter-bar">
        <el-select v-model="filters.task_type" :placeholder="t('clusterTasks.taskType')" clearable size="small" style="width: 160px" @change="fetchData(1)">
          <el-option label="qmigrate" value="qmigrate" />
          <el-option label="vzdump" value="vzdump" />
          <el-option label="hamigrate" value="hamigrate" />
          <el-option label="ha-fencing" value="ha-fencing" />
          <el-option :label="t('clusterTasks.other')" value="other" />
        </el-select>
        <el-select v-model="filters.status" :placeholder="t('clusterTasks.status')" clearable size="small" style="width: 120px; margin-left: 8px" @change="fetchData(1)">
          <el-option label="OK" value="OK" />
          <el-option label="running" value="running" />
        </el-select>
        <el-input v-model="filters.search" :placeholder="t('clusterTasks.searchPlaceholder')" clearable size="small" style="width: 240px; margin-left: 8px" @keyup.enter="fetchData(1)" @clear="fetchData(1)" />
      </div>

      <el-table :data="tasks" stripe style="width: 100%" v-loading="loading" :empty-text="t('clusterTasks.noData')">
        <el-table-column prop="start_time" :label="t('clusterTasks.startTime')" min-width="160">
          <template #default="{ row }">
            <span class="mono">{{ formatTime(row.start_time) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="task_type" :label="t('clusterTasks.taskType')" min-width="120" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="taskTypeTag(row.task_type)">{{ row.task_type || '-' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="node_name" :label="t('clusterTasks.node')" min-width="100" />
        <el-table-column prop="user" :label="t('clusterTasks.user')" min-width="140" show-overflow-tooltip />
        <el-table-column prop="vmid" :label="t('clusterTasks.vmid')" min-width="80" align="center">
          <template #default="{ row }">
            <span v-if="row.vmid != null">{{ row.vmid }}</span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" :label="t('clusterTasks.status')" min-width="90" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.status === 'OK'" type="success" size="small">OK</el-tag>
            <el-tag v-else-if="row.status === 'running'" type="warning" size="small">{{ t('clusterTasks.running') }}</el-tag>
            <el-tag v-else size="small" effect="plain">{{ row.status || '-' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="t('clusterTasks.duration')" min-width="100" align="center">
          <template #default="{ row }">
            <span v-if="row.duration_seconds != null">{{ formatDuration(row.duration_seconds) }}</span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="upid" :label="t('clusterTasks.upid')" min-width="240" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="mono text-muted">{{ row.upid }}</span>
          </template>
        </el-table-column>
      </el-table>

      <div v-if="total > pageSize" class="pagination-wrap">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          layout="prev, pager, next"
          @current-change="fetchData"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useClusterStore } from '@/stores/cluster'
import { getClusterTasks, type ClusterTaskItem } from '@/api/cluster-tasks'

const { t } = useI18n()
const clusterStore = useClusterStore()

const loading = ref(false)
const tasks = ref<ClusterTaskItem[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = 20
const filters = reactive({ task_type: '', status: '', search: '' })

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

function taskTypeTag(type: string) {
  if (type?.includes('migrate')) return 'primary'
  if (type?.includes('vzdump')) return 'success'
  if (type?.includes('ha')) return 'warning'
  return 'info'
}

async function fetchData(page = 1) {
  currentPage.value = page
  loading.value = true
  try {
    const resp = await getClusterTasks({
      cluster_id: clusterStore.currentClusterId || undefined,
      task_type: filters.task_type || undefined,
      status: filters.status || undefined,
      search: filters.search || undefined,
      page,
      page_size: pageSize,
    })
    tasks.value = resp.results
    total.value = resp.count
  } catch { /* ignore */ } finally {
    loading.value = false
  }
}

onMounted(async () => {
  if (!clusterStore.clusterList.length) await clusterStore.fetchClusters()
  fetchData()
})

watch(() => clusterStore.currentClusterId, () => {
  filters.task_type = ''
  filters.status = ''
  filters.search = ''
  fetchData()
})
</script>

<style scoped>
.page-container { max-width: 1400px; margin: 0 auto; }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 28px; }
.page-title { font-size: 24px; font-weight: 700; color: var(--text-heading); margin: 0; }
.page-desc { font-size: 14px; color: var(--text-muted); margin: 4px 0 0; }
.table-card { margin-top: 0; }
.filter-bar { display: flex; align-items: center; margin-bottom: 12px; }
.text-muted { color: var(--text-muted); }
.mono { font-family: 'SF Mono', 'Fira Code', 'Cascadia Code', monospace; font-size: 13px; }
.pagination-wrap { display: flex; justify-content: flex-end; margin-top: 16px; }
</style>
