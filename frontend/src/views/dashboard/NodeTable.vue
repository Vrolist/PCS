<template>
  <div class="node-table-card">
    <div class="card-header">
      <span class="card-title">节点详情</span>
      <router-link to="/dashboard/clusters" class="view-all">查看全部</router-link>
    </div>
    <div v-if="loading" class="node-loading">
      <el-icon class="is-loading" :size="20"><Loading /></el-icon>
      <span>加载中...</span>
    </div>
    <el-table v-else :data="nodes" style="width: 100%">
      <el-table-column prop="name" label="节点名称" min-width="120" fixed="left">
        <template #default="{ row }">
          <span class="node-name">{{ row.name }}</span>
        </template>
      </el-table-column>
      <el-table-column label="CPU" min-width="160">
        <template #default="{ row }">
          <div class="usage-cell">
            <el-progress
              :percentage="Math.round(row.cpu_load)"
              :stroke-width="8"
              :color="getCpuColor(Math.round(row.cpu_load))"
              :show-text="false"
            />
            <span class="usage-text">{{ Math.round(row.cpu_load) }}%</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="内存" min-width="200">
        <template #default="{ row }">
          <div class="usage-cell">
            <el-progress
              :percentage="Math.round(row.memory_usage_pct || 0)"
              :stroke-width="8"
              :color="'#409eff'"
              :show-text="false"
            />
            <span class="usage-text">{{ formatMB(row.memory_used_mb) }}/{{ formatMB(row.memory_total_mb) }} ({{ Math.round(row.memory_usage_pct || 0) }}%)</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="磁盘" min-width="140">
        <template #default="{ row }">
          <span class="disk-text">{{ row.rootfs_used_gb || 0 }}GB/{{ row.rootfs_total_gb || 0 }}GB</span>
        </template>
      </el-table-column>
      <el-table-column prop="ip_address" label="IP地址" min-width="150">
        <template #default="{ row }">
          {{ row.ip_address || '未知' }}
        </template>
      </el-table-column>
      <el-table-column prop="pve_version" label="PVE版本" min-width="160" />
      <el-table-column prop="status" label="状态" width="100" align="center" fixed="right">
        <template #default="{ row }">
          <el-tag :type="row.status === 'online' ? 'success' : 'warning'" disable-transitions>
            {{ row.status === 'online' ? '在线' : '告警' }}
          </el-tag>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Loading } from '@element-plus/icons-vue'
import { getDashboardNodes } from '@/api/dashboard'
import type { DashboardNode } from '@/api/dashboard'

const loading = ref(true)
const nodes = ref<DashboardNode[]>([])

onMounted(async () => {
  try {
    nodes.value = await getDashboardNodes()
  } catch {
    // error handled by interceptor
  } finally {
    loading.value = false
  }
})

function formatMB(mb: number) {
  if (mb >= 1024) return `${(mb / 1024).toFixed(1)}GB`
  return `${mb}MB`
}

function getCpuColor(percent: number): string {
  if (percent > 85) return '#f56c6c'
  if (percent >= 70) return '#e6a23c'
  return '#67c23a'
}
</script>

<style scoped>
.node-table-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  padding: 0;
  margin-top: 28px;
  overflow: hidden;
  transition: background-color 0.3s, border-color 0.3s;
}
.card-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 20px 24px 16px;
}
.card-title { font-size: 16px; font-weight: 600; color: var(--text-heading); }
.view-all { font-size: 13px; color: var(--primary-color); text-decoration: none; transition: opacity 0.2s; }
.view-all:hover { opacity: 0.8; }
.node-loading {
  display: flex; align-items: center; justify-content: center; gap: 8px;
  padding: 40px; color: var(--text-secondary); font-size: 14px;
}
:deep(.el-table) {
  background: var(--bg-card);
  --el-table-bg-color: var(--bg-card);
  --el-table-tr-bg-color: var(--bg-card);
  --el-table-header-bg-color: var(--bg-card);
  --el-table-row-hover-bg-color: rgba(64, 158, 255, 0.05);
  --el-table-border-color: var(--border-color);
  --el-table-text-color: var(--text-primary);
  --el-table-header-text-color: var(--text-secondary);
}
:deep(.el-table::before), :deep(.el-table--border::after) { display: none; }
:deep(.el-table th.el-table__cell) { background-color: var(--bg-card); border-bottom: 1px solid var(--border-color); }
:deep(.el-table td.el-table__cell) { border-bottom: 1px solid var(--border-color); }
/* 固定列容器中的 td 强制使用卡片背景色 */
:deep(.el-table__fixed td),
:deep(.el-table__fixed-right td),
:deep(.el-table .el-table-fixed-column--left),
:deep(.el-table .el-table-fixed-column--right) {
  background-color: var(--bg-card) !important;
}
/* 固定列表头也同步 */
:deep(.el-table__fixed th),
:deep(.el-table__fixed-right th) {
  background-color: var(--bg-card) !important;
}
:deep(.el-table--enable-row-hover .el-table__body tr:hover > td) { background-color: rgba(64, 158, 255, 0.05); }
:deep(.el-table--border .el-table__inner-wrapper::after),
:deep(.el-table--border::before),
:deep(.el-table--border::after) { background-color: var(--border-color); }
.node-name { font-weight: 600; color: var(--text-primary); }
.usage-cell { display: flex; flex-direction: column; gap: 4px; }
.usage-text { font-size: 12px; color: var(--text-muted); }
.disk-text { font-size: 14px; color: var(--text-primary); }
:deep(.el-tag--success) {
  --el-tag-bg-color: rgba(103, 194, 58, 0.15);
  --el-tag-text-color: #67c23a;
  --el-tag-border-color: transparent;
}
:deep(.el-tag--warning) {
  --el-tag-bg-color: rgba(230, 162, 60, 0.15);
  --el-tag-text-color: #e6a23c;
  --el-tag-border-color: transparent;
}
</style>
