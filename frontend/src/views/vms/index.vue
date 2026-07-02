<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">虚拟机</h2>
        <p class="page-desc">查看和管理所有 PVE 虚拟机实例</p>
      </div>
      <div class="header-actions">
        <el-select v-model="nodeFilter" placeholder="节点" clearable style="width: 160px" @change="loadData">
          <el-option v-for="n in nodes" :key="n.id" :label="n.node_name" :value="n.id" />
        </el-select>
        <el-select v-model="statusFilter" placeholder="状态" clearable style="width: 110px" @change="loadData">
          <el-option label="运行中" value="running" />
          <el-option label="已停止" value="stopped" />
          <el-option label="暂停" value="paused" />
        </el-select>
        <el-input v-model="search" placeholder="搜索名称 / VMID" clearable prefix-icon="Search" style="width: 220px" @input="debounceLoad" />
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
            <span>{{ row.max_disk_gb || 0 }}GB</span>
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
    <el-dialog v-model="detailVisible" :title="detailData?.vm?.name || 'VM 详情'" width="720px" destroy-on-close top="5vh">
      <div v-if="detailLoading" class="loading-box">
        <el-icon class="is-loading" :size="20"><Loading /></el-icon>
        <span>加载中...</span>
      </div>
      <div v-else-if="detailData" class="detail-content">
        <!-- 基本信息 -->
        <div class="detail-section">
          <h4>基本信息</h4>
          <div class="detail-kv">
            <div class="kv-row"><span class="kv-label">VMID</span><span class="kv-val mono">{{ detailData.vm.vmid }}</span></div>
            <div class="kv-row"><span class="kv-label">状态</span><span class="kv-val"><el-tag :type="detailData.vm.status === 'running' ? 'success' : 'danger'" size="small">{{ detailData.vm.status === 'running' ? '运行中' : detailData.vm.status === 'paused' ? '暂停' : '已停止' }}</el-tag></span></div>
            <div class="kv-row"><span class="kv-label">节点</span><span class="kv-val">{{ detailData.vm.node_name }}</span></div>
            <div class="kv-row"><span class="kv-label">集群</span><span class="kv-val">{{ detailData.vm.cluster_name }}</span></div>
            <div class="kv-row" v-if="detailData.vm.has_template"><span class="kv-label">类型</span><span class="kv-val"><el-tag type="warning" size="small" effect="plain">模板</el-tag></span></div>
            <div class="kv-row"><span class="kv-label">系统</span><span class="kv-val">{{ detailData.vm.os_type || '-' }}</span></div>
            <div class="kv-row"><span class="kv-label">CPU</span><span class="kv-val">{{ detailData.vm.cpu_usage }}% · {{ detailData.vm.cpu_cores }}核 × {{ detailData.vm.cpu_sockets || 1 }}插槽</span></div>
            <div class="kv-row"><span class="kv-label">内存</span><span class="kv-val">{{ fmtMB(detailData.vm.memory_used_mb) }} / {{ fmtMB(detailData.vm.memory_mb) }}</span></div>
            <div class="kv-row" v-if="detailData.vm.balloon_min_mb"><span class="kv-label">Balloon</span><span class="kv-val">{{ fmtMB(detailData.vm.balloon_min_mb) }} ~ {{ fmtMB(detailData.vm.balloon_max_mb) }}</span></div>
            <div class="kv-row"><span class="kv-label">磁盘</span><span class="kv-val">{{ detailData.vm.disk_gb }}GB / {{ detailData.vm.max_disk_gb }}GB</span></div>
            <div class="kv-row"><span class="kv-label">网络</span><span class="kv-val">↓{{ fmtBits(detailData.vm.net_in_bps) }} ↑{{ fmtBits(detailData.vm.net_out_bps) }}</span></div>
            <div class="kv-row"><span class="kv-label">磁盘 IOPS</span><span class="kv-val">读 {{ detailData.vm.disk_read_iops?.toFixed(1) || 0 }} / 写 {{ detailData.vm.disk_write_iops?.toFixed(1) || 0 }}</span></div>
            <div class="kv-row" v-if="detailData.vm.uptime_seconds"><span class="kv-label">运行时长</span><span class="kv-val">{{ fmtUptime(detailData.vm.uptime_seconds) }}</span></div>
            <div class="kv-row" v-if="detailData.vm.snapshot_count"><span class="kv-label">快照数</span><span class="kv-val">{{ detailData.vm.snapshot_count }}</span></div>
            <div class="kv-row" v-if="detailData.vm.tags"><span class="kv-label">标签</span><span class="kv-val">{{ detailData.vm.tags }}</span></div>
            <div class="kv-row" v-if="detailData.vm.description"><span class="kv-label">描述</span><span class="kv-val">{{ detailData.vm.description }}</span></div>
            <div class="kv-row"><span class="kv-label">扫描时间</span><span class="kv-val mono">{{ fmtTime(detailData.vm.scanned_at) }}</span></div>
          </div>
        </div>
        <!-- 配置信息 -->
        <div class="detail-section" v-if="detailData.config">
          <h4>配置</h4>
          <div class="detail-kv">
            <div class="kv-row"><span class="kv-label">CPU 类型</span><span class="kv-val mono">{{ detailData.config.cpu_type || 'host' }}</span></div>
            <div class="kv-row"><span class="kv-label">CPU 核心</span><span class="kv-val">{{ detailData.config.cpu_cores }}核 × {{ detailData.config.cpu_sockets || 1 }}插槽</span></div>
            <div class="kv-row"><span class="kv-label">内存</span><span class="kv-val">{{ detailData.config.memory_mb ? fmtMB(detailData.config.memory_mb) : '-' }}</span></div>
            <div class="kv-row" v-if="detailData.config.balloon_min_mb"><span class="kv-label">Balloon</span><span class="kv-val">{{ fmtMB(detailData.config.balloon_min_mb) }}</span></div>
            <div class="kv-row" v-if="detailData.config.os_type"><span class="kv-label">系统类型</span><span class="kv-val">{{ detailData.config.os_type }}</span></div>
            <div class="kv-row"><span class="kv-label">启动顺序</span><span class="kv-val mono">{{ detailData.config.boot_order || '-' }}</span></div>
            <div class="kv-row"><span class="kv-label">QEMU Agent</span><span class="kv-val"><el-tag :type="detailData.config.agent_enabled ? 'success' : 'info'" size="small">{{ detailData.config.agent_enabled ? '启用' : '未启用' }}</el-tag></span></div>
            <div class="kv-row"><span class="kv-label">HA</span><span class="kv-val"><el-tag :type="detailData.config.ha_enabled ? 'success' : 'info'" size="small">{{ detailData.config.ha_enabled ? (detailData.config.ha_group || '启用') : '未启用' }}</el-tag></span></div>
            <div class="kv-row" v-if="detailData.config.tags"><span class="kv-label">标签</span><span class="kv-val">{{ detailData.config.tags }}</span></div>
            <div class="kv-row" v-if="detailData.config.description"><span class="kv-label">描述</span><span class="kv-val">{{ detailData.config.description }}</span></div>
          </div>
        </div>
        <!-- SCSI 磁盘 -->
        <div class="detail-section" v-if="detailData.config?.scsi_disks?.length">
          <h4>SCSI 磁盘</h4>
          <div class="device-list">
            <div v-for="d in detailData.config.scsi_disks" :key="d.slot" class="device-chip">
              <span class="chip-tag">scsi{{ d.slot }}</span>
              <span class="chip-body">{{ d.storage || '-' }}</span>
              <span class="chip-sub mono">{{ d.raw }}</span>
            </div>
          </div>
        </div>
        <!-- IDE 设备 -->
        <div class="detail-section" v-if="detailData.config?.ide_disks?.length">
          <h4>IDE 设备</h4>
          <div class="device-list">
            <div v-for="d in detailData.config.ide_disks" :key="d.slot" class="device-chip">
              <span class="chip-tag">ide{{ d.slot }}</span>
              <span class="chip-body">{{ d.storage || '-' }}</span>
              <el-tag v-if="d.media" size="small" type="info" effect="plain">{{ d.media }}</el-tag>
              <span class="chip-sub mono">{{ d.raw }}</span>
            </div>
          </div>
        </div>
        <!-- 网卡 -->
        <div class="detail-section" v-if="detailData.config?.net_devices?.length">
          <h4>网卡</h4>
          <div class="device-list">
            <div v-for="n in detailData.config.net_devices" :key="n.slot" class="device-chip">
              <span class="chip-tag">net{{ n.slot }}</span>
              <span class="chip-body">{{ n.model || '-' }}</span>
              <span class="chip-sub">桥接 {{ n.bridge || '-' }}</span>
              <span class="chip-sub mono">{{ n.hwaddr || '-' }}</span>
            </div>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { Loading } from '@element-plus/icons-vue'
import { getVMs, getVMDetail } from '@/api/vms'
import type { VMInfo, VMDetail } from '@/api/vms'
import { getNodes } from '@/api/nodes'
import type { NodeInfo } from '@/api/nodes'
import { useClusterStore } from '@/stores/cluster'

const clusterStore = useClusterStore()

const loading = ref(true)
const vms = ref<VMInfo[]>([])
const search = ref('')
const statusFilter = ref('')
const nodeFilter = ref<number | ''>('')
const nodes = ref<NodeInfo[]>([])
const detailVisible = ref(false)
const detailLoading = ref(false)
const detailData = ref<VMDetail | null>(null)
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
    if (statusFilter.value) params.status = statusFilter.value
    if (search.value) params.search = search.value
    if (nodeFilter.value !== '') params.node_id = nodeFilter.value
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
function fmtBits(bps: number) {
  if (!bps) return '0bps'
  if (bps >= 1000000000) return `${(bps / 1000000000).toFixed(1)}Gbps`
  if (bps >= 1000000) return `${(bps / 1000000).toFixed(1)}Mbps`
  if (bps >= 1000) return `${(bps / 1000).toFixed(1)}Kbps`
  return `${bps}bps`
}
function fmtTime(iso: string) {
  if (!iso) return '-'
  return new Date(iso).toLocaleString('zh-CN')
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
.detail-content { max-height: 70vh; overflow-y: auto; }
.detail-section { margin-bottom: 16px; }
.detail-section:last-child { margin-bottom: 0; }
.detail-section h4 { font-size: 13px; font-weight: 600; color: var(--text-secondary); margin: 0 0 8px; padding-bottom: 6px; border-bottom: 1px solid var(--border-color); text-transform: uppercase; letter-spacing: 0.5px; }
.detail-kv { display: grid; grid-template-columns: 1fr 1fr; gap: 2px 20px; }
.kv-row { display: flex; align-items: center; padding: 5px 0; border-bottom: 1px dashed var(--border-color); }
.kv-label { font-size: 13px; color: var(--text-muted); min-width: 72px; flex-shrink: 0; }
.kv-val { font-size: 13px; color: var(--text-primary); }
.mono { font-family: 'SF Mono', 'Menlo', monospace; font-size: 12px; }
.device-list { display: flex; flex-direction: column; gap: 4px; }
.device-chip { display: flex; align-items: center; gap: 8px; padding: 6px 10px; background: var(--bg-secondary); border-radius: 8px; }
.chip-tag { font-size: 12px; font-weight: 600; color: var(--color-primary); background: rgba(64, 158, 255, 0.1); padding: 1px 6px; border-radius: 4px; white-space: nowrap; }
.chip-body { font-size: 13px; font-weight: 500; color: var(--text-primary); }
.chip-sub { font-size: 12px; color: var(--text-muted); }
:deep(.el-table) { background: var(--el-card-bg-color); --el-table-bg-color: var(--el-card-bg-color); --el-table-tr-bg-color: var(--el-card-bg-color); --el-table-header-bg-color: var(--el-card-bg-color); --el-table-border-color: var(--border-color); --el-table-text-color: var(--text-primary); --el-table-header-text-color: var(--text-secondary); }
:deep(.el-table::before) { display: none; }
:deep(.el-table th.el-table__cell) { background-color: var(--el-card-bg-color); }
:deep(.el-table--enable-row-hover .el-table__body tr:hover > td) { background-color: rgba(64, 158, 255, 0.05); }
:deep(.el-tag--success) { --el-tag-bg-color: rgba(103, 194, 58, 0.15); --el-tag-text-color: #67c23a; --el-tag-border-color: transparent; }
:deep(.el-tag--danger) { --el-tag-bg-color: rgba(245, 108, 108, 0.15); --el-tag-text-color: #f56c6c; --el-tag-border-color: transparent; }
/* 固定列强制不透明背景 */
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
:deep(.el-tag--warning) { --el-tag-bg-color: rgba(230, 162, 60, 0.15); --el-tag-text-color: #e6a23c; --el-tag-border-color: transparent; }
</style>
