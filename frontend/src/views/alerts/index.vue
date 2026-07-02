<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ t('alerts.title') }}</h2>
        <p class="page-desc">{{ t('alerts.subtitle') }}</p>
      </div>
    </div>
    <div class="filter-bar">
      <el-select v-model="clusterFilter" :placeholder="t('alerts.selectCluster')" clearable style="width: 180px" @change="fetchData">
        <el-option v-for="c in clusterList" :key="c.id" :label="c.name" :value="c.id" />
      </el-select>
    </div>
    <el-card shadow="hover">
      <el-table :data="alerts" style="width: 100%" stripe v-loading="loading">
        <el-table-column prop="title" :label="t('alerts.alertTitle')" min-width="200" />
        <el-table-column prop="severity" :label="t('alerts.level')" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.severity === 'critical' ? 'danger' : row.severity === 'warning' ? 'warning' : 'info'" size="small">
              {{ row.severity === 'critical' ? t('alerts.critical') : row.severity === 'warning' ? t('alerts.warning') : t('alerts.info') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="category" :label="t('alerts.category')" width="100" />
        <el-table-column prop="affected_resource" :label="t('alerts.affectedResource')" min-width="120" />
        <el-table-column prop="detail" :label="t('alerts.detail')" min-width="250" show-overflow-tooltip />
        <el-table-column prop="cluster_name" :label="t('alerts.cluster')" min-width="140" />
        <el-table-column prop="created_at" :label="t('alerts.alertTime')" min-width="160">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && !alerts.length" :description="t('alerts.noData')" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { getDashboardAlerts, type DashboardAlert } from '@/api/dashboard'
import { getClusters, type Cluster } from '@/api/clusters'

const { t } = useI18n()

const loading = ref(true)
const alerts = ref<DashboardAlert[]>([])
const clusterFilter = ref<number | ''>('')
const clusterList = ref<Cluster[]>([])

async function fetchData() {
  loading.value = true
  try {
    alerts.value = await getDashboardAlerts(50, clusterFilter.value || undefined)
  } catch {} finally { loading.value = false }
}

onMounted(async () => {
  try {
    const res = await getClusters()
    clusterList.value = res.results
    if (clusterList.value.length) clusterFilter.value = clusterList.value[0].id
  } catch {} finally {
    fetchData()
  }
})

function formatTime(t: string) {
  if (!t) return '-'
  return new Date(t).toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' })
}
</script>

<style scoped>
.page-container { max-width: 1400px; margin: 0 auto; }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.page-title { font-size: 24px; font-weight: 700; color: var(--text-heading); margin: 0; }
.page-desc { font-size: 14px; color: var(--text-muted); margin: 4px 0 0; }
.filter-bar { margin-bottom: 16px; display: flex; gap: 12px; }
:deep(.el-table) { background: transparent; --el-table-bg-color: transparent; --el-table-tr-bg-color: transparent; --el-table-header-bg-color: transparent; --el-table-border-color: var(--border-color); --el-table-text-color: var(--text-primary); --el-table-header-text-color: var(--text-secondary); }
:deep(.el-table::before) { display: none; }
:deep(.el-table th.el-table__cell) { background: transparent; }
:deep(.el-table--enable-row-hover .el-table__body tr:hover > td) { background-color: rgba(64, 158, 255, 0.05); }
:deep(.el-tag--danger) { --el-tag-bg-color: rgba(245, 108, 108, 0.15); --el-tag-text-color: #f56c6c; --el-tag-border-color: transparent; }
:deep(.el-tag--warning) { --el-tag-bg-color: rgba(230, 162, 60, 0.15); --el-tag-text-color: #e6a23c; --el-tag-border-color: transparent; }
:deep(.el-tag--info) { --el-tag-bg-color: var(--bg-secondary); --el-tag-text-color: var(--text-muted); --el-tag-border-color: transparent; }
</style>
