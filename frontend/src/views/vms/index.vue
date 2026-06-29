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
        <el-table-column label="操作" width="80" align="center" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="showDetail(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && !vms.length" description="暂无虚拟机数据" />
    </el-card>
    <!-- VM 详情弹窗 -->
    <el-dialog v-model="detailVisible" :title="detailData?.vm?.name || 'VM 详情'" width="680px" destroy-on-close>
      <div v-if="detailLoading" class="loading-box">
        <el-icon class="is-loading" :size="20"><Loading /></el-icon>
        <span>加载中...</span>
      </div>
      <div v-else-if="detailData" class="detail-content">
        <div class="detail-section">
          <h4>基本信息</h4>
          <div class="detail-grid">
            <div class="detail-item"><span class="detail-label">VMID</span><span>{{ detailData.vm.vmid }}</span></div>
            <div class="detail-item"><span class="detail-label">状态</span>
              <el-tag :type="detailData.vm.status === 'running' ? 'success' : 'danger'" size="small">{{ detailData.vm.status === 'running' ? '运行中' : '已停止' }}</el-tag>
            </div>
            <div class="detail-item"><span class="detail-label">节点</span><span>{{ detailData.vm.node_name }}</span></div>
            <div class="detail-item"><span class="detail-label">CPU</span><span>{{ detailData.vm.cpu_usage }}% · {{ detailData.vm.cpu_cores }}核</span></div>
            <div class="detail-item"><span class="detail-label">内存</span><span>{{ fmtMB(detailData.vm.memory_used_mb) }} / {{ fmtMB(detailData.vm.memory_mb) }}</span></div>
            <div class="detail-item"><span class="detail-label">磁盘</span><span>{{ detailData.vm.disk_gb }}GB / {{ detailData.vm.max_disk_gb }}GB</span></div>
          </div>
        </div>
        <div class="detail-section" v-if="detailData.config">
          <h4>配置信息</h4>
          <div class="detail-grid">
            <div class="detail-item"><span class="detail-label">CPU 类型</span><span>{{ detailData.config.cpu_type || 'host' }}</span></div>
            <div class="detail-item"><span class="detail-label">CPU 插槽</span><span>{{ detailData.config.cpu_sockets || 1 }}</span></div>
            <div class="detail-item"><span class="detail-label">启动顺序</span><span class="mono">{{ detailData.config.boot_order || '-' }}</span></div>
            <div class="detail-item"><span class="detail-label">QEMU Agent</span>
              <el-tag :type="detailData.config.agent_enabled ? 'success' : 'info'" size="small">{{ detailData.config.agent_enabled ? '启用' : '未启用' }}</el-tag>
            </div>
          </div>
        </div>
        <div class="detail-section" v-if="detailData.config?.scsi_disks?.length">
          <h4>SCSI 磁盘</h4>
          <el-table :data="detailData.config.scsi_disks" size="small" stripe>
            <el-table-column prop="slot" label="槽位" width="100" />
            <el-table-column prop="storage" label="存储" width="120" />
            <el-table-column prop="raw" label="配置" />
          </el-table>
        </div>
        <div class="detail-section" v-if="detailData.config?.ide_disks?.length">
          <h4>IDE 设备</h4>
          <el-table :data="detailData.config.ide_disks" size="small" stripe>
            <el-table-column prop="slot" label="槽位" width="100" />
            <el-table-column prop="storage" label="存储" width="120" />
            <el-table-column prop="media" label="类型" width="80" />
            <el-table-column prop="raw" label="配置" />
          </el-table>
        </div>
        <div class="detail-section" v-if="detailData.config?.net_devices?.length">
          <h4>网卡</h4>
          <el-table :data="detailData.config.net_devices" size="small" stripe>
            <el-table-column prop="slot" label="槽位" width="100" />
            <el-table-column label="模型" width="100">
              <template #default="{ row }">{{ row.model || '-' }}</template>
            </el-table-column>
            <el-table-column label="桥接" width="100">
              <template #default="{ row }">{{ row.bridge || '-' }}</template>
            </el-table-column>
            <el-table-column label="MAC">
              <template #default="{ row }">{{ row.hwaddr || '-' }}</template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Loading } from '@element-plus/icons-vue'
import { getVMs, getVMDetail } from '@/api/vms'
import type { VMInfo, VMDetail } from '@/api/vms'

const loading = ref(true)
const vms = ref<VMInfo[]>([])
const search = ref('')
const statusFilter = ref('')
const detailVisible = ref(false)
const detailLoading = ref(false)
const detailData = ref<VMDetail | null>(null)
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

async function showDetail(row: VMInfo) {
  detailVisible.value = true
  detailLoading.value = true
  try {
    detailData.value = await getVMDetail(row.id)
  } catch { detailData.value = null } finally { detailLoading.value = false }
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
.detail-content { max-height: 60vh; overflow-y: auto; }
.detail-section { margin-bottom: 20px; }
.detail-section h4 { font-size: 15px; font-weight: 600; color: var(--text-primary); margin: 0 0 12px; }
.detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.detail-item { display: flex; flex-direction: column; gap: 4px; }
.detail-label { font-size: 12px; color: var(--text-muted); }
.mono { font-family: monospace; font-size: 13px; }
:deep(.el-table) { background: transparent; --el-table-bg-color: transparent; --el-table-tr-bg-color: transparent; --el-table-header-bg-color: transparent; --el-table-border-color: var(--border-color); --el-table-text-color: var(--text-primary); --el-table-header-text-color: var(--text-secondary); }
:deep(.el-table::before) { display: none; }
:deep(.el-table th.el-table__cell) { background: transparent; }
:deep(.el-table--enable-row-hover .el-table__body tr:hover > td) { background-color: rgba(64, 158, 255, 0.05); }
:deep(.el-tag--success) { --el-tag-bg-color: rgba(103, 194, 58, 0.15); --el-tag-text-color: #67c23a; --el-tag-border-color: transparent; }
:deep(.el-tag--danger) { --el-tag-bg-color: rgba(245, 108, 108, 0.15); --el-tag-text-color: #f56c6c; --el-tag-border-color: transparent; }
:deep(.el-tag--warning) { --el-tag-bg-color: rgba(230, 162, 60, 0.15); --el-tag-text-color: #e6a23c; --el-tag-border-color: transparent; }
</style>
