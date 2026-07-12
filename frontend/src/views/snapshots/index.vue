<template>
  <div class="snapshot-container">
    <!-- 左侧：VM 列表 -->
    <div class="vm-list-panel">
      <div class="panel-header">
        <h3 class="panel-title">{{ t('snapshots.vmList') }}</h3>
        <span class="vm-count">{{ filteredVmList.length }} {{ t('snapshots.units') }}</span>
      </div>
      
      <!-- 筛选栏 -->
      <div class="filter-bar">
        <el-input
          v-model="vmSearch"
          :placeholder="t('snapshots.searchVm')"
          clearable
          prefix-icon="Search"
          size="small"
        />
        <el-select
          v-model="selectedNode"
          :placeholder="t('snapshots.allNodes')"
          clearable
          size="small"
          style="margin-top: 8px"
        >
          <el-option
            v-for="node in nodeList"
            :key="node.name"
            :label="node.name"
            :value="node.name"
            :disabled="!node.hasVms"
          >
            <span>{{ node.name }}</span>
            <span v-if="!node.hasVms" style="color: var(--text-muted); font-size: 12px; margin-left: 8px;">{{ t('snapshots.noVms') }}</span>
          </el-option>
        </el-select>
      </div>
      
      <!-- VM 列表 -->
      <div class="vm-list" v-loading="loading">
        <div
          v-for="vm in paginatedVmList"
          :key="vm.vmId"
          class="vm-item"
          :class="{ active: selectedVmId === vm.vmId }"
          @click="selectVm(vm)"
        >
          <div class="vm-item-info">
            <div class="vm-item-name">{{ vm.vmName }}</div>
            <div class="vm-item-meta">
              <span class="vmid">VMID: {{ vm.vmVmid }}</span>
              <span class="node">{{ vm.nodeName }}</span>
            </div>
          </div>
          <span class="snap-count-tag">{{ vm.snapCount }} {{ t('snapshots.snaps') }}</span>
        </div>
        
        <el-empty v-if="!loading && filteredVmList.length === 0" :description="t('snapshots.noVms')" :image-size="60" />
      </div>
      
      <!-- 分页 -->
      <div class="pagination" v-if="filteredVmList.length > pageSize">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="filteredVmList.length"
          layout="prev, pager, next"
          small
        />
      </div>
    </div>
    
    <!-- 右侧：快照详情 -->
    <div class="snapshot-detail-panel">
      <template v-if="selectedVm">
        <div class="detail-header">
          <div class="detail-title-row">
            <h3 class="detail-title">{{ selectedVm.vmName }}</h3>
            <el-tag size="small" type="info">VMID: {{ selectedVm.vmVmid }}</el-tag>
          </div>
          <div class="detail-meta">
            <span>{{ t('snapshots.node') }}: {{ selectedVm.nodeName }}</span>
            <span class="divider">|</span>
            <span>{{ t('snapshots.cluster') }}: {{ selectedVm.clusterName }}</span>
            <span class="divider">|</span>
            <span>{{ t('snapshots.status') }}: <el-tag :type="selectedVm.vmStatus === 'running' ? 'success' : 'danger'" size="small">{{ selectedVm.vmStatus }}</el-tag></span>
          </div>
        </div>
        
        <!-- 快照统计 -->
        <div class="snapshot-stats">
          <div class="stat-item">
            <span class="stat-value">{{ selectedVm.snapCount }}</span>
            <span class="stat-label">{{ t('snapshots.snapshotCount') }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-value">{{ maxDepth }}</span>
            <span class="stat-label">{{ t('snapshots.maxDepth') }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-value">{{ totalSizeMb ? (totalSizeMb / 1024).toFixed(1) + ' GB' : '-' }}</span>
            <span class="stat-label">{{ t('snapshots.totalSize') }}</span>
          </div>
        </div>
        
        <!-- 快照树 -->
        <div class="snapshot-tree" v-loading="snapshotLoading">
          <div v-if="vmSnapshots.length === 0" class="empty-snap">
            <el-empty :description="t('snapshots.noSnapshots')" :image-size="80" />
          </div>
          <div v-else class="tree-content">
            <div v-for="node in snapshotTree" :key="node.snapid" class="snap-tree-item" :style="{ paddingLeft: node.depth * 28 + 'px' }">
              <!-- 连接线 -->
              <div class="tree-connector" v-if="node.depth > 0">
                <span class="tree-line-v"></span>
                <span class="tree-line-h"></span>
              </div>
              <div class="snap-node" :class="{ 'is-current': node.snapid === 'current', 'is-root': node.depth === 0 }">
                <div class="snap-icon">
                  <el-icon v-if="node.snapid === 'current'" :size="16" style="color: var(--success-color)"><VideoPlay /></el-icon>
                  <el-icon v-else :size="16" style="color: var(--warning-color)"><Camera /></el-icon>
                </div>
                <div class="snap-content">
                  <div class="snap-title-row">
                    <span class="snap-name" :class="{ 'current-name': node.snapid === 'current' }">{{ node.name }}</span>
                    <el-tag v-if="node.snapid === 'current'" type="success" size="small" effect="dark">{{ t('snapshots.current') }}</el-tag>
                    <el-tag v-if="node.snap_type" size="small" type="warning" effect="plain">{{ node.snap_type }}</el-tag>
                    <el-tag v-if="node.ram" size="small" type="info" effect="plain">{{ t('snapshots.saveMemory') }}</el-tag>
                    <el-tag v-if="node.vmstate" size="small" type="info" effect="plain">{{ t('snapshots.saveState') }}</el-tag>
                  </div>
                  <div class="snap-meta-row">
                    <span v-if="node.snap_time" class="meta-time">{{ formatTime(node.snap_time) }}</span>
                    <span v-else class="meta-time dim">-</span>
                    <span v-if="node.size_mb" class="meta-size">{{ (node.size_mb / 1024).toFixed(2) }} GB</span>
                    <span v-if="node.description" class="meta-desc">{{ node.description }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>
      
      <template v-else>
        <div class="no-selection">
          <el-empty :description="t('snapshots.selectVmHint')" :image-size="120" />
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { VideoPlay, Camera } from '@element-plus/icons-vue'
import { getSnapshots } from '@/api/snapshots'
import type { SnapshotInfo } from '@/api/snapshots'
import { getNodes } from '@/api/nodes'
import type { NodeInfo } from '@/api/nodes'
import { useClusterStore } from '@/stores/cluster'

const { t } = useI18n()
const clusterStore = useClusterStore()

// 状态
const loading = ref(false)
const snapshotLoading = ref(false)
const snapshots = ref<SnapshotInfo[]>([])
const nodes = ref<NodeInfo[]>([])
const vmSearch = ref('')
const selectedNode = ref('')
const selectedVmId = ref<number | null>(null)
const currentPage = ref(1)
const pageSize = 15

// VM 分组接口
interface VmGroup {
  vmId: number
  vmVmid: number
  vmName: string
  nodeName: string
  clusterName: string
  vmStatus: string
  snapCount: number
}

// 树节点接口
interface TreeNode extends SnapshotInfo {
  depth: number
  children: TreeNode[]
}

// 加载数据
onMounted(async () => {
  if (!clusterStore.clusterList.length) await clusterStore.fetchClusters()
  loadData()
})

watch(() => clusterStore.currentClusterId, () => {
  loadData()
  selectedVmId.value = null
})

async function loadData() {
  loading.value = true
  try {
    const params: Record<string, any> = {}
    if (clusterStore.currentClusterId) params.cluster_id = clusterStore.currentClusterId
    const [snapshotsData, nodesData] = await Promise.all([
      getSnapshots(params),
      getNodes(params)
    ])
    snapshots.value = snapshotsData
    nodes.value = nodesData
  } catch {} finally { loading.value = false }
}

// VM 列表（去重）
const vmList = computed<VmGroup[]>(() => {
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
        vmStatus: s.vm_status,
        snapCount: 0
      })
    }
    groups.get(key)!.snapCount++
  }
  return Array.from(groups.values()).sort((a, b) => a.vmName.localeCompare(b.vmName))
})

// 有VM的节点集合
const nodesWithVms = computed(() => {
  return new Set(vmList.value.map(v => v.nodeName))
})

// 节点列表（所有节点，标记是否有VM）
const nodeList = computed(() => {
  return nodes.value.map(node => ({
    name: node.node_name,
    hasVms: nodesWithVms.value.has(node.node_name)
  })).sort((a, b) => a.name.localeCompare(b.name))
})

// 筛选后的 VM 列表
const filteredVmList = computed(() => {
  let list = vmList.value
  
  if (selectedNode.value) {
    list = list.filter(v => v.nodeName === selectedNode.value)
  }
  
  if (vmSearch.value) {
    const search = vmSearch.value.toLowerCase()
    list = list.filter(v => 
      v.vmName.toLowerCase().includes(search) || 
      v.vmVmid.toString().includes(search)
    )
  }
  
  return list
})

// 分页后的 VM 列表
const paginatedVmList = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return filteredVmList.value.slice(start, start + pageSize)
})

// 选中的 VM
const selectedVm = computed(() => {
  if (!selectedVmId.value) return null
  return vmList.value.find(v => v.vmId === selectedVmId.value) || null
})

// 选中 VM 的快照
const vmSnapshots = computed(() => {
  if (!selectedVm.value) return []
  return snapshots.value.filter(s => s.vm_id === selectedVm.value!.vmId)
})

// 快照树
const snapshotTree = computed<TreeNode[]>(() => {
  return buildTree(vmSnapshots.value)
})

// 最大深度
const maxDepth = computed(() => {
  let max = 0
  for (const node of snapshotTree.value) {
    if (node.depth > max) max = node.depth
  }
  return max
})

// 总大小
const totalSizeMb = computed(() => {
  let total = 0
  for (const snap of vmSnapshots.value) {
    if (snap.size_mb) total += snap.size_mb
  }
  return total
})

// 选择 VM
function selectVm(vm: VmGroup) {
  selectedVmId.value = vm.vmId
}

// 构建快照树
function buildTree(snaps: SnapshotInfo[]): TreeNode[] {
  const map = new Map<string, TreeNode>()
  const roots: TreeNode[] = []

  for (const s of snaps) {
    map.set(s.snapid, { ...s, depth: 0, children: [] })
  }

  for (const node of map.values()) {
    if (node.parent && map.has(node.parent)) {
      const parent = map.get(node.parent)!
      node.depth = parent.depth + 1
      parent.children.push(node)
    } else {
      roots.push(node)
    }
  }

  // current 放最前，其余按时间降序
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

  // DFS 展平
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

function formatTime(iso: string | null) {
  if (!iso) return '-'
  return new Date(iso).toLocaleString('zh-CN')
}
</script>

<style scoped>
.snapshot-container {
  display: flex;
  gap: 16px;
  height: calc(100vh - 120px);
  max-width: 1600px;
  margin: 0 auto;
}

/* 左侧面板 */
.vm-list-panel {
  width: 320px;
  min-width: 320px;
  background: var(--bg-card);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid var(--border-color);
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 16px 12px;
  border-bottom: 1px solid var(--border-color);
}

.panel-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-heading);
  margin: 0;
}

.vm-count {
  font-size: 12px;
  color: var(--text-muted);
  background: var(--bg-secondary);
  padding: 2px 8px;
  border-radius: 10px;
}

.filter-bar {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color);
}

.vm-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.vm-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  margin-bottom: 4px;
}

.vm-item:hover {
  background: var(--bg-secondary);
}

.vm-item.active {
  background: var(--primary-color);
  opacity: 0.9;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.3);
}

.vm-item.active .vm-item-name,
.vm-item.active .vm-item-meta {
  color: #fff;
}

.vm-item-info {
  flex: 1;
  min-width: 0;
}

.vm-item-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-heading);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.vm-item-meta {
  display: flex;
  gap: 8px;
  margin-top: 4px;
  font-size: 12px;
  color: var(--text-muted);
}

.snap-count-tag {
  flex-shrink: 0;
  font-size: 12px;
  color: var(--text-muted);
  background: var(--bg-secondary);
  padding: 2px 8px;
  border-radius: 10px;
  white-space: nowrap;
}

.pagination {
  padding: 12px 16px;
  border-top: 1px solid var(--border-color);
  display: flex;
  justify-content: center;
}

/* 右侧面板 */
.snapshot-detail-panel {
  flex: 1;
  background: var(--bg-card);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid var(--border-color);
}

.detail-header {
  padding: 20px 24px 16px;
  border-bottom: 1px solid var(--border-color);
}

.detail-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.detail-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-heading);
  margin: 0;
}

.detail-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 13px;
  color: var(--text-secondary);
}

.divider {
  color: var(--border-color);
}

.snapshot-stats {
  display: flex;
  gap: 24px;
  padding: 16px 24px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: var(--primary-color);
}

.stat-label {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 4px;
}

.snapshot-tree {
  flex: 1;
  overflow-y: auto;
  padding: 16px 24px;
}

.empty-snap,
.no-selection {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}

/* 快照树样式 */
.tree-content {
  display: flex;
  flex-direction: column;
}

.snap-tree-item {
  position: relative;
}

.tree-connector {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 28px;
  pointer-events: none;
}

.tree-line-v {
  position: absolute;
  left: 10px;
  top: 0;
  bottom: 50%;
  width: 1.5px;
  background: var(--border-color);
}

.tree-line-h {
  position: absolute;
  left: 10px;
  top: 50%;
  width: 14px;
  height: 1.5px;
  background: var(--border-color);
}

.snap-node {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 8px;
  transition: background 0.15s;
  margin-bottom: 4px;
}

.snap-node:hover {
  background: var(--bg-secondary);
}

.snap-node.is-current {
  background: rgba(103, 194, 58, 0.15);
  border: 1px solid rgba(103, 194, 58, 0.4);
}

.snap-icon {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--bg-secondary);
  margin-top: 2px;
}

.snap-node.is-current .snap-icon {
  background: rgba(103, 194, 58, 0.2);
}

.snap-content {
  flex: 1;
  min-width: 0;
}

.snap-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.snap-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-heading);
}

.snap-name.current-name {
  color: var(--success-color);
}

.snap-meta-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 6px;
  flex-wrap: wrap;
}

.meta-time {
  font-size: 12px;
  color: var(--text-muted);
  font-family: 'SF Mono', 'Menlo', monospace;
}

.meta-time.dim {
  opacity: 0.5;
}

.meta-size {
  font-size: 12px;
  color: var(--primary-color);
  font-weight: 500;
}

.meta-desc {
  font-size: 12px;
  color: var(--text-secondary);
}

/* 响应式 */
@media (max-width: 900px) {
  .snapshot-container {
    flex-direction: column;
    height: auto;
  }
  
  .vm-list-panel {
    width: 100%;
    min-width: unset;
    max-height: 300px;
  }
}
</style>
