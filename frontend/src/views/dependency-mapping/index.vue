<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ t('smartAnalysis.dependencyMapping.title') }}</h2>
        <p class="page-desc">{{ t('smartAnalysis.dependencyMapping.subtitle') }}</p>
      </div>
      <div class="toolbar">
        <div class="toolbar-group">
          <button class="toolbar-btn" @click="zoomOut" :title="t('smartAnalysis.dependencyMapping.zoomOut')">−</button>
          <span class="toolbar-zoom-val">{{ Math.round(scale * 100) }}%</span>
          <button class="toolbar-btn" @click="zoomIn" :title="t('smartAnalysis.dependencyMapping.zoomIn')">+</button>
        </div>
        <span class="toolbar-divider"></span>
        <div class="toolbar-group">
          <button class="toolbar-btn-text" @click="resetView">{{ t('smartAnalysis.dependencyMapping.reset') }}</button>
        </div>
      </div>
    </div>

    <!-- 资源选择器 -->
    <div class="resource-selector">
      <div class="selector-row">
        <div class="selector-item">
          <label class="selector-label">{{ t('smartAnalysis.dependencyMapping.resourceType') }}</label>
          <el-select v-model="selectedResourceType" :placeholder="t('smartAnalysis.dependencyMapping.selectResourcePlaceholder')" @change="onResourceTypeChange" style="width: 160px" clearable>
            <el-option :label="t('smartAnalysis.dependencyMapping.legendVM')" value="vm" />
            <el-option :label="t('smartAnalysis.dependencyMapping.legendContainer')" value="container" />
          </el-select>
        </div>
        <div class="selector-item" v-if="selectedResourceType">
          <label class="selector-label">{{ t('smartAnalysis.dependencyMapping.selectResource') }}</label>
          <el-select
            v-model="selectedResourceId"
            :placeholder="t('smartAnalysis.dependencyMapping.selectResourcePlaceholder')"
            filterable
            clearable
            @change="onResourceChange"
            style="width: 240px"
          >
            <el-option
              v-for="item in resourceOptions"
              :key="item.id"
              :label="`${item.name} (${item.vmid})`"
              :value="item.id"
            />
          </el-select>
        </div>
      </div>
    </div>

    <div class="graph-container" v-loading="loading">
      <div v-if="!loading && !graphData.nodes.length" class="empty-state">
        <el-empty :description="!selectedResourceType || !selectedResourceId ? '请先选择虚拟机/容器' : t('smartAnalysis.dependencyMapping.emptyDesc')" />
      </div>
      <div v-else class="graph-canvas">
        <svg :viewBox="currentViewBox" class="graph-svg"
          preserveAspectRatio="xMidYMin meet"
          @mousedown.prevent="onCanvasMouseDown"
          @mousemove="onMouseMove" @mouseup="onMouseUp" @mouseleave="onMouseUp"
          @wheel.prevent="onWheel">
          <!-- 连线 -->
          <g class="edges">
            <path v-for="(edge, idx) in renderedEdges" :key="'edge-' + idx"
              :d="edge.path" :stroke="edge.color" stroke-width="2" fill="none"
              :stroke-dasharray="edge.dashed ? '6,3' : ''"
              marker-end="url(#arrowhead)" />
          </g>
          <!-- 节点 -->
          <g v-for="node in renderedNodes" :key="node.id"
            class="node-group" :class="{ dragging: draggingId === node.id }"
            :transform="`translate(${node.x}, ${node.y})`"
            @mousedown.prevent="onNodeMouseDown($event, node)"
            @click="selectNode(node)">
            <rect :width="node.width" :height="node.height" rx="10"
              :fill="getNodeFill(node.type)" :stroke="getNodeStroke(node.type)"
              stroke-width="2" :class="['node-rect', `node-${node.type}`]" />
            <text :x="node.width / 2" :y="node.height / 2 - 6" text-anchor="middle"
              class="node-label">{{ node.name }}</text>
            <text v-if="node.subLabel" :x="node.width / 2" :y="node.height / 2 + 12"
              text-anchor="middle" class="node-sub">{{ node.subLabel }}</text>
            <circle v-if="node.statusDot" :cx="node.width - 10" cy="10" r="5"
              :fill="node.statusDot === 'online' || node.statusDot === 'running' ? '#67c23a' : '#f56c6c'" />
          </g>
          <!-- 箭头标记 -->
          <defs>
            <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="10" refY="3.5" orient="auto">
              <polygon points="0 0, 10 3.5, 0 7" fill="var(--text-muted, #909399)" />
            </marker>
          </defs>
        </svg>
      </div>
    </div>

    <!-- 图例 -->
    <div class="legend-bar">
      <span v-for="item in legendItems" :key="item.type"
        class="legend-item" :class="{ 'is-hidden': hiddenTypes.has(item.type) }"
        @click="toggleType(item.type)">
        <span class="legend-dot" :style="{ background: item.color }"></span>{{ item.label }}
      </span>
    </div>

    <!-- 详情面板 -->
    <transition name="slide">
      <div v-if="selectedNode" class="detail-panel">
        <div class="detail-header">
          <h3>{{ selectedNode.name }}</h3>
          <button class="detail-close" @click="selectedNode = null">×</button>
        </div>
        <div class="detail-body">
          <div class="detail-row" v-for="(value, key) in selectedNode.details" :key="key">
            <span class="detail-label">{{ key }}</span>
            <span class="detail-value">{{ value }}</span>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { getDependencyGraph, type DependencyNode, type DependencyGraph } from '@/api/dependency'
import { useClusterStore } from '@/stores/cluster'
import { getVMs, type VMInfo } from '@/api/vms'
import { getContainers, type ContainerInfo } from '@/api/containers'

const { t } = useI18n()
const clusterStore = useClusterStore()

const loading = ref(false)
const graphData = ref<DependencyGraph>({ nodes: [], edges: [] })
const scale = ref(1)
const minScale = 0.3
const maxScale = 3
const hiddenTypes = ref(new Set<string>())
const selectedNode = ref<any>(null)

// 资源选择状态
const selectedResourceType = ref<'all' | 'vm' | 'container' | ''>('')
const selectedResourceId = ref<number | undefined>(undefined)
const vmList = ref<VMInfo[]>([])
const containerList = ref<ContainerInfo[]>([])

// 拖动状态
const draggingId = ref('')
const dragOffset = { x: 0, y: 0 }

// 节点位置
const nodePositions = ref<Map<string, { x: number; y: number }>>(new Map())

// 初始 SVG 尺寸
const initialSvgWidth = ref(1200)
const initialSvgHeight = ref(800)

// 资源选项
const resourceOptions = computed(() => {
  if (selectedResourceType.value === 'vm') {
    return vmList.value.map(vm => ({
      id: vm.id,
      name: vm.name,
      vmid: vm.vmid
    }))
  } else if (selectedResourceType.value === 'container') {
    return containerList.value.map(ct => ({
      id: ct.id,
      name: ct.name,
      vmid: ct.vmid
    }))
  }
  return []
})

// 图例
const legendItems = computed(() => [
  { type: 'cluster', label: t('smartAnalysis.dependencyMapping.legendCluster'), color: '#4f46e5' },
  { type: 'node', label: t('smartAnalysis.dependencyMapping.legendNode'), color: '#409eff' },
  { type: 'vm', label: t('smartAnalysis.dependencyMapping.legendVM'), color: '#67c23a' },
  { type: 'container', label: t('smartAnalysis.dependencyMapping.legendContainer'), color: '#e6a23c' },
  { type: 'storage', label: t('smartAnalysis.dependencyMapping.legendStorage'), color: '#f56c6c' },
  { type: 'network', label: t('smartAnalysis.dependencyMapping.legendNetwork'), color: '#8b5cf6' },
  { type: 'ceph', label: t('smartAnalysis.dependencyMapping.legendCeph'), color: '#06b6d4' },
  { type: 'ha', label: t('smartAnalysis.dependencyMapping.legendHA'), color: '#f97316' },
  { type: 'sdn_zone', label: t('smartAnalysis.dependencyMapping.legendSDN'), color: '#ec4899' },
])

function toggleType(type: string) {
  const s = new Set(hiddenTypes.value)
  if (s.has(type)) s.delete(type); else s.add(type)
  hiddenTypes.value = s
}

// 节点尺寸
const nodeSizes: Record<string, { width: number; height: number }> = {
  cluster: { width: 160, height: 60 },
  node: { width: 150, height: 56 },
  vm: { width: 140, height: 50 },
  container: { width: 140, height: 50 },
  storage: { width: 130, height: 46 },
  network: { width: 130, height: 46 },
  ceph: { width: 140, height: 50 },
  ha: { width: 130, height: 46 },
  sdn_zone: { width: 130, height: 46 },
  sdn_vnet: { width: 120, height: 42 },
  sdn_subnet: { width: 120, height: 42 },
}

// 渲染的节点
const renderedNodes = computed(() => {
  const nodes: any[] = []
  graphData.value.nodes.forEach(node => {
    if (hiddenTypes.value.has(node.type)) return
    const pos = nodePositions.value.get(node.id)
    if (!pos) return
    const size = nodeSizes[node.type] || { width: 120, height: 42 }
    let subLabel = ''
    let statusDot = ''

    if (node.type === 'node') {
      subLabel = `${node.cpu_load ? (node.cpu_load * 100).toFixed(0) + '%' : ''} ${node.ip_address || ''}`
      statusDot = node.status || 'unknown'
    } else if (node.type === 'vm' || node.type === 'container') {
      subLabel = `${node.cpu_cores || 0}核 ${node.memory_mb ? (node.memory_mb / 1024).toFixed(0) + 'G' : ''}`
      statusDot = node.status || 'unknown'
    } else if (node.type === 'storage') {
      subLabel = `${node.total_gb || 0}GB ${node.storage_type || ''}`
    } else if (node.type === 'network') {
      subLabel = `${node.net_type || ''} ${node.address || ''}`
    } else if (node.type === 'ceph') {
      subLabel = `${node.health || ''} ${node.total_osds || 0} OSD`
      statusDot = node.health === 'HEALTH_OK' ? 'online' : 'offline'
    } else if (node.type === 'ha') {
      subLabel = `${node.state || ''} ${node.ha_group || ''}`
    }

    nodes.push({
      ...node,
      x: pos.x,
      y: pos.y,
      width: size.width,
      height: size.height,
      subLabel,
      statusDot,
    })
  })
  return nodes
})

// 渲染的边
const renderedEdges = computed(() => {
  const edges: any[] = []
  graphData.value.edges.forEach(edge => {
    const sourcePos = nodePositions.value.get(edge.source)
    const targetPos = nodePositions.value.get(edge.target)
    if (!sourcePos || !targetPos) return

    // 检查源和目标节点是否被隐藏
    const sourceNode = graphData.value.nodes.find(n => n.id === edge.source)
    const targetNode = graphData.value.nodes.find(n => n.id === edge.target)
    if (!sourceNode || !targetNode) return
    if (hiddenTypes.value.has(sourceNode.type) || hiddenTypes.value.has(targetNode.type)) return

    const sourceSize = nodeSizes[sourceNode.type] || { width: 120, height: 42 }
    const targetSize = nodeSizes[targetNode.type] || { width: 120, height: 42 }

    const sx = sourcePos.x + sourceSize.width / 2
    const sy = sourcePos.y + sourceSize.height
    const tx = targetPos.x + targetSize.width / 2
    const ty = targetPos.y

    const midY = (sy + ty) / 2
    const path = `M${sx},${sy} C${sx},${midY} ${tx},${midY} ${tx},${ty}`

    let color = 'var(--text-muted, #909399)'
    let dashed = false

    if (edge.type === 'cluster-node') color = '#409eff'
    else if (edge.type === 'node-vm') color = '#67c23a'
    else if (edge.type === 'node-container') color = '#e6a23c'
    else if (edge.type === 'node-storage') color = '#f56c6c'
    else if (edge.type === 'node-network') color = '#8b5cf6'
    else if (edge.type === 'vm-network' || edge.type === 'container-network') { color = '#8b5cf6'; dashed = true }
    else if (edge.type === 'cluster-ceph') color = '#06b6d4'
    else if (edge.type === 'node-ha' || edge.type === 'resource-ha') color = '#f97316'
    else if (edge.type === 'cluster-sdn' || edge.type === 'zone-vnet' || edge.type === 'vnet-subnet') color = '#ec4899'

    edges.push({ path, color, dashed })
  })
  return edges
})

const currentViewBox = computed(() => {
  const w = initialSvgWidth.value / scale.value
  const h = initialSvgHeight.value / scale.value
  const x = (initialSvgWidth.value - w) / 2
  const y = (initialSvgHeight.value - h) / 2
  return `${x} ${y} ${w} ${h}`
})

// 自动布局
function autoLayout() {
  const positions = new Map<string, { x: number; y: number }>()
  const { nodes, edges } = graphData.value

  if (!nodes.length) {
    nodePositions.value = positions
    return
  }

  // 1. 构建邻接表（用 edges 自动推导父子关系）
  const children = new Map<string, string[]>()
  const parents = new Map<string, string>()
  const nodeMap = new Map(nodes.map(n => [n.id, n]))

  edges.forEach(e => {
    if (!children.has(e.source)) children.set(e.source, [])
    children.get(e.source)!.push(e.target)
    parents.set(e.target, e.source)
  })

  // 2. 找根节点（没有父节点的）
  const roots = nodes.filter(n => !parents.has(n.id))

  // 3. BFS 分层
  const layers: string[][] = []
  let frontier = roots.map(n => n.id)
  const visited = new Set<string>()

  while (frontier.length) {
    layers.push(frontier)
    frontier.forEach(id => visited.add(id))
    const next: string[] = []
    frontier.forEach(id => {
      (children.get(id) || []).forEach(cid => {
        if (!visited.has(cid)) next.push(cid)
      })
    })
    // 去重
    frontier = [...new Set(next)]
  }

  // 4. 每层水平居中布局
  const gapY = 140
  const gapX = 170
  const baseY = 40

  layers.forEach((layer, layerIdx) => {
    const totalWidth = layer.length * gapX
    const startX = (initialSvgWidth.value - totalWidth) / 2 + gapX / 2
    layer.forEach((id, i) => {
      positions.set(id, { x: startX + i * gapX, y: baseY + layerIdx * gapY })
    })
  })

  nodePositions.value = positions

  // 动态计算 SVG 尺寸
  let maxX = 0, maxY = 0
  positions.forEach(pos => {
    maxX = Math.max(maxX, pos.x + 200)
    maxY = Math.max(maxY, pos.y + 100)
  })
  initialSvgWidth.value = Math.max(1200, maxX + 100)
  initialSvgHeight.value = Math.max(800, maxY + 100)
}

// 节点颜色
function getNodeFill(type: string): string {
  const colors: Record<string, string> = {
    cluster: 'rgba(79, 70, 229, 0.1)',
    node: 'rgba(64, 158, 255, 0.1)',
    vm: 'rgba(103, 194, 58, 0.1)',
    container: 'rgba(230, 162, 60, 0.1)',
    storage: 'rgba(245, 108, 108, 0.1)',
    network: 'rgba(139, 92, 246, 0.1)',
    ceph: 'rgba(6, 182, 212, 0.1)',
    ha: 'rgba(249, 115, 22, 0.1)',
    sdn_zone: 'rgba(236, 72, 153, 0.1)',
    sdn_vnet: 'rgba(236, 72, 153, 0.08)',
    sdn_subnet: 'rgba(236, 72, 153, 0.06)',
  }
  return colors[type] || 'rgba(144, 147, 153, 0.1)'
}

function getNodeStroke(type: string): string {
  const colors: Record<string, string> = {
    cluster: '#4f46e5',
    node: '#409eff',
    vm: '#67c23a',
    container: '#e6a23c',
    storage: '#f56c6c',
    network: '#8b5cf6',
    ceph: '#06b6d4',
    ha: '#f97316',
    sdn_zone: '#ec4899',
    sdn_vnet: '#ec4899',
    sdn_subnet: '#ec4899',
  }
  return colors[type] || '#909399'
}

// 拖动
function onNodeMouseDown(e: MouseEvent, node: any) {
  draggingId.value = node.id
  dragOffset.x = e.clientX - node.x
  dragOffset.y = e.clientY - node.y
}

function onCanvasMouseDown(e: MouseEvent) {
  if ((e.target as Element).tagName !== 'svg') return
  draggingId.value = 'canvas'
  dragOffset.x = e.clientX
  dragOffset.y = e.clientY
}

function onMouseMove(e: MouseEvent) {
  if (draggingId.value === 'canvas') {
    const dx = e.clientX - dragOffset.x
    const dy = e.clientY - dragOffset.y
    const newPositions = new Map(nodePositions.value)
    newPositions.forEach((pos, key) => {
      newPositions.set(key, { x: pos.x + dx, y: pos.y + dy })
    })
    nodePositions.value = newPositions
    dragOffset.x = e.clientX
    dragOffset.y = e.clientY
  } else if (draggingId.value) {
    const pos = nodePositions.value.get(draggingId.value)
    if (pos) {
      const newPositions = new Map(nodePositions.value)
      newPositions.set(draggingId.value, {
        x: e.clientX - dragOffset.x,
        y: e.clientY - dragOffset.y,
      })
      nodePositions.value = newPositions
    }
  }
}

function onMouseUp() {
  draggingId.value = ''
}

function onWheel(e: WheelEvent) {
  const delta = e.deltaY > 0 ? -0.1 : 0.1
  scale.value = Math.min(Math.max(scale.value + delta, minScale), maxScale)
}

function zoomIn() {
  scale.value = Math.min(scale.value + 0.1, maxScale)
}

function zoomOut() {
  scale.value = Math.max(scale.value - 0.1, minScale)
}

function resetView() {
  scale.value = 1
  autoLayout()
}

function selectNode(node: any) {
  const details: Record<string, string> = {}
  if (node.type === 'node') {
    details[t('smartAnalysis.dependencyMapping.cpuLoad')] = node.cpu_load ? `${(node.cpu_load * 100).toFixed(1)}%` : '-'
    details[t('smartAnalysis.dependencyMapping.memory')] = node.memory_usage_pct ? `${node.memory_usage_pct.toFixed(1)}%` : '-'
    details[t('smartAnalysis.dependencyMapping.ip')] = node.ip_address || '-'
    details[t('smartAnalysis.dependencyMapping.status')] = node.status || '-'
  } else if (node.type === 'vm' || node.type === 'container') {
    details[t('smartAnalysis.dependencyMapping.vmid')] = String(node.vmid || '-')
    details[t('smartAnalysis.dependencyMapping.cpuCores')] = String(node.cpu_cores || '-')
    details[t('smartAnalysis.dependencyMapping.memory')] = node.memory_mb ? `${(node.memory_mb / 1024).toFixed(1)} GB` : '-'
    details[t('smartAnalysis.dependencyMapping.status')] = node.status || '-'
  } else if (node.type === 'storage') {
    details[t('smartAnalysis.dependencyMapping.type')] = node.storage_type || '-'
    details[t('smartAnalysis.dependencyMapping.totalCapacity')] = node.total_gb ? `${node.total_gb} GB` : '-'
    details[t('smartAnalysis.dependencyMapping.used')] = node.used_gb ? `${node.used_gb} GB` : '-'
    details[t('smartAnalysis.dependencyMapping.shared')] = node.shared ? t('smartAnalysis.dependencyMapping.yes') : t('smartAnalysis.dependencyMapping.no')
  } else if (node.type === 'network') {
    details[t('smartAnalysis.dependencyMapping.type')] = node.net_type || '-'
    details[t('smartAnalysis.dependencyMapping.address')] = node.address || '-'
    details[t('smartAnalysis.dependencyMapping.active')] = node.active ? t('smartAnalysis.dependencyMapping.yes') : t('smartAnalysis.dependencyMapping.no')
  } else if (node.type === 'ceph') {
    details[t('smartAnalysis.dependencyMapping.health')] = node.health || '-'
    details[t('smartAnalysis.dependencyMapping.osdCount')] = String(node.total_osds || '-')
    details[t('smartAnalysis.dependencyMapping.onlineOsd')] = String(node.up_osds || '-')
  } else if (node.type === 'ha') {
    details[t('smartAnalysis.dependencyMapping.type')] = node.resource_type || '-'
    details[t('smartAnalysis.dependencyMapping.state')] = node.state || '-'
    details[t('smartAnalysis.dependencyMapping.haGroup')] = node.ha_group || '-'
  }

  selectedNode.value = {
    name: node.name,
    type: node.type,
    details,
  }
}

// 资源类型变化
function onResourceTypeChange() {
  selectedResourceId.value = undefined
  if (!selectedResourceType.value) {
    // 清空选择时，清空图形数据
    graphData.value = { nodes: [], edges: [] }
    nodePositions.value = new Map()
    return
  }
  loadData()
}

// 资源选择变化
function onResourceChange() {
  if (!selectedResourceId.value) {
    // 清空选择时，清空图形数据
    graphData.value = { nodes: [], edges: [] }
    nodePositions.value = new Map()
    return
  }
  loadData()
}

// 加载 VM/容器列表
async function loadResourceLists() {
  const clusterId = clusterStore.currentClusterId
  if (!clusterId) return

  try {
    const [vms, containers] = await Promise.all([
      getVMs({ cluster_id: clusterId }),
      getContainers({ cluster_id: clusterId })
    ])
    vmList.value = vms
    containerList.value = containers
  } catch (e) {
    console.error('Failed to load resource lists:', e)
  }
}

// 加载依赖图数据
async function loadData() {
  // 如果没有选择资源类型，不加载数据
  if (!selectedResourceType.value) {
    graphData.value = { nodes: [], edges: [] }
    nodePositions.value = new Map()
    return
  }

  // 如果选择了资源类型但没有选择具体资源，不加载数据
  if (selectedResourceType.value && !selectedResourceId.value) {
    graphData.value = { nodes: [], edges: [] }
    nodePositions.value = new Map()
    return
  }

  loading.value = true
  try {
    if (!clusterStore.clusterList.length) await clusterStore.fetchClusters()
    const params: any = {}
    if (clusterStore.currentClusterId) {
      params.cluster_id = clusterStore.currentClusterId
    }
    params.resource_type = selectedResourceType.value
    params.resource_id = selectedResourceId.value
    graphData.value = await getDependencyGraph(params)
    autoLayout()
  } catch (e) {
    console.error('Failed to load dependency graph:', e)
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await loadResourceLists()
  // 初始状态为空，不加载数据
})

watch(() => clusterStore.currentClusterId, async () => {
  await loadResourceLists()
  // 如果已选择资源类型和具体资源，才加载数据
  if (selectedResourceType.value && selectedResourceId.value) {
    await loadData()
  }
})
</script>

<style scoped>
.page-container {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  position: relative;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 12px;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-heading);
  margin: 0;
}

.page-desc {
  font-size: 14px;
  color: var(--text-muted);
  margin: 4px 0 0;
}

/* 资源选择器 */
.resource-selector {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
}

.selector-row {
  display: flex;
  align-items: center;
  gap: 24px;
  flex-wrap: wrap;
}

.selector-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.selector-label {
  font-size: 14px;
  color: var(--text-secondary);
  white-space: nowrap;
}

/* 工具栏 */
.toolbar {
  display: flex;
  align-items: center;
  gap: 0;
  background: var(--bg-secondary, #f5f7fa);
  border: 1px solid var(--border-color, #e4e7ed);
  border-radius: 8px;
  padding: 4px 8px;
  height: 36px;
}

.toolbar-group {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 0 6px;
}

.toolbar-divider {
  width: 1px;
  height: 18px;
  background: var(--border-color, #dcdfe6);
  flex-shrink: 0;
}

.toolbar-btn {
  width: 26px;
  height: 26px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--border-color, #dcdfe6);
  border-radius: 6px;
  background: var(--bg-card, #fff);
  color: var(--text-primary, #303133);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.15s;
  line-height: 1;
}

.toolbar-btn:hover {
  border-color: #409eff;
  color: #409eff;
  background: rgba(64, 158, 255, 0.06);
}

.toolbar-btn:active {
  transform: scale(0.92);
}

.toolbar-zoom-val {
  font-size: 12px;
  color: var(--text-muted, #909399);
  min-width: 36px;
  text-align: center;
  font-variant-numeric: tabular-nums;
  user-select: none;
}

.toolbar-btn-text {
  height: 26px;
  padding: 0 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--border-color, #dcdfe6);
  border-radius: 6px;
  background: var(--bg-card, #fff);
  color: var(--text-secondary, #606266);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
}

.toolbar-btn-text:hover {
  border-color: #409eff;
  color: #409eff;
  background: rgba(64, 158, 255, 0.06);
}

.toolbar-btn-text:active {
  transform: scale(0.92);
}

/* 图形容器 */
.graph-container {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1;
}

.graph-canvas {
  width: 100%;
  flex: 1;
  min-height: 0;
}

.graph-svg {
  display: block;
  width: 100%;
  height: 100%;
  user-select: none;
}

/* 节点样式 */
.node-group {
  cursor: grab;
}

.node-group:active {
  cursor: grabbing;
}

.node-group.dragging {
  cursor: grabbing;
}

.node-group.dragging rect {
  stroke-width: 3;
  filter: brightness(1.05);
}

.node-group:hover rect {
  filter: brightness(1.05);
  stroke-width: 3;
}

.node-label {
  font-size: 12px;
  font-weight: 600;
  fill: var(--text-heading, #303133);
}

.node-sub {
  font-size: 10px;
  fill: var(--text-muted, #909399);
}

/* 图例 */
.legend-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 16px;
  padding: 8px 14px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  flex-wrap: wrap;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  color: var(--text-secondary);
  padding: 4px 10px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  user-select: none;
  border: 1px solid transparent;
}

.legend-item:hover {
  background: rgba(64, 158, 255, 0.06);
}

.legend-item.is-hidden {
  opacity: 0.4;
}

.legend-item.is-hidden .legend-dot {
  background: #c0c4cc !important;
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
  position: relative;
  transition: all 0.2s;
}

/* 详情面板 */
.detail-panel {
  position: absolute;
  right: 20px;
  top: 80px;
  width: 300px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  z-index: 100;
}

.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  border-bottom: 1px solid var(--border-color);
}

.detail-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-heading);
}

.detail-close {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  color: var(--text-muted);
  font-size: 18px;
  cursor: pointer;
  border-radius: 6px;
  transition: all 0.2s;
}

.detail-close:hover {
  background: rgba(245, 108, 108, 0.1);
  color: #f56c6c;
}

.detail-body {
  padding: 16px;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px dashed var(--border-color);
}

.detail-row:last-child {
  border-bottom: none;
}

.detail-label {
  font-size: 13px;
  color: var(--text-muted);
}

.detail-value {
  font-size: 13px;
  color: var(--text-primary);
  font-weight: 500;
}

/* 过渡动画 */
.slide-enter-active,
.slide-leave-active {
  transition: all 0.3s ease;
}

.slide-enter-from,
.slide-leave-to {
  transform: translateX(20px);
  opacity: 0;
}
</style>
