<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ t('advanced.ha.title') }}</h2>
        <p class="page-desc">{{ t('advanced.ha.subtitle') }}</p>
      </div>
    </div>

    <div class="stats-row">
      <el-card shadow="never" class="stat-card">
        <div class="stat-label">{{ t('advanced.ha.totalResources') }}</div>
        <div class="stat-value">{{ resources.length }}</div>
      </el-card>
      <el-card shadow="never" class="stat-card">
        <div class="stat-label">{{ t('advanced.ha.vmCount') }}</div>
        <div class="stat-value">{{ resources.filter(r => r.resource_type === 'vm').length }}</div>
      </el-card>
      <el-card shadow="never" class="stat-card">
        <div class="stat-label">{{ t('advanced.ha.ctCount') }}</div>
        <div class="stat-value">{{ resources.filter(r => r.resource_type === 'ct').length }}</div>
      </el-card>
      <el-card shadow="never" class="stat-card">
        <div class="stat-label">{{ t('advanced.ha.activeCount') }}</div>
        <div class="stat-value stat-active">{{ resources.filter(r => r.state === 'started').length }}</div>
      </el-card>
    </div>

    <el-card shadow="hover" class="table-card">
      <el-table :data="resources" style="width: 100%" stripe v-loading="loading">
        <el-table-column prop="sid" :label="t('advanced.ha.resourceId')" min-width="120">
          <template #default="{ row }"><code class="sid">{{ row.sid }}</code></template>
        </el-table-column>
        <el-table-column prop="resource_type" :label="t('advanced.ha.type')" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.resource_type === 'vm' ? 'primary' : 'success'" size="small" effect="plain">{{ row.resource_type.toUpperCase() }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="vmid" :label="t('advanced.ha.vmId')" width="90" align="center" />
        <el-table-column prop="node_name" :label="t('advanced.ha.node')" min-width="120" />
        <el-table-column prop="state" :label="t('advanced.ha.status')" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.state === 'started' ? 'success' : row.state === 'stopped' ? 'danger' : 'warning'" size="small" disable-transitions>
              {{ row.state === 'started' ? t('advanced.ha.running') : row.state === 'stopped' ? t('advanced.ha.stopped') : row.state }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="ha_group" :label="t('advanced.ha.haGroup')" width="110" />
        <el-table-column prop="ha_status" :label="t('advanced.ha.haStatus')" width="100" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.ha_status" :type="row.ha_status === 'active' ? 'success' : 'info'" size="small" disable-transitions>{{ row.ha_status }}</el-tag>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="crm_state" :label="t('advanced.ha.crmStatus')" width="100" align="center">
          <template #default="{ row }">
            <span v-if="row.crm_state">{{ row.crm_state }}</span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="max_restarts" :label="t('advanced.ha.maxRestarts')" width="100" align="center">
          <template #default="{ row }">{{ row.max_restarts ?? '-' }}</template>
        </el-table-column>
        <el-table-column prop="max_shutdown" :label="t('advanced.ha.maxShutdown')" width="100" align="center">
          <template #default="{ row }">{{ row.max_shutdown ?? '-' }}</template>
        </el-table-column>
        <el-table-column prop="cluster_name" :label="t('advanced.ha.cluster')" min-width="120" />
        <el-table-column :label="t('advanced.ha.scanTime')" min-width="160">
          <template #default="{ row }">{{ formatTime(row.scanned_at) }}</template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && !resources.length" :description="t('advanced.ha.noData')" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { getHAResources, type HAResource } from '@/api/ha'
import { useClusterStore } from '@/stores/cluster'

const { t } = useI18n()
const clusterStore = useClusterStore()

const loading = ref(true)
const resources = ref<HAResource[]>([])

async function fetchData() {
  loading.value = true
  try {
    const params: Record<string, any> = {}
    if (clusterStore.currentClusterId) params.cluster_id = clusterStore.currentClusterId
    resources.value = await getHAResources(params)
  } catch {} finally { loading.value = false }
}

onMounted(async () => {
  if (!clusterStore.clusterList.length) await clusterStore.fetchClusters()
  fetchData()
})

watch(() => clusterStore.currentClusterId, () => { fetchData() })

function formatTime(val: string) {
  if (!val) return '-'
  return new Date(val).toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' })
}
</script>

<style scoped>
.page-container { max-width: 1400px; margin: 0 auto; }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.page-title { font-size: 24px; font-weight: 700; color: var(--text-heading); margin: 0; }
.page-desc { font-size: 14px; color: var(--text-muted); margin: 4px 0 0; }
.stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 20px; }
.stat-card { text-align: center; }
.stat-label { font-size: 13px; color: var(--text-secondary); margin-bottom: 8px; }
.stat-value { font-size: 24px; font-weight: 700; color: var(--text-heading); }
.stat-active { color: var(--el-color-success); }
.table-card { border-radius: 16px; }
.sid { font-size: 12px; background: var(--bg-secondary); padding: 2px 6px; border-radius: 4px; }
.text-muted { color: var(--text-muted); }
:deep(.el-table) { background: transparent; --el-table-bg-color: transparent; --el-table-tr-bg-color: transparent; --el-table-header-bg-color: transparent; --el-table-border-color: var(--border-color); --el-table-text-color: var(--text-primary); --el-table-header-text-color: var(--text-secondary); }
:deep(.el-table::before) { display: none; }
:deep(.el-table th.el-table__cell) { background: transparent; }
:deep(.el-table--enable-row-hover .el-table__body tr:hover > td) { background-color: rgba(64, 158, 255, 0.05); }
:deep(.el-tag--success) { --el-tag-bg-color: rgba(103, 194, 58, 0.15); --el-tag-text-color: #67c23a; --el-tag-border-color: transparent; }
:deep(.el-tag--danger) { --el-tag-bg-color: rgba(245, 108, 108, 0.15); --el-tag-text-color: #f56c6c; --el-tag-border-color: transparent; }
:deep(.el-tag--warning) { --el-tag-bg-color: rgba(230, 162, 60, 0.15); --el-tag-text-color: #e6a23c; --el-tag-border-color: transparent; }
:deep(.el-tag--primary) { --el-tag-bg-color: rgba(64, 158, 255, 0.15); --el-tag-text-color: #409eff; --el-tag-border-color: transparent; }
:deep(.el-tag--info) { --el-tag-bg-color: var(--bg-secondary); --el-tag-text-color: var(--text-muted); --el-tag-border-color: transparent; }
</style>
