<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">虚拟机</h2>
        <p class="page-desc">查看和管理所有 PVE 虚拟机实例</p>
      </div>
      <div class="header-actions">
        <el-input v-model="search" placeholder="搜索名称 / VMID" clearable prefix-icon="Search" style="width: 220px" @input="debounceLoad" />
        <el-select v-model="statusFilter" placeholder="状态" clearable style="width: 110px" @change="loadData">
          <el-option label="运行中" value="running" />
          <el-option label="已停止" value="stopped" />
          <el-option label="暂停" value="paused" />
        </el-select>
      </div>
    </div>
    <el-card shadow="hover" class="table-card">
      <div v-if="loading" class="loading-box">
        <el-icon class="is-loading" :size="20"><Loading /></el-icon>
        <span>加载中...</span>
      </div>
      <el-table v-else :data="vms" style="width: 100%" stripe :default-sort="{ prop: 'vmid', order: 'ascending' }">
        <el-table-column label="VMID" width="80" align="center" sortable sort-by="vmid">
          <template #default="{ row }"><code class="vmid">{{ row.vmid }}</code></template>
        </el-table-column>
        <el-table-column prop="name" label="名称" min-width="160" fixed>
          <template #default="{ row }">
            <span class="vm-name">{{ row.name }}</span>
            <div class="sub-text">{{ row.node_name }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="90" align="center" sortable sort-by="status">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small" disable-transitions>{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="CPU" min-width="120" sortable :sort-method="(a, b) => (a.cpu_usage || 0) - (b.cpu_usage || 0)">
          <template #default="{ row }">
            <div class="usage-cell">
              <el-progress :percentage="Math.round(row.cpu_usage || 0)" :stroke-width="8" :color="cpuColor(Math.round(row.cpu_usage || 0))" :show-text="false" />
              <span class="usage-text">{{ Math.round(row.cpu_usage || 0) }}% · {{ row.cpu_cores || '?' }}核</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="内存" min-width="140" sortable :sort-method="(a, b) => (a.memory_mb || 0) - (b.memory_mb || 0)">
          <template #default="{ row }">
            <span>{{ fmtMB(row.memory_used_mb) }} / {{ fmtMB(row.memory_mb) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="磁盘" min-width="110" sortable :sort-method="(a, b) => (a.max_disk_gb || 0) - (b.max_disk_gb || 0)">
          <template #default="{ row }">
            <span>{{ row.disk_gb || 0 }}GB / {{ row.max_disk_gb || 0 }}GB</span>
          </template>
        </el-table-column>
        <el-table-column label="网络 (累计)" min-width="140">
          <template #default="{ row }">
            <span class="net-text">↓{{ fmtBytes(row.net_in_bps) }} ↑{{ fmtBytes(row.net_out_bps) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="运行时长" min-width="100">
          <template #default="{ row }">{{ fmtUptime(row.uptime_seconds) }}</template>
        </el-table-column>
        <el-table-column prop="os_type" label="系统" width="90">
          <template #default="{ row }">{{ row.os_type || '-' }}</template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && !vms.length" description="暂无虚拟机数据" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Loading } from '@element-plus/icons-vue'
import { getVMs } from '@/api/vms'
import type { VMInfo } from '@/api/vms'

const loading = ref(true)
const vms = ref<VMInfo[]>([])
const search = ref('')
const statusFilter = ref('')
let timer: ReturnType<typeof setTimeout> | null = null

onMounted(() => loadData())

async function loadData() {
  loading.value = true
  try {
    const params: Record<string, string> = {}
    if (statusFilter.value) params.status = statusFilter.value
    if (search.value) params.search = search.value
    vms.value = await getVMs(params)
  } catch {} finally { loading.value = false }
}

function debounceLoad() {
  if (timer) clearTimeout(timer)
  timer = setTimeout(loadData, 300)
}

function statusType(s: string) { return s === 'running' ? 'success' : s === 'stopped' ? 'danger' : 'warning' }
function statusLabel(s: string) { return s === 'running' ? '运行中' : s === 'stopped' ? '已停止' : s === 'paused' ? '暂停' : s }
function cpuColor(p: number) { return p > 85 ? '#f56c6c' : p >= 70 ? '#e6a23c' : '#67c23a' }
function fmtMB(mb: number) { return mb >= 1024 ? `${(mb / 1024).toFixed(1)}GB` : `${mb || 0}MB` }
function fmtBytes(bytes: number) {
  if (!bytes) return '0B'
  if (bytes >= 1073741824) return `${(bytes / 1073741824).toFixed(1)}GB`
  if (bytes >= 1048576) return `${(bytes / 1048576).toFixed(1)}MB`
  if (bytes >= 1024) return `${(bytes / 1024).toFixed(1)}KB`
  return `${bytes}B`
}
function fmtUptime(s: number) {
  if (!s) return '-'
  const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600)
  return d > 0 ? `${d}天${h}时` : `${h}时${Math.floor((s % 3600) / 60)}分`
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
.vmid { font-size: 12px; background: var(--bg-secondary); padding: 2px 6px; border-radius: 4px; }
.vm-name { font-weight: 600; color: var(--text-primary); }
.sub-text { font-size: 12px; color: var(--text-muted); }
.usage-cell { display: flex; flex-direction: column; gap: 4px; }
.usage-text { font-size: 12px; color: var(--text-muted); }
.net-text { font-size: 12px; color: var(--text-secondary); }
:deep(.el-table) { background: transparent; --el-table-bg-color: transparent; --el-table-tr-bg-color: transparent; --el-table-header-bg-color: transparent; --el-table-border-color: var(--border-color); --el-table-text-color: var(--text-primary); --el-table-header-text-color: var(--text-secondary); }
:deep(.el-table::before) { display: none; }
:deep(.el-table th.el-table__cell) { background: transparent; }
:deep(.el-table--enable-row-hover .el-table__body tr:hover > td) { background-color: rgba(64, 158, 255, 0.05); }
:deep(.el-tag--success) { --el-tag-bg-color: rgba(103, 194, 58, 0.15); --el-tag-text-color: #67c23a; --el-tag-border-color: transparent; }
:deep(.el-tag--danger) { --el-tag-bg-color: rgba(245, 108, 108, 0.15); --el-tag-text-color: #f56c6c; --el-tag-border-color: transparent; }
:deep(.el-tag--warning) { --el-tag-bg-color: rgba(230, 162, 60, 0.15); --el-tag-text-color: #e6a23c; --el-tag-border-color: transparent; }
</style>
