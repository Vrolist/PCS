<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ t('advanced.snapshots.title') }}</h2>
        <p class="page-desc">{{ t('advanced.snapshots.subtitle') }}</p>
      </div>
      <div class="header-actions">
        <el-input v-model="search" :placeholder="t('advanced.snapshots.searchPlaceholder')" clearable prefix-icon="Search" style="width: 260px" @input="debounceLoad" />
      </div>
    </div>
    <el-card shadow="hover" class="table-card">
      <div v-if="loading" class="loading-box">
        <el-icon class="is-loading" :size="20"><Loading /></el-icon>
        <span>{{ t('common.loading') }}</span>
      </div>
      <el-table v-else :data="snapshots" style="width: 100%" stripe :default-sort="{ prop: 'snap_time', order: 'descending' }">
        <el-table-column :label="t('advanced.snapshots.snapName')" min-width="160" fixed>
          <template #default="{ row }">
            <span class="snap-name">{{ row.name }}</span>
            <div class="sub-text" v-if="row.description">{{ row.description }}</div>
          </template>
        </el-table-column>
        <el-table-column :label="t('advanced.snapshots.vmName')" min-width="140">
          <template #default="{ row }">
            <span class="vm-name">{{ row.vm_name }}</span>
            <div class="sub-text">VMID: {{ row.vm_vmid }}</div>
          </template>
        </el-table-column>
        <el-table-column :label="t('advanced.snapshots.node')" prop="node_name" width="110" />
        <el-table-column :label="t('advanced.snapshots.snapTime')" min-width="160" sortable sort-by="snap_time">
          <template #default="{ row }">{{ fmtTime(row.snap_time) }}</template>
        </el-table-column>
        <el-table-column :label="t('advanced.snapshots.parent')" width="120">
          <template #default="{ row }">
            <span v-if="row.parent" class="parent-tag">{{ row.parent }}</span>
            <span v-else class="no-parent">{{ t('advanced.snapshots.noParent') }}</span>
          </template>
        </el-table-column>
        <el-table-column :label="t('advanced.snapshots.saveMemory')" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.ram ? 'success' : 'info'" size="small">{{ row.ram ? t('advanced.snapshots.yes') : t('advanced.snapshots.no') }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="t('advanced.snapshots.saveState')" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.vmstate ? 'success' : 'info'" size="small">{{ row.vmstate ? t('advanced.snapshots.yes') : t('advanced.snapshots.no') }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="t('advanced.snapshots.snapType')" width="100" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.snap_type" type="warning" size="small" effect="plain">{{ row.snap_type }}</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column :label="t('common.scanTime')" min-width="160" sortable sort-by="scanned_at">
          <template #default="{ row }">{{ fmtTime(row.scanned_at) }}</template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && !snapshots.length" :description="t('advanced.snapshots.emptyDesc')" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Loading } from '@element-plus/icons-vue'
import { getSnapshots } from '@/api/snapshots'
import type { SnapshotInfo } from '@/api/snapshots'
import { useClusterStore } from '@/stores/cluster'

const { t } = useI18n()
const clusterStore = useClusterStore()

const loading = ref(true)
const snapshots = ref<SnapshotInfo[]>([])
const search = ref('')
let timer: ReturnType<typeof setTimeout> | null = null

onMounted(async () => {
  if (!clusterStore.clusterList.length) await clusterStore.fetchClusters()
  loadData()
})

watch(() => clusterStore.currentClusterId, () => { loadData() })

async function loadData() {
  loading.value = true
  try {
    const params: Record<string, any> = {}
    if (clusterStore.currentClusterId) params.cluster_id = clusterStore.currentClusterId
    if (search.value) params.search = search.value
    snapshots.value = await getSnapshots(params)
  } catch {} finally { loading.value = false }
}

function debounceLoad() {
  if (timer) clearTimeout(timer)
  timer = setTimeout(loadData, 300)
}

function fmtTime(iso: string | null) {
  if (!iso) return '-'
  return new Date(iso).toLocaleString('zh-CN')
}
</script>

<style scoped>
.page-container { max-width: 1400px; margin: 0 auto; }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 28px; flex-wrap: wrap; gap: 12px; }
.page-title { font-size: 24px; font-weight: 700; color: var(--text-heading); margin: 0; }
.page-desc { font-size: 14px; color: var(--text-muted); margin: 4px 0 0; }
.header-actions { display: flex; gap: 8px; align-items: center; }
.table-card { border-radius: 16px; }
.loading-box { display: flex; align-items: center; justify-content: center; gap: 8px; padding: 40px; color: var(--text-secondary); }
.snap-name { font-weight: 600; color: var(--text-primary); }
.vm-name { font-weight: 500; color: var(--text-primary); }
.sub-text { font-size: 12px; color: var(--text-muted); margin-top: 2px; }
.parent-tag { font-size: 12px; font-family: 'SF Mono', 'Menlo', monospace; background: var(--bg-secondary); padding: 2px 6px; border-radius: 4px; }
.no-parent { font-size: 12px; color: var(--text-muted); }
:deep(.el-table) { background: var(--el-card-bg-color); --el-table-bg-color: var(--el-card-bg-color); --el-table-tr-bg-color: var(--el-card-bg-color); --el-table-header-bg-color: var(--el-card-bg-color); --el-table-border-color: var(--border-color); --el-table-text-color: var(--text-primary); --el-table-header-text-color: var(--text-secondary); }
:deep(.el-table::before) { display: none; }
:deep(.el-table th.el-table__cell) { background-color: var(--el-card-bg-color); }
:deep(.el-table--enable-row-hover .el-table__body tr:hover > td) { background-color: rgba(64, 158, 255, 0.05); }
:deep(.el-tag--success) { --el-tag-bg-color: rgba(103, 194, 58, 0.15); --el-tag-text-color: #67c23a; --el-tag-border-color: transparent; }
:deep(.el-tag--info) { --el-tag-bg-color: rgba(144, 147, 153, 0.15); --el-tag-text-color: #909399; --el-tag-border-color: transparent; }
:deep(.el-tag--warning) { --el-tag-bg-color: rgba(230, 162, 60, 0.15); --el-tag-text-color: #e6a23c; --el-tag-border-color: transparent; }
:deep(.el-table__fixed td),
:deep(.el-table__fixed-right td),
:deep(.el-table .el-table-fixed-column--left),
:deep(.el-table .el-table-fixed-column--right) {
  background-color: var(--el-card-bg-color) !important;
}
:deep(.el-table__fixed th),
:deep(.el-table__fixed-right th) {
  background-color: var(--el-card-bg-color) !important;
}
</style>
