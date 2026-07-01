<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">网络拓扑</h2>
        <p class="page-desc">可视化展示 PVE 集群网络架构</p>
      </div>
      <div class="toolbar">
        <div class="toolbar-group">
          <el-select v-model="selectedCluster" placeholder="选择集群" size="small" style="width: 180px">
            <el-option v-for="c in clusterList" :key="c" :label="c" :value="c" />
          </el-select>
        </div>
        <span class="toolbar-divider"></span>
        <div class="toolbar-group">
          <button class="toolbar-btn" @click="zoomOut" title="缩小">−</button>
          <span class="toolbar-zoom-val">{{ Math.round(scale * 100) }}%</span>
          <button class="toolbar-btn" @click="zoomIn" title="放大">+</button>
        </div>
        <span class="toolbar-divider"></span>
        <div class="toolbar-group">
          <button class="toolbar-btn-text" @click="resetView">重置</button>
        </div>
      </div>
    </div>

    <div class="topology-container" v-loading="loading">
      <div v-if="!loading && !topologyData.length" class="empty-state">
        <el-empty description="暂无网络拓扑数据" />
      </div>
      <div v-else class="topology-canvas">
        <svg :viewBox="currentViewBox" class="topology-svg"
          preserveAspectRatio="xMidYMin meet"
          @mousedown.prevent="onCanvasMouseDown"
          @mousemove="onMouseMove" @mouseup="onMouseUp" @mouseleave="onMouseUp"
          @wheel.prevent="onWheel">
          <!-- 网络段色带 -->
          <g class="segment-bands">
            <g v-for="seg in networkSegments" :key="'seg-' + seg.cidr"
              :transform="`translate(0, ${segmentOffsets[seg.cidr] || 0})`"
              style="cursor: grab"
              @mousedown.prevent="onSegmentMouseDown($event, seg.cidr)">
              <rect :x="seg.bounds.x" :y="seg.bounds.y"
                :width="seg.bounds.width" :height="seg.bounds.height"
                :fill="seg.fillColor" :stroke="seg.strokeColor"
                stroke-width="1" rx="10" stroke-dasharray="8,4" />
            </g>
          </g>
          <!-- 连线 -->
          <g class="connections">
            <line v-for="(conn, idx) in connections" :key="'conn-' + idx"
              :x1="conn.x1" :y1="conn.y1" :x2="conn.x2" :y2="conn.y2"
              :stroke="conn.color" stroke-width="2" stroke-dasharray="5,3" />
          </g>
          <!-- 节点 -->
          <g v-for="node in nodePositions" :key="'node-' + node.name"
            class="node-group" :class="{ dragging: dragType === 'node' && draggingId === node.name }"
            :transform="`translate(${node.x}, ${node.y})`"
            @mousedown.prevent="onNodeMouseDown($event, node)">
            <rect x="0" y="0" :width="nodeWidth" :height="nodeHeight" rx="12"
              :fill="nodeFill" :stroke="nodeStroke" stroke-width="2" />
            <text :x="nodeWidth / 2" y="24" text-anchor="middle" class="node-label">{{ node.name }}</text>
            <text :x="nodeWidth / 2" y="42" text-anchor="middle" class="node-sub">{{ node.ifaceCount }} 个接口</text>
          </g>
          <!-- 接口 -->
          <g v-for="iface in interfacePositions" :key="'iface-' + iface.id"
            class="iface-group" :class="{ dragging: dragType === 'iface' && draggingId === iface.id }"
            :transform="`translate(${iface.x}, ${iface.y + getIfaceSegOffset(iface)})`"
            @mousedown.prevent="onIfaceMouseDown($event, iface)">
            <rect x="0" y="0" :width="ifaceWidth" :height="ifaceHeight" rx="8"
              :fill="getIfaceFill(iface.type)" :stroke="getIfaceStroke(iface.type)" stroke-width="1.5" />
            <text :x="ifaceWidth / 2" y="16" text-anchor="middle" class="iface-label">{{ iface.name }}</text>
            <text :x="ifaceWidth / 2" y="29" text-anchor="middle" class="iface-type">
              <template v-if="iface.type === 'bridge' && iface.bridge_ports">bridge · {{ (iface.bridge_ports || '').split(/\s+/).length }} ports</template>
              <template v-else-if="iface.type === 'bond'">bond · {{ iface.bond_mode || 'balance-rr' }}<template v-if="iface.bond_slaves"> · {{ iface.bond_slaves.split(/\s+/).length }} nics</template></template>
              <template v-else-if="getIfaceBondOwner(iface)">{{ iface.type }} · {{ getIfaceBondOwner(iface) }} slave</template>
              <template v-else>{{ iface.type }}</template>
            </text>
            <text v-if="iface.address" :x="ifaceWidth / 2" y="41" text-anchor="middle" class="iface-ip">{{ iface.address.split('/')[0] }}</text>
            <circle :cx="ifaceWidth - 8" cy="8" r="4" :fill="iface.status === 'up' ? '#67c23a' : '#f56c6c'" />
          </g>
          <!-- 段标签（在接口之后渲染，确保不被遮挡） -->
          <g class="segment-labels">
            <g v-for="seg in networkSegments" :key="'label-' + seg.cidr"
              :transform="`translate(0, ${segmentOffsets[seg.cidr] || 0})`">
              <text :x="seg.bounds.x + seg.bounds.width / 2" :y="seg.bounds.y + 16"
                text-anchor="middle" class="segment-label" :fill="seg.labelColor">
                {{ seg.label }}
              </text>
            </g>
          </g>
        </svg>
      </div>
    </div>

    <!-- 图例（可点击过滤） -->
    <div class="legend-bar">
      <span v-for="item in legendItems" :key="item.type"
        class="legend-item"
        :class="{ 'is-hidden': hiddenTypes.has(item.type), 'legend-static': item.type === 'node' }"
        @click="item.type !== 'node' && toggleType(item.type)">
        <span class="legend-dot" :style="{ background: item.color }"></span>{{ item.label }}
      </span>
      <span class="legend-item legend-sep"></span>
      <span class="legend-item legend-static"><span class="legend-band"></span>网络段分组</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { getNetworkList, type NetworkInterface } from '@/api/networks'

const loading = ref(true)
const topologyData = ref<NetworkInterface[]>([])
const selectedCluster = ref('')
// 图例过滤：点击可隐藏/显示某类接口
const hiddenTypes = ref(new Set<string>())
const legendItems = [
    { type: 'node', label: '节点', color: '#4f46e5' },
    { type: 'eth', label: '物理网口', color: '#409eff' },
    { type: 'bridge', label: '网桥 (Bridge)', color: '#67c23a' },
    { type: 'bond', label: 'Bond 聚合', color: '#e6a23c' },
    { type: 'vlan', label: 'VLAN', color: '#8b5cf6' },
    { type: 'other', label: '其他', color: '#909399' },
  ]
function toggleType(type: string) {
  const s = new Set(hiddenTypes.value)
  if (s.has(type)) s.delete(type); else s.add(type)
  hiddenTypes.value = s
}
function isTypeHidden(type: string): boolean {
  const known = ['eth', 'bridge', 'bond', 'vlan']
  return hiddenTypes.value.has(known.includes(type) ? type : 'other')
}

const nodeWidth = 140
const nodeHeight = 56
const ifaceWidth = 120
const ifaceHeight = 52
const ifaceGapY = 56

// 拖动状态
const dragType = ref<'node' | 'iface' | 'canvas' | 'segment' | ''>('')
const draggingId = ref<string | number>('')
const dragOffset = { x: 0, y: 0 }
// 段拖动：记录每段的 Y 偏移
const segmentOffsets = ref<Record<string, number>>({})
const segmentDragStartY = ref(0)
const segmentDragBaseOffset = ref(0)

// 缩放状态
const scale = ref(1)
const minScale = 0.3
const maxScale = 3

// 固定的初始 SVG 尺寸（加载时计算，拖动时不变）
const initialSvgWidth = ref(400)
const initialSvgHeight = ref(200)

const clusterList = computed(() => {
  const set = new Set(topologyData.value.map(n => n.cluster_name))
  return Array.from(set).sort()
})

const filteredData = computed(() => {
  if (!selectedCluster.value) return topologyData.value
  return topologyData.value.filter(n => n.cluster_name === selectedCluster.value)
})

// 集群切换或图例过滤时重新布局
watch(filteredData, () => { segmentOffsets.value = {}; initPositions() })
watch(hiddenTypes, () => { initPositions() }, { deep: true })

const nodeFill = 'var(--bg-card, #fff)'
const nodeStroke = '#4f46e5'

interface NodePos { name: string; x: number; y: number; ifaceCount: number }
interface IfacePos extends NetworkInterface { x: number; y: number; nodeName: string }

const nodePositions = ref<NodePos[]>([])
const interfacePositions = ref<IfacePos[]>([])

/** 接口类型排序权重：bridge → bond → vlan → eth → 其他 */
function ifaceSortOrder(i: NetworkInterface): number {
  if (i.type === 'bridge') return 0
  if (i.type === 'bond') return 1
  if (i.type === 'vlan') return 2
  return 3
}

/** 递归布局子接口，返回子接口列表和下一个 Y 坐标 */
function layoutChildren(
  parentX: number, startY: number, children: NetworkInterface[],
  depth: number, bondChildMap: Map<string, NetworkInterface[]>,
  bridgeChildMap: Map<string, NetworkInterface[]>, nodeName: string
): { ifaces: IfacePos[]; nextY: number } {
  const indent = 30
  const result: IfacePos[] = []
  let curY = startY

  children
    .sort((a, b) => ifaceSortOrder(a) - ifaceSortOrder(b) || a.name.localeCompare(b.name))
    .forEach(child => {
      // 图例过滤：跳过
      if (isTypeHidden(child.type)) return

      const childX = parentX + indent * depth
      result.push({ ...child, x: childX, y: curY, nodeName })
      curY += ifaceGapY

      // bond → 展开 bond_slaves（嵌套）
      if (child.type === 'bond' && bondChildMap.has(child.name)) {
        const sub = layoutChildren(childX, curY, bondChildMap.get(child.name)!, depth + 1, bondChildMap, bridgeChildMap, nodeName)
        result.push(...sub.ifaces)
        curY = sub.nextY
      }
      // bridge → 展开 bridge_ports（桥上桥场景）
      if (child.type === 'bridge' && bridgeChildMap.has(child.name)) {
        const sub = layoutChildren(childX, curY, bridgeChildMap.get(child.name)!, depth + 1, bondChildMap, bridgeChildMap, nodeName)
        result.push(...sub.ifaces)
        curY = sub.nextY
      }
    })

  return { ifaces: result, nextY: curY }
}

function initPositions() {
  const groups = new Map<string, NetworkInterface[]>()
  filteredData.value.forEach(iface => {
    const list = groups.get(iface.node_name) || []
    list.push(iface)
    groups.set(iface.node_name, list)
  })

  const nodeEntries = Array.from(groups.entries())
  const nodeSpacing = 380

  const nodes: NodePos[] = []
  const ifaces: IfacePos[] = []

  nodeEntries.forEach(([nodeName, allIfaces], idx) => {
    const x = 60 + idx * nodeSpacing
    nodes.push({ name: nodeName, x, y: 40, ifaceCount: allIfaces.length })

    // ── 构建层级映射 ──
    // bridge → ports（bridge_ports 中可能包含 bond 名称，形成嵌套）
    const bridges = allIfaces.filter(i => i.type === 'bridge')
    const bridgeChildMap = new Map<string, NetworkInterface[]>()
    const bridgePortNames = new Set<string>()

    bridges.forEach(b => {
      const ports = (b.bridge_ports || '').split(/\s+/).filter(Boolean)
      const children = allIfaces.filter(i => ports.includes(i.name))
      bridgeChildMap.set(b.name, children)
      children.forEach(c => bridgePortNames.add(c.name))
    })

    // bond → slaves（bond_slaves 中是物理接口名）
    const bonds = allIfaces.filter(i => i.type === 'bond')
    const bondChildMap = new Map<string, NetworkInterface[]>()
    const bondSlaveNames = new Set<string>()

    bonds.forEach(b => {
      const slaves = (b.bond_slaves || '').split(/\s+/).filter(Boolean)
      const children = allIfaces.filter(i => slaves.includes(i.name))
      bondChildMap.set(b.name, children)
      children.forEach(c => bondSlaveNames.add(c.name))
    })

    // 顶层接口：排除已被 bridge 或 bond 收纳的接口
    const topLevel = allIfaces.filter(i => {
      // 图例过滤：跳过被隐藏的类型
      if (isTypeHidden(i.type)) return false
      if (i.type === 'bridge') return true
      // bond：如果已被某个 bridge 的 bridge_ports 包含，不算顶层
      if (i.type === 'bond' && !bridgePortNames.has(i.name)) return true
      // 其他：未被任何 bridge/bond 收纳才算顶层
      if (i.type !== 'bridge' && i.type !== 'bond' && !bridgePortNames.has(i.name) && !bondSlaveNames.has(i.name)) return true
      return false
    })

    let curY = nodes[idx].y + nodeHeight + 30

    // 先画 bridge（含嵌套 bond），再画 bond（顶层独立 bond），再画其余
    const sortedTop = topLevel
      .sort((a, b) => ifaceSortOrder(a) - ifaceSortOrder(b) || a.name.localeCompare(b.name))

    sortedTop.forEach(iface => {
      ifaces.push({ ...iface, x, y: curY, nodeName })
      curY += ifaceGapY

      // bridge → 展开 bridge_ports
      if (iface.type === 'bridge' && bridgeChildMap.has(iface.name)) {
        const children = bridgeChildMap.get(iface.name)!
        // 子接口中属于 bond 的会自动展开 bond_slaves
        const sub = layoutChildren(x, curY, children, 1, bondChildMap, bridgeChildMap, nodeName)
        ifaces.push(...sub.ifaces)
        curY = sub.nextY
      }

      // bond → 展开 bond_slaves（独立 bond，不在 bridge 下）
      if (iface.type === 'bond' && bondChildMap.has(iface.name)) {
        // 检查是否已经被某个 bridge 展开过（即 bridge_ports 包含此 bond）
        const isInsideBridge = bridgePortNames.has(iface.name)
        if (!isInsideBridge) {
          const sub = layoutChildren(x, curY, bondChildMap.get(iface.name)!, 1, bondChildMap, bridgeChildMap, nodeName)
          ifaces.push(...sub.ifaces)
          curY = sub.nextY
        }
      }
    })
  })

  // ── 按网段重新排列接口卡片（避免段色带重叠） ──
  const segPad = 12
  const segGap = 16
  const segMinH = ifaceHeight + 32
  const cidrMap = new Map<string, IfacePos[]>()
  ifaces.forEach(iface => {
    if (!iface.address) return
    const cidr = toNetworkCidr(iface.address)
    if (!cidr) return
    if (!cidrMap.has(cidr)) cidrMap.set(cidr, [])
    cidrMap.get(cidr)!.push(iface)
  })
  const sortedCidrs = Array.from(cidrMap.entries())
    .filter(([, g]) => new Set(g.map(i => i.node_name)).size >= 2)
    .sort((a, b) => Math.max(...a[1].map(i => i.y)) - Math.max(...b[1].map(i => i.y)))
  let segY = 100
  sortedCidrs.forEach(([, group]) => {
    const minY = Math.min(...group.map(i => i.y))
    const maxY = Math.max(...group.map(i => i.y))
    const contentH = maxY - minY + ifaceHeight + segPad
    const segH = Math.max(contentH, segMinH)
    const dy = segY - minY + segPad
    group.forEach(i => { i.y += dy })
    segY += segH + segGap
  })

  nodePositions.value = nodes
  interfacePositions.value = ifaces

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
      const so = getIfaceSegOffset(iface)
      // 优先查找 bond 父级（bond_slaves 包含该接口名）
      const parentBond = ifaces.find(
        i => i.type === 'bond' && (i.bond_slaves || '').split(/\s+/).includes(iface.name)
      )
      if (parentBond) {
        const pso = getIfaceSegOffset(parentBond)
        conns.push({
          x1: parentBond.x + ifaceWidth / 2, y1: parentBond.y + pso + ifaceHeight,
          x2: iface.x + ifaceWidth / 2, y2: iface.y + so,
          color: getIfaceColor('bond')
        })
        return
      }

      // 其次查找 bridge 父级（bridge_ports 包含该接口名）
      const parentBridge = ifaces.find(
        i => i.type === 'bridge' && (i.bridge_ports || '').split(/\s+/).includes(iface.name)
      )
      if (parentBridge) {
        const pso = getIfaceSegOffset(parentBridge)
        conns.push({
          x1: parentBridge.x + ifaceWidth / 2, y1: parentBridge.y + pso + ifaceHeight,
          x2: iface.x + ifaceWidth / 2, y2: iface.y + so,
          color: getIfaceColor('bridge')
        })
        return
      }

      // 顶层接口：连到节点
      conns.push({
        x1: np.x + nodeWidth / 2, y1: np.y + nodeHeight,
        x2: iface.x + ifaceWidth / 2, y2: iface.y + so,
        color: getIfaceColor(iface.type)
      })
    })
  })
  return conns
})

// ── 跨节点网络段分组 ──
interface SegmentBounds { x: number; y: number; width: number; height: number }
interface NetworkSegment {
  cidr: string
  label: string
  fillColor: string
  strokeColor: string
  labelColor: string
  bounds: SegmentBounds
  ifaces: IfacePos[]
}

/** 从 IP 地址提取子网前缀。
 *  支持 "192.168.2.1/24" 和裸 IP "192.168.2.3"（默认 /24） */
function toNetworkCidr(address: string): string | null {
  // 带 CIDR：192.168.2.1/24
  const cidrMatch = address.match(/^(\d+\.\d+\.\d+)\.\d+\/(\d+)$/)
  if (cidrMatch) {
    const prefix = cidrMatch[1]
    const bits = parseInt(cidrMatch[2])
    if (bits >= 24) return `${prefix}.0/24`
    if (bits >= 16) return `${prefix.split('.')[0]}.${prefix.split('.')[1]}.0.0/16`
    return `${prefix}.0.0.0/8`
  }
  // 裸 IP：192.168.2.3 → 默认 /24
  const bareMatch = address.match(/^(\d+\.\d+\.\d+)\.\d+$/)
  if (bareMatch) return `${bareMatch[1]}.0/24`
  return null
}

// 获取接口所属段的 Y 偏移（用于段拖动）
function getIfaceSegOffset(iface: IfacePos): number {
  const cidr = iface.address ? toNetworkCidr(iface.address) : null
  return cidr ? (segmentOffsets.value[cidr] || 0) : 0
}

const segmentColors = [
  { fill: 'rgba(103, 194, 58, 0.08)',  stroke: 'rgba(103, 194, 58, 0.35)',  label: 'rgba(103, 194, 58, 0.8)' },  // 绿
  { fill: 'rgba(230, 162, 60, 0.08)',  stroke: 'rgba(230, 162, 60, 0.35)',  label: 'rgba(230, 162, 60, 0.8)' },  // 橙
  { fill: 'rgba(64, 158, 255, 0.08)',  stroke: 'rgba(64, 158, 255, 0.35)',  label: 'rgba(64, 158, 255, 0.8)' },  // 蓝
  { fill: 'rgba(139, 92, 246, 0.08)',  stroke: 'rgba(139, 92, 246, 0.35)',  label: 'rgba(139, 92, 246, 0.8)' },  // 紫
  { fill: 'rgba(245, 108, 108, 0.08)', stroke: 'rgba(245, 108, 108, 0.35)', label: 'rgba(245, 108, 108, 0.8)' },  // 红
]

/** 按接口类型猜测网段名称 */
function guessSegmentLabel(ifaces: IfacePos[]): string {
  const types = new Set(ifaces.map(i => i.type))
  if (types.has('bridge') && !types.has('bond')) return '管理网段'
  if (types.has('bond')) {
    // 检查是否 bridge 下的 bond（业务/VM 网段）或独立 bond
    return '聚合网段'
  }
  return '网络段'
}

const networkSegments = computed<NetworkSegment[]>(() => {
  const allIfaces = interfacePositions.value
  if (!allIfaces.length) return []

  // 按子网分组
  const subnetMap = new Map<string, IfacePos[]>()
  allIfaces.forEach(iface => {
    if (!iface.address) return
    const cidr = toNetworkCidr(iface.address)
    if (!cidr) return
    if (!subnetMap.has(cidr)) subnetMap.set(cidr, [])
    subnetMap.get(cidr)!.push(iface)
  })

  // 过滤：至少跨 2 个节点的子网才显示色带
  const multiNodeSegments = Array.from(subnetMap.entries()).filter(([, group]) => {
    const nodeNames = new Set(group.map(i => i.node_name))
    return nodeNames.size >= 2
  })

  const padding = 12
  const segmentGap = 16
  const segMinHeight = ifaceHeight + 32 // 色带最小高度：接口卡片 + 上下留白
  const segments: NetworkSegment[] = []

  multiNodeSegments.sort((a, b) => b[1].length - a[1].length) // 接口多的在前

  // 按段内最高接口的 Y 坐标排序，确保从上到下排列
  multiNodeSegments.sort((a, b) => {
    const maxYa = Math.max(...a[1].map(i => i.y))
    const maxYb = Math.max(...b[1].map(i => i.y))
    return maxYa - maxYb
  })

  let curY = 100 // 起始 Y（节点卡片下方）

  multiNodeSegments.forEach(([cidr, group], idx) => {
    const minX = Math.min(...group.map(i => i.x)) - padding
    const maxX = Math.max(...group.map(i => i.x)) + ifaceWidth + padding
    const width = maxX - minX

    // 段高度取：接口实际跨度 vs 最小高度，取较大值
    const contentHeight = Math.max(...group.map(i => i.y)) - Math.min(...group.map(i => i.y)) + ifaceHeight + padding
    const height = Math.max(contentHeight, segMinHeight)

    const colors = segmentColors[idx % segmentColors.length]

    const hasBridge = group.some(i => i.type === 'bridge')
    const hasBond = group.some(i => i.type === 'bond')
    const label = hasBridge && !hasBond ? '管理网段'
      : hasBond && hasBridge ? '管理+业务'
      : hasBond ? '聚合网段'
      : guessSegmentLabel(group)

    segments.push({
      cidr,
      label: `${label} (${cidr})`,
      fillColor: colors.fill,
      strokeColor: colors.stroke,
      labelColor: colors.label,
      bounds: { x: minX, y: curY, width, height },
      ifaces: group,
    })

    curY += height + segmentGap
  })

  return segments
})

/** 查找接口所属的 bond 父级名称（模板用） */
function getIfaceBondOwner(iface: IfacePos): string {
  const owner = interfacePositions.value.find(
    i => i.type === 'bond' && i.node_name === iface.node_name
      && (i.bond_slaves || '').split(/\s+/).includes(iface.name)
  )
  return owner?.name || ''
}

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

// 段色带拖动
function onSegmentMouseDown(e: MouseEvent, segCidr: string) {
  dragType.value = 'segment'
  draggingId.value = segCidr
  segmentDragStartY.value = e.clientY
  segmentDragBaseOffset.value = segmentOffsets.value[segCidr] || 0
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
  } else if (dragType.value === 'segment') {
    const dy = e.clientY - segmentDragStartY.value
    segmentOffsets.value = { ...segmentOffsets.value, [draggingId.value as string]: segmentDragBaseOffset.value + dy }
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
  selectedCluster.value = clusterList.value[0] || ''
  scale.value = 1
  segmentOffsets.value = {}
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
    // 默认选择第一个集群
    if (clusterList.value.length && !selectedCluster.value) {
      selectedCluster.value = clusterList.value[0]
    }
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
/* ── 工具栏 ── */
.toolbar {
  display: flex; align-items: center; gap: 0;
  background: var(--bg-secondary, #f5f7fa);
  border: 1px solid var(--border-color, #e4e7ed);
  border-radius: 8px; padding: 4px 8px; height: 36px;
}
.toolbar-group { display: flex; align-items: center; gap: 4px; padding: 0 6px; }
.toolbar-divider { width: 1px; height: 18px; background: var(--border-color, #dcdfe6); flex-shrink: 0; }
.toolbar-btn {
  width: 26px; height: 26px; display: flex; align-items: center; justify-content: center;
  border: 1px solid var(--border-color, #dcdfe6); border-radius: 6px;
  background: var(--bg-card, #fff); color: var(--text-primary, #303133);
  font-size: 14px; cursor: pointer; transition: all .15s; line-height: 1;
}
.toolbar-btn:hover { border-color: #409eff; color: #409eff; background: rgba(64,158,255,.06); }
.toolbar-btn:active { transform: scale(.92); }
.toolbar-zoom-val {
  font-size: 12px; color: var(--text-muted, #909399); min-width: 36px; text-align: center;
  font-variant-numeric: tabular-nums; user-select: none;
}
.toolbar-btn-text {
  height: 26px; padding: 0 10px; display: flex; align-items: center; justify-content: center;
  border: 1px solid var(--border-color, #dcdfe6); border-radius: 6px;
  background: var(--bg-card, #fff); color: var(--text-secondary, #606266);
  font-size: 12px; cursor: pointer; transition: all .15s; white-space: nowrap;
}
.toolbar-btn-text:hover { border-color: #409eff; color: #409eff; background: rgba(64,158,255,.06); }
.toolbar-btn-text:active { transform: scale(.92); }

.topology-container {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
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
.iface-ip { font-size: 9px; fill: var(--text-muted); opacity: .75; }

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
  display: flex; align-items: center; gap: 6px; margin-top: 16px; padding: 8px 14px;
  background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 10px;
  flex-wrap: wrap;
}
.legend-item {
  display: flex; align-items: center; gap: 5px; font-size: 12px;
  color: var(--text-secondary); padding: 4px 10px; border-radius: 6px;
  cursor: pointer; transition: all .2s; user-select: none;
  border: 1px solid transparent;
}
.legend-item:hover { background: rgba(64,158,255,.06); }
.legend-item.is-hidden { opacity: .4; }
.legend-item.is-hidden .legend-dot { background: #c0c4cc !important; }
.legend-item.is-hidden .legend-dot::after { content: ''; position: absolute; width: 12px; height: 1.5px; background: #c0c4cc; transform: rotate(-45deg); top: 4.25px; left: -1px; }
.legend-dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; position: relative; transition: all .2s; }
.legend-sep { width: 1px; height: 16px; background: var(--border-color); padding: 0; cursor: default; }
.legend-sep:hover { background: var(--border-color); }
.legend-static { cursor: default; }
.legend-static:hover { background: transparent; }
.legend-band { width: 16px; height: 8px; border-radius: 3px; display: inline-block;
  background: repeating-linear-gradient(45deg, rgba(103,194,58,0.15), rgba(103,194,58,0.15) 2px, rgba(103,194,58,0.3) 2px, rgba(103,194,58,0.3) 4px);
  border: 1px dashed rgba(103,194,58,0.5); }
.segment-label { font-size: 10px; font-weight: 600; }
</style>
