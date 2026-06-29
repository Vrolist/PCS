<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">容器</h2>
        <p class="page-desc">查看和管理所有 PVE LXC 容器</p>
      </div>
      <div class="header-actions">
        <el-input v-model="search" placeholder="搜索名称 / ID" clearable prefix-icon="Search" style="width: 220px" @input="debounceLoad" />
        <el-select v-model="statusFilter" placeholder="状态" clearable style="width: 110px" @change="loadData">
          <el-option label="运行中" value="running" />
          <el-option label="已停止" value="stopped" />
        </el-select>
      </div>
    </div>
    <el-card shadow="hover" class="table-card">
      <div v-if="loading" class="loading-box">
        <el-icon class="is-loading" :size="20"><Loading /></el-icon>
        <span>加载中...</span>
      </div>
      <el-table v-else :data="containers" style="width: 100%" stripe>
        <el-table-column label="ID" width="80" align="center">
          <template #default="{ row }"><code class="vmid">{{ row.vmid }}</code></template>
        </el-table-column>
        <el-table-column prop="name" label="名称" min-width="160" fixed>
          <template #default="{ row }">
            <span class="ct-name">{{ row.name }}</span>
            <div class="sub-text">{{ row.node_name }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 'running' ? 'success' : 'danger'" size="small" disable-transitions>
              {{ row.status === 'running' ? '运行中' : '已停止' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="CPU" min-width="120">
          <template #default="{ row }">
            <div class="usage-cell">
              <el-progress :percentage="Math.round(row.cpu_usage || 0)" :stroke-width="8" :color="cpuColor(Math.round(row.cpu_usage || 0))" :show-text="false" />
              <span class="usage-text">{{ Math.round(row.cpu_usage || 0) }}% · {{ row.cpu_cores || '?' }}核</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="内存" min-width="140">
          <template #default="{ row }">
            <span>{{ fmtMB(row.memory_used_mb) }} / {{ fmtMB(row.memory_mb) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="Swap" min-width="120">
          <template #default="{ row }">
            <span>{{ fmtMB(row.swap_used_mb) }} / {{ fmtMB(row.swap_mb) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="磁盘" min-width="100">
          <template #default="{ row }">
            <span>{{ row.disk_gb || 0 }}GB</span>
          </template>
        </el-table-column>
        <el-table-column label="运行时长" min-width="100">
          <template #default="{ row }">{{ fmtUptime(row.uptime_seconds) }}</template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && !containers.length" description="暂无容器数据" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Loading } from '@element-plus/icons-vue'
import { getContainers } from '@/api/containers'
import type { ContainerInfo } from '@/api/containers'

const loading = ref(true)
const containers = ref<ContainerInfo[]>([])
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
    containers.value = await getContainers(params)
  } catch {} finally { loading.value = false }
}

function debounceLoad() {
  if (timer) clearTimeout(timer)
  timer = setTimeout(loadData, 300)
}

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
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 28px; flex-wrap: wrap; gap: 12px; }
.page-title { font-size: 24px; font-weight: 700; color: var(--text-heading); margin: 0; }
.page-desc { font-size: 14px; color: var(--text-muted); margin: 4px 0 0; }
.header-actions { display: flex; gap: 8px; align-items: center; }
.table-card { border-radius: 16px; }
.loading-box { display: flex; align-items: center; justify-content: center; gap: 8px; padding: 40px; color: var(--text-secondary); }
.vmid { font-size: 12px; background: var(--bg-secondary); padding: 2px 6px; border-radius: 4px; }
.ct-name { font-weight: 600; color: var(--text-primary); }
.sub-text { font-size: 12px; color: var(--text-muted); }
.usage-cell { display: flex; flex-direction: column; gap: 4px; }
.usage-text { font-size: 12px; color: var(--text-muted); }
:deep(.el-table) { background: transparent; --el-table-bg-color: transparent; --el-table-tr-bg-color: transparent; --el-table-header-bg-color: transparent; --el-table-border-color: var(--border-color); --el-table-text-color: var(--text-primary); --el-table-header-text-color: var(--text-secondary); }
:deep(.el-table::before) { display: none; }
:deep(.el-table th.el-table__cell) { background: transparent; }
:deep(.el-table--enable-row-hover .el-table__body tr:hover > td) { background-color: rgba(64, 158, 255, 0.05); }
:deep(.el-tag--success) { --el-tag-bg-color: rgba(103, 194, 58, 0.15); --el-tag-text-color: #67c23a; --el-tag-border-color: transparent; }
:deep(.el-tag--danger) { --el-tag-bg-color: rgba(245, 108, 108, 0.15); --el-tag-text-color: #f56c6c; --el-tag-border-color: transparent; }
</style>
