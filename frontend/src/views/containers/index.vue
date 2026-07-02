<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ t('containers.title') }}</h2>
        <p class="page-desc">{{ t('containers.subtitle') }}</p>
      </div>
      <div class="header-actions">
        <el-select v-model="nodeFilter" :placeholder="t('containers.nodeFilter')" clearable style="width: 160px" @change="loadData">
          <el-option v-for="n in nodes" :key="n.id" :label="n.node_name" :value="n.id" />
        </el-select>
        <el-select v-model="statusFilter" :placeholder="t('containers.statusFilter')" clearable style="width: 110px" @change="loadData">
          <el-option :label="t('containers.running')" value="running" />
          <el-option :label="t('containers.stopped')" value="stopped" />
        </el-select>
        <el-select v-model="typeFilter" :placeholder="t('containers.typeFilter')" clearable style="width: 110px" @change="loadData">
          <el-option :label="t('containers.typeContainer')" value="container" />
          <el-option :label="t('containers.typeTemplate')" value="template" />
        </el-select>
        <el-input v-model="search" :placeholder="t('containers.searchPlaceholder')" clearable prefix-icon="Search" style="width: 220px" @input="debounceLoad" />
      </div>
    </div>
    <el-card shadow="hover" class="table-card">
      <div v-if="loading" class="loading-box">
        <el-icon class="is-loading" :size="20"><Loading /></el-icon>
        <span>{{ t('common.loading') }}</span>
      </div>
      <el-table v-else :data="containers" style="width: 100%" stripe>
        <el-table-column label="ID" width="80" align="center">
          <template #default="{ row }"><code class="vmid">{{ row.vmid }}</code></template>
        </el-table-column>
        <el-table-column prop="name" :label="t('containers.name')" min-width="160" fixed>
          <template #default="{ row }">
            <span class="ct-name">{{ row.name }}</span>
            <div class="sub-text">{{ row.node_name }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="status" :label="t('containers.status')" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 'running' ? 'success' : 'danger'" size="small" disable-transitions>
              {{ row.status === 'running' ? t('containers.running') : t('containers.stopped') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="t('containers.type')" width="80" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.has_template" type="warning" size="small" effect="plain">{{ t('containers.typeTemplate') }}</el-tag>
            <el-tag v-else type="primary" size="small" effect="plain">{{ t('containers.typeContainer') }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="t('containers.ip')" min-width="140">
          <template #default="{ row }">
            <span style="font-family: monospace; font-size: 12px;">{{ row.ip_address || '--' }}</span>
          </template>
        </el-table-column>
        <el-table-column :label="t('containers.cpu')" min-width="120">
          <template #default="{ row }">
            <div class="usage-cell">
              <el-progress :percentage="Math.round(row.cpu_usage || 0)" :stroke-width="8" :color="cpuColor(Math.round(row.cpu_usage || 0))" :show-text="false" />
              <span class="usage-text">{{ Math.round(row.cpu_usage || 0) }}% · {{ row.cpu_cores || '?' }}{{ t('common.cores') }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column :label="t('containers.memory')" min-width="140">
          <template #default="{ row }">
            <span>{{ fmtMB(row.memory_used_mb) }} / {{ fmtMB(row.memory_mb) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="Swap" min-width="120">
          <template #default="{ row }">
            <span>{{ fmtMB(row.swap_used_mb) }} / {{ fmtMB(row.swap_mb) }}</span>
          </template>
        </el-table-column>
        <el-table-column :label="t('containers.disk')" min-width="100">
          <template #default="{ row }">
            <span>{{ row.disk_gb || 0 }}GB</span>
          </template>
        </el-table-column>
        <el-table-column :label="t('containers.runtime')" min-width="100">
          <template #default="{ row }">{{ fmtUptime(row.uptime_seconds) }}</template>
        </el-table-column>
        <el-table-column :label="t('common.operation')" width="80" align="center" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="showDetail(row)">{{ t('common.detail') }}</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && !containers.length" :description="t('containers.emptyDesc')" />
    </el-card>

    <!-- 详情对话框 -->
    <el-dialog v-model="detailVisible" :title="detailData?.container?.name || t('containers.containerDetailTitle')" width="720px" :close-on-click-modal="true" top="5vh">
      <div v-if="detailLoading" class="loading-box">
        <el-icon class="is-loading" :size="20"><Loading /></el-icon>
        <span>{{ t('common.loading') }}</span>
      </div>
      <div v-else-if="detailData" class="detail-content">
        <!-- 基本信息 -->
        <div class="detail-section">
          <h4>{{ t('containers.basicInfo') }}</h4>
          <div class="detail-kv">
            <div class="kv-row"><span class="kv-label">VMID</span><span class="kv-val mono">{{ detailData.container.vmid }}</span></div>
            <div class="kv-row"><span class="kv-label">{{ t('containers.status') }}</span><span class="kv-val"><el-tag :type="detailData.container.status === 'running' ? 'success' : 'danger'" size="small" disable-transitions>{{ detailData.container.status === 'running' ? t('containers.running') : t('containers.stopped') }}</el-tag></span></div>
            <div class="kv-row"><span class="kv-label">{{ t('common.name') }}</span><span class="kv-val">{{ detailData.container.node_name }}</span></div>
            <div class="kv-row"><span class="kv-label">{{ t('containers.cluster') }}</span><span class="kv-val">{{ detailData.container.cluster_name }}</span></div>
            <div class="kv-row"><span class="kv-label">{{ t('containers.type') }}</span><span class="kv-val"><el-tag :type="detailData.container.has_template ? 'warning' : 'primary'" size="small" effect="plain">{{ detailData.container.has_template ? t('containers.typeTemplate') : t('containers.typeContainer') }}</el-tag></span></div>
            <div class="kv-row" v-if="detailData.container.ip_address"><span class="kv-label">{{ t('containers.ip') }}</span><span class="kv-val mono">{{ detailData.container.ip_address }}</span></div>
            <div class="kv-row"><span class="kv-label">{{ t('containers.cpu') }}</span><span class="kv-val">{{ Math.round(detailData.container.cpu_usage || 0) }}% · {{ detailData.container.cpu_cores || '?' }} {{ t('common.cores') }}</span></div>
            <div class="kv-row"><span class="kv-label">{{ t('containers.memory') }}</span><span class="kv-val">{{ fmtMB(detailData.container.memory_used_mb) }} / {{ fmtMB(detailData.container.memory_mb) }}</span></div>
            <div class="kv-row"><span class="kv-label">Swap</span><span class="kv-val">{{ fmtMB(detailData.container.swap_used_mb) }} / {{ fmtMB(detailData.container.swap_mb) }}</span></div>
            <div class="kv-row"><span class="kv-label">{{ t('containers.disk') }}</span><span class="kv-val">{{ detailData.container.disk_gb || 0 }}GB</span></div>
            <div class="kv-row" v-if="detailData.container.uptime_seconds"><span class="kv-label">{{ t('containers.runtime') }}</span><span class="kv-val">{{ fmtUptime(detailData.container.uptime_seconds) }}</span></div>
            <div class="kv-row" v-if="detailData.container.tags"><span class="kv-label">{{ t('containers.tags') }}</span><span class="kv-val">{{ detailData.container.tags }}</span></div>
            <div class="kv-row" v-if="detailData.container.description"><span class="kv-label">{{ t('clusters.description') }}</span><span class="kv-val">{{ detailData.container.description }}</span></div>
            <div class="kv-row"><span class="kv-label">{{ t('common.scanTime') }}</span><span class="kv-val mono">{{ fmtTime(detailData.container.scanned_at) }}</span></div>
          </div>
        </div>
        <!-- 配置信息 -->
        <div v-if="detailData.config" class="detail-section">
          <h4>{{ t('containers.config') }}</h4>
          <div class="detail-kv">
            <div class="kv-row"><span class="kv-label">{{ t('containers.hostname') }}</span><span class="kv-val">{{ detailData.config.hostname || '-' }}</span></div>
            <div class="kv-row"><span class="kv-label">{{ t('containers.osType') }}</span><span class="kv-val">{{ detailData.config.os_type || '-' }}</span></div>
            <div class="kv-row"><span class="kv-label">{{ t('containers.cpuCores') }}</span><span class="kv-val">{{ detailData.config.cpu_cores || '-' }}</span></div>
            <div class="kv-row"><span class="kv-label">{{ t('containers.memory') }}</span><span class="kv-val">{{ detailData.config.memory_mb ? fmtMB(detailData.config.memory_mb) : '-' }}</span></div>
            <div class="kv-row"><span class="kv-label">Swap</span><span class="kv-val">{{ detailData.config.swap_mb ? fmtMB(detailData.config.swap_mb) : '-' }}</span></div>
            <div class="kv-row" v-if="detailData.config.startup_order"><span class="kv-label">{{ t('vms.bootOrder') }}</span><span class="kv-val mono">{{ detailData.config.startup_order }}</span></div>
            <div class="kv-row"><span class="kv-label">{{ t('containers.ha') }}</span><span class="kv-val"><el-tag :type="detailData.config.ha_enabled ? 'success' : 'info'" size="small">{{ detailData.config.ha_enabled ? (detailData.config.ha_group || t('common.enabled')) : t('common.disabled') }}</el-tag></span></div>
            <div class="kv-row" v-if="detailData.config.tags"><span class="kv-label">{{ t('containers.tags') }}</span><span class="kv-val">{{ detailData.config.tags }}</span></div>
            <div class="kv-row" v-if="detailData.config.description"><span class="kv-label">{{ t('clusters.description') }}</span><span class="kv-val">{{ detailData.config.description }}</span></div>
          </div>
        </div>
        <!-- 存储设备 -->
        <div class="detail-section" v-if="detailData.config?.rootfs || detailData.config?.mount_points?.length">
          <h4>{{ t('containers.storage') }}</h4>
          <div class="device-list">
            <div v-if="detailData.config.rootfs" class="device-chip">
              <span class="chip-tag">rootfs</span>
              <span class="chip-body">{{ detailData.config.rootfs.storage || '-' }}</span>
              <span class="chip-sub mono">{{ detailData.config.rootfs.raw }}</span>
            </div>
            <div v-for="mp in (detailData.config.mount_points || [])" :key="mp.slot" class="device-chip">
              <span class="chip-tag">mp{{ mp.slot }}</span>
              <span class="chip-body">{{ mp.raw }}</span>
            </div>
          </div>
        </div>
        <!-- 网络设备 -->
        <div class="detail-section" v-if="detailData.config?.net_devices?.length">
          <h4>{{ t('containers.network') }}</h4>
          <div class="device-list">
            <div v-for="(net, idx) in detailData.config.net_devices" :key="idx" class="device-chip">
              <span class="chip-tag">{{ net.name || net.iface || `net${idx}` }}</span>
              <span class="chip-body">{{ net.type || 'veth' }}</span>
              <span class="chip-sub">{{ t('containers.bridge') }} {{ net.bridge || '-' }}</span>
              <span v-if="net.address" class="chip-sub mono">{{ net.address }}</span>
              <span v-if="net.hwaddr" class="chip-sub mono">{{ net.hwaddr }}</span>
            </div>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="detailVisible = false">{{ t('common.close') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Loading } from '@element-plus/icons-vue'

const { t } = useI18n()
import { getContainers, getContainerDetail } from '@/api/containers'
import type { ContainerInfo, ContainerDetail } from '@/api/containers'
import { getNodes } from '@/api/nodes'
import type { NodeInfo } from '@/api/nodes'
import { useClusterStore } from '@/stores/cluster'

const clusterStore = useClusterStore()

const loading = ref(true)
const containers = ref<ContainerInfo[]>([])
const search = ref('')
const statusFilter = ref('')
const typeFilter = ref('')
const nodeFilter = ref<number | ''>('')
const nodes = ref<NodeInfo[]>([])
let timer: ReturnType<typeof setTimeout> | null = null

const detailVisible = ref(false)
const detailLoading = ref(false)
const detailData = ref<ContainerDetail | null>(null)

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
    let data = await getContainers(params)
    if (typeFilter.value === 'template') data = data.filter(c => c.has_template)
    else if (typeFilter.value === 'container') data = data.filter(c => !c.has_template)
    containers.value = data
  } catch {} finally { loading.value = false }
}

function debounceLoad() {
  if (timer) clearTimeout(timer)
  timer = setTimeout(loadData, 300)
}

async function showDetail(row: ContainerInfo) {
  detailVisible.value = true
  detailLoading.value = true
  detailData.value = null
  try {
    detailData.value = await getContainerDetail(row.id)
  } catch {} finally {
    detailLoading.value = false
  }
}

function cpuColor(p: number) { return p > 85 ? '#f56c6c' : p >= 70 ? '#e6a23c' : '#67c23a' }
function fmtMB(mb: number) { return mb >= 1024 ? `${(mb / 1024).toFixed(1)}GB` : `${mb || 0}MB` }
function fmtTime(iso: string) {
  if (!iso) return '-'
  return new Date(iso).toLocaleString('zh-CN')
}
function fmtUptime(s: number) {
  if (!s) return '-'
  const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600)
  return d > 0 ? `${d}${t('common.days')}${h}${t('common.hours')}` : `${h}${t('common.hours')}${Math.floor((s % 3600) / 60)}${t('common.minutes')}`
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

/* 详情对话框样式 */
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
:deep(.el-table__fixed-right td),
:deep(.el-table .el-table-fixed-column--right) {
  background-color: var(--el-card-bg-color) !important;
}
:deep(.el-table__fixed-right th) {
  background-color: var(--el-card-bg-color) !important;
}
</style>
