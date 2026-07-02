<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ t('advanced.snapshots.title') }}</h2>
        <p class="page-desc">{{ t('advanced.snapshots.subtitle') }}</p>
      </div>
      <div class="header-actions">
        <el-input v-model="search" :placeholder="t('advanced.snapshots.searchPlaceholder')" clearable prefix-icon="Search" style="width: 260px" @input="debounceLoad" />
        <el-radio-group v-model="viewMode" size="small">
          <el-radio-button value="tree">{{ t('advanced.snapshots.treeView') }}</el-radio-button>
          <el-radio-button value="table">{{ t('advanced.snapshots.tableView') }}</el-radio-button>
        </el-radio-group>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stat-row" v-if="!loading && snapshots.length">
      <div class="stat-item">
        <span class="stat-value">{{ vmGroups.length }}</span>
        <span class="stat-label">{{ t('advanced.snapshots.vmCount') }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-value">{{ snapshots.length }}</span>
        <span class="stat-label">{{ t('advanced.snapshots.totalSnaps') }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-value">{{ maxChainLen }}</span>
        <span class="stat-label">{{ t('advanced.snapshots.maxDepth') }}</span>
      </div>
    </div>

    <!-- 树形视图 -->
    <template v-if="viewMode === 'tree'">
      <div v-if="loading" class="loading-box">
        <el-icon class="is-loading" :size="20"><Loading /></el-icon>
        <span>{{ t('common.loading') }}</span>
      </div>
      <div v-else-if="!vmGroups.length" class="empty-box">
        <el-empty :description="t('advanced.snapshots.emptyDesc')" />
      </div>
      <div v-else class="vm-cards">
        <el-card v-for="group in vmGroups" :key="group.vmId" shadow="hover" class="vm-card">
          <div class="vm-card-header">
            <div class="vm-info">
              <span class="vm-name">{{ group.vmName }}</span>
              <el-tag size="small" type="info" effect="plain">VMID: {{ group.vmVmid }}</el-tag>
            </div>
            <div class="vm-meta">
              <span class="meta-item">{{ t('advanced.snapshots.node') }}: {{ group.nodeName }}</span>
              <span class="meta-divider">|</span>
              <span class="meta-item">{{ t('advanced.snapshots.snapCount') }}: {{ group.snaps.length }}</span>
            </div>
          </div>
          <div class="snap-tree">
            <div v-for="node in group.tree" :key="node.snapid" class="snap-tree-item" :style="{ paddingLeft: node.depth * 28 + 'px' }">
              <!-- 连接线 -->
              <div class="tree-connector" v-if="node.depth > 0">
                <span class="tree-line-v"></span>
                <span class="tree-line-h"></span>
              </div>
              <div class="snap-node" :class="{ 'is-current': node.snapid === 'current', 'is-root': node.depth === 0 }">
                <div class="snap-icon">
                  <el-icon v-if="node.snapid === 'current'" :size="16" style="color: #67c23a"><VideoPlay /></el-icon>
                  <el-icon v-else :size="16" style="color: #e6a23c"><Camera /></el-icon>
                </div>
                <div class="snap-content">
                  <div class="snap-title-row">
                    <span class="snap-name" :class="{ 'current-name': node.snapid === 'current' }">{{ node.name }}</span>
                    <el-tag v-if="node.snapid === 'current'" type="success" size="small" effect="dark">{{ t('advanced.snapshots.current') }}</el-tag>
                    <el-tag v-if="node.snap_type" size="small" type="warning" effect="plain">{{ node.snap_type }}</el-tag>
                    <el-tag v-if="node.ram" size="small" type="info" effect="plain">{{ t('advanced.snapshots.saveMemory') }}</el-tag>
                    <el-tag v-if="node.vmstate" size="small" type="info" effect="plain">{{ t('advanced.snapshots.saveState') }}</el-tag>
                  </div>
                  <div class="snap-meta-row">
                    <span v-if="node.snap_time" class="meta-time">{{ fmtTime(node.snap_time) }}</span>
                    <span v-else class="meta-time dim">-</span>
                    <span v-if="node.description" class="meta-desc">{{ node.description }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </el-card>
      </div>
    </template>

    <!-- 表格视图 -->
    <template v-else>
      <el-card shadow="hover" class="table-card">
        <div v-if="loading" class="loading-box">
          <el-icon class="is-loading" :size="20"><Loading /></el-icon>
          <span>{{ t('common.loading') }}</span>
        </div>
        <el-table v-else :data="snapshots" style="width: 100%" stripe :default-sort="{ prop: 'snap_time', order: 'descending' }">
          <el-table-column :label="t('advanced.snapshots.snapName')" min-width="160" fixed>
            <template #default="{ row }">
              <span class="snap-name" :class="{ 'current-name': row.snapid === 'current' }">{{ row.name }}</span>
              <el-tag v-if="row.snapid === 'current'" type="success" size="small" effect="dark" style="margin-left:6px">{{ t('advanced.snapshots.current') }}</el-tag>
              <div class="sub-text" v-if="row.description">{{ row.description }}</div>
            </template>
          </el-table-column>
          <el-table-column :label="t('advanced.snapshots.vmName')" min-width="140">
            <template #default="{ row }">
              <span class="vm-name">{{ row.vm_name }}</span>
              <div class="sub-text">VMID: {{ row.vm_vmid }}</div>
            </template>
          </el-table-column>
          <el-table-column :label="t('advanced.snapshots.node')" prop="node_name" width="110" />
          <el-table-column :label="t('advanced.snapshots.snapTime')" min-width="160" sortable sort-by="snap_time">
            <template #default="{ row }">{{ fmtTime(row.snap_time) }}</template>
          </el-table-column>
          <el-table-column :label="t('advanced.snapshots.parent')" width="130">
            <template #default="{ row }">
              <span v-if="row.parent" class="parent-tag">{{ row.parent }}</span>
              <span v-else class="no-parent">{{ t('advanced.snapshots.noParent') }}</span>
            </template>
          </el-table-column>
          <el-table-column :label="t('advanced.snapshots.saveMemory')" width="90" align="center">
            <template #default="{ row }">
              <el-tag :type="row.ram ? 'success' : 'info'" size="small">{{ row.ram ? t('advanced.snapshots.yes') : t('advanced.snapshots.no') }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column :label="t('advanced.snapshots.saveState')" width="90" align="center">
            <template #default="{ row }">
              <el-tag :type="row.vmstate ? 'success' : 'info'" size="small">{{ row.vmstate ? t('advanced.snapshots.yes') : t('advanced.snapshots.no') }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column :label="t('advanced.snapshots.snapType')" width="100" align="center">
            <template #default="{ row }">
              <el-tag v-if="row.snap_type" type="warning" size="small" effect="plain">{{ row.snap_type }}</el-tag>
              <span v-else>-</span>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="!loading && !snapshots.length" :description="t('advanced.snapshots.emptyDesc')" />
      </el-card>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Loading, VideoPlay, Camera } from '@element-plus/icons-vue'
import { getSnapshots } from '@/api/snapshots'
import type { SnapshotInfo } from '@/api/snapshots'
import { useClusterStore } from '@/stores/cluster'

const { t } = useI18n()
const clusterStore = useClusterStore()

const loading = ref(true)
const snapshots = ref<SnapshotInfo[]>([])
const search = ref('')
const viewMode = ref<'tree' | 'table'>('tree')
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
    if (search.value) params.search = search.value
    snapshots.value = await getSnapshots(params)
  } catch {} finally { loading.value = false }
}

function debounceLoad() {
  if (timer) clearTimeout(timer)
  timer = setTimeout(loadData, 300)
}

interface TreeNode extends SnapshotInfo {
  depth: number
  children: TreeNode[]
}

interface VmGroup {
  vmId: number
  vmVmid: number
  vmName: string
  nodeName: string
  clusterName: string
  snaps: SnapshotInfo[]
  tree: TreeNode[]
}

function buildTree(snaps: SnapshotInfo[]): TreeNode[] {
  const map = new Map<string, TreeNode>()
  const roots: TreeNode[] = []

  // 创建节点
  for (const s of snaps) {
    map.set(s.snapid, { ...s, depth: 0, children: [] })
  }

  // 建立父子关系
  for (const node of map.values()) {
    if (node.parent && map.has(node.parent)) {
      const parent = map.get(node.parent)!
      node.depth = parent.depth + 1
      parent.children.push(node)
    } else {
      roots.push(node)
    }
  }

  // 按时间排序：current 放最前，其余按时间降序
  roots.sort((a, b) => {
    if (a.snapid === 'current') return -1
    if (b.snapid === 'current') return 1
    return (b.snap_time || '').localeCompare(a.snap_time || '')
  })

  for (const node of map.values()) {
    node.children.sort((a, b) => {
      if (a.snapid === 'current') return -1
      if (b.snapid === 'current') return 1
      return (b.snap_time || '').localeCompare(a.snap_time || '')
    })
  }

  // 展平为有序列表（DFS），同时更新 depth
  const flat: TreeNode[] = []
  function dfs(node: TreeNode, depth: number) {
    node.depth = depth
    flat.push(node)
    for (const child of node.children) {
      dfs(child, depth + 1)
    }
  }
  for (const root of roots) {
    dfs(root, 0)
  }

  return flat
}

const vmGroups = computed<VmGroup[]>(() => {
  const groups = new Map<string, VmGroup>()
  for (const s of snapshots.value) {
    const key = `${s.node_name}-${s.vm_vmid}`
    if (!groups.has(key)) {
      groups.set(key, {
        vmId: s.vm_id,
        vmVmid: s.vm_vmid,
        vmName: s.vm_name,
        nodeName: s.node_name,
        clusterName: s.cluster_name,
        snaps: [],
        tree: [],
      })
    }
    groups.get(key)!.snaps.push(s)
  }
  const result = Array.from(groups.values())
  for (const g of result) {
    g.tree = buildTree(g.snaps)
  }
  // 按 VM 名称排序
  result.sort((a, b) => a.vmName.localeCompare(b.vmName))
  return result
})

const maxChainLen = computed(() => {
  let max = 0
  for (const g of vmGroups.value) {
    if (g.snaps.length > max) max = g.snaps.length
  }
  return max
})

function fmtTime(iso: string | null) {
  if (!iso) return '-'
  return new Date(iso).toLocaleString('zh-CN')
}
</script>

<style scoped>
.page-container { max-width: 1400px; margin: 0 auto; }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; flex-wrap: wrap; gap: 12px; }
.page-title { font-size: 24px; font-weight: 700; color: var(--text-heading); margin: 0; }
.page-desc { font-size: 14px; color: var(--text-muted); margin: 4px 0 0; }
.header-actions { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.loading-box { display: flex; align-items: center; justify-content: center; gap: 8px; padding: 40px; color: var(--text-secondary); }
.empty-box { padding: 40px 0; }

/* 统计卡片 */
.stat-row { display: flex; gap: 16px; margin-bottom: 20px; }
.stat-item { background: var(--bg-secondary, #f5f7fa); border-radius: 12px; padding: 16px 24px; display: flex; flex-direction: column; align-items: center; min-width: 100px; }
.stat-value { font-size: 28px; font-weight: 700; color: var(--color-primary, #409eff); }
.stat-label { font-size: 12px; color: var(--text-muted); margin-top: 4px; }

/* VM 卡片 */
.vm-cards { display: flex; flex-direction: column; gap: 16px; }
.vm-card { border-radius: 12px; overflow: hidden; }
.vm-card-header { display: flex; align-items: center; justify-content: space-between; padding-bottom: 12px; margin-bottom: 12px; border-bottom: 1px solid var(--border-color, #ebeef5); flex-wrap: wrap; gap: 8px; }
.vm-info { display: flex; align-items: center; gap: 10px; }
.vm-name { font-size: 16px; font-weight: 700; color: var(--text-heading, #303133); }
.vm-meta { display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--text-muted); }
.meta-divider { color: var(--border-color, #dcdfe6); }

/* 快照树 */
.snap-tree { display: flex; flex-direction: column; }
.snap-tree-item { position: relative; padding-left: 0; }

/* 连接线 */
.tree-connector { position: absolute; left: 0; top: 0; bottom: 0; width: 28px; pointer-events: none; }
.tree-line-v { position: absolute; left: 10px; top: 0; bottom: 50%; width: 1.5px; background: var(--border-color, #dcdfe6); }
.tree-line-h { position: absolute; left: 10px; top: 50%; width: 14px; height: 1.5px; background: var(--border-color, #dcdfe6); }

.snap-node { display: flex; align-items: flex-start; gap: 10px; padding: 10px 12px; border-radius: 8px; transition: background 0.15s; }
.snap-node:hover { background: rgba(64, 158, 255, 0.04); }
.snap-node.is-current { background: rgba(103, 194, 58, 0.06); }
.snap-node.is-root { padding-left: 12px; }

.snap-icon { flex-shrink: 0; width: 28px; height: 28px; display: flex; align-items: center; justify-content: center; border-radius: 50%; background: var(--bg-secondary, #f5f7fa); margin-top: 2px; }
.snap-node.is-current .snap-icon { background: rgba(103, 194, 58, 0.15); }

.snap-content { flex: 1; min-width: 0; }
.snap-title-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.snap-name { font-size: 14px; font-weight: 600; color: var(--text-primary); }
.snap-name.current-name { color: #67c23a; }
.snap-meta-row { display: flex; align-items: center; gap: 12px; margin-top: 4px; flex-wrap: wrap; }
.meta-time { font-size: 12px; color: var(--text-muted); font-family: 'SF Mono', 'Menlo', monospace; }
.meta-time.dim { color: var(--text-muted); opacity: 0.5; }
.meta-desc { font-size: 12px; color: var(--text-secondary); }

/* 表格视图 */
.table-card { border-radius: 16px; }
.sub-text { font-size: 12px; color: var(--text-muted); margin-top: 2px; }
.parent-tag { font-size: 12px; font-family: 'SF Mono', 'Menlo', monospace; background: var(--bg-secondary); padding: 2px 6px; border-radius: 4px; }
.no-parent { font-size: 12px; color: var(--text-muted); }
.vm-name { font-weight: 500; color: var(--text-primary); }

:deep(.el-table) { background: var(--el-card-bg-color); --el-table-bg-color: var(--el-card-bg-color); --el-table-tr-bg-color: var(--el-card-bg-color); --el-table-header-bg-color: var(--el-card-bg-color); --el-table-border-color: var(--border-color); --el-table-text-color: var(--text-primary); --el-table-header-text-color: var(--text-secondary); }
:deep(.el-table::before) { display: none; }
:deep(.el-table th.el-table__cell) { background-color: var(--el-card-bg-color); }
:deep(.el-table--enable-row-hover .el-table__body tr:hover > td) { background-color: rgba(64, 158, 255, 0.05); }
:deep(.el-tag--success) { --el-tag-bg-color: rgba(103, 194, 58, 0.15); --el-tag-text-color: #67c23a; --el-tag-border-color: transparent; }
:deep(.el-tag--info) { --el-tag-bg-color: rgba(144, 147, 153, 0.15); --el-tag-text-color: #909399; --el-tag-border-color: transparent; }
:deep(.el-tag--warning) { --el-tag-bg-color: rgba(230, 162, 60, 0.15); --el-tag-text-color: #e6a23c; --el-tag-border-color: transparent; }
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
</style>
