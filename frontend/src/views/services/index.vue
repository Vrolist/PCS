<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">运维服务</h2>
        <p class="page-desc">HA 高可用资源监控</p>
      </div>
    </div>
    <el-card shadow="hover" class="table-card">
      <div v-if="loading" class="loading-box">
        <el-icon class="is-loading" :size="20"><Loading /></el-icon>
        <span>加载中...</span>
      </div>
      <el-table v-else :data="resources" style="width: 100%" stripe>
        <el-table-column prop="sid" label="资源 ID" min-width="120">
          <template #default="{ row }"><code class="sid">{{ row.sid }}</code></template>
        </el-table-column>
        <el-table-column prop="resource_type" label="类型" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.resource_type === 'vm' ? 'primary' : 'success'" size="small" effect="plain">{{ row.resource_type.toUpperCase() }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="vmid" label="VM/CT ID" width="90" align="center" />
        <el-table-column prop="node_name" label="节点" min-width="120" />
        <el-table-column prop="state" label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.state === 'started' ? 'success' : row.state === 'stopped' ? 'danger' : 'warning'" size="small" disable-transitions>
              {{ row.state === 'started' ? '运行中' : row.state === 'stopped' ? '已停止' : row.state }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="ha_group" label="HA 组" width="100" />
        <el-table-column prop="ha_status" label="HA 状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.ha_status === 'active' ? 'success' : 'info'" size="small" disable-transitions>{{ row.ha_status || '-' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="crm_state" label="CRM 状态" width="100" align="center">
          <template #default="{ row }">{{ row.crm_state || '-' }}</template>
        </el-table-column>
        <el-table-column prop="cluster_name" label="集群" min-width="120" />
        <el-table-column label="扫描时间" min-width="160">
          <template #default="{ row }">{{ formatTime(row.scanned_at) }}</template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && !resources.length" description="暂无 HA 资源数据" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Loading } from '@element-plus/icons-vue'
import { getHAResources } from '@/api/ha'
import type { HAResource } from '@/api/ha'

const loading = ref(true)
const resources = ref<HAResource[]>([])

onMounted(async () => {
  try { resources.value = await getHAResources() } catch {} finally { loading.value = false }
})

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
