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
      <div class="stat-card sc-total">
        <div class="sc-icon">📦</div>
        <div class="sc-body">
          <div class="sc-value">{{ resources.length }}</div>
          <div class="sc-label">{{ t('advanced.ha.totalResources') }}</div>
        </div>
      </div>
      <div class="stat-card sc-vm">
        <div class="sc-icon">🖥️</div>
        <div class="sc-body">
          <div class="sc-value">{{ vmCount }}</div>
          <div class="sc-label">{{ t('advanced.ha.vmCount') }}</div>
        </div>
      </div>
      <div class="stat-card sc-ct">
        <div class="sc-icon">📦</div>
        <div class="sc-body">
          <div class="sc-value">{{ ctCount }}</div>
          <div class="sc-label">{{ t('advanced.ha.ctCount') }}</div>
        </div>
      </div>
      <div class="stat-card sc-active">
        <div class="sc-icon">✅</div>
        <div class="sc-body">
          <div class="sc-value">{{ activeCount }}</div>
          <div class="sc-label">{{ t('advanced.ha.activeCount') }}</div>
        </div>
      </div>
    </div>

    <!-- HA 组分布 -->
    <div v-if="groupList.length > 1" class="group-section">
      <div class="group-header">
        <span class="group-title">HA 组分布</span>
        <span class="group-sub">{{ groupList.length }} 个组</span>
      </div>
      <div class="group-chips">
        <div v-for="g in groupList" :key="g.name" class="group-chip">
          <span class="gc-dot" :style="{ background: g.color }"></span>
          <span class="gc-name">{{ g.name }}</span>
          <span class="gc-count">{{ g.count }}</span>
        </div>
      </div>
    </div>

    <!-- 资源表格 -->
    <div class="table-card">
      <div class="table-toolbar">
        <span class="tt-title">{{ t('advanced.ha.resourceList') }}</span>
        <div class="tt-filters">
          <el-radio-group v-model="filterType" size="small">
            <el-radio-button value="">{{ t('common.all') }}</el-radio-button>
            <el-radio-button value="vm">VM</el-radio-button>
            <el-radio-button value="ct">CT</el-radio-button>
          </el-radio-group>
          <el-select v-model="filterGroup" size="small" clearable :placeholder="t('advanced.ha.haGroup')" style="width: 140px">
            <el-option v-for="g in groupList" :key="g.name" :label="g.name" :value="g.name" />
          </el-select>
        </div>
      </div>

      <el-table :data="filteredResources" style="width: 100%" stripe v-loading="loading" @row-click="showDetail">
        <el-table-column prop="sid" :label="t('advanced.ha.resourceId')" min-width="110">
          <template #default="{ row }">
            <code class="sid">{{ row.sid }}</code>
          </template>
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
        <el-table-column prop="cluster_name" :label="t('advanced.ha.cluster')" min-width="100" />
        <el-table-column :label="t('advanced.ha.scanTime')" min-width="150">
          <template #default="{ row }">
            <span class="time-text">{{ formatTime(row.scanned_at) }}</span>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && !filteredResources.length" :description="t('advanced.ha.noData')" />
    </div>

    <!-- 详情抽屉 -->
    <el-drawer v-model="drawerVisible" :title="detailResource?.sid" size="400px">
      <template v-if="detailResource">
        <div class="detail-grid">
          <div class="dg-item"><span class="dg-label">资源 ID</span><span class="dg-val"><code class="sid">{{ detailResource.sid }}</code></span></div>
          <div class="dg-item"><span class="dg-label">类型</span><span class="dg-val"><span class="type-badge" :class="'type-' + detailResource.resource_type">{{ detailResource.resource_type.toUpperCase() }}</span></span></div>
          <div class="dg-item"><span class="dg-label">VM/CT ID</span><span class="dg-val">{{ detailResource.vmid }}</span></div>
          <div class="dg-item"><span class="dg-label">节点</span><span class="dg-val">{{ detailResource.node_name || '-' }}</span></div>
          <div class="dg-item"><span class="dg-label">状态</span><span class="dg-val"><span class="state-dot" :class="'state-' + detailResource.state"></span> {{ detailResource.state }}</span></div>
          <div class="dg-item"><span class="dg-label">HA 组</span><span class="dg-val">{{ detailResource.ha_group || '-' }}</span></div>
          <div class="dg-item"><span class="dg-label">HA 状态</span><span class="dg-val">{{ detailResource.ha_status || '-' }}</span></div>
          <div class="dg-item"><span class="dg-label">CRM 状态</span><span class="dg-val">{{ detailResource.crm_state || '-' }}</span></div>
          <div class="dg-item"><span class="dg-label">最大重启</span><span class="dg-val">{{ detailResource.max_restarts ?? '-' }}</span></div>
          <div class="dg-item"><span class="dg-label">最大关机</span><span class="dg-val">{{ detailResource.max_shutdown ?? '-' }}</span></div>
          <div class="dg-item"><span class="dg-label">集群</span><span class="dg-val">{{ detailResource.cluster_name }}</span></div>
          <div class="dg-item"><span class="dg-label">扫描时间</span><span class="dg-val">{{ formatTime(detailResource.scanned_at) }}</span></div>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { getHAResources, type HAResource } from '@/api/ha'
import { useClusterStore } from '@/stores/cluster'

const { t } = useI18n()
const clusterStore = useClusterStore()

const loading = ref(true)
const resources = ref<HAResource[]>([])
const filterType = ref('')
const filterGroup = ref('')
const drawerVisible = ref(false)
const detailResource = ref<HAResource | null>(null)

const vmCount = computed(() => resources.value.filter(r => r.resource_type === 'vm').length)
const ctCount = computed(() => resources.value.filter(r => r.resource_type === 'ct').length)
const activeCount = computed(() => resources.value.filter(r => r.state === 'started').length)

const groupColors = ['#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#909399', '#b37feb', '#36cfc9', '#ff85c0']
const groupList = computed(() => {
  const map = new Map<string, number>()
  resources.value.forEach(r => {
    const g = r.ha_group || '未分组'
    map.set(g, (map.get(g) || 0) + 1)
  })
  return Array.from(map.entries()).map(([name, count], i) => ({
    name, count, color: groupColors[i % groupColors.length]
  })).sort((a, b) => b.count - a.count)
})

const filteredResources = computed(() => {
  return resources.value.filter(r => {
    if (filterType.value && r.resource_type !== filterType.value) return false
    if (filterGroup.value && (r.ha_group || '未分组') !== filterGroup.value) return false
    return true
  })
})

function showDetail(row: HAResource) {
  detailResource.value = row
  drawerVisible.value = true
}

async function fetchData() {
  loading.value = true
  try {
    const params: Record<string, any> = {}
    if (clusterStore.currentClusterId) params.cluster_id = clusterStore.currentClusterId
    resources.value = await getHAResources(params)
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
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px; }
.page-title { font-size: 24px; font-weight: 700; color: var(--text-heading); margin: 0; }
.page-desc { font-size: 14px; color: var(--text-muted); margin: 4px 0 0; }

/* ---- 统计卡片 ---- */
.stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }
.stat-card {
  display: flex; align-items: center; gap: 16px; padding: 20px 24px;
  background: var(--bg-primary, #fff); border-radius: 12px; border: 1px solid var(--border-color, #e4e7ed);
  transition: all .2s; cursor: default;
}
.stat-card:hover { border-color: var(--el-color-primary-light-5); }
.sc-icon { font-size: 32px; width: 52px; height: 52px; display: flex; align-items: center; justify-content: center; border-radius: 12px; flex-shrink: 0; }
.sc-total .sc-icon { background: rgba(64, 158, 255, 0.1); }
.sc-vm .sc-icon { background: rgba(103, 194, 58, 0.1); }
.sc-ct .sc-icon { background: rgba(230, 162, 60, 0.1); }
.sc-active .sc-icon { background: rgba(103, 194, 58, 0.1); }
.sc-body { flex: 1; min-width: 0; }
.sc-value { font-size: 28px; font-weight: 700; color: var(--text-heading); line-height: 1.2; }
.sc-label { font-size: 13px; color: var(--text-muted); margin-top: 2px; }

/* ---- HA 组分布 ---- */
.group-section { margin-bottom: 20px; padding: 16px 20px; background: var(--bg-primary, #fff); border-radius: 12px; border: 1px solid var(--border-color, #e4e7ed); }
.group-header { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
.group-title { font-size: 14px; font-weight: 600; color: var(--text-primary); }
.group-sub { font-size: 12px; color: var(--text-muted); }
.group-chips { display: flex; flex-wrap: wrap; gap: 8px; }
.group-chip { display: flex; align-items: center; gap: 6px; padding: 6px 14px; background: var(--bg-secondary, #f5f7fa); border-radius: 8px; font-size: 13px; }
.gc-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.gc-name { color: var(--text-primary); }
.gc-count { font-weight: 600; color: var(--text-heading); background: var(--bg-primary, #fff); padding: 1px 8px; border-radius: 10px; font-size: 12px; }

/* ---- 表格 ---- */
.table-card {
  background: var(--bg-primary, #fff); border-radius: 12px; border: 1px solid var(--border-color, #e4e7ed);
  overflow: hidden;
}
.table-toolbar { display: flex; align-items: center; justify-content: space-between; padding: 16px 20px; border-bottom: 1px solid var(--border-color, #e4e7ed); }
.tt-title { font-size: 15px; font-weight: 600; color: var(--text-primary); }
.tt-filters { display: flex; align-items: center; gap: 12px; }

.sid { font-size: 12px; font-weight: 600; background: var(--bg-secondary, #f0f2f5); padding: 2px 8px; border-radius: 4px; color: var(--text-primary); }
.type-badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }
.type-vm { background: rgba(64, 158, 255, 0.12); color: #409eff; }
.type-ct { background: rgba(103, 194, 58, 0.12); color: #67c23a; }
.group-tag { display: inline-block; padding: 2px 10px; border-radius: 6px; font-size: 12px; background: var(--bg-secondary, #f0f2f5); color: var(--text-secondary); }
.state-dot { display: inline-block; width: 7px; height: 7px; border-radius: 50%; margin-right: 6px; vertical-align: middle; }
.state-started { background: #67c23a; box-shadow: 0 0 6px rgba(103, 194, 58, 0.4); }
.state-stopped { background: #f56c6c; box-shadow: 0 0 6px rgba(245, 108, 108, 0.4); }
.state-error { background: #e6a23c; box-shadow: 0 0 6px rgba(230, 162, 60, 0.4); }
.time-text { font-size: 12px; color: var(--text-muted); }
.text-muted { color: var(--text-muted); }

/* ---- 详情抽屉 ---- */
.detail-grid { display: flex; flex-direction: column; gap: 0; }
.dg-item { display: flex; align-items: center; padding: 12px 0; border-bottom: 1px solid var(--el-border-color-lighter); }
.dg-item:last-child { border-bottom: none; }
.dg-label { width: 90px; font-size: 13px; color: var(--text-muted); flex-shrink: 0; }
.dg-val { font-size: 13px; color: var(--text-primary); word-break: break-all; }

:deep(.el-table) { background: transparent; --el-table-bg-color: transparent; --el-table-tr-bg-color: transparent; --el-table-header-bg-color: transparent; --el-table-border-color: var(--border-color); --el-table-text-color: var(--text-primary); --el-table-header-text-color: var(--text-secondary); }
:deep(.el-table::before) { display: none; }
:deep(.el-table th.el-table__cell) { background: transparent; font-weight: 600; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; }
:deep(.el-table--enable-row-hover .el-table__body tr:hover > td) { background-color: rgba(64, 158, 255, 0.04); cursor: pointer; }
:deep(.el-table--striped .el-table__body tr.el-table__row--striped td.el-table__cell) { background: var(--bg-secondary, #fafafa); }
:deep(.el-radio-group) { --el-radio-button-checked-bg-color: var(--el-color-primary); }
</style>
