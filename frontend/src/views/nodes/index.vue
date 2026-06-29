<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">节点管理</h2>
        <p class="page-desc">管理和监控 PVE 集群节点状态</p>
      </div>
      <div class="header-stats" v-if="nodes.length">
        <el-tag type="success" effect="plain">在线 {{ onlineCount }}</el-tag>
        <el-tag type="info" effect="plain">总计 {{ nodes.length }}</el-tag>
      </div>
    </div>
    <el-card shadow="hover" class="table-card">
      <div v-if="loading" class="loading-box">
        <el-icon class="is-loading" :size="20"><Loading /></el-icon>
        <span>加载中...</span>
      </div>
      <el-table v-else :data="nodes" style="width: 100%" stripe>
        <el-table-column prop="node_name" label="节点名称" min-width="130" fixed>
          <template #default="{ row }">
            <span class="node-name">{{ row.node_name }}</span>
            <div class="sub-text">{{ row.cluster_name }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 'online' ? 'success' : 'danger'" size="small" disable-transitions>
              {{ row.status === 'online' ? '在线' : '离线' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="CPU" min-width="150">
          <template #default="{ row }">
            <div class="usage-cell">
              <el-progress :percentage="cpuPercent(row)" :stroke-width="8" :color="cpuColor(cpuPercent(row))" :show-text="false" />
              <span class="usage-text">{{ cpuPercent(row) }}% · {{ row.cpu_cores || '?' }}核</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="内存" min-width="180">
          <template #default="{ row }">
            <div class="usage-cell">
              <el-progress :percentage="Math.round(row.memory_usage_pct || 0)" :stroke-width="8" color="#409eff" :show-text="false" />
              <span class="usage-text">{{ fmtMB(row.memory_used_mb) }}/{{ fmtMB(row.memory_total_mb) }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="磁盘" min-width="130">
          <template #default="{ row }">
            <span>{{ row.rootfs_used_gb || 0 }}GB / {{ row.rootfs_total_gb || 0 }}GB</span>
          </template>
        </el-table-column>
        <el-table-column label="I/O延迟" width="90" align="center">
          <template #default="{ row }">
            <span :class="{ 'text-warn': (row.disk_io_delay_ms || 0) > 50 }">{{ (row.disk_io_delay_ms || 0).toFixed(1) }}ms</span>
          </template>
        </el-table-column>
        <el-table-column prop="ip_address" label="IP 地址" min-width="140">
          <template #default="{ row }">{{ row.ip_address || '未知' }}</template>
        </el-table-column>
        <el-table-column prop="pve_version" label="PVE 版本" min-width="140" />
        <el-table-column label="运行时长" min-width="100">
          <template #default="{ row }">{{ fmtUptime(row.uptime_seconds) }}</template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && !nodes.length" description="暂无节点数据，请先部署 Agent 采集数据" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Loading } from '@element-plus/icons-vue'
import { getNodes } from '@/api/nodes'
import type { NodeInfo } from '@/api/nodes'

const loading = ref(true)
const nodes = ref<NodeInfo[]>([])
const onlineCount = computed(() => nodes.value.filter(n => n.status === 'online').length)

onMounted(async () => {
  try { nodes.value = await getNodes() } catch {} finally { loading.value = false }
})

function cpuPercent(row: NodeInfo) { return Math.round(row.cpu_load || 0) }
function cpuColor(p: number) { return p > 85 ? '#f56c6c' : p >= 70 ? '#e6a23c' : '#67c23a' }
function fmtMB(mb: number) { return mb >= 1024 ? `${(mb / 1024).toFixed(1)}GB` : `${mb || 0}MB` }
function fmtUptime(s: number) {
  if (!s) return '-'
  const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600)
  return d > 0 ? `${d}天${h}时` : `${h}时${Math.floor((s % 3600) / 60)}分`
}
</script>

<style scoped>
.page-container { max-width: 1400px; margin: 0 auto; }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 28px; }
.page-title { font-size: 24px; font-weight: 700; color: var(--text-heading); margin: 0; }
.page-desc { font-size: 14px; color: var(--text-muted); margin: 4px 0 0; }
.header-stats { display: flex; gap: 8px; }
.table-card { border-radius: 16px; }
.loading-box { display: flex; align-items: center; justify-content: center; gap: 8px; padding: 40px; color: var(--text-secondary); }
.node-name { font-weight: 600; color: var(--text-primary); }
.sub-text { font-size: 12px; color: var(--text-muted); }
.usage-cell { display: flex; flex-direction: column; gap: 4px; }
.usage-text { font-size: 12px; color: var(--text-muted); }
.text-warn { color: #e6a23c; font-weight: 600; }
:deep(.el-table) { background: transparent; --el-table-bg-color: transparent; --el-table-tr-bg-color: transparent; --el-table-header-bg-color: transparent; --el-table-border-color: var(--border-color); --el-table-text-color: var(--text-primary); --el-table-header-text-color: var(--text-secondary); }
:deep(.el-table::before) { display: none; }
:deep(.el-table th.el-table__cell) { background: transparent; }
:deep(.el-table--enable-row-hover .el-table__body tr:hover > td) { background-color: rgba(64, 158, 255, 0.05); }
:deep(.el-tag--success) { --el-tag-bg-color: rgba(103, 194, 58, 0.15); --el-tag-text-color: #67c23a; --el-tag-border-color: transparent; }
:deep(.el-tag--danger) { --el-tag-bg-color: rgba(245, 108, 108, 0.15); --el-tag-text-color: #f56c6c; --el-tag-border-color: transparent; }
</style>
