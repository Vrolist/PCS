<template>
  <div class="page-container">
    <!-- 标题区 -->
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ t('containers.title') }}</h2>
        <p class="page-desc">{{ t('containers.subtitle') }}</p>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-row" v-if="!loading && containers.length">
      <div class="stat-card" v-for="s in statCards" :key="s.key">
        <div class="stat-icon" :style="{ background: s.iconBg }">
          <el-icon :size="20"><component :is="s.icon" /></el-icon>
        </div>
        <div class="stat-info">
          <span class="stat-value">{{ s.value }}</span>
          <span class="stat-label">{{ s.label }}</span>
        </div>
      </div>
    </div>

    <!-- 搜索 & 筛选 -->
    <div class="toolbar">
      <el-input
        v-model="search"
        :placeholder="t('containers.searchPlaceholder')"
        clearable
        prefix-icon="Search"
        class="toolbar-search"
        @input="debounceLoad"
      />
      <el-select v-model="nodeFilter" :placeholder="t('containers.nodeFilter')" clearable style="width:150px" @change="loadData">
        <el-option v-for="n in nodes" :key="n.id" :label="n.node_name" :value="n.id" />
      </el-select>
      <el-select v-model="statusFilter" :placeholder="t('containers.statusFilter')" clearable style="width:110px" @change="loadData">
        <el-option :label="t('containers.running')" value="running" />
        <el-option :label="t('containers.stopped')" value="stopped" />
      </el-select>
      <el-select v-model="typeFilter" :placeholder="t('containers.typeFilter')" clearable style="width:110px" @change="loadData">
        <el-option :label="t('containers.typeContainer')" value="container" />
        <el-option :label="t('containers.typeTemplate')" value="template" />
      </el-select>
    </div>

    <!-- Master-Detail 双面板 -->
    <div class="master-detail" v-loading="loading">
      <!-- 左侧列表 -->
      <div class="master-panel">
        <div class="master-list" v-if="filteredContainers.length">
          <div
            v-for="item in filteredContainers"
            :key="item.id"
            class="master-item"
            :class="{ active: selectedId === item.id }"
            @click="selectItem(item)"
          >
            <div class="mi-top">
              <code class="mi-vmid">{{ item.vmid }}</code>
              <span class="mi-name">{{ item.name }}</span>
              <span class="mi-dot" :class="item.status === 'running' ? 'dot-run' : 'dot-stop'" />
            </div>
            <div class="mi-bottom">
              <span class="mi-node">{{ item.node_name }}</span>
              <span v-if="item.has_template" class="mi-template">{{ t('containers.typeTemplate') }}</span>
              <span v-if="item.ip_address" class="mi-ip">{{ item.ip_address }}</span>
            </div>
          </div>
        </div>
        <el-empty v-else-if="!loading" :description="t('containers.emptyDesc')" :image-size="80" />
      </div>

      <!-- 右侧详情 -->
      <div class="detail-panel">
        <template v-if="detailData">
          <!-- 详情头部 -->
          <div class="dp-header">
            <div class="dp-header-info">
              <div class="dp-title-row">
                <code class="dp-vmid">{{ detailData.container.vmid }}</code>
                <h3 class="dp-name">{{ detailData.container.name }}</h3>
                <el-tag :type="detailData.container.status === 'running' ? 'success' : 'danger'" size="small" disable-transitions>
                  {{ detailData.container.status === 'running' ? t('containers.running') : t('containers.stopped') }}
                </el-tag>
                <el-tag v-if="detailData.container.has_template" type="warning" size="small" effect="plain">{{ t('containers.typeTemplate') }}</el-tag>
              </div>
              <div class="dp-meta">
                <span>{{ detailData.container.node_name }}</span>
                <span v-if="detailData.container.ip_address" class="dp-ip">{{ detailData.container.ip_address }}</span>
              </div>
            </div>
          </div>

          <!-- 资源概览条 -->
          <div class="dp-resources">
            <div class="res-item">
              <span class="res-label">{{ t('containers.cpu') }}</span>
              <el-progress :percentage="Math.round(detailData.container.cpu_usage || 0)" :stroke-width="10" :color="cpuColor(Math.round(detailData.container.cpu_usage || 0))" />
              <span class="res-text">{{ Math.round(detailData.container.cpu_usage || 0) }}% · {{ detailData.container.cpu_cores || '?' }}{{ t('common.cores') }}</span>
            </div>
            <div class="res-item">
              <span class="res-label">{{ t('containers.memory') }}</span>
              <el-progress :percentage="memPercent" :stroke-width="10" color="#409eff" />
              <span class="res-text">{{ fmtMB(detailData.container.memory_used_mb) }} / {{ fmtMB(detailData.container.memory_mb) }}</span>
            </div>
            <div class="res-item">
              <span class="res-label">Swap</span>
              <el-progress :percentage="swapPercent" :stroke-width="10" color="#909399" />
              <span class="res-text">{{ fmtMB(detailData.container.swap_used_mb) }} / {{ fmtMB(detailData.container.swap_mb) }}</span>
            </div>
            <div class="res-item">
              <span class="res-label">{{ t('containers.disk') }}</span>
              <span class="res-value">{{ detailData.container.disk_gb || 0 }}GB</span>
            </div>
            <div class="res-item" v-if="detailData.container.uptime_seconds">
              <span class="res-label">{{ t('containers.runtime') }}</span>
              <span class="res-value">{{ fmtUptime(detailData.container.uptime_seconds) }}</span>
            </div>
          </div>

          <!-- Tab 切换 -->
          <el-tabs v-model="activeTab" class="dp-tabs">
            <!-- Tab: 基本信息 -->
            <el-tab-pane :label="t('containers.basicInfo')" name="basic">
              <div class="dp-kv-grid">
                <div class="dp-kv"><span class="dp-kv-label">VMID</span><span class="dp-kv-val mono">{{ detailData.container.vmid }}</span></div>
                <div class="dp-kv"><span class="dp-kv-label">{{ t('common.status') }}</span><span class="dp-kv-val"><el-tag :type="detailData.container.status === 'running' ? 'success' : 'danger'" size="small" disable-transitions>{{ detailData.container.status === 'running' ? t('containers.running') : t('containers.stopped') }}</el-tag></span></div>
                <div class="dp-kv"><span class="dp-kv-label">{{ t('common.name') }}</span><span class="dp-kv-val">{{ detailData.container.node_name }}</span></div>
                <div class="dp-kv"><span class="dp-kv-label">{{ t('containers.cluster') }}</span><span class="dp-kv-val">{{ detailData.container.cluster_name }}</span></div>
                <div class="dp-kv"><span class="dp-kv-label">{{ t('containers.type') }}</span><span class="dp-kv-val"><el-tag :type="detailData.container.has_template ? 'warning' : 'primary'" size="small" effect="plain">{{ detailData.container.has_template ? t('containers.typeTemplate') : t('containers.typeContainer') }}</el-tag></span></div>
                <div class="dp-kv" v-if="detailData.container.ip_address"><span class="dp-kv-label">{{ t('containers.ip') }}</span><span class="dp-kv-val mono">{{ detailData.container.ip_address }}</span></div>
                <div class="dp-kv" v-if="detailData.container.tags"><span class="dp-kv-label">{{ t('containers.tags') }}</span><span class="dp-kv-val">{{ detailData.container.tags }}</span></div>
                <div class="dp-kv"><span class="dp-kv-label">{{ t('common.scanTime') }}</span><span class="dp-kv-val mono">{{ fmtTime(detailData.container.scanned_at) }}</span></div>
              </div>
            </el-tab-pane>

            <!-- Tab: 配置 -->
            <el-tab-pane :label="t('containers.config')" name="config" v-if="detailData.config">
              <div class="dp-kv-grid">
                <div class="dp-kv"><span class="dp-kv-label">{{ t('containers.hostname') }}</span><span class="dp-kv-val">{{ detailData.config.hostname || '-' }}</span></div>
                <div class="dp-kv"><span class="dp-kv-label">{{ t('containers.osType') }}</span><span class="dp-kv-val">{{ detailData.config.os_type || '-' }}</span></div>
                <div class="dp-kv"><span class="dp-kv-label">{{ t('containers.cpuCores') }}</span><span class="dp-kv-val">{{ detailData.config.cpu_cores || '-' }}</span></div>
                <div class="dp-kv"><span class="dp-kv-label">{{ t('containers.memory') }}</span><span class="dp-kv-val">{{ detailData.config.memory_mb ? fmtMB(detailData.config.memory_mb) : '-' }}</span></div>
                <div class="dp-kv"><span class="dp-kv-label">Swap</span><span class="dp-kv-val">{{ detailData.config.swap_mb ? fmtMB(detailData.config.swap_mb) : '-' }}</span></div>
                <div class="dp-kv" v-if="detailData.config.startup_order"><span class="dp-kv-label">{{ t('vms.bootOrder') }}</span><span class="dp-kv-val mono">{{ detailData.config.startup_order }}</span></div>
                <div class="dp-kv"><span class="dp-kv-label">{{ t('containers.ha') }}</span><span class="dp-kv-val"><el-tag :type="detailData.config.ha_enabled ? 'success' : 'info'" size="small">{{ detailData.config.ha_enabled ? (detailData.config.ha_group || t('common.enabled')) : t('common.disabled') }}</el-tag></span></div>
                <div class="dp-kv" v-if="detailData.config.tags"><span class="dp-kv-label">{{ t('containers.tags') }}</span><span class="dp-kv-val">{{ detailData.config.tags }}</span></div>
                <div class="dp-kv" v-if="detailData.config.description"><span class="dp-kv-label">{{ t('clusters.description') }}</span><span class="dp-kv-val">{{ detailData.config.description }}</span></div>
              </div>
            </el-tab-pane>

            <!-- Tab: 存储 -->
            <el-tab-pane :label="t('containers.storage')" name="storage" v-if="detailData.config?.rootfs || detailData.config?.mount_points?.length">
              <div class="dp-devices">
                <div v-if="detailData.config?.rootfs" class="dp-device">
                  <div class="dp-device-head">
                    <span class="dp-device-tag">rootfs</span>
                    <span class="dp-device-name">{{ detailData.config.rootfs.storage || '-' }}</span>
                  </div>
                  <code class="dp-device-raw">{{ detailData.config.rootfs.raw }}</code>
                </div>
                <div v-for="mp in (detailData.config?.mount_points || [])" :key="mp.slot" class="dp-device">
                  <div class="dp-device-head">
                    <span class="dp-device-tag">mp{{ mp.slot }}</span>
                  </div>
                  <code class="dp-device-raw">{{ mp.raw }}</code>
                </div>
              </div>
            </el-tab-pane>

            <!-- Tab: 网络 -->
            <el-tab-pane :label="t('containers.network')" name="network" v-if="detailData.config?.net_devices?.length">
              <div class="dp-devices">
                <div v-for="(net, idx) in detailData.config?.net_devices || []" :key="idx" class="dp-device">
                  <div class="dp-device-head">
                    <span class="dp-device-tag">{{ net.name || net.iface || `net${idx}` }}</span>
                    <span class="dp-device-name">{{ net.type || 'veth' }}</span>
                    <span class="dp-device-sub">{{ t('containers.bridge') }} {{ net.bridge || '-' }}</span>
                  </div>
                  <div class="dp-device-meta">
                    <span v-if="net.address" class="mono">{{ net.address }}</span>
                    <span v-if="net.hwaddr" class="mono">{{ net.hwaddr }}</span>
                  </div>
                </div>
              </div>
            </el-tab-pane>
          </el-tabs>
        </template>

        <!-- 未选中状态 -->
        <div v-else-if="!loading && !detailLoading" class="dp-empty">
          <el-icon :size="48" color="var(--text-muted)"><Monitor /></el-icon>
          <p>{{ t('containers.emptyDesc') }}</p>
        </div>

        <!-- 详情加载中 -->
        <div v-if="detailLoading" class="dp-loading">
          <el-icon class="is-loading" :size="24"><Loading /></el-icon>
          <span>{{ t('common.loading') }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Loading, Monitor, Box, CircleCheckFilled, WarningFilled, Document } from '@element-plus/icons-vue'
import { getContainers, getContainerDetail } from '@/api/containers'
import type { ContainerInfo, ContainerDetail } from '@/api/containers'
import { getNodes } from '@/api/nodes'
import type { NodeInfo } from '@/api/nodes'
import { useClusterStore } from '@/stores/cluster'

const { t } = useI18n()
const clusterStore = useClusterStore()

const loading = ref(true)
const containers = ref<ContainerInfo[]>([])
const search = ref('')
const statusFilter = ref('')
const typeFilter = ref('')
const nodeFilter = ref<number | ''>('')
const nodes = ref<NodeInfo[]>([])
let timer: ReturnType<typeof setTimeout> | null = null

const selectedId = ref<number | null>(null)
const detailData = ref<ContainerDetail | null>(null)
const detailLoading = ref(false)
const activeTab = ref('basic')

/* ---- 计算属性 ---- */

const filteredContainers = computed(() => {
  let data = containers.value
  if (typeFilter.value === 'template') data = data.filter(c => c.has_template)
  else if (typeFilter.value === 'container') data = data.filter(c => !c.has_template)
  return data
})

const statCards = computed(() => [
  { key: 'total', label: t('containers.total') || '容器总数', value: filteredContainers.value.length, icon: Box, iconBg: 'rgba(64,158,255,0.12)' },
  { key: 'running', label: t('containers.running'), value: filteredContainers.value.filter(c => c.status === 'running').length, icon: CircleCheckFilled, iconBg: 'rgba(103,194,58,0.12)' },
  { key: 'stopped', label: t('containers.stopped'), value: filteredContainers.value.filter(c => c.status !== 'running').length, icon: WarningFilled, iconBg: 'rgba(245,108,108,0.12)' },
  { key: 'template', label: t('containers.typeTemplate'), value: filteredContainers.value.filter(c => c.has_template).length, icon: Document, iconBg: 'rgba(230,162,60,0.12)' },
])

const memPercent = computed(() => {
  const c = detailData.value?.container
  if (!c || !c.memory_mb) return 0
  return Math.round((c.memory_used_mb / c.memory_mb) * 100)
})

const swapPercent = computed(() => {
  const c = detailData.value?.container
  if (!c || !c.swap_mb) return 0
  return Math.round((c.swap_used_mb / c.swap_mb) * 100)
})

/* ---- 生命周期 ---- */

onMounted(async () => {
  if (!clusterStore.clusterList.length) await clusterStore.fetchClusters()
  loadData()
})

watch(() => clusterStore.currentClusterId, () => { loadData() })

/* ---- 数据加载 ---- */

async function loadData() {
  loading.value = true
  selectedId.value = null
  detailData.value = null
  try {
    const params: Record<string, any> = {}
    if (clusterStore.currentClusterId) params.cluster_id = clusterStore.currentClusterId
    if (statusFilter.value) params.status = statusFilter.value
    if (search.value) params.search = search.value
    if (nodeFilter.value !== '') params.node_id = nodeFilter.value
    const [nodeData, ctData] = await Promise.all([
      getNodes(clusterStore.currentClusterId ? { cluster_id: clusterStore.currentClusterId } : undefined),
      getContainers(params),
    ])
    nodes.value = nodeData
    containers.value = ctData
  } catch {} finally { loading.value = false }
}

function debounceLoad() {
  if (timer) clearTimeout(timer)
  timer = setTimeout(loadData, 300)
}

async function selectItem(item: ContainerInfo) {
  if (selectedId.value === item.id) return
  selectedId.value = item.id
  activeTab.value = 'basic'
  detailLoading.value = true
  detailData.value = null
  try {
    detailData.value = await getContainerDetail(item.id)
  } catch {
    detailData.value = null
  } finally {
    detailLoading.value = false
  }
}

/* ---- 工具函数 ---- */

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
.page-container { max-width: 1560px; margin: 0 auto; }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; }
.page-title { font-size: 24px; font-weight: 700; color: var(--text-heading); margin: 0; }
.page-desc { font-size: 14px; color: var(--text-muted); margin: 4px 0 0; }

/* ---- 统计卡片 ---- */
.stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 20px; }
.stat-card {
  display: flex; align-items: center; gap: 14px;
  padding: 16px 20px; border-radius: 12px;
  background: var(--bg-secondary); border: 1px solid var(--border-color);
}
.stat-icon { display: flex; align-items: center; justify-content: center; width: 44px; height: 44px; border-radius: 10px; flex-shrink: 0; color: var(--color-primary); }
.stat-info { display: flex; flex-direction: column; }
.stat-value { font-size: 22px; font-weight: 700; color: var(--text-heading); line-height: 1.2; }
.stat-label { font-size: 12px; color: var(--text-muted); margin-top: 2px; }

/* ---- 工具栏 ---- */
.toolbar { display: flex; align-items: center; gap: 10px; margin-bottom: 16px; flex-wrap: wrap; }
.toolbar-search { width: 260px; }

/* ---- Master-Detail 面板 ---- */
.master-detail {
  display: flex; gap: 0;
  border-radius: 14px; overflow: hidden;
  border: 1px solid var(--border-color);
  background: var(--bg-secondary);
  min-height: 560px;
}

/* ---- 左侧列表 ---- */
.master-panel {
  width: 320px; flex-shrink: 0;
  border-right: 1px solid var(--border-color);
  overflow-y: auto;
  background: var(--bg-secondary);
}
.master-list { display: flex; flex-direction: column; }
.master-item {
  padding: 14px 18px; cursor: pointer;
  border-bottom: 1px solid var(--border-color);
  transition: background .15s;
}
.master-item:hover { background: rgba(64, 158, 255, 0.06); }
.master-item.active { background: rgba(64, 158, 255, 0.12); border-left: 3px solid var(--color-primary); padding-left: 15px; }
.mi-top { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.mi-vmid { font-size: 11px; font-family: 'SF Mono', 'Menlo', monospace; background: var(--bg-primary); padding: 1px 5px; border-radius: 4px; color: var(--text-muted); flex-shrink: 0; }
.mi-name { font-size: 14px; font-weight: 600; color: var(--text-primary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; }
.mi-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.dot-run { background: #67c23a; box-shadow: 0 0 6px rgba(103, 194, 58, 0.5); }
.dot-stop { background: #909399; }
.mi-bottom { display: flex; align-items: center; gap: 8px; font-size: 12px; color: var(--text-muted); }
.mi-node { background: var(--bg-primary); padding: 1px 6px; border-radius: 4px; }
.mi-template { color: #e6a23c; font-weight: 500; }
.mi-ip { font-family: 'SF Mono', 'Menlo', monospace; font-size: 11px; }

/* ---- 右侧详情 ---- */
.detail-panel {
  flex: 1; min-width: 0;
  background: var(--bg-primary);
  display: flex; flex-direction: column;
  overflow-y: auto;
}

/* 详情头部 */
.dp-header {
  padding: 20px 28px 16px;
  border-bottom: 1px solid var(--border-color);
}
.dp-header-info {}
.dp-title-row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.dp-vmid { font-size: 12px; font-family: 'SF Mono', 'Menlo', monospace; background: var(--bg-secondary); padding: 2px 8px; border-radius: 6px; color: var(--text-muted); }
.dp-name { font-size: 18px; font-weight: 700; color: var(--text-heading); margin: 0; }
.dp-meta { display: flex; align-items: center; gap: 12px; margin-top: 6px; font-size: 13px; color: var(--text-muted); }
.dp-ip { font-family: 'SF Mono', 'Menlo', monospace; font-size: 12px; color: var(--text-secondary); }

/* 资源概览 */
.dp-resources {
  display: flex; align-items: center; gap: 28px;
  padding: 16px 28px;
  border-bottom: 1px solid var(--border-color);
  flex-wrap: wrap;
}
.res-item { display: flex; flex-direction: column; gap: 4px; min-width: 140px; }
.res-label { font-size: 11px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }
.res-text { font-size: 12px; color: var(--text-muted); margin-top: 2px; }
.res-value { font-size: 14px; font-weight: 600; color: var(--text-primary); margin-top: 2px; }
.res-item :deep(.el-progress) { width: 140px; }

/* Tab */
.dp-tabs { flex: 1; overflow-y: auto; }
.dp-tabs :deep(.el-tabs__header) { margin: 0; padding: 0 28px; background: var(--bg-secondary); }
.dp-tabs :deep(.el-tabs__nav-wrap::after) { display: none; }
.dp-tabs :deep(.el-tabs__content) { padding: 20px 28px; }
.dp-tabs :deep(.el-tab-pane) { min-height: 200px; }

/* KV 网格 */
.dp-kv-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0 24px; }
.dp-kv { display: flex; align-items: center; padding: 8px 0; border-bottom: 1px dashed var(--border-color); }
.dp-kv-label { font-size: 13px; color: var(--text-muted); min-width: 76px; flex-shrink: 0; }
.dp-kv-val { font-size: 13px; color: var(--text-primary); word-break: break-all; }
.mono { font-family: 'SF Mono', 'Menlo', monospace; font-size: 12px; }

/* 设备列表 */
.dp-devices { display: flex; flex-direction: column; gap: 8px; }
.dp-device {
  padding: 12px 16px; border-radius: 10px;
  background: var(--bg-secondary); border: 1px solid var(--border-color);
}
.dp-device-head { display: flex; align-items: center; gap: 10px; margin-bottom: 4px; }
.dp-device-tag {
  font-size: 12px; font-weight: 600; color: var(--color-primary);
  background: rgba(64, 158, 255, 0.1); padding: 2px 8px; border-radius: 5px; white-space: nowrap;
}
.dp-device-name { font-size: 13px; font-weight: 500; color: var(--text-primary); }
.dp-device-sub { font-size: 12px; color: var(--text-muted); }
.dp-device-raw { font-size: 12px; color: var(--text-muted); display: block; word-break: break-all; margin-top: 4px; font-family: 'SF Mono', 'Menlo', monospace; background: transparent; padding: 0; }
.dp-device-meta { display: flex; gap: 16px; font-size: 12px; color: var(--text-muted); margin-top: 4px; }

/* 空状态 & 加载 */
.dp-empty { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 12px; color: var(--text-muted); font-size: 14px; min-height: 400px; }
.dp-loading { display: flex; align-items: center; justify-content: center; gap: 10px; padding: 60px; color: var(--text-secondary); font-size: 14px; }

/* ---- 响应式 ---- */
@media (max-width: 1200px) {
  .stats-row { grid-template-columns: repeat(2, 1fr); }
  .master-panel { width: 260px; }
  .dp-kv-grid { grid-template-columns: 1fr; }
}
@media (max-width: 768px) {
  .stats-row { grid-template-columns: repeat(2, 1fr); }
  .master-detail { flex-direction: column; min-height: auto; }
  .master-panel { width: 100%; max-height: 320px; border-right: none; border-bottom: 1px solid var(--border-color); }
  .dp-resources { gap: 16px; }
}
</style>
