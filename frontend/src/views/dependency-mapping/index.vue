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

    <div class="graph-container" v-loading="loading">
      <!-- 资源选择器 - 浮在图左侧 -->
      <div class="resource-selector-overlay">
        <div class="selector-item">
          <label class="selector-label">{{ t('smartAnalysis.dependencyMapping.resourceType') }}</label>
          <el-select v-model="selectedResourceType" :placeholder="t('smartAnalysis.dependencyMapping.selectResourcePlaceholder')" @change="onResourceTypeChange" style="width: 150px" size="small" clearable>
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
            style="width: 200px"
            size="small"
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
      <div v-if="!loading && !graphData.nodes.length" class="empty-state">
        <el-empty :description="!selectedResourceType || !selectedResourceId ? '请先选择虚拟机/容器' : t('smartAnalysis.dependencyMapping.emptyDesc')" />
      </div>
      <div v-else class="graph-canvas">
        <svg :viewBox="currentViewBox" class="graph-svg"
          preserveAspectRatio="xMidYMin meet"
          @mousedown.prevent="onCanvasMouseDown"
          @mousemove="onMouseMove" @mouseup="onMouseUp" @mouseleave="onMouseUp"
          @wheel.prevent="onWheel">
          <!-- HA 组覆盖层矩形（Phase 3） -->
          <g v-for="rect in haOverlayRects" :key="rect.id" class="ha-overlay">
            <rect :x="rect.x" :y="rect.y" :width="rect.width" :height="rect.height"
              rx="12" fill="rgba(249, 115, 22, 0.04)" stroke="#f97316"
              stroke-width="1.5" stroke-dasharray="8,4" opacity="0.6" />
            <text :x="rect.x + 10" :y="rect.y - 6" class="ha-overlay-label"
              fill="#f97316" font-size="11" font-weight="600">
              {{ rect.name }} ({{ rect.memberCount }})
            </text>
          </g>

          <!-- 节点容器（大区域） -->
          <g v-for="node in renderedNodeContainers" :key="'nc-' + node.id"
            class="node-group" :class="{ dragging: draggingId === node.id }"
            :transform="`translate(${node.x}, ${node.y})`"
            @mousedown.prevent="onNodeMouseDown($event, node)"
            @click="selectNode(node)">
            <rect :width="node.nodeW" :height="node.nodeH" rx="16"
              :fill="getNodeFill(node.type)" :stroke="getNodeStroke(node.type)"
              stroke-width="2" class="node-rect node-container-box"
              filter="url(#node-shadow)" />
            <text :x="node.nodeW / 2" :y="22" text-anchor="middle"
              class="node-label node-container-label">{{ node.name }}</text>
            <line v-if="node.subLabel" :x1="16" :y1="34" :x2="node.nodeW - 16" :y2="34"
              :stroke="getNodeStroke(node.type)" stroke-width="1" opacity="0.3" />
            <text v-if="node.subLabel" :x="node.nodeW / 2" :y="48" text-anchor="middle"
              class="node-sub">{{ node.subLabel }}</text>
            <circle v-if="node.statusDot" :cx="node.nodeW - 14" cy="14" r="5"
              :fill="node.statusDot === 'online' || node.statusDot === 'running' ? '#67c23a' : '#f56c6c'" />
          </g>

          <!-- 连线 -->
          <g class="edges">
            <path v-for="(edge, idx) in renderedEdges" :key="'edge-' + idx"
              :d="edge.path" :stroke="edge.color" stroke-width="2" fill="none"
              :stroke-dasharray="edge.dashed ? '6,3' : ''"
              marker-end="url(#arrowhead)" class="edge-path" />
          </g>

          <!-- 子节点（VM/容器/存储/网络/HA/Ceph/SDN） -->
          <g v-for="node in renderedChildNodes" :key="node.id"
            class="node-group" :class="{ dragging: draggingId === node.id }"
            :transform="`translate(${node.x}, ${node.y})`"
            @mousedown.prevent="onNodeMouseDown($event, node)"
            @click="selectNode(node)">
            <rect :width="node.width" :height="node.height" rx="10"
              :fill="getNodeFill(node.type)" :stroke="getNodeStroke(node.type)"
              stroke-width="2" :class="['node-rect', `node-${node.type}`]"
              filter="url(#node-shadow)" />
            <text :x="node.width / 2" :y="node.height / 2 - 6" text-anchor="middle"
              class="node-label">{{ node.name }}</text>
            <text v-if="node.subLabel" :x="node.width / 2" :y="node.height / 2 + 12"
              text-anchor="middle" class="node-sub">{{ node.subLabel }}</text>
            <circle v-if="node.statusDot" :cx="node.width - 10" cy="10" r="5"
              :fill="node.statusDot === 'online' || node.statusDot === 'running' ? '#67c23a' : '#f56c6c'" />
            <!-- HA 徽章 -->
            <g v-if="node.ha_enabled" transform="translate(6, 5)">
              <rect width="28" height="14" rx="3" fill="#f97316" opacity="0.9" />
              <text x="14" y="11" text-anchor="middle" font-size="8" font-weight="700" fill="#fff">HA</text>
            </g>
          </g>
          <!-- 滤镜定义 -->
          <defs>
            <marker id="arrowhead" markerWidth="12" markerHeight="8" refX="12" refY="4" orient="auto">
              <polygon points="0 0, 12 4, 0 8" fill="var(--text-muted, #909399)" />
            </marker>
            <filter id="node-shadow" x="-10%" y="-10%" width="130%" height="130%">
              <feDropShadow dx="0" dy="4" stdDeviation="6" flood-color="rgba(0,0,0,0.12)" />
            </filter>
            <filter id="edge-glow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="2" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
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
import { getDependencyGraph, type DependencyGraph } from '@/api/dependency'
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
  vm: { width: 170, height: 50 },
  container: { width: 170, height: 50 },
  storage: { width: 170, height: 50 },
  network: { width: 170, height: 50 },
  ceph: { width: 140, height: 50 },
  ha: { width: 130, height: 46 },
  sdn_zone: { width: 130, height: 46 },
  sdn_vnet: { width: 120, height: 42 },
  sdn_subnet: { width: 120, height: 42 },
}

function getNodeSubLabel(node: any): { subLabel: string; statusDot: string } {
  let subLabel = ''
  let statusDot = ''
  if (node.type === 'node') {
    subLabel = `${node.cpu_load ? (node.cpu_load * 100).toFixed(0) + '%' : ''} ${node.ip_address || ''}`
    statusDot = node.status || 'unknown'
  } else if (node.type === 'vm' || node.type === 'container') {
    const baseLabel = `${node.cpu_cores || 0}核 ${node.memory_mb ? (node.memory_mb / 1024).toFixed(0) + 'G' : ''}`
    subLabel = node.ha_enabled ? `${baseLabel} · HA:${node.ha_group}` : baseLabel
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
  return { subLabel, statusDot }
}

// 渲染的节点容器（集群 + 节点大区域）
const renderedNodeContainers = computed(() => {
  const nodes: any[] = []
  graphData.value.nodes.forEach(node => {
    if (node.type !== 'cluster' && node.type !== 'node') return
    if (hiddenTypes.value.has(node.type)) return
    const pos = nodePositions.value.get(node.id)
    if (!pos) return
    const { subLabel, statusDot } = getNodeSubLabel(node)
    const nodeW = (node as any).nodeW || 160
    const nodeH = (node as any).nodeH || 60
    nodes.push({ ...node, x: pos.x, y: pos.y, nodeW, nodeH, subLabel, statusDot })
  })
  return nodes
})

// 渲染的子节点（VM/容器/存储/网络/HA/Ceph/SDN）
const renderedChildNodes = computed(() => {
  const nodes: any[] = []
  graphData.value.nodes.forEach(node => {
    if (node.type === 'cluster' || node.type === 'node') return
    if (hiddenTypes.value.has(node.type)) return
    const pos = nodePositions.value.get(node.id)
    if (!pos) return
    const size = nodeSizes[node.type] || { width: 120, height: 42 }
    const { subLabel, statusDot } = getNodeSubLabel(node)
    nodes.push({ ...node, x: pos.x, y: pos.y, width: size.width, height: size.height, subLabel, statusDot })
  })
  return nodes
})

// 渲染的边
const renderedEdges = computed(() => {
  const edges: any[] = []
  graphData.value.edges.forEach(edge => {
    // 跳过节点到子节点的连线（子节点已在节点容器内部，靠视觉包含体现关系）
    if (edge.type === 'node-storage' || edge.type === 'node-network' ||
        edge.type === 'node-vm' || edge.type === 'node-container') return

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

    // 对于节点容器，使用 nodeW/nodeH
    const sw = sourceNode.type === 'node' ? (sourceNode as any).nodeW || sourceSize.width : sourceSize.width
    const sh = sourceNode.type === 'node' ? (sourceNode as any).nodeH || sourceSize.height : sourceSize.height

    // 判断是否为水平连接（VM/容器 → 网络，目标在源右侧）
    const isHorizontal = (targetPos.x > sourcePos.x + sw / 2 + 20)

    let sx: number, sy: number, tx: number, ty: number, path: string

    if (isHorizontal) {
      // 水平连接：源右侧 → 目标左侧
      sx = sourcePos.x + sw
      sy = sourcePos.y + sourceSize.height / 2
      tx = targetPos.x
      ty = targetPos.y + targetSize.height / 2
      const midX = (sx + tx) / 2
      path = `M${sx},${sy} C${midX},${sy} ${midX},${ty} ${tx},${ty}`
    } else {
      // 垂直连接：源底部 → 目标顶部
      sx = sourcePos.x + sw / 2
      sy = sourcePos.y + sh
      tx = targetPos.x + targetSize.width / 2
      ty = targetPos.y
      const midY = (sy + ty) / 2
      path = `M${sx},${sy} C${sx},${midY} ${tx},${midY} ${tx},${ty}`
    }

    let color = 'var(--text-muted, #909399)'
    let dashed = false

    if (edge.type === 'cluster-node') color = '#409eff'
    else if (edge.type === 'node-vm') color = '#67c23a'
    else if (edge.type === 'node-container') color = '#e6a23c'
    else if (edge.type === 'vm-network' || edge.type === 'container-network') { color = '#8b5cf6'; dashed = true }
    else if (edge.type === 'vm-storage' || edge.type === 'container-storage') { color = '#f56c6c'; dashed = true }
    else if (edge.type === 'cluster-ceph') color = '#06b6d4'
    else if (edge.type === 'node-ha' || edge.type === 'resource-ha' || edge.type === 'ha-resource') { color = '#f97316'; dashed = true }
    else if (edge.type === 'cluster-sdn' || edge.type === 'zone-vnet' || edge.type === 'vnet-subnet') color = '#ec4899'

    edges.push({ path, color, dashed })
  })
  return edges
})

// HA 组覆盖层矩形（Phase 3：跨节点 HA 组视觉标识）
const haOverlayRects = computed(() => {
  const rects: any[] = []
  const haGroups = graphData.value.nodes.filter(n => n.type === 'ha')
  if (!haGroups.length) return rects

  haGroups.forEach(haNode => {
    // 找到该 HA 组的所有成员边
    const memberEdges = graphData.value.edges.filter(e => e.source === haNode.id && e.type === 'ha-resource')
    const memberIds = memberEdges.map(e => e.target)
    if (!memberIds.length) return

    // 计算所有成员的包围盒
    const pad = 20
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity
    memberIds.forEach(id => {
      const pos = nodePositions.value.get(id)
      if (!pos) return
      const memberNode = graphData.value.nodes.find(n => n.id === id)
      const size = memberNode ? (nodeSizes[memberNode.type] || { width: 120, height: 42 }) : { width: 120, height: 42 }
      minX = Math.min(minX, pos.x - pad)
      minY = Math.min(minY, pos.y - pad)
      maxX = Math.max(maxX, pos.x + size.width + pad)
      maxY = Math.max(maxY, pos.y + size.height + pad)
    })

    if (minX === Infinity) return
    rects.push({
      id: `overlay-${haNode.id}`,
      x: minX,
      y: minY,
      width: maxX - minX,
      height: maxY - minY,
      name: `HA: ${haNode.name}`,
      memberCount: memberIds.length,
    })
  })
  return rects
})

const currentViewBox = computed(() => {
  const w = initialSvgWidth.value / scale.value
  const h = initialSvgHeight.value / scale.value
  const x = (initialSvgWidth.value - w) / 2
  const y = (initialSvgHeight.value - h) / 2
  return `${x} ${y} ${w} ${h}`
})

// 自动布局 - 节点内嵌布局
// 子节点相对父节点的偏移量（用于拖动）
const childOffsets = new Map<string, { dx: number; dy: number }>()

function autoLayout() {
  const { nodes } = graphData.value
  if (!nodes.length) {
    nodePositions.value = new Map()
    return
  }
  const positions = new Map<string, { x: number; y: number }>()
  childOffsets.clear()

  const cluster = nodes.find(n => n.type === 'cluster')
  const nodeNodes = nodes.filter(n => n.type === 'node')
  const vmNodes = nodes.filter(n => n.type === 'vm')
  const ctNodes = nodes.filter(n => n.type === 'container')
  const storageNodes = nodes.filter(n => n.type === 'storage')
  const networkNodes = nodes.filter(n => n.type === 'network')
  const haNodes = nodes.filter(n => n.type === 'ha')
  const cephNodes = nodes.filter(n => n.type === 'ceph')
  const sdnNodes = nodes.filter(n => n.type === 'sdn_zone' || n.type === 'sdn_vnet' || n.type === 'sdn_subnet')

  const padding = 28
  const cardW = 170
  const cardH = 52
  const gapX = 16
  const gapY = 16
  const headerH = 42

  // 1. 每个节点作为一个大区域，水平排列
  let nodeStartX = 0
  const nodeStartY = 120
  const nodeGapX = 40

  nodeNodes.forEach((node) => {
    const nodeId = node.id
    const vms = vmNodes.filter(n => n.node_id === node.node_id)
    const cts = ctNodes.filter(n => n.node_id === node.node_id)
    const storages = storageNodes.filter(n => n.node_id === node.node_id)
    const networks = networkNodes.filter(n => n.node_id === node.node_id)

    const centerItems = [...vms, ...cts]
    const hasStorage = storages.length > 0
    const hasNetwork = networks.length > 0

    // 各区域宽度
    const centerW = Math.max(centerItems.length, 1) * (cardW + gapX) - gapX
    const storageW = hasStorage ? storages.length * (cardW + gapX) - gapX : 0
    const networkW = hasNetwork ? networks.length * (cardW + gapX) - gapX : 0

    // 内容区总宽度（如果右侧有网络，加上间距和网络宽度）
    const contentW = centerW + (hasNetwork ? gapX * 2 + networkW : 0)

    // 计算节点区域尺寸
    const nodeW = Math.max(320, contentW + padding * 2, storageW + padding * 2 + 40)
    let nodeH = headerH + padding + cardH + padding + 6
    if (hasStorage) nodeH += cardH + gapY + 8

    const nx = nodeStartX
    const ny = nodeStartY
    positions.set(nodeId, { x: nx, y: ny })

    // 各 Y 坐标
    const contentY = ny + headerH + 10

    // VM/容器在节点内左上区域
    const centerStartX = nx + padding
    centerItems.forEach((item, i) => {
      const ix = centerStartX + i * (cardW + gapX)
      const iy = contentY
      positions.set(item.id, { x: ix, y: iy })
      childOffsets.set(item.id, { dx: ix - nx, dy: iy - ny })
    })

    // 存储在节点内底部（换行）
    let storageContentY = contentY
    if (hasStorage) {
      storageContentY = contentY + cardH + gapY + 10
      const storageStartX = nx + padding
      storages.forEach((item, i) => {
        const ix = storageStartX + i * (cardW + gapX)
        const iy = storageContentY
        positions.set(item.id, { x: ix, y: iy })
        childOffsets.set(item.id, { dx: ix - nx, dy: iy - ny })
      })
    }

    // 网络在节点内右侧（与 VM/容器同行）
    let networkStartX = nx + nodeW - padding - networkW
    if (hasNetwork) {
      networks.forEach((item, i) => {
        const ix = networkStartX + i * (cardW + gapX)
        const iy = contentY
        positions.set(item.id, { x: ix, y: iy })
        childOffsets.set(item.id, { dx: ix - nx, dy: iy - ny })
      })
    }

    // 区域尺寸元数据
    ;(node as any).nodeW = nodeW
    ;(node as any).nodeH = nodeH

    nodeStartX += nodeW + nodeGapX
  })

  // 2. 集群居中于所有节点上方
  if (cluster && nodeNodes.length > 0) {
    const firstPos = positions.get(nodeNodes[0].id)!
    const lastNode = nodeNodes[nodeNodes.length - 1]
    const lastPos = positions.get(lastNode.id)!
    const centerX = (firstPos.x + lastPos.x + (lastNode as any).nodeW) / 2
    positions.set(cluster.id, { x: centerX - 80, y: 20 })
  }

  // 3. HA、Ceph、SDN 在节点区域下方（动态计算 Y）
  const extraItems = [...haNodes, ...cephNodes, ...sdnNodes]
  if (extraItems.length > 0) {
    // 计算所有节点容器的最大底部 Y
    let maxNodeBottom = nodeStartY
    nodeNodes.forEach(n => {
      const np = positions.get(n.id)
      if (np) maxNodeBottom = Math.max(maxNodeBottom, np.y + ((n as any).nodeH || 120))
    })
    const extraY = maxNodeBottom + 60
    const totalW = extraItems.length * (cardW + gapX) - gapX
    let startX = 0
    if (nodeNodes.length > 0) {
      const firstPos = positions.get(nodeNodes[0].id)!
      const lastNode = nodeNodes[nodeNodes.length - 1]
      const lastPos = positions.get(lastNode.id)!
      startX = (firstPos.x + lastPos.x + (lastNode as any).nodeW) / 2 - totalW / 2
    }
    extraItems.forEach((item, i) => {
      positions.set(item.id, { x: startX + i * (cardW + gapX), y: extraY })
    })
  }

  // 4. 计算内容边界，居中所有节点
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity
  positions.forEach((pos, id) => {
    const node = nodes.find(n => n.id === id)
    if (!node) return
    const w = (node.type === 'node' || node.type === 'cluster')
      ? ((node as any).nodeW || 160)
      : (nodeSizes[node.type]?.width || 120)
    const h = (node.type === 'node' || node.type === 'cluster')
      ? ((node as any).nodeH || 60)
      : (nodeSizes[node.type]?.height || 42)
    minX = Math.min(minX, pos.x)
    minY = Math.min(minY, pos.y)
    maxX = Math.max(maxX, pos.x + w)
    maxY = Math.max(maxY, pos.y + h)
  })

  const contentPad = 80
  const svgW = Math.max(1200, maxX - minX + contentPad * 2)
  const svgH = Math.max(800, maxY - minY + contentPad * 2)
  const offsetX = (svgW - (maxX - minX)) / 2 - minX
  const offsetY = (svgH - (maxY - minY)) / 2 - minY

  positions.forEach((pos, id) => {
    positions.set(id, { x: pos.x + offsetX, y: pos.y + offsetY })
  })

  initialSvgWidth.value = svgW
  initialSvgHeight.value = svgH
  nodePositions.value = positions
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
// 拖动中的节点 ID 及其子节点 IDs
const draggingChildren = ref<string[]>([])

// 将屏幕坐标转换为 SVG viewBox 坐标（适配缩放）
function screenToSvg(clientX: number, clientY: number): { x: number; y: number } {
  const svg = document.querySelector('.graph-svg') as SVGSVGElement
  if (!svg) return { x: clientX, y: clientY }
  const rect = svg.getBoundingClientRect()
  const vb = svg.viewBox.baseVal
  return {
    x: (clientX - rect.left) * (vb.width / rect.width) + vb.x,
    y: (clientY - rect.top) * (vb.height / rect.height) + vb.y,
  }
}

function onNodeMouseDown(e: MouseEvent, node: any) {
  const pt = screenToSvg(e.clientX, e.clientY)
  draggingId.value = node.id
  dragOffset.x = pt.x - node.x
  dragOffset.y = pt.y - node.y
  // 找出该节点的所有子节点
  const children: string[] = []
  childOffsets.forEach((_, childId) => {
    const childNode = graphData.value.nodes.find(n => n.id === childId)
    if (childNode && String(childNode.node_id) === String(node.node_id)) {
      children.push(childId)
    }
  })
  draggingChildren.value = children
}

function onCanvasMouseDown(e: MouseEvent) {
  if ((e.target as Element).tagName !== 'svg') return
  draggingId.value = 'canvas'
  const pt = screenToSvg(e.clientX, e.clientY)
  dragOffset.x = pt.x
  dragOffset.y = pt.y
}

function onMouseMove(e: MouseEvent) {
  const pt = screenToSvg(e.clientX, e.clientY)
  if (draggingId.value === 'canvas') {
    const dx = pt.x - dragOffset.x
    const dy = pt.y - dragOffset.y
    const newPositions = new Map(nodePositions.value)
    newPositions.forEach((pos, key) => {
      newPositions.set(key, { x: pos.x + dx, y: pos.y + dy })
    })
    nodePositions.value = newPositions
    dragOffset.x = pt.x
    dragOffset.y = pt.y
  } else if (draggingId.value) {
    const pos = nodePositions.value.get(draggingId.value)
    if (pos) {
      const newX = pt.x - dragOffset.x
      const newY = pt.y - dragOffset.y
      const dx = newX - pos.x
      const dy = newY - pos.y
      const newPositions = new Map(nodePositions.value)
      // 移动父节点
      newPositions.set(draggingId.value, { x: newX, y: newY })
      // 移动子节点
      draggingChildren.value.forEach(childId => {
        const childPos = newPositions.get(childId)
        if (childPos) {
          newPositions.set(childId, { x: childPos.x + dx, y: childPos.y + dy })
        }
      })
      // 子节点边界约束：防止拖出父节点，自动扩充父节点
      enforceChildBounds(newPositions, draggingId.value)
      nodePositions.value = newPositions
    }
  }
}

/** 子节点边界约束：防止内部元素移出父节点，触边时自动扩充 */
function enforceChildBounds(positions: Map<string, { x: number; y: number }>, movedId: string) {
  const nodeSizesLocal = nodeSizes
  const padding = 28
  const headerH = 42

  // 收集所有本次移动的子节点（含被拖节点 + 同组子节点）
  const movedIds = new Set([movedId, ...draggingChildren.value])

  // 找到每个子节点对应的父节点，统一扩充
  const parentExpansions = new Map<string, { right: number; bottom: number }>()

  movedIds.forEach(childId => {
    // 只处理子节点类型（vm/container/storage/network）
    const childNode = graphData.value.nodes.find(n => n.id === childId)
    if (!childNode || childNode.type === 'node' || childNode.type === 'cluster') return

    // 查找父节点
    const parentNode = graphData.value.nodes.find(n => n.type === 'node' && n.node_id === childNode.node_id)
    if (!parentNode) return
    const parentPos = positions.get(parentNode.id)
    if (!parentPos) return
    const childPos = positions.get(childId)
    if (!childPos) return

    const childW = nodeSizesLocal[childNode.type]?.width || 170
    const childH = nodeSizesLocal[childNode.type]?.height || 50
    const parentW = (parentNode as any).nodeW || 320
    const parentH = (parentNode as any).nodeH || 120

    // 右边界溢出 → 需要扩充宽度
    const maxX = parentPos.x + parentW - padding - childW
    const maxY = parentPos.y + parentH - padding - childH
    let needRight = 0
    let needBottom = 0

    if (childPos.x > maxX) {
      needRight = Math.max(needRight, childPos.x + childW + padding - parentPos.x - parentW)
    }
    if (childPos.y > maxY) {
      needBottom = Math.max(needBottom, childPos.y + childH + padding - parentPos.y - parentH)
    }

    if (needRight > 0 || needBottom > 0) {
      const existing = parentExpansions.get(parentNode.id) || { right: 0, bottom: 0 }
      parentExpansions.set(parentNode.id, {
        right: Math.max(existing.right, needRight),
        bottom: Math.max(existing.bottom, needBottom),
      })
    }
  })

  // 执行扩充
  parentExpansions.forEach((expansion, parentId) => {
    const parentNode = graphData.value.nodes.find(n => n.id === parentId)
    if (!parentNode) return
    const parentPos = positions.get(parentId)
    if (!parentPos) return

    ;(parentNode as any).nodeW = ((parentNode as any).nodeW || 320) + Math.ceil(expansion.right)
    ;(parentNode as any).nodeH = ((parentNode as any).nodeH || 120) + Math.ceil(expansion.bottom)
    const parentW = (parentNode as any).nodeW
    const parentH = (parentNode as any).nodeH

    // 重新束缚该父节点下所有子节点位置
    movedIds.forEach(childId => {
      const childNode = graphData.value.nodes.find(n => n.id === childId)
      if (!childNode || childNode.type === 'node' || childNode.type === 'cluster') return
      if (childNode.node_id !== parentNode.node_id) return

      const childPos = positions.get(childId)
      if (!childPos) return
      const childW = nodeSizesLocal[childNode.type]?.width || 170
      const childH = nodeSizesLocal[childNode.type]?.height || 50

      childPos.x = Math.min(childPos.x, parentPos.x + parentW - padding - childW)
      childPos.y = Math.min(childPos.y, parentPos.y + parentH - padding - childH)
    })
  })
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
    if (node.ha_enabled) {
      details['HA'] = `${t('smartAnalysis.dependencyMapping.legendHA')} · ${node.ha_group || '-'}`
    }
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
    details[t('smartAnalysis.dependencyMapping.haGroup')] = node.ha_group || node.name || '-'
    if (node.member_count) details['成员数量'] = String(node.member_count)
    if (node.resource_type) details[t('smartAnalysis.dependencyMapping.type')] = node.resource_type
    if (node.state) details[t('smartAnalysis.dependencyMapping.state')] = node.state
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
  // 切换集群时全量重置 SVG
  scale.value = 1
  selectedNode.value = null
  graphData.value = { nodes: [], edges: [] }
  nodePositions.value = new Map()
  selectedResourceType.value = ''
  selectedResourceId.value = undefined
  await loadResourceLists()
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
  position: relative;
}

/* 资源选择器浮层 */
.resource-selector-overlay {
  position: absolute;
  top: 12px;
  left: 12px;
  z-index: 10;
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: var(--bg-card, #fff);
  border: 1px solid var(--border-color, #e4e7ed);
  border-radius: 10px;
  padding: 10px 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.resource-selector-overlay .selector-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.resource-selector-overlay .selector-label {
  font-size: 12px;
  color: var(--text-secondary, #606266);
  white-space: nowrap;
  min-width: 56px;
  text-align: right;
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
  filter: brightness(1.1);
  stroke-width: 3;
  transition: filter 0.2s, stroke-width 0.2s;
}

/* 边 hover 发光效果 */
.edge-path {
  transition: stroke-width 0.2s, filter 0.2s;
  cursor: pointer;
}

.edge-path:hover {
  stroke-width: 3;
  filter: url(#edge-glow);
}

.node-label {
  font-size: 12px;
  font-weight: 600;
  fill: var(--text-heading, #303133);
}

.node-container-label {
  font-size: 14px;
  font-weight: 700;
}

.node-container-box {
  stroke-dasharray: none;
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

/* HA 覆盖层 */
.ha-overlay-label {
  font-family: inherit;
  user-select: none;
  pointer-events: none;
}
</style>
