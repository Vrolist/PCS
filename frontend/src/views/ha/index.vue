<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ t('advanced.ha.title') }}</h2>
        <p class="page-desc">{{ t('advanced.ha.subtitle') }}</p>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-row">
      <div class="stat-card">
        <div class="sc-ring">
          <svg viewBox="0 0 36 36"><circle cx="18" cy="18" r="15.9" fill="none" stroke="var(--border-color)" stroke-width="2.5" /><circle cx="18" cy="18" r="15.9" fill="none" :stroke="coverage.coverage_pct >= 50 ? '#67c23a' : coverage.coverage_pct >= 20 ? '#e6a23c' : '#f56c6c'" stroke-width="2.5" stroke-dasharray="100" :stroke-dashoffset="100 - coverage.coverage_pct" stroke-linecap="round" transform="rotate(-90 18 18)" /></svg>
          <span class="sc-ring-val">{{ coverage.coverage_pct }}%</span>
        </div>
        <div class="sc-body">
          <div class="sc-value">{{ coverage.ha_protected }}<span class="sc-total"> / {{ coverage.total_resources }}</span></div>
          <div class="sc-label">{{ t('advanced.ha.haCoverage') }}</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="sc-icon sc-icon-blue">🖥️</div>
        <div class="sc-body">
          <div class="sc-value">{{ coverage.total_vms }}</div>
          <div class="sc-label">{{ t('advanced.ha.vmCount') }}</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="sc-icon sc-icon-green">📦</div>
        <div class="sc-body">
          <div class="sc-value">{{ coverage.total_lxc }}</div>
          <div class="sc-label">{{ t('advanced.ha.ctCount') }}</div>
        </div>
      </div>
      <div class="stat-card" :class="{ 'sc-warn': coverage.unprotected_count > 0 }">
        <div class="sc-icon" :class="coverage.unprotected_count > 0 ? 'sc-icon-red' : 'sc-icon-green'">⚠️</div>
        <div class="sc-body">
          <div class="sc-value" :class="coverage.unprotected_count > 0 ? 'text-danger' : 'text-success'">{{ coverage.unprotected_count }}</div>
          <div class="sc-label">{{ t('advanced.ha.unprotected') }}</div>
        </div>
      </div>
    </div>

    <!-- 无保护资源告警 -->
    <div v-if="coverage.unprotected_count > 0" class="alert-banner">
      <div class="alert-icon">⚠️</div>
      <div class="alert-body">
        <div class="alert-title">{{ coverage.unprotected_count }} {{ t('advanced.ha.unprotectedAlert') }}</div>
        <div class="alert-desc">{{ t('advanced.ha.unprotectedDesc') }}</div>
      </div>
      <el-button size="small" type="danger" plain @click="filterTab = 'unprotected'">{{ t('advanced.ha.viewUnprotected') }}</el-button>
    </div>

    <!-- HA 组概览 -->
    <div v-if="groupList.length > 0" class="section-card">
      <div class="section-header">
        <span class="section-title">{{ t('advanced.ha.haGroups') }}</span>
        <span class="section-sub">{{ groupList.length }}</span>
      </div>
      <div class="group-grid">
        <div v-for="g in groupList" :key="g.name" class="group-card">
          <div class="gc-head">
            <span class="gc-dot" :style="{ background: g.color }"></span>
            <span class="gc-name">{{ g.name }}</span>
            <span class="gc-count">{{ g.count }}</span>
          </div>
          <div class="gc-body">
            <div class="gc-stat">
              <span class="gc-stat-label">运行</span>
              <span class="gc-stat-val text-success">{{ g.running }}</span>
            </div>
            <div class="gc-stat">
              <span class="gc-stat-label">停止</span>
              <span class="gc-stat-val" :class="g.stopped > 0 ? 'text-danger' : 'text-muted'">{{ g.stopped }}</span>
            </div>
            <div class="gc-stat">
              <span class="gc-stat-label">CRM</span>
              <span class="gc-stat-val" :class="g.crmOk === g.count ? 'text-success' : 'text-warn'">{{ g.crmOk }}/{{ g.count }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 资源表格 -->
    <div class="section-card">
      <div class="section-header">
        <span class="section-title">{{ t('advanced.ha.resourceList') }}</span>
        <div class="section-filters">
          <el-radio-group v-model="filterTab" size="small">
            <el-radio-button value="all">{{ t('common.all') }} ({{ resources.length }})</el-radio-button>
            <el-radio-button value="protected">{{ t('advanced.ha.protected') }} ({{ coverage.ha_protected }})</el-radio-button>
            <el-radio-button value="unprotected">{{ t('advanced.ha.unprotected') }} ({{ coverage.unprotected_count }})</el-radio-button>
          </el-radio-group>
          <el-select v-model="filterGroup" size="small" clearable :placeholder="t('advanced.ha.haGroup')" style="width: 140px">
            <el-option v-for="g in groupList" :key="g.name" :label="g.name" :value="g.name" />
          </el-select>
        </div>
      </div>

      <!-- 无保护资源子表 -->
      <div v-if="filterTab === 'unprotected'" class="unprotected-section">
        <div v-if="unprotectedList.length === 0" class="empty-hint">
          <span class="text-success">✓ {{ t('advanced.ha.allProtected') }}</span>
        </div>
        <el-table v-else :data="unprotectedList" style="width: 100%" stripe @row-click="showDetail">
          <el-table-column prop="name" :label="t('nodes.name')" min-width="140">
            <template #default="{ row }"><span class="res-name">{{ row.name }}</span></template>
          </el-table-column>
          <el-table-column prop="vmid" label="ID" width="80" align="center" />
          <el-table-column prop="type" :label="t('advanced.ha.type')" width="80" align="center">
            <template #default="{ row }">
              <span class="type-badge" :class="'type-' + row.type">{{ row.type.toUpperCase() }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="node" :label="t('advanced.ha.node')" min-width="120" />
          <el-table-column prop="cluster" :label="t('advanced.ha.cluster')" min-width="100" />
        </el-table>
      </div>

      <!-- HA 资源子表 -->
      <el-table v-else :data="filteredResources" style="width: 100%" stripe v-loading="loading" @row-click="showDetail">
        <el-table-column prop="sid" :label="t('advanced.ha.resourceId')" min-width="110">
          <template #default="{ row }"><code class="sid">{{ row.sid }}</code></template>
        </el-table-column>
        <el-table-column prop="resource_type" :label="t('advanced.ha.type')" width="70" align="center">
          <template #default="{ row }">
            <span class="type-badge" :class="'type-' + row.resource_type">{{ row.resource_type.toUpperCase() }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="vmid" :label="t('advanced.ha.vmId')" width="80" align="center" />
        <el-table-column prop="ha_group" :label="t('advanced.ha.haGroup')" min-width="110">
          <template #default="{ row }">
            <span v-if="row.ha_group" class="group-tag">{{ row.ha_group }}</span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="state" :label="t('advanced.ha.status')" width="90" align="center">
          <template #default="{ row }">
            <span class="state-dot" :class="'state-' + row.state"></span>
            {{ row.state === 'started' ? t('advanced.ha.running') : row.state === 'stopped' ? t('advanced.ha.stopped') : row.state }}
          </template>
        </el-table-column>
        <el-table-column prop="crm_state" :label="t('advanced.ha.crmStatus')" width="90" align="center">
          <template #default="{ row }">
            <span v-if="row.crm_state" class="crm-badge" :class="row.crm_state === 'started' ? 'crm-ok' : 'crm-bad'">{{ row.crm_state }}</span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="cluster_name" :label="t('advanced.ha.cluster')" min-width="100" />
        <el-table-column :label="t('advanced.ha.scanTime')" min-width="140">
          <template #default="{ row }"><span class="time-text">{{ formatTime(row.scanned_at) }}</span></template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && filterTab !== 'unprotected' && !filteredResources.length" :description="t('advanced.ha.noData')" />
    </div>

    <!-- 详情抽屉 -->
    <el-drawer v-model="drawerVisible" :title="detailTitle" size="420px">
      <template v-if="detailResource">
        <div class="detail-grid">
          <div class="dg-item"><span class="dg-label">资源 ID</span><span class="dg-val"><code class="sid">{{ detailResource.sid }}</code></span></div>
          <div class="dg-item"><span class="dg-label">类型</span><span class="dg-val"><span class="type-badge" :class="'type-' + detailResource.resource_type">{{ detailResource.resource_type.toUpperCase() }}</span></span></div>
          <div class="dg-item"><span class="dg-label">VM/CT ID</span><span class="dg-val">{{ detailResource.vmid }}</span></div>
          <div class="dg-item"><span class="dg-label">{{ t('advanced.ha.haGroup') }}</span><span class="dg-val">{{ detailResource.ha_group || '-' }}</span></div>
          <div class="dg-item"><span class="dg-label">{{ t('advanced.ha.status') }}</span><span class="dg-val"><span class="state-dot" :class="'state-' + detailResource.state"></span> {{ detailResource.state }}</span></div>
          <div class="dg-item"><span class="dg-label">CRM</span><span class="dg-val">{{ detailResource.crm_state || '-' }}</span></div>
          <div class="dg-item"><span class="dg-label">HA 状态</span><span class="dg-val">{{ detailResource.ha_status || '-' }}</span></div>
          <div class="dg-item"><span class="dg-label">最大重启</span><span class="dg-val">{{ detailResource.max_restarts ?? '-' }}</span></div>
          <div class="dg-item"><span class="dg-label">最大关机</span><span class="dg-val">{{ detailResource.max_shutdown ?? '-' }}</span></div>
          <div class="dg-item"><span class="dg-label">{{ t('advanced.ha.cluster') }}</span><span class="dg-val">{{ detailResource.cluster_name }}</span></div>
          <div class="dg-item"><span class="dg-label">{{ t('common.scanTime') }}</span><span class="dg-val">{{ formatTime(detailResource.scanned_at) }}</span></div>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { getHAResources, getHACoverage, type HAResource, type HACoverage } from '@/api/ha'
import { useClusterStore } from '@/stores/cluster'

const { t } = useI18n()
const clusterStore = useClusterStore()

const loading = ref(true)
const resources = ref<HAResource[]>([])
const coverage = ref<HACoverage>({ total_resources: 0, total_vms: 0, total_lxc: 0, ha_protected: 0, ha_vms: 0, ha_lxc: 0, coverage_pct: 0, unprotected_count: 0, crm_abnormal: 0 })
const filterTab = ref<'all' | 'protected' | 'unprotected'>('all')
const filterGroup = ref('')
const drawerVisible = ref(false)
const detailResource = ref<HAResource | null>(null)

const detailTitle = computed(() => detailResource.value?.sid || '')

// 无保护资源（从 VM/LXC API 获取，这里用简化逻辑）
const unprotectedList = computed(() => {
  // 简化：返回空数组，实际需要调用 VM/LXC API 对比
  return []
})

// HA 组列表
const groupColors = ['#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#909399', '#b37feb', '#36cfc9', '#ff85c0']
const groupList = computed(() => {
  const map = new Map<string, { count: number; running: number; stopped: number; crmOk: number }>()
  resources.value.forEach(r => {
    const g = r.ha_group || '未分组'
    if (!map.has(g)) map.set(g, { count: 0, running: 0, stopped: 0, crmOk: 0 })
    const stat = map.get(g)!
    stat.count++
    if (r.state === 'started') stat.running++
    if (r.state === 'stopped') stat.stopped++
    if (!r.crm_state || r.crm_state === 'started') stat.crmOk++
  })
  return Array.from(map.entries()).map(([name, stat], i) => ({
    name, ...stat, color: groupColors[i % groupColors.length]
  })).sort((a, b) => b.count - a.count)
})

const filteredResources = computed(() => {
  return resources.value.filter(r => {
    if (filterTab.value === 'protected') return true // 所有 HA 资源都是有保护的
    if (filterGroup.value && (r.ha_group || '未分组') !== filterGroup.value) return false
    return true
  })
})

function showDetail(row: any) {
  if (row.sid) {
    detailResource.value = row
  }
  drawerVisible.value = true
}

async function fetchData() {
  loading.value = true
  try {
    const params: Record<string, any> = {}
    if (clusterStore.currentClusterId) params.cluster_id = clusterStore.currentClusterId
    const [haData, covData] = await Promise.all([
      getHAResources(params),
      getHACoverage(params),
    ])
    resources.value = haData
    coverage.value = covData
  } catch {} finally { loading.value = false }
}

onMounted(async () => {
  if (!clusterStore.clusterList.length) await clusterStore.fetchClusters()
  fetchData()
})

watch(() => clusterStore.currentClusterId, () => { fetchData() })

function formatTime(val: string) {
  if (!val) return '-'
  return new Date(val).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}
</script>

<style scoped>
.page-container { max-width: 1400px; margin: 0 auto; }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 28px; }
.page-title { font-size: 24px; font-weight: 700; color: var(--text-primary, #303133); margin: 0; }
.page-desc { font-size: 14px; color: var(--text-secondary, #909399); margin: 4px 0 0; }

/* ---- 统计卡片 ---- */
.stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 20px; }
.stat-card {
  display: flex; align-items: center; gap: 16px; padding: 20px 24px;
  background: var(--el-bg-color, #fff); border-radius: 12px; border: 1px solid var(--border-light, #e4e7ed);
  transition: all .2s ease;
}
.stat-card:hover { border-color: #c0c4cc; }
.stat-card.sc-warn { border-color: rgba(245, 108, 108, 0.3); }
.sc-ring { position: relative; width: 52px; height: 52px; flex-shrink: 0; }
.sc-ring svg { width: 100%; height: 100%; }
.sc-ring-val { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700; color: var(--text-primary, #303133); }
.sc-icon { width: 52px; height: 52px; display: flex; align-items: center; justify-content: center; border-radius: 12px; font-size: 24px; flex-shrink: 0; }
.sc-icon-blue { background: rgba(64, 158, 255, 0.1); }
.sc-icon-green { background: rgba(103, 194, 58, 0.1); }
.sc-icon-red { background: rgba(245, 108, 108, 0.1); }
.sc-body { flex: 1; min-width: 0; }
.sc-value { font-size: 28px; font-weight: 700; color: var(--text-primary, #303133); line-height: 1.2; }
.sc-total { font-size: 16px; font-weight: 400; color: var(--text-secondary, #909399); }
.sc-label { font-size: 13px; color: var(--text-secondary, #909399); margin-top: 2px; }
.text-success { color: #67c23a; }
.text-danger { color: #f56c6c; }
.text-warn { color: #e6a23c; }

/* ---- 告警横幅 ---- */
.alert-banner {
  display: flex; align-items: center; gap: 16px; padding: 16px 20px; margin-bottom: 20px;
  background: rgba(245, 108, 108, 0.04); border: 1px solid rgba(245, 108, 108, 0.2);
  border-radius: 12px;
}
.alert-icon { font-size: 24px; flex-shrink: 0; }
.alert-body { flex: 1; }
.alert-title { font-size: 14px; font-weight: 600; color: #f56c6c; }
.alert-desc { font-size: 12px; color: var(--text-secondary, #909399); margin-top: 2px; }

/* ---- 通用卡片 ---- */
.section-card {
  background: var(--el-bg-color, #fff); border-radius: 12px; border: 1px solid var(--border-light, #e4e7ed);
  margin-bottom: 20px; overflow: hidden;
}
.section-header { display: flex; align-items: center; justify-content: space-between; padding: 16px 20px; border-bottom: 1px solid var(--border-light, #e4e7ed); }
.section-title { font-size: 15px; font-weight: 600; color: var(--text-primary, #303133); }
.section-sub { font-size: 12px; color: var(--text-secondary, #909399); background: var(--el-fill-color-light, #f5f7fa); padding: 2px 8px; border-radius: 10px; }
.section-filters { display: flex; align-items: center; gap: 12px; }

/* ---- HA 组卡片 ---- */
.group-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 12px; padding: 16px 20px; }
.group-card {
  padding: 14px 16px; border-radius: 10px; border: 1px solid var(--border-light, #e4e7ed);
  background: var(--el-fill-color-light, #f5f7fa); transition: all .2s ease;
}
.group-card:hover { border-color: #c0c4cc; }
.gc-head { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.gc-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.gc-name { font-size: 14px; font-weight: 600; color: var(--text-primary, #303133); flex: 1; }
.gc-count { font-size: 12px; color: var(--text-secondary, #909399); background: var(--el-bg-color, #fff); padding: 1px 8px; border-radius: 10px; }
.gc-body { display: flex; gap: 16px; }
.gc-stat { display: flex; flex-direction: column; gap: 2px; }
.gc-stat-label { font-size: 11px; color: var(--text-secondary, #909399); }
.gc-stat-val { font-size: 15px; font-weight: 600; color: var(--text-primary, #303133); }

/* ---- 表格 ---- */
.unprotected-section { padding: 16px 20px; }
.empty-hint { padding: 24px; text-align: center; font-size: 14px; }
.res-name { font-weight: 500; }
.sid { font-size: 12px; font-weight: 600; background: var(--el-fill-color-light, #f5f7fa); padding: 2px 8px; border-radius: 4px; color: var(--text-primary, #303133); }
.type-badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }
.type-vm { background: rgba(64, 158, 255, 0.12); color: #409eff; }
.type-ct { background: rgba(103, 194, 58, 0.12); color: #67c23a; }
.group-tag { display: inline-block; padding: 2px 10px; border-radius: 6px; font-size: 12px; background: var(--el-fill-color-light, #f5f7fa); color: var(--text-secondary, #909399); }
.state-dot { display: inline-block; width: 7px; height: 7px; border-radius: 50%; margin-right: 6px; vertical-align: middle; }
.state-started { background: #67c23a; box-shadow: 0 0 0 3px #67c23a20; }
.state-stopped { background: #f56c6c; box-shadow: 0 0 0 3px #f56c6c20; }
.crm-badge { display: inline-block; padding: 1px 8px; border-radius: 4px; font-size: 11px; }
.crm-ok { background: rgba(103, 194, 58, 0.12); color: #67c23a; }
.crm-bad { background: rgba(245, 108, 108, 0.12); color: #f56c6c; }
.time-text { font-size: 12px; color: var(--text-secondary, #909399); }

/* ---- 详情抽屉 ---- */
.detail-grid { display: flex; flex-direction: column; }
.dg-item { display: flex; align-items: center; padding: 12px 0; border-bottom: 1px solid var(--border-light, #e4e7ed); }
.dg-item:last-child { border-bottom: none; }
.dg-label { width: 90px; font-size: 13px; color: var(--text-secondary, #909399); flex-shrink: 0; }
.dg-val { font-size: 13px; color: var(--text-primary, #303133); word-break: break-all; }

:deep(.el-table) { background: transparent; --el-table-bg-color: transparent; --el-table-tr-bg-color: transparent; --el-table-header-bg-color: transparent; --el-table-border-color: var(--border-light, #e4e7ed); --el-table-text-color: var(--text-primary, #303133); --el-table-header-text-color: var(--text-secondary, #909399); }
:deep(.el-table::before) { display: none; }
:deep(.el-table th.el-table__cell) { background: transparent; font-weight: 600; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; }
:deep(.el-table--enable-row-hover .el-table__body tr:hover > td) { background-color: rgba(64, 158, 255, 0.04); cursor: pointer; }
:deep(.el-table--striped .el-table__body tr.el-table__row--striped td.el-table__cell) { background: var(--el-fill-color-light, #f5f7fa); }
</style>
