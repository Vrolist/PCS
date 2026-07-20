<template>
  <div class="page-container">
    <!-- 标题 + 统计 + 筛选 -->
    <div class="page-top">
      <div class="page-top-left">
        <h2 class="page-title">{{ t('nodes.title') }}</h2>
        <div class="mini-stats" v-if="!loading && nodes.length">
          <span class="ms-item"><i class="ms-dot ms-dot-total" />{{ nodes.length }}</span>
          <span class="ms-item"><i class="ms-dot ms-dot-run" />{{ onlineCount }}</span>
          <span class="ms-item"><i class="ms-dot ms-dot-stop" />{{ offlineCount }}</span>
        </div>
      </div>
      <div class="page-top-right">
        <el-input v-model="search" :placeholder="t('nodes.searchPlaceholder')" clearable prefix-icon="Search" size="small" class="top-search" />
      </div>
    </div>

    <!-- Master-Detail 双面板 -->
    <div class="master-detail" v-loading="loading">
      <!-- 左侧列表 -->
      <div class="master-panel">
        <div class="master-list" v-if="filteredNodes.length">
          <div
            v-for="item in filteredNodes"
            :key="item.id"
            class="master-item"
            :class="{ active: selectedId === item.id }"
            @click="selectItem(item)"
          >
            <div class="mi-top">
              <span class="mi-name">{{ item.node_name }}</span>
              <span class="mi-dot" :class="item.status === 'online' ? 'dot-run' : 'dot-stop'" />
            </div>
            <div class="mi-bottom">
              <span class="mi-health" :class="healthClass(healthScore(item))">{{ healthScore(item) }}</span>
              <span v-if="item.is_ceph_node" class="mi-tag mi-ceph">Ceph</span>
              <span v-if="item.is_ha_node" class="mi-tag mi-ha">HA</span>
              <span class="mi-usage">{{ Math.round(item.cpu_load || 0) }}% · {{ fmtMB(item.memory_used_mb) }}</span>
            </div>
          </div>
        </div>
        <el-empty v-else-if="!loading" :description="t('nodes.emptyDesc')" :image-size="80" />
      </div>

      <!-- 右侧详情 -->
      <div class="detail-panel">
        <template v-if="detailData">
          <!-- 详情头部 -->
          <div class="dp-header">
            <div class="dp-title-row">
              <h3 class="dp-name">{{ detailData.node.node_name }}</h3>
              <el-tag :type="detailData.node.status === 'online' ? 'success' : 'danger'" size="small" disable-transitions>
                {{ detailData.node.status === 'online' ? t('common.online') : t('common.offline') }}
              </el-tag>
              <el-tag v-if="detailData.node.is_ceph_node" type="success" size="small" effect="plain">Ceph</el-tag>
              <el-tag v-if="detailData.node.is_ha_node" type="warning" size="small" effect="plain">HA</el-tag>
              <span class="dp-health" :class="healthClass(healthScore(detailData.node))">{{ t('nodes.healthScore') }} {{ healthScore(detailData.node) }}</span>
            </div>
            <div class="dp-meta">
              <span class="dp-meta-item">{{ detailData.node.cluster_name }}</span>
              <span class="dp-meta-item dp-ip">{{ detailData.node.ip_address || '-' }}</span>
              <span class="dp-meta-item">{{ detailData.node.pve_version?.split('/')[0] || '-' }} {{ detailData.node.pve_version?.split('/')[1] || '' }}</span>
            </div>
          </div>

          <!-- 资源概览卡片 -->
          <div class="dp-resources-card">
            <div class="res-item">
              <div class="res-header">
                <span class="res-label">CPU</span>
                <span class="res-pct" :style="{ color: cpuColor(Math.round(detailData.node.cpu_load || 0)) }">{{ Math.round(detailData.node.cpu_load || 0) }}%</span>
              </div>
              <el-progress :percentage="Math.round(detailData.node.cpu_load || 0)" :stroke-width="8" :color="cpuColor(Math.round(detailData.node.cpu_load || 0))" :show-text="false" />
              <span class="res-sub">{{ detailData.node.cpu_cores }}{{ t('common.cores') }} × {{ detailData.node.cpu_sockets || 1 }}</span>
            </div>
            <div class="res-item">
              <div class="res-header">
                <span class="res-label">{{ t('nodes.memoryTotal') }}</span>
                <span class="res-pct">{{ Math.round(detailData.node.memory_usage_pct || 0) }}%</span>
              </div>
              <el-progress :percentage="Math.round(detailData.node.memory_usage_pct || 0)" :stroke-width="8" color="#409eff" :show-text="false" />
              <span class="res-sub">{{ fmtMB(detailData.node.memory_used_mb) }} / {{ fmtMB(detailData.node.memory_total_mb) }}</span>
            </div>
            <div class="res-item">
              <div class="res-header">
                <span class="res-label">{{ t('nodes.rootFs') }}</span>
                <span class="res-pct">{{ diskPercent }}%</span>
              </div>
              <el-progress :percentage="diskPercent" :stroke-width="8" color="#e6a23c" :show-text="false" />
              <span class="res-sub">{{ detailData.node.rootfs_used_gb || 0 }}GB / {{ detailData.node.rootfs_total_gb || 0 }}GB</span>
            </div>
            <div class="res-item res-item-plain">
              <span class="res-label">{{ t('nodes.ioDelay') }}</span>
              <span class="res-value res-value-sm" :class="{ 'text-warn': (detailData.node.disk_io_delay_ms || 0) > 50 }">{{ (detailData.node.disk_io_delay_ms || 0).toFixed(1) }}ms</span>
            </div>
            <div class="res-item res-item-plain">
              <span class="res-label">{{ t('nodes.runtime') }}</span>
              <span class="res-value res-value-sm">{{ fmtUptime(detailData.node.uptime_seconds) }}</span>
            </div>
            <div class="res-item res-item-plain" v-if="detailData.vms?.length || detailData.containers?.length">
              <span class="res-label">{{ t('nodes.vmTab') }} / {{ t('nodes.containerTab') }}</span>
              <span class="res-value res-value-sm">{{ detailData.vms?.length || 0 }} / {{ detailData.containers?.length || 0 }}</span>
            </div>
          </div>

          <!-- Tab 切换 -->
          <el-tabs v-model="activeTab" class="dp-tabs">
            <!-- Tab: 基本信息 -->
            <el-tab-pane :label="t('nodes.basicInfo')" name="basic">
              <div class="dp-section-card">
                <div class="dp-kv-grid">
                  <div class="dp-kv"><span class="dp-kv-label">{{ t('dashboard.nodeName') }}</span><span class="dp-kv-val">{{ detailData.node.node_name }}</span></div>
                  <div class="dp-kv"><span class="dp-kv-label">{{ t('vms.cluster') }}</span><span class="dp-kv-val">{{ detailData.node.cluster_name }}</span></div>
                  <div class="dp-kv"><span class="dp-kv-label">{{ t('common.ip') }}</span><span class="dp-kv-val mono">{{ detailData.node.ip_address || '-' }}</span></div>
                  <div class="dp-kv" v-if="detailData.node.mac_address"><span class="dp-kv-label">MAC</span><span class="dp-kv-val mono">{{ detailData.node.mac_address }}</span></div>
                  <div class="dp-kv"><span class="dp-kv-label">{{ t('clusters.pveVersion') }}</span><span class="dp-kv-val mono">{{ detailData.node.pve_version || '-' }}</span></div>
                  <div class="dp-kv"><span class="dp-kv-label">{{ t('nodes.kernelVersion') }}</span><span class="dp-kv-val mono">{{ detailData.node.kernel_version || '-' }}</span></div>
                  <div class="dp-kv"><span class="dp-kv-label">{{ t('nodes.cpuModel') }}</span><span class="dp-kv-val">{{ detailData.node.cpu_model || '-' }}</span></div>
                  <div class="dp-kv"><span class="dp-kv-label">{{ t('nodes.cpuVendor') }}</span><span class="dp-kv-val">
                    <el-tag v-if="detailData.node.cpu_vendor" :type="detailData.node.cpu_vendor.includes('Intel') ? 'primary' : 'danger'" size="small" effect="plain">{{ detailData.node.cpu_vendor }}</el-tag>
                    <span v-else>-</span>
                  </span></div>
                  <div class="dp-kv" v-if="detailData.node.cpu_family"><span class="dp-kv-label">{{ t('nodes.cpuFamily') }}</span><span class="dp-kv-val">{{ detailData.node.cpu_family }}</span></div>
                  <div class="dp-kv"><span class="dp-kv-label">{{ t('nodes.cpuCores') }}</span><span class="dp-kv-val">{{ detailData.node.cpu_cores }}{{ t('common.cores') }} × {{ detailData.node.cpu_sockets || 1 }}{{ t('nodes.cpuSockets') }}</span></div>
                  <div class="dp-kv" v-if="detailData.node.cpu_mhz"><span class="dp-kv-label">{{ t('nodes.cpuMhz') }}</span><span class="dp-kv-val">{{ detailData.node.cpu_mhz }} MHz</span></div>
                  <div class="dp-kv"><span class="dp-kv-label">{{ t('nodes.cpuHvm') }}</span><span class="dp-kv-val">
                    <el-tag :type="detailData.node.cpu_hvm ? 'success' : 'info'" size="small" effect="plain">{{ detailData.node.cpu_hvm ? 'VT-x / AMD-V' : '-' }}</el-tag>
                  </span></div>
                  <div class="dp-kv" v-if="detailData.node.cpu_flags"><span class="dp-kv-label">{{ t('nodes.cpuFlags') }}</span><span class="dp-kv-val dp-flags">{{ detailData.node.cpu_flags }}</span></div>
                  <div class="dp-kv"><span class="dp-kv-label">{{ t('nodes.swap') }}</span><span class="dp-kv-val">{{ fmtMB(detailData.node.swap_used_mb) }} / {{ fmtMB(detailData.node.swap_total_mb) }}</span></div>
                  <div class="dp-kv"><span class="dp-kv-label">{{ t('nodes.memoryAvail') }}</span><span class="dp-kv-val">{{ fmtMB(detailData.node.memory_free_mb) }}</span></div>
                  <div class="dp-kv"><span class="dp-kv-label">{{ t('nodes.rootFsAvail') }}</span><span class="dp-kv-val">{{ detailData.node.rootfs_avail_gb || 0 }}GB</span></div>
                  <div class="dp-kv"><span class="dp-kv-label">{{ t('nodes.ioDelay') }}</span><span class="dp-kv-val" :class="{ 'text-warn': (detailData.node.disk_io_delay_ms || 0) > 50 }">{{ (detailData.node.disk_io_delay_ms || 0).toFixed(1) }}ms</span></div>
                  <div class="dp-kv"><span class="dp-kv-label">{{ t('nodes.role') }}</span><span class="dp-kv-val">
                    <el-tag v-if="detailData.node.is_ceph_node" type="success" size="small" effect="plain">Ceph</el-tag>
                    <el-tag v-if="detailData.node.is_ha_node" type="warning" size="small" effect="plain" style="margin-left:4px">HA</el-tag>
                    <span v-if="!detailData.node.is_ceph_node && !detailData.node.is_ha_node">-</span>
                  </span></div>
                  <div class="dp-kv"><span class="dp-kv-label">{{ t('common.scanTime') }}</span><span class="dp-kv-val mono">{{ fmtTime(detailData.node.scanned_at) }}</span></div>
                </div>
              </div>
            </el-tab-pane>

            <!-- Tab: 存储 -->
            <el-tab-pane :label="`${t('nodes.storage')}${detailData.storages?.length ? ' (' + detailData.storages.length + ')' : ''}`" name="storage" v-if="detailData.storages?.length">
              <div class="dp-devices">
                <div v-for="s in detailData.storages" :key="s.name" class="dp-device">
                  <div class="dp-device-head">
                    <span class="dp-device-tag">{{ s.name }}</span>
                    <span class="dp-device-name">{{ s.type }}</span>
                    <el-tag :type="s.status === 'available' ? 'success' : 'danger'" size="small" effect="plain">{{ s.status === 'available' ? t('nodes.storageAvailable') : t('nodes.storageUnavailable') }}</el-tag>
                    <el-tag v-if="s.shared" type="info" size="small" effect="plain">{{ t('nodes.shared') }}</el-tag>
                  </div>
                  <div class="dp-device-meta">
                    <span v-if="s.total_gb">{{ s.used_gb || 0 }}GB / {{ s.total_gb }}GB</span>
                    <span v-if="s.content_types" class="mono">{{ s.content_types }}</span>
                  </div>
                </div>
              </div>
            </el-tab-pane>

            <!-- Tab: 网络 -->
            <el-tab-pane :label="`${t('nodes.networkInterfaces')}${detailData.networks?.length ? ' (' + detailData.networks.length + ')' : ''}`" name="network" v-if="detailData.networks?.length">
              <div class="dp-devices">
                <div v-for="net in detailData.networks" :key="net.name" class="dp-device">
                  <div class="dp-device-head">
                    <span class="dp-device-tag">{{ net.name }}</span>
                    <span class="dp-device-name">{{ net.type }}</span>
                    <el-tag :type="net.active ? 'success' : 'info'" size="small" effect="plain">{{ net.active ? t('common.enabled') : t('common.disabled') }}</el-tag>
                  </div>
                  <div class="dp-device-meta">
                    <span v-if="net.address" class="mono">{{ net.address }}</span>
                    <span v-if="net.gateway">GW {{ net.gateway }}</span>
                    <span v-if="net.speed_mbps">{{ net.speed_mbps }}Mbps</span>
                  </div>
                </div>
              </div>
            </el-tab-pane>
          </el-tabs>
        </template>

        <!-- 未选中状态 -->
        <div v-else-if="!loading && !detailLoading" class="dp-empty">
          <el-icon :size="48" color="var(--text-muted)"><Monitor /></el-icon>
          <p>{{ t('nodes.emptyDesc') }}</p>
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
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { Loading, Monitor } from '@element-plus/icons-vue'

const { t } = useI18n()
import { getNodes, getNodeDetail } from '@/api/nodes'
import type { NodeInfo, NodeDetail } from '@/api/nodes'
import { useClusterStore } from '@/stores/cluster'

const clusterStore = useClusterStore()

const loading = ref(true)
const nodes = ref<NodeInfo[]>([])
const search = ref('')

const selectedId = ref<number | null>(null)
const detailData = ref<NodeDetail | null>(null)
const detailLoading = ref(false)
const activeTab = ref('basic')

/* ---- 计算属性 ---- */

const filteredNodes = computed(() => {
  if (!search.value) return nodes.value
  const q = search.value.toLowerCase()
  return nodes.value.filter(n =>
    n.node_name.toLowerCase().includes(q) ||
    n.ip_address?.toLowerCase().includes(q) ||
    n.cluster_name?.toLowerCase().includes(q)
  )
})

const onlineCount = computed(() => nodes.value.filter(n => n.status === 'online').length)
const offlineCount = computed(() => nodes.value.filter(n => n.status !== 'online').length)

const diskPercent = computed(() => {
  const n = detailData.value?.node
  if (!n || !n.rootfs_total_gb) return 0
  return Math.round((n.rootfs_used_gb / n.rootfs_total_gb) * 100)
})

/* ---- 健康评分 ---- */

function healthScore(node: NodeInfo): number {
  if (node.status !== 'online') return 0
  let score = 100
  const cpu = node.cpu_load || 0
  const mem = node.memory_usage_pct || 0
  const io = node.disk_io_delay_ms || 0
  // CPU 扣分: >80% 开始扣, 每超 1% 扣 2 分
  if (cpu > 80) score -= Math.min((cpu - 80) * 2, 30)
  // 内存扣分: >85% 开始扣
  if (mem > 85) score -= Math.min((mem - 85) * 2, 30)
  // 磁盘使用率扣分: >90% 开始扣
  const diskPct = node.rootfs_total_gb ? (node.rootfs_used_gb / node.rootfs_total_gb) * 100 : 0
  if (diskPct > 90) score -= Math.min((diskPct - 90) * 3, 20)
  // IO 延迟扣分: >50ms 开始扣
  if (io > 50) score -= Math.min((io - 50) * 0.5, 20)
  return Math.max(0, Math.round(score))
}

function healthClass(score: number): string {
  if (score >= 80) return 'health-good'
  if (score >= 50) return 'health-warn'
  return 'health-bad'
}

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
    nodes.value = await getNodes(params)
    await nextTick()
    if (filteredNodes.value.length) {
      selectItem(filteredNodes.value[0])
    }
  } catch {} finally { loading.value = false }
}

async function selectItem(item: NodeInfo) {
  if (selectedId.value === item.id) return
  selectedId.value = item.id
  activeTab.value = 'basic'
  detailLoading.value = true
  detailData.value = null
  try {
    detailData.value = await getNodeDetail(item.id)
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
.page-container {
  display: flex; flex-direction: column;
  height: calc(100vh - 56px - 48px);
  min-height: 0 !important;
  padding: 0; max-width: none;
  overflow: hidden;
}

/* ========== 顶部一行 ========== */
.page-top {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 20px; flex-shrink: 0;
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-secondary);
  gap: 12px; flex-wrap: wrap;
}
.page-top-left { display: flex; align-items: center; gap: 20px; }
.page-title { font-size: 18px; font-weight: 700; color: var(--text-heading); margin: 0; white-space: nowrap; }
.mini-stats { display: flex; align-items: center; gap: 14px; }
.ms-item { display: flex; align-items: center; gap: 5px; font-size: 13px; font-weight: 600; color: var(--text-primary); }
.ms-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.ms-dot-total { background: var(--color-primary); }
.ms-dot-run { background: #67c23a; box-shadow: 0 0 4px rgba(103,194,58,0.5); }
.ms-dot-stop { background: #909399; }
.page-top-right { display: flex; align-items: center; gap: 8px; }
.top-search { width: 200px; }

/* ========== Master-Detail ========== */
.master-detail {
  display: flex; flex: 1; min-height: 0;
  background: var(--bg-primary);
  overflow: hidden;
}

/* ========== 左侧列表 ========== */
.master-panel {
  width: 300px; flex-shrink: 0;
  border-right: 1px solid var(--border-color);
  overflow-y: scroll;
  scrollbar-width: none;
  -ms-overflow-style: none;
  background: var(--bg-secondary);
}
.master-panel::-webkit-scrollbar { display: none; }
.master-list { display: flex; flex-direction: column; }
.master-item {
  padding: 12px 16px; cursor: pointer;
  border-bottom: 1px solid var(--border-color);
  transition: all .2s;
  border-left: 3px solid transparent;
}
.master-item:hover { background: rgba(64, 158, 255, 0.06); }
.master-item.active {
  background: var(--bg-primary);
  border-left-color: var(--color-primary);
  box-shadow: inset 0 0 20px rgba(64, 158, 255, 0.04);
}
.mi-top { display: flex; align-items: center; gap: 6px; margin-bottom: 4px; }
.mi-name { font-size: 13px; font-weight: 600; color: var(--text-primary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; }
.mi-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.dot-run { background: #67c23a; box-shadow: 0 0 5px rgba(103, 194, 58, 0.5); }
.dot-stop { background: #909399; }
.mi-bottom { display: flex; align-items: center; gap: 6px; font-size: 11px; color: var(--text-muted); }
.mi-health {
  font-size: 11px; font-weight: 700; padding: 1px 6px; border-radius: 4px;
}
.health-good { color: #67c23a; background: rgba(103,194,58,0.1); }
.health-warn { color: #e6a23c; background: rgba(230,162,60,0.1); }
.health-bad { color: #f56c6c; background: rgba(245,108,108,0.1); }
.mi-tag {
  font-size: 10px; font-weight: 600; padding: 1px 5px; border-radius: 3px; white-space: nowrap;
}
.mi-ceph { color: #67c23a; background: rgba(103,194,58,0.1); }
.mi-ha { color: #e6a23c; background: rgba(230,162,60,0.1); }
.mi-usage { font-family: 'SF Mono', 'Menlo', monospace; font-size: 10px; }

/* ========== 右侧详情 ========== */
.detail-panel {
  flex: 1; min-width: 0; min-height: 0;
  background: var(--bg-primary);
  display: flex; flex-direction: column;
  overflow: hidden;
  padding: 20px 24px;
  gap: 16px;
}

/* 详情头部卡片 */
.dp-header {
  padding: 18px 22px;
  background: var(--bg-secondary);
  border-radius: 12px;
  border: 1px solid var(--border-color);
  flex-shrink: 0;
}
.dp-title-row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.dp-name { font-size: 18px; font-weight: 700; color: var(--text-heading); margin: 0; }
.dp-health {
  font-size: 14px; font-weight: 700; padding: 2px 12px; border-radius: 8px; margin-left: auto;
}
.dp-meta { display: flex; align-items: center; gap: 10px; margin-top: 8px; }
.dp-meta-item { font-size: 13px; color: var(--text-muted); background: var(--bg-primary); padding: 2px 10px; border-radius: 6px; }
.dp-ip { font-family: 'SF Mono', 'Menlo', monospace; font-size: 12px; color: var(--color-primary); background: rgba(64,158,255,0.08); }

/* 资源概览卡片 */
.dp-resources-card {
  display: flex; align-items: stretch; gap: 12px;
  padding: 16px 20px;
  background: var(--bg-secondary);
  border-radius: 12px;
  border: 1px solid var(--border-color);
  flex-shrink: 0;
}
.res-item { flex: 1; display: flex; flex-direction: column; gap: 4px; padding: 8px 12px; background: var(--bg-primary); border-radius: 8px; min-width: 0; }
.res-item-plain { justify-content: center; }
.res-header { display: flex; align-items: center; justify-content: space-between; }
.res-label { font-size: 11px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }
.res-pct { font-size: 16px; font-weight: 700; color: var(--text-heading); line-height: 1; }
.res-sub { font-size: 11px; color: var(--text-muted); margin-top: 2px; }
.res-value { font-size: 18px; font-weight: 700; color: var(--text-heading); }
.res-value-sm { font-size: 14px; }
.res-item :deep(.el-progress) { width: 100%; }

/* Tab — 整体卡片化 */
.dp-tabs {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: var(--bg-secondary);
  border-radius: 12px;
  border: 1px solid var(--border-color);
  overflow: hidden;
}
.dp-tabs :deep(.el-tabs__header) { margin: 0; padding: 0 8px; background: transparent; border-bottom: 1px solid var(--border-color); flex-shrink: 0; }
.dp-tabs :deep(.el-tabs__nav-wrap::after) { display: none; }
.dp-tabs :deep(.el-tabs__content) { padding: 0; flex: 1; min-height: 0; overflow-y: auto; }
.dp-tabs :deep(.el-tab-pane) { min-height: 100%; }

/* 信息区块 */
.dp-section-card { padding: 16px 22px; }

/* KV 网格 */
.dp-kv-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0 20px; }
.dp-kv { display: flex; align-items: center; padding: 8px 0; border-bottom: 1px dashed var(--border-color); }
.dp-kv:last-child { border-bottom: none; }
.dp-kv-label { font-size: 13px; color: var(--text-muted); min-width: 80px; flex-shrink: 0; }
.dp-kv-val { font-size: 13px; color: var(--text-primary); word-break: break-all; }
.mono { font-family: 'SF Mono', 'Menlo', monospace; font-size: 12px; }
.text-warn { color: #e6a23c; font-weight: 600; }
.dp-flags { font-size: 11px; line-height: 1.5; max-height: 80px; overflow-y: auto; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; }

/* 设备列表 */
.dp-devices { display: flex; flex-direction: column; gap: 8px; padding: 16px 22px; }
.dp-device {
  padding: 12px 16px; border-radius: 10px;
  background: var(--bg-secondary); border: 1px solid var(--border-color);
  transition: border-color .2s;
}
.dp-device:hover { border-color: rgba(64, 158, 255, 0.3); }
.dp-device-head { display: flex; align-items: center; gap: 10px; margin-bottom: 6px; }
.dp-device-tag {
  font-size: 12px; font-weight: 600; color: var(--color-primary);
  background: rgba(64, 158, 255, 0.1); padding: 2px 10px; border-radius: 6px; white-space: nowrap;
}
.dp-device-name { font-size: 13px; font-weight: 500; color: var(--text-primary); }
.dp-device-sub { font-size: 12px; color: var(--text-muted); }
.dp-device-meta { display: flex; gap: 16px; font-size: 12px; color: var(--text-muted); }

/* 空状态 & 加载 */
.dp-empty { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 12px; color: var(--text-muted); font-size: 14px; }
.dp-loading { display: flex; align-items: center; justify-content: center; gap: 10px; padding: 60px; color: var(--text-secondary); font-size: 14px; }

/* ========== 滚动条美化 ========== */
.dp-tabs :deep(.el-tabs__content)::-webkit-scrollbar { width: 6px; }
.dp-tabs :deep(.el-tabs__content)::-webkit-scrollbar-thumb { background: var(--border-color); border-radius: 3px; }
.dp-tabs :deep(.el-tabs__content)::-webkit-scrollbar-thumb:hover { background: var(--text-muted); }
.dp-tabs :deep(.el-tabs__content)::-webkit-scrollbar-track { background: transparent; }

/* ========== 响应式 ========== */
@media (max-width: 1200px) {
  .master-panel { width: 240px; }
  .dp-kv-grid { grid-template-columns: 1fr; }
  .dp-resources-card { flex-wrap: wrap; }
}
@media (max-width: 768px) {
  .page-top { flex-direction: column; align-items: flex-start; }
  .master-detail { flex-direction: column; }
  .master-panel { width: 100%; max-height: 260px; border-right: none; border-bottom: 1px solid var(--border-color); flex-shrink: 0; }
  .dp-resources-card { flex-direction: column; }
}
</style>
