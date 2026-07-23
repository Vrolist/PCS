<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ t('clusterPveLog.title') }}</h2>
        <p class="page-desc">{{ t('clusterPveLog.subtitle') }}</p>
      </div>
    </div>

    <el-card shadow="hover" class="table-card">
      <div class="filter-bar">
        <el-select v-model="filters.level" :placeholder="t('clusterPveLog.logLevel')" clearable size="small" style="width: 120px" @change="fetchData(1)">
          <el-option label="info" value="info" />
          <el-option label="warning" value="warning" />
          <el-option label="err" value="err" />
        </el-select>
        <el-select v-model="filters.tag" :placeholder="t('clusterPveLog.tag')" clearable size="small" style="width: 140px; margin-left: 8px" @change="fetchData(1)">
          <el-option label="cluster" value="cluster" />
          <el-option label="corosync" value="corosync" />
          <el-option label="ha" value="ha" />
          <el-option label="pve" value="pve" />
        </el-select>
        <el-input v-model="filters.search" :placeholder="t('clusterPveLog.searchPlaceholder')" clearable size="small" style="width: 280px; margin-left: 8px" @keyup.enter="fetchData(1)" @clear="fetchData(1)" />
      </div>

      <el-table :data="logs" stripe style="width: 100%" v-loading="loading" :empty-text="t('clusterPveLog.noData')">
        <el-table-column prop="log_time" :label="t('clusterPveLog.time')" min-width="160">
          <template #default="{ row }">
            <span class="mono">{{ formatTime(row.log_time) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="log_level" :label="t('clusterPveLog.logLevel')" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="levelTagType(row.log_level)" size="small">{{ row.log_level || '-' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="tag" :label="t('clusterPveLog.tag')" width="110" align="center">
          <template #default="{ row }">
            <el-tag size="small" effect="plain">{{ row.tag || '-' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="message" :label="t('clusterPveLog.message')" min-width="400" show-overflow-tooltip />
        <el-table-column prop="cluster_name" :label="t('clusterPveLog.cluster')" width="130" />
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
import { getClusterLogs, type ClusterLogItem } from '@/api/cluster-log'

const { t } = useI18n()
const clusterStore = useClusterStore()

const loading = ref(false)
const logs = ref<ClusterLogItem[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = 50
const filters = reactive({ level: '', tag: '', search: '' })

function formatTime(iso: string | null) {
  if (!iso) return '-'
  const d = new Date(iso)
  return `${d.getFullYear()}/${String(d.getMonth() + 1).padStart(2, '0')}/${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}`
}

function levelTagType(level: string) {
  if (level === 'err') return 'danger'
  if (level === 'warning') return 'warning'
  return 'info'
}

async function fetchData(page = 1) {
  currentPage.value = page
  loading.value = true
  try {
    const resp = await getClusterLogs({
      cluster_id: clusterStore.currentClusterId || undefined,
      level: filters.level || undefined,
      tag: filters.tag || undefined,
      search: filters.search || undefined,
      page,
      page_size: pageSize,
    })
    logs.value = resp.results
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
  filters.level = ''
  filters.tag = ''
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
.mono { font-family: 'SF Mono', 'Fira Code', 'Cascadia Code', monospace; font-size: 13px; }
.pagination-wrap { display: flex; justify-content: flex-end; margin-top: 16px; }
</style>
