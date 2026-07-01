<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">网络拓扑</h2>
        <p class="page-desc">可视化展示 PVE 集群网络架构</p>
      </div>
      <div class="header-actions">
        <el-select v-model="selectedNode" placeholder="全部节点" clearable style="width: 160px">
          <el-option v-for="n in nodeList" :key="n" :label="n" :value="n" />
        </el-select>
        <div class="zoom-controls">
          <el-button-group>
            <el-button @click="zoomOut" size="small">-</el-button>
            <el-button size="small" disabled>{{ Math.round(scale * 100) }}%</el-button>
            <el-button @click="zoomIn" size="small">+</el-button>
          </el-button-group>
        </div>
        <el-button @click="resetView" size="small">重置</el-button>
      </div>
    </div>

    <div class="topology-container" v-loading="loading">
      <div v-if="!loading && !topologyData.length" class="empty-state">
        <el-empty description="暂无网络拓扑数据" />
      </div>
      <div v-else class="topology-canvas" ref="canvasRef">
        <svg :viewBox="currentViewBox" class="topology-svg"
          preserveAspectRatio="xMidYMin meet"
          @mousedown.prevent="onCanvasMouseDown"
          @mousemove="onMouseMove" @mouseup="onMouseUp" @mouseleave="onMouseUp"
          @wheel.prevent="onWheel">
          <!-- 连线 -->
          <g class="connections">
            <line v-for="(conn, idx) in connections" :key="'conn-' + idx"
              :x1="conn.x1" :y1="conn.y1" :x2="conn.x2" :y2="conn.y2"
              :stroke="conn.color" stroke-width="2" stroke-dasharray="5,3" />
          </g>
          <!-- 节点 -->
          <g v-for="(node, nIdx) in nodePositions" :key="'node-' + node.name"
            class="node-group" :class="{ dragging: dragType === 'node' && draggingId === node.name }"
            :transform="`translate(${node.x}, ${node.y})`"
            @mousedown.prevent="onNodeMouseDown($event, node)">
            <rect x="0" y="0" :width="nodeWidth" :height="nodeHeight" rx="12"
              :fill="nodeFill" :stroke="nodeStroke" stroke-width="2" />
            <text :x="nodeWidth / 2" y="24" text-anchor="middle" class="node-label">{{ node.name }}</text>
            <text :x="nodeWidth / 2" y="42" text-anchor="middle" class="node-sub">{{ node.ip || '--' }}</text>
          </g>
          <!-- 接口 -->
          <g v-for="(iface, iIdx) in interfacePositions" :key="'iface-' + iface.id"
            class="iface-group" :class="{ dragging: dragType === 'iface' && draggingId === iface.id }"
            :transform="`translate(${iface.x}, ${iface.y})`"
            @mousedown.prevent="onIfaceMouseDown($event, iface)">
            <rect x="0" y="0" :width="ifaceWidth" :height="ifaceHeight" rx="8"
              :fill="getIfaceFill(iface.type)" :stroke="getIfaceStroke(iface.type)" stroke-width="1.5" />
            <text :x="ifaceWidth / 2" y="18" text-anchor="middle" class="iface-label">{{ iface.name }}</text>
            <text :x="ifaceWidth / 2" y="34" text-anchor="middle" class="iface-type">{{ iface.type }}</text>
            <circle :cx="ifaceWidth - 8" cy="8" r="4" :fill="iface.status === 'up' ? '#67c23a' : '#f56c6c'" />
          </g>
        </svg>
      </div>
    </div>

    <!-- 图例 -->
    <div class="legend-bar">
      <span class="legend-item"><span class="legend-dot" style="background: #409eff"></span>物理接口</span>
      <span class="legend-item"><span class="legend-dot" style="background: #67c23a"></span>网桥 (Bridge)</span>
      <span class="legend-item"><span class="legend-dot" style="background: #e6a23c"></span>Bond 聚合</span>
      <span class="legend-item"><span class="legend-dot" style="background: #8b5cf6"></span>VLAN</span>
      <span class="legend-item"><span class="legend-dot" style="background: #909399"></span>其他</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { getNetworkList, type NetworkInterface } from '@/api/networks'

const loading = ref(true)
const topologyData = ref<NetworkInterface[]>([])
const selectedNode = ref('')
const canvasRef = ref<HTMLElement>()

const nodeWidth = 140
const nodeHeight = 56
const ifaceWidth = 120
const ifaceHeight = 44
const ifaceGapY = 56
const nodeGapY = 200

// 拖动状态
const dragType = ref<'node' | 'iface' | 'canvas' | ''>('')
const draggingId = ref<string | number>('')
const dragOffset = { x: 0, y: 0 }

// 缩放状态
const scale = ref(1)
const minScale = 0.3
const maxScale = 3

// 固定的初始 SVG 尺寸（加载时计算，拖动时不变）
const initialSvgWidth = ref(400)
const initialSvgHeight = ref(200)

const nodeList = computed(() => {
  const set = new Set(topologyData.value.map(n => n.node_name))
  return Array.from(set).sort()
})

const filteredData = computed(() => {
  if (!selectedNode.value) return topologyData.value
  return topologyData.value.filter(n => n.node_name === selectedNode.value)
})

const nodeFill = 'var(--bg-card, #fff)'
const nodeStroke = '#409eff'

interface NodePos { name: string; x: number; y: number; ip: string }
interface IfacePos extends NetworkInterface { x: number; y: number; nodeName: string }

const nodePositions = ref<NodePos[]>([])
const interfacePositions = ref<IfacePos[]>([])

function initPositions() {
  const groups = new Map<string, NetworkInterface[]>()
  filteredData.value.forEach(iface => {
    const list = groups.get(iface.node_name) || []
    list.push(iface)
    groups.set(iface.node_name, list)
  })

  const nodeEntries = Array.from(groups.entries())
  const nodeSpacing = 340 // 每个节点区域的宽度

  // 节点水平排列
  const nodes: NodePos[] = []
  nodeEntries.forEach(([nodeName, ifaces], idx) => {
    const nodeIface = ifaces.find(i => i.type === 'bridge' && i.name === 'vmbr0') || ifaces[0]
    const x = 60 + idx * nodeSpacing
    nodes.push({ name: nodeName, x, y: 40, ip: nodeIface?.address || '' })
  })
  nodePositions.value = nodes

  // 接口垂直排列在节点下方
  const ifaces: IfacePos[] = []
  nodes.forEach(np => {
    const nodeIfaces = groups.get(np.name) || []
    nodeIfaces.forEach((iface, idx) => {
      ifaces.push({ ...iface, x: np.x, y: np.y + nodeHeight + 30 + idx * ifaceGapY })
    })
  })
  interfacePositions.value = ifaces

  // 计算并存储初始尺寸（固定不变）
  initialSvgWidth.value = nodes.length > 0
    ? nodes[nodes.length - 1].x + nodeWidth + 120
    : 400
  initialSvgHeight.value = ifaces.length > 0
    ? Math.max(...ifaces.map(i => i.y)) + ifaceHeight + 60
    : 200
}

const currentViewBox = computed(() => {
  const w = initialSvgWidth.value / scale.value
  const h = initialSvgHeight.value / scale.value
  const x = (initialSvgWidth.value - w) / 2
  const y = (initialSvgHeight.value - h) / 2
  return `${x} ${y} ${w} ${h}`
})

interface Connection { x1: number; y1: number; x2: number; y2: number; color: string }

const connections = computed<Connection[]>(() => {
  const conns: Connection[] = []
  nodePositions.value.forEach(np => {
    const ifaces = interfacePositions.value.filter(i => i.node_name === np.name)
    ifaces.forEach(iface => {
      conns.push({
        x1: np.x + nodeWidth / 2,
        y1: np.y + nodeHeight,
        x2: iface.x + ifaceWidth / 2,
        y2: iface.y,
        color: getIfaceColor(iface.type)
      })
    })
  })
  return conns
})

// 节点拖动
function onNodeMouseDown(e: MouseEvent, node: NodePos) {
  dragType.value = 'node'
  draggingId.value = node.name
  dragOffset.x = e.clientX - node.x
  dragOffset.y = e.clientY - node.y
}

// 接口拖动
function onIfaceMouseDown(e: MouseEvent, iface: IfacePos) {
  dragType.value = 'iface'
  draggingId.value = iface.id
  dragOffset.x = e.clientX - iface.x
  dragOffset.y = e.clientY - iface.y
}

// 画布拖动
function onCanvasMouseDown(e: MouseEvent) {
  // 只在点击空白区域时触发（检查目标是否是 SVG 本身）
  if ((e.target as Element).tagName !== 'svg') return
  dragType.value = 'canvas'
  draggingId.value = 'canvas'
  dragOffset.x = e.clientX
  dragOffset.y = e.clientY
}

function onMouseMove(e: MouseEvent) {
  if (dragType.value === 'canvas') {
    const dx = e.clientX - dragOffset.x
    const dy = e.clientY - dragOffset.y
    // 移动所有节点和接口
    nodePositions.value.forEach(n => { n.x += dx; n.y += dy })
    interfacePositions.value.forEach(i => { i.x += dx; i.y += dy })
    dragOffset.x = e.clientX
    dragOffset.y = e.clientY
  } else if (dragType.value === 'node') {
    const node = nodePositions.value.find(n => n.name === draggingId.value)
    if (!node) return
    node.x = e.clientX - dragOffset.x
    node.y = e.clientY - dragOffset.y
  } else if (dragType.value === 'iface') {
    const iface = interfacePositions.value.find(i => i.id === draggingId.value)
    if (!iface) return
    iface.x = e.clientX - dragOffset.x
    iface.y = e.clientY - dragOffset.y
  }
}

function onMouseUp() {
  dragType.value = ''
  draggingId.value = ''
}

function onWheel(e: WheelEvent) {
  const delta = e.deltaY > 0 ? -0.1 : 0.1
  const newScale = Math.min(Math.max(scale.value + delta, minScale), maxScale)
  scale.value = newScale
}

function zoomIn() {
  scale.value = Math.min(scale.value + 0.1, maxScale)
}

function zoomOut() {
  scale.value = Math.max(scale.value - 0.1, minScale)
}

function resetView() {
  selectedNode.value = ''
  scale.value = 1
  initPositions()
}

function getIfaceColor(type: string): string {
  switch (type) {
    case 'eth': return '#409eff'
    case 'bridge': return '#67c23a'
    case 'bond': return '#e6a23c'
    case 'vlan': return '#8b5cf6'
    default: return '#909399'
  }
}

function getIfaceFill(type: string): string {
  switch (type) {
    case 'eth': return 'rgba(64, 158, 255, 0.1)'
    case 'bridge': return 'rgba(103, 194, 58, 0.1)'
    case 'bond': return 'rgba(230, 162, 60, 0.1)'
    case 'vlan': return 'rgba(139, 92, 246, 0.1)'
    default: return 'rgba(144, 147, 153, 0.1)'
  }
}

function getIfaceStroke(type: string): string {
  switch (type) {
    case 'eth': return '#409eff'
    case 'bridge': return '#67c23a'
    case 'bond': return '#e6a23c'
    case 'vlan': return '#8b5cf6'
    default: return '#909399'
  }
}

onMounted(async () => {
  loading.value = true
  try {
    topologyData.value = await getNetworkList()
    initPositions()
  } catch {} finally {
    loading.value = false
  }
})
</script>

<style scoped>
.page-container { width: 100%; height: 100%; display: flex; flex-direction: column; }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px; flex-wrap: wrap; gap: 12px; }
.page-title { font-size: 24px; font-weight: 700; color: var(--text-heading); margin: 0; }
.page-desc { font-size: 14px; color: var(--text-muted); margin: 4px 0 0; }
.header-actions { display: flex; gap: 8px; align-items: center; }
.zoom-controls { display: flex; align-items: center; }

.topology-container {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  padding: 24px;
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.empty-state { display: flex; align-items: center; justify-content: center; flex: 1; }

.topology-canvas { width: 100%; flex: 1; min-height: 0; }
.topology-svg {
  display: block;
  width: 100%;
  height: 100%;
  user-select: none;
}

.node-label { font-size: 14px; font-weight: 600; fill: var(--text-heading); }
.node-sub { font-size: 11px; fill: var(--text-muted); }
.iface-label { font-size: 12px; font-weight: 500; fill: var(--text-primary); }
.iface-type { font-size: 10px; fill: var(--text-muted); }

.node-group { cursor: grab; }
.node-group:active { cursor: grabbing; }
.node-group.dragging { cursor: grabbing; }
.node-group.dragging rect { stroke-width: 3; filter: brightness(1.05); }
.node-group:hover rect { filter: brightness(1.05); stroke-width: 3; }

.iface-group { cursor: grab; }
.iface-group:active { cursor: grabbing; }
.iface-group.dragging { cursor: grabbing; }
.iface-group.dragging rect { stroke-width: 2.5; filter: brightness(1.1); }
.iface-group:hover rect { filter: brightness(1.1); stroke-width: 2; }

.legend-bar {
  display: flex; gap: 20px; margin-top: 16px; padding: 12px 16px;
  background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 12px;
}
.legend-item { display: flex; align-items: center; gap: 6px; font-size: 13px; color: var(--text-secondary); }
.legend-dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
</style>
