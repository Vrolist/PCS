<template>
  <div class="page-container">
    <!-- 标题 + 统计 + 筛选 -->
    <div class="page-top">
      <div class="page-top-left">
        <h2 class="page-title">{{ t('storagePage.title') }}</h2>
        <div class="mini-stats" v-if="!loading && storageList.length">
          <span class="ms-item"><i class="ms-dot ms-dot-total" />{{ storageList.length }}</span>
          <span class="ms-item"><i class="ms-dot ms-dot-online" />{{ onlineCount }}</span>
          <span class="ms-item"><i class="ms-dot ms-dot-shared" />{{ sharedCount }}</span>
        </div>
      </div>
      <div class="page-top-right">
        <el-input v-model="search" :placeholder="t('storagePage.searchPlaceholder')" clearable prefix-icon="Search" size="small" class="top-search" />
        <el-select v-model="filterNode" :placeholder="t('storagePage.allNodes')" clearable size="small" style="width:130px">
          <el-option v-for="n in nodes" :key="n" :label="n" :value="n" />
        </el-select>
        <el-select v-model="filterType" :placeholder="t('storagePage.allTypes')" clearable size="small" style="width:120px">
          <el-option v-for="tp in types" :key="tp" :label="tp" :value="tp" />
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
              <span class="mi-dot" :class="item.status === 'available' ? 'dot-run' : 'dot-stop'" />
            </div>
            <div class="mi-mid">
              <span class="mi-type">{{ item.type }}</span>
              <span class="mi-node">{{ item.node_name }}</span>
              <span v-if="item.shared" class="mi-shared">{{ t('storagePage.shared') }}</span>
            </div>
            <div class="mi-bar" v-if="item.total_gb > 0">
              <div class="mi-bar-track">
                <div class="mi-bar-fill" :style="{ width: getPercent(item.used_gb, item.total_gb) + '%', background: getProgressColor(getPercent(item.used_gb, item.total_gb)) }" />
              </div>
              <span class="mi-bar-text">{{ formatGB(item.used_gb) }} / {{ formatGB(item.total_gb) }}</span>
            </div>
          </div>
        </div>
        <el-empty v-else-if="!loading" :description="t('storagePage.emptyDesc')" :image-size="80" />
      </div>

      <!-- 右侧详情 -->
      <div class="detail-panel">
        <template v-if="selected">
          <!-- 详情头部 -->
          <div class="dp-header">
            <div class="dp-title-row">
              <h3 class="dp-name">{{ selected.name }}</h3>
              <el-tag size="small" effect="plain">{{ selected.type }}</el-tag>
              <el-tag :type="selected.status === 'available' ? 'success' : 'danger'" size="small" disable-transitions>
                {{ selected.status === 'available' ? t('common.enabled') : selected.status }}
              </el-tag>
              <el-tag v-if="selected.shared" type="info" size="small" effect="plain">{{ t('storagePage.shared') }}</el-tag>
            </div>
            <div class="dp-meta">
              <span class="dp-meta-item">{{ selected.node_name }}</span>
              <span class="dp-meta-item" v-if="selected.content">{{ selected.content }}</span>
            </div>
          </div>

          <!-- 容量概览卡片 -->
          <div class="dp-capacity-card" v-if="selected.total_gb > 0">
            <div class="cap-main">
              <div class="cap-ring">
                <el-progress type="circle" :percentage="getPercent(selected.used_gb, selected.total_gb)" :width="120" :stroke-width="10" :color="getProgressColor(getPercent(selected.used_gb, selected.total_gb))" />
              </div>
              <div class="cap-info">
                <div class="cap-row"><span class="cap-label">{{ t('storagePage.totalCapacity') }}</span><span class="cap-value">{{ formatGB(selected.total_gb) }}</span></div>
                <div class="cap-row"><span class="cap-label">{{ t('storagePage.usedCapacity') }}</span><span class="cap-value cap-used">{{ formatGB(selected.used_gb) }}</span></div>
                <div class="cap-row"><span class="cap-label">{{ t('storagePage.availCapacity') }}</span><span class="cap-value cap-avail">{{ formatGB(selected.available_gb) }}</span></div>
              </div>
            </div>
            <div class="cap-bar-wrap">
              <div class="cap-bar-track">
                <div class="cap-bar-fill" :style="{ width: getPercent(selected.used_gb, selected.total_gb) + '%', background: getProgressColor(getPercent(selected.used_gb, selected.total_gb)) }" />
              </div>
              <div class="cap-bar-labels">
                <span>{{ t('storagePage.used') }} {{ formatGB(selected.used_gb) }}</span>
                <span>{{ t('storagePage.avail') }} {{ formatGB(selected.available_gb) }}</span>
              </div>
            </div>
          </div>

          <!-- 无容量信息时的提示 -->
          <div class="dp-capacity-card dp-capacity-empty" v-else>
            <el-icon :size="32" color="var(--text-muted)"><Coin /></el-icon>
            <span>{{ t('storagePage.noCapacityInfo') }}</span>
          </div>

          <!-- Tab 切换 -->
          <el-tabs v-model="activeTab" class="dp-tabs">
            <el-tab-pane :label="t('storagePage.basicInfo')" name="basic">
              <div class="dp-section-card">
                <div class="dp-kv-grid">
                  <div class="dp-kv"><span class="dp-kv-label">{{ t('storagePage.storageName') }}</span><span class="dp-kv-val">{{ selected.name }}</span></div>
                  <div class="dp-kv"><span class="dp-kv-label">{{ t('common.type') }}</span><span class="dp-kv-val"><el-tag size="small" effect="plain">{{ selected.type }}</el-tag></span></div>
                  <div class="dp-kv"><span class="dp-kv-label">{{ t('common.status') }}</span><span class="dp-kv-val"><el-tag :type="selected.status === 'available' ? 'success' : 'danger'" size="small" disable-transitions>{{ selected.status === 'available' ? t('common.enabled') : selected.status }}</el-tag></span></div>
                  <div class="dp-kv"><span class="dp-kv-label">{{ t('common.nodes') }}</span><span class="dp-kv-val">{{ selected.node_name }}</span></div>
                  <div class="dp-kv"><span class="dp-kv-label">{{ t('storagePage.shared') }}</span><span class="dp-kv-val">{{ selected.shared ? t('storagePage.yes') : '-' }}</span></div>
                  <div class="dp-kv" v-if="selected.content"><span class="dp-kv-label">{{ t('storagePage.contentType') }}</span><span class="dp-kv-val">
                    <el-tag v-for="c in selected.content.split(',')" :key="c" size="small" effect="plain" style="margin-right:4px">{{ c.trim() }}</el-tag>
                  </span></div>
                  <div class="dp-kv"><span class="dp-kv-label">{{ t('storagePage.totalCapacity') }}</span><span class="dp-kv-val">{{ formatGB(selected.total_gb) }}</span></div>
                  <div class="dp-kv"><span class="dp-kv-label">{{ t('storagePage.usedCapacity') }}</span><span class="dp-kv-val">{{ formatGB(selected.used_gb) }}</span></div>
                  <div class="dp-kv"><span class="dp-kv-label">{{ t('storagePage.availCapacity') }}</span><span class="dp-kv-val">{{ formatGB(selected.available_gb) }}</span></div>
                  <div class="dp-kv"><span class="dp-kv-label">{{ t('common.scanTime') }}</span><span class="dp-kv-val mono">{{ fmtTime(selected.scanned_at) }}</span></div>
                </div>
              </div>
            </el-tab-pane>
          </el-tabs>
        </template>

        <!-- 未选中状态 -->
        <div v-else-if="!loading" class="dp-empty">
          <el-icon :size="48" color="var(--text-muted)"><Coin /></el-icon>
          <p>{{ t('storagePage.emptyDesc') }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Coin } from '@element-plus/icons-vue'
import { getStorageList, type Storage } from '@/api/storage'
import { useClusterStore } from '@/stores/cluster'

const { t } = useI18n()
const clusterStore = useClusterStore()

const loading = ref(false)
const storageList = ref<Storage[]>([])
const filterNode = ref('')
const filterType = ref('')
const search = ref('')
const selectedId = ref<number | null>(null)
const activeTab = ref('basic')

const nodes = computed(() => {
  const set = new Set(storageList.value.map(s => s.node_name))
  return Array.from(set).sort()
})

const types = computed(() => {
  const set = new Set(storageList.value.map(s => s.type))
  return Array.from(set).sort()
})

const onlineCount = computed(() => storageList.value.filter(s => s.status === 'available').length)
const sharedCount = computed(() => storageList.value.filter(s => s.shared).length)

const filteredList = computed(() => {
  let data = storageList.value
  if (filterNode.value) data = data.filter(s => s.node_name === filterNode.value)
  if (filterType.value) data = data.filter(s => s.type === filterType.value)
  if (search.value) {
    const q = search.value.toLowerCase()
    data = data.filter(s => s.name.toLowerCase().includes(q) || s.node_name.toLowerCase().includes(q))
  }
  return data
})

const selected = computed(() => filteredList.value.find(s => s.id === selectedId.value) || null)

watch(() => clusterStore.currentClusterId, () => { fetchData() })

async function fetchData() {
  loading.value = true
  selectedId.value = null
  try {
    const params: Record<string, any> = {}
    if (clusterStore.currentClusterId) params.cluster_id = clusterStore.currentClusterId
    storageList.value = await getStorageList(params)
    if (filteredList.value.length) {
      selectedId.value = filteredList.value[0].id
    }
  } finally {
    loading.value = false
  }
}

function selectItem(item: Storage) {
  selectedId.value = item.id
  activeTab.value = 'basic'
}

function formatGB(val: number): string {
  if (!val) return '0GB'
  return val >= 1024 ? `${(val / 1024).toFixed(1)}TB` : `${Math.round(val)}GB`
}

function getPercent(used: number, total: number): number {
  return Math.min(Math.round((used / total) * 100), 100)
}

function getProgressColor(percent: number): string {
  if (percent >= 90) return '#f56c6c'
  if (percent >= 70) return '#e6a23c'
  return '#67c23a'
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
.ms-dot-online { background: #67c23a; box-shadow: 0 0 4px rgba(103,194,58,0.5); }
.ms-dot-shared { background: #e6a23c; }
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
  width: 320px; flex-shrink: 0;
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
.mi-mid { display: flex; align-items: center; gap: 6px; margin-bottom: 6px; }
.mi-type { font-size: 11px; font-weight: 600; color: var(--color-primary); background: rgba(64,158,255,0.08); padding: 1px 6px; border-radius: 3px; }
.mi-node { font-size: 11px; color: var(--text-muted); background: var(--bg-primary); padding: 1px 5px; border-radius: 3px; }
.master-item.active .mi-node { background: var(--bg-secondary); }
.mi-shared { font-size: 10px; font-weight: 600; color: #e6a23c; background: rgba(230,162,60,0.1); padding: 1px 5px; border-radius: 3px; }
.mi-bar { display: flex; align-items: center; gap: 8px; }
.mi-bar-track { flex: 1; height: 4px; background: var(--border-color); border-radius: 2px; overflow: hidden; }
.mi-bar-fill { height: 100%; border-radius: 2px; transition: width .3s; }
.mi-bar-text { font-size: 10px; color: var(--text-muted); font-family: 'SF Mono', 'Menlo', monospace; white-space: nowrap; }

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

/* 容量概览卡片 */
.dp-capacity-card {
  padding: 20px 24px;
  background: var(--bg-secondary);
  border-radius: 12px;
  border: 1px solid var(--border-color);
  flex-shrink: 0;
}
.dp-capacity-empty {
  display: flex; align-items: center; justify-content: center; gap: 10px;
  color: var(--text-muted); font-size: 14px; padding: 32px;
}
.cap-main { display: flex; align-items: center; gap: 32px; margin-bottom: 20px; }
.cap-ring { flex-shrink: 0; }
.cap-ring :deep(.el-progress-circle) { display: block; }
.cap-info { flex: 1; display: flex; flex-direction: column; gap: 10px; }
.cap-row { display: flex; align-items: center; justify-content: space-between; }
.cap-label { font-size: 13px; color: var(--text-muted); }
.cap-value { font-size: 16px; font-weight: 700; color: var(--text-heading); }
.cap-used { color: #e6a23c; }
.cap-avail { color: #67c23a; }
.cap-bar-wrap { display: flex; flex-direction: column; gap: 6px; }
.cap-bar-track { height: 8px; background: var(--bg-primary); border-radius: 4px; overflow: hidden; }
.cap-bar-fill { height: 100%; border-radius: 4px; transition: width .3s; }
.cap-bar-labels { display: flex; justify-content: space-between; font-size: 12px; color: var(--text-muted); }

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
  .master-panel { width: 260px; }
  .dp-kv-grid { grid-template-columns: 1fr; }
  .cap-main { flex-direction: column; align-items: flex-start; }
}
@media (max-width: 768px) {
  .page-top { flex-direction: column; align-items: flex-start; }
  .master-detail { flex-direction: column; }
  .master-panel { width: 100%; max-height: 260px; border-right: none; border-bottom: 1px solid var(--border-color); flex-shrink: 0; }
}
</style>
