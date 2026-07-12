<template>
  <div class="page-container">
    <!-- 标题 + 统计 + 筛选 -->
    <div class="page-top">
      <div class="page-top-left">
        <h2 class="page-title">{{ t('networks.title') }}</h2>
        <div class="mini-stats" v-if="!loading && networkList.length">
          <span class="ms-item"><i class="ms-dot ms-dot-total" />{{ networkList.length }}</span>
          <span class="ms-item"><i class="ms-dot ms-dot-run" />{{ upCount }}</span>
          <span class="ms-item"><i class="ms-dot ms-dot-stop" />{{ downCount }}</span>
        </div>
      </div>
      <div class="page-top-right">
        <el-input v-model="search" :placeholder="t('networks.searchPlaceholder')" clearable prefix-icon="Search" size="small" class="top-search" />
        <el-select v-model="filterNode" :placeholder="t('networks.allNodes')" clearable size="small" style="width:130px">
          <el-option v-for="n in nodeOptions" :key="n" :label="n" :value="n" />
        </el-select>
        <el-select v-model="filterType" :placeholder="t('networks.allTypes')" clearable size="small" style="width:120px">
          <el-option v-for="tp in typeOptions" :key="tp" :label="tp" :value="tp" />
        </el-select>
      </div>
    </div>

    <!-- Master-Detail 双面板 -->
    <div class="master-detail" v-loading="loading">
      <!-- 左侧列表 -->
      <div class="master-panel">
        <div class="master-list" v-if="filteredList.length">
          <div
            v-for="item in filteredList"
            :key="item.id"
            class="master-item"
            :class="{ active: selectedId === item.id }"
            @click="selectItem(item)"
          >
            <div class="mi-top">
              <span class="mi-name">{{ item.name }}</span>
              <span class="mi-dot" :class="item.status === 'up' ? 'dot-run' : 'dot-stop'" />
            </div>
            <div class="mi-mid">
              <span class="mi-type">{{ item.type }}</span>
              <span class="mi-node">{{ item.node_name }}</span>
            </div>
            <div class="mi-bottom">
              <span v-if="item.address" class="mi-ip">{{ item.address }}</span>
              <span v-if="item.gateway" class="mi-gw">GW {{ item.gateway }}</span>
            </div>
          </div>
        </div>
        <el-empty v-else-if="!loading" :description="t('networks.emptyDesc')" :image-size="80" />
      </div>

      <!-- 右侧详情 -->
      <div class="detail-panel">
        <template v-if="selected">
          <!-- 详情头部 -->
          <div class="dp-header">
            <div class="dp-title-row">
              <h3 class="dp-name">{{ selected.name }}</h3>
              <el-tag size="small" effect="plain">{{ selected.type }}</el-tag>
              <el-tag :type="selected.status === 'up' ? 'success' : 'danger'" size="small" disable-transitions>
                {{ selected.status === 'up' ? t('networks.statusUp') : t('networks.statusDown') }}
              </el-tag>
            </div>
            <div class="dp-meta">
              <span class="dp-meta-item">{{ selected.node_name }}</span>
              <span class="dp-meta-item dp-ip" v-if="selected.address">{{ selected.address }}</span>
              <span class="dp-meta-item" v-if="selected.gateway">GW {{ selected.gateway }}</span>
            </div>
          </div>

          <!-- Tab 切换 -->
          <el-tabs v-model="activeTab" class="dp-tabs">
            <el-tab-pane :label="t('networks.basicInfo')" name="basic">
              <div class="dp-section-card">
                <div class="dp-kv-grid">
                  <div class="dp-kv"><span class="dp-kv-label">{{ t('networks.ifaceName') }}</span><span class="dp-kv-val">{{ selected.name }}</span></div>
                  <div class="dp-kv"><span class="dp-kv-label">{{ t('networks.type') }}</span><span class="dp-kv-val"><el-tag size="small" effect="plain">{{ selected.type }}</el-tag></span></div>
                  <div class="dp-kv"><span class="dp-kv-label">{{ t('networks.status') }}</span><span class="dp-kv-val"><el-tag :type="selected.status === 'up' ? 'success' : 'danger'" size="small" disable-transitions>{{ selected.status === 'up' ? t('networks.statusUp') : t('networks.statusDown') }}</el-tag></span></div>
                  <div class="dp-kv"><span class="dp-kv-label">{{ t('networks.node') }}</span><span class="dp-kv-val">{{ selected.node_name }}</span></div>
                  <div class="dp-kv"><span class="dp-kv-label">{{ t('networks.ipAddr') }}</span><span class="dp-kv-val mono">{{ selected.address || '-' }}</span></div>
                  <div class="dp-kv" v-if="selected.gateway"><span class="dp-kv-label">{{ t('networks.gateway') }}</span><span class="dp-kv-val mono">{{ selected.gateway }}</span></div>
                  <div class="dp-kv" v-if="selected.mac_address"><span class="dp-kv-label">MAC</span><span class="dp-kv-val mono">{{ selected.mac_address }}</span></div>
                  <div class="dp-kv" v-if="selected.mtu"><span class="dp-kv-label">MTU</span><span class="dp-kv-val">{{ selected.mtu }}</span></div>
                  <div class="dp-kv" v-if="selected.vlan_id"><span class="dp-kv-label">VLAN</span><span class="dp-kv-val">{{ selected.vlan_id }}</span></div>
                  <div class="dp-kv" v-if="selected.speed"><span class="dp-kv-label">{{ t('networks.speed') }}</span><span class="dp-kv-val">{{ selected.speed }} Mbps</span></div>
                  <div class="dp-kv" v-if="selected.bridge_ports"><span class="dp-kv-label">{{ t('networks.bridgePorts') }}</span><span class="dp-kv-val mono">{{ selected.bridge_ports }}</span></div>
                  <div class="dp-kv" v-if="selected.bond_mode"><span class="dp-kv-label">{{ t('networks.bondMode') }}</span><span class="dp-kv-val">{{ selected.bond_mode }}</span></div>
                  <div class="dp-kv" v-if="selected.bond_slaves"><span class="dp-kv-label">{{ t('networks.bondSlaves') }}</span><span class="dp-kv-val mono">{{ selected.bond_slaves }}</span></div>
                  <div class="dp-kv"><span class="dp-kv-label">{{ t('common.scanTime') }}</span><span class="dp-kv-val mono">{{ fmtTime(selected.scanned_at) }}</span></div>
                </div>
              </div>
            </el-tab-pane>
          </el-tabs>
        </template>

        <!-- 未选中状态 -->
        <div v-else-if="!loading" class="dp-empty">
          <el-icon :size="48" color="var(--text-muted)"><Connection /></el-icon>
          <p>{{ t('networks.emptyDesc') }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Connection } from '@element-plus/icons-vue'
import { getNetworkList, type NetworkInterface } from '@/api/networks'
import { useClusterStore } from '@/stores/cluster'

const { t } = useI18n()
const clusterStore = useClusterStore()

const loading = ref(false)
const networkList = ref<NetworkInterface[]>([])
const filterNode = ref('')
const filterType = ref('')
const search = ref('')
const selectedId = ref<number | null>(null)
const activeTab = ref('basic')

const nodeOptions = computed(() => {
  const set = new Set(networkList.value.map(n => n.node_name))
  return Array.from(set).sort()
})

const typeOptions = computed(() => {
  const set = new Set(networkList.value.map(n => n.type))
  return Array.from(set).sort()
})

const upCount = computed(() => networkList.value.filter(n => n.status === 'up').length)
const downCount = computed(() => networkList.value.filter(n => n.status !== 'up').length)

const filteredList = computed(() => {
  let data = networkList.value
  if (filterNode.value) data = data.filter(n => n.node_name === filterNode.value)
  if (filterType.value) data = data.filter(n => n.type === filterType.value)
  if (search.value) {
    const q = search.value.toLowerCase()
    data = data.filter(n =>
      n.name.toLowerCase().includes(q) ||
      n.node_name.toLowerCase().includes(q) ||
      n.address?.toLowerCase().includes(q) ||
      n.gateway?.toLowerCase().includes(q) ||
      n.mac_address?.toLowerCase().includes(q)
    )
  }
  return data
})

const selected = computed(() => filteredList.value.find(n => n.id === selectedId.value) || null)

watch(() => clusterStore.currentClusterId, () => { fetchData() })

async function fetchData() {
  loading.value = true
  selectedId.value = null
  try {
    const params: Record<string, any> = {}
    if (clusterStore.currentClusterId) params.cluster_id = clusterStore.currentClusterId
    networkList.value = await getNetworkList(params)
    if (filteredList.value.length) {
      selectedId.value = filteredList.value[0].id
    }
  } finally {
    loading.value = false
  }
}

function selectItem(item: NetworkInterface) {
  selectedId.value = item.id
  activeTab.value = 'basic'
}

function fmtTime(iso: string) {
  if (!iso) return '-'
  return new Date(iso).toLocaleString('zh-CN')
}

onMounted(async () => {
  if (!clusterStore.clusterList.length) await clusterStore.fetchClusters()
  fetchData()
})
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
.mi-mid { display: flex; align-items: center; gap: 6px; margin-bottom: 4px; }
.mi-type { font-size: 11px; font-weight: 600; color: var(--color-primary); background: rgba(64,158,255,0.08); padding: 1px 6px; border-radius: 3px; }
.mi-node { font-size: 11px; color: var(--text-muted); background: var(--bg-primary); padding: 1px 5px; border-radius: 3px; }
.master-item.active .mi-node { background: var(--bg-secondary); }
.mi-bottom { display: flex; align-items: center; gap: 8px; font-size: 11px; color: var(--text-muted); }
.mi-ip { font-family: 'SF Mono', 'Menlo', monospace; }
.mi-gw { color: var(--text-muted); }

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
.dp-meta { display: flex; align-items: center; gap: 10px; margin-top: 8px; }
.dp-meta-item { font-size: 13px; color: var(--text-muted); background: var(--bg-primary); padding: 2px 10px; border-radius: 6px; }
.dp-ip { font-family: 'SF Mono', 'Menlo', monospace; font-size: 12px; color: var(--color-primary); background: rgba(64,158,255,0.08); }

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

/* 空状态 */
.dp-empty { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 12px; color: var(--text-muted); font-size: 14px; }

/* ========== 滚动条美化 ========== */
.dp-tabs :deep(.el-tabs__content)::-webkit-scrollbar { width: 6px; }
.dp-tabs :deep(.el-tabs__content)::-webkit-scrollbar-thumb { background: var(--border-color); border-radius: 3px; }
.dp-tabs :deep(.el-tabs__content)::-webkit-scrollbar-thumb:hover { background: var(--text-muted); }
.dp-tabs :deep(.el-tabs__content)::-webkit-scrollbar-track { background: transparent; }

/* ========== 响应式 ========== */
@media (max-width: 1200px) {
  .master-panel { width: 240px; }
  .dp-kv-grid { grid-template-columns: 1fr; }
}
@media (max-width: 768px) {
  .page-top { flex-direction: column; align-items: flex-start; }
  .master-detail { flex-direction: column; }
  .master-panel { width: 100%; max-height: 260px; border-right: none; border-bottom: 1px solid var(--border-color); flex-shrink: 0; }
}
</style>
