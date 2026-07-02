<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ t('services.title') }}</h2>
        <p class="page-desc">{{ t('services.subtitle') }}</p>
      </div>
    </div>
    <el-card shadow="hover" class="table-card">
      <div v-if="loading" class="loading-box">
        <el-icon class="is-loading" :size="20"><Loading /></el-icon>
        <span>{{ t('common.loading') }}</span>
      </div>
      <el-table v-else :data="resources" style="width: 100%" stripe>
        <el-table-column prop="sid" :label="t('services.resourceId')" min-width="120">
          <template #default="{ row }"><code class="sid">{{ row.sid }}</code></template>
        </el-table-column>
        <el-table-column prop="resource_type" :label="t('services.type')" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.resource_type === 'vm' ? 'primary' : 'success'" size="small" effect="plain">{{ row.resource_type.toUpperCase() }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="vmid" label="VM/CT ID" width="90" align="center" />
        <el-table-column prop="node_name" :label="t('services.node')" min-width="120" />
        <el-table-column prop="state" :label="t('services.status')" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.state === 'started' ? 'success' : row.state === 'stopped' ? 'danger' : 'warning'" size="small" disable-transitions>
              {{ row.state === 'started' ? t('services.running') : row.state === 'stopped' ? t('services.stopped') : row.state }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="ha_group" :label="t('services.haGroup')" width="100" />
        <el-table-column prop="ha_status" :label="t('services.haStatus')" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.ha_status === 'active' ? 'success' : 'info'" size="small" disable-transitions>{{ row.ha_status || '-' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="crm_state" :label="t('services.crmStatus')" width="100" align="center">
          <template #default="{ row }">{{ row.crm_state || '-' }}</template>
        </el-table-column>
        <el-table-column prop="cluster_name" :label="t('services.cluster')" min-width="120" />
        <el-table-column :label="t('services.scanTime')" min-width="160">
          <template #default="{ row }">{{ formatTime(row.scanned_at) }}</template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && !resources.length" :description="t('services.noData')" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Loading } from '@element-plus/icons-vue'
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

function formatTime(t: string) {
  if (!t) return '-'
  return new Date(t).toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' })
}
</script>

<style scoped>
.page-container { max-width: 1400px; margin: 0 auto; }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 28px; }
.page-title { font-size: 24px; font-weight: 700; color: var(--text-heading); margin: 0; }
.page-desc { font-size: 14px; color: var(--text-muted); margin: 4px 0 0; }
.table-card { border-radius: 16px; }
.loading-box { display: flex; align-items: center; justify-content: center; gap: 8px; padding: 40px; color: var(--text-secondary); }
.sid { font-size: 12px; background: var(--bg-secondary); padding: 2px 6px; border-radius: 4px; }
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
