<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ t('smartAnalysis.dependencyMapping.title') }}</h2>
        <p class="page-desc">{{ t('smartAnalysis.dependencyMapping.subtitle') }}</p>
      </div>
      <div class="toolbar">
        <div class="toolbar-group">
          <button class="toolbar-btn" @click="zoomBy(0.8)" title="缩小">−</button>
          <span class="toolbar-zoom-val">{{ zoomPercent }}%</span>
          <button class="toolbar-btn" @click="zoomBy(1.25)" title="放大">+</button>
        </div>
        <span class="toolbar-divider"></span>
        <div class="toolbar-group">
          <button class="toolbar-btn-text" @click="fitView">自适应</button>
          <button class="toolbar-btn-text" @click="zoomTo(1)">100%</button>
        </div>
      </div>
    </div>

    <div class="graph-container" v-loading="loading">
      <!-- 统一浮动面板：资源选择 + 详情 -->
      <div class="unified-panel">
        <div class="panel-section">
          <div class="selector-item">
            <label class="selector-label">{{ t('smartAnalysis.dependencyMapping.resourceType') }}</label>
            <el-select v-model="selectedResourceType" :placeholder="t('smartAnalysis.dependencyMapping.selectResourcePlaceholder')" @change="onResourceTypeChange" style="width: 150px" size="small" clearable>
              <el-option :label="t('smartAnalysis.dependencyMapping.legendVM')" value="vm" />
              <el-option :label="t('smartAnalysis.dependencyMapping.legendContainer')" value="container" />
            </el-select>
          </div>
          <div class="selector-item" v-if="selectedResourceType">
            <label class="selector-label">{{ t('smartAnalysis.dependencyMapping.selectResource') }}</label>
            <el-select v-model="selectedResourceId" :placeholder="t('smartAnalysis.dependencyMapping.selectResourcePlaceholder')" filterable clearable @change="onResourceChange" style="width: 220px" size="small">
              <el-option v-for="item in resourceOptions" :key="item.id" :value="item.id" :label="`${item.name} (${item.vmid})`">
                <span>{{ item.name }} ({{ item.vmid }})</span>
                <span v-if="item.ha_enabled" style="margin-left: 6px; color: #f97316; font-size: 11px; font-weight: 600;">HA</span>
              </el-option>
            </el-select>
          </div>
        </div>

        <transition name="fade">
           <div v-if="selectedNode" class="panel-detail">
             <div class="detail-body">
               <div class="detail-row" v-for="(value, key) in selectedNode.details" :key="key">
                 <span class="detail-label">{{ key }}</span>
                 <span class="detail-value">{{ value }}</span>
               </div>
             </div>
           </div>
         </transition>
      </div>

      <div v-if="!loading && !initDone" class="empty-state">
        <el-empty :description="t('smartAnalysis.dependencyMapping.emptyDesc')" />
      </div>

      <!-- ═══════════════════ SVG 画布（官方 SVG 语法，纯 Vue 模板渲染）═══════════════════ -->
      <svg ref="svgRef" class="graph-svg"
        @mousedown.prevent="onSvgMouseDown"
        @mousemove="onMouseMove"
        @mouseup="onMouseUp"
        @mouseleave="onMouseUp"
        @wheel.prevent="onWheel">
        <defs>
          <filter id="dep-shadow" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="3" stdDeviation="5" flood-color="rgba(0,0,0,0.15)" />
          </filter>
          <marker id="dep-arrowhead" markerWidth="10" markerHeight="7" refX="10" refY="3.5" orient="auto">
            <polygon points="0 0, 10 3.5, 0 7" fill="var(--text-muted)" />
          </marker>
        </defs>

        <!-- 缩放/平移容器（等 positions 就绪后才渲染） -->
        <g v-if="initDone" :transform="`translate(${panX}, ${panY}) scale(${scale})`">
          <!-- 1️⃣ 边（跨节点连接线） -->
          <g v-for="(e, idx) in edgeData" :key="'e-'+idx">
            <path
              :d="e.d" fill="none"
              :stroke="e.color" :stroke-width="e.dashed ? 1.5 : 2"
              :stroke-dasharray="e.dashed ? '6,3' : undefined"
              marker-end="url(#dep-arrowhead)" />
            <!-- HA 标签 -->
            <g v-if="e.label" :transform="`translate(${e.mx}, ${e.my})`">
              <rect x="-14" y="-10" width="28" height="18" rx="9"
                :fill="e.color" opacity="0.9" />
              <text text-anchor="middle" y="3" fill="#fff" font-size="9" font-weight="700">{{ e.label }}</text>
            </g>
          </g>

          <!-- 2️⃣ 集群背景 -->
          <g v-if="clusterNode" class="bg-cluster"
            :transform="`translate(${clusterPos.x}, ${clusterPos.y})`"
            @mousedown.prevent.stop="onClusterMouseDown($event)">
            <rect x="0" y="0" :width="clusterPos.w" :height="clusterPos.h" rx="20"
              :fill="getColors('cluster').fill" :stroke="getColors('cluster').stroke"
              stroke-width="2.5" stroke-dasharray="8,4" />
            <text x="16" y="26" fill="var(--text-heading)" font-size="15" font-weight="700" class="svg-text-primary">{{ clusterNode.name }}</text>
          </g>

          <!-- 3️⃣ PVE 节点背景（中心坐标系：translate(x,y) + rect 在 (-w/2, -h/2)） -->
          <g v-for="nd in pveNodes" :key="nd.id"
            class="bg-node"
            :class="{ dragging: dragTargetType === 'node' && dragTargetId === nd.id }"
            :transform="`translate(${getPos(nd.id)?.x ?? nd.x}, ${getPos(nd.id)?.y ?? nd.y})`"
            @mousedown.prevent.stop="onNodeMouseDown($event, nd.id)">
            <rect :x="-(getPos(nd.id)?.w ?? nd.width)/2" :y="-(getPos(nd.id)?.h ?? nd.height)/2"
              :width="getPos(nd.id)?.w ?? nd.width" :height="getPos(nd.id)?.h ?? nd.height"
              rx="14" :fill="getColors('node').fill" :stroke="getColors('node').stroke"
              stroke-width="2" stroke-dasharray="6,3" />
            <text text-anchor="middle" y="0" dy="0.35em"
              fill="var(--text-heading)" font-size="13" font-weight="700" class="svg-text-primary">
              {{ nd.name }} {{ getSubLabel(nd) }}
            </text>
          </g>

          <!-- 4️⃣ 叶子节点卡片（VM/容器/存储/网络/Ceph/HA/SDN） -->
          <g v-for="lf in leafList" :key="lf.id"
            class="leaf-card"
            :class="{ dragging: dragTargetType === 'leaf' && dragTargetId === lf.id }"
            :transform="`translate(${getPos(lf.id)?.x ?? lf.x}, ${getPos(lf.id)?.y ?? lf.y})`"
            @mousedown.prevent.stop="onLeafMouseDown($event, lf.id)"
            @click.stop="onLeafClick(lf.id)">
            <rect :x="-lf.width/2" :y="-lf.height/2"
              :width="lf.width" :height="lf.height" rx="10"
              :fill="getColors(lf.type).fill" :stroke="getColors(lf.type).stroke"
              stroke-width="2" filter="url(#dep-shadow)" />
            <!-- 标签文字 -->
            <text text-anchor="middle" :y="getSubLabel(lf) ? -5 : 0" dy="0.35em"
              fill="var(--text-heading)" font-size="12" font-weight="600" class="svg-text-primary leaf-name"
              :data-maxw="lf.width - 16">{{ lf.name }}</text>
            <!-- 子标题 -->
            <text v-if="getSubLabel(lf)" text-anchor="middle" y="10"
              fill="var(--text-muted)" font-size="10" class="svg-text-muted">{{ getSubLabel(lf) }}</text>
            <!-- HA 标签 -->
            <g v-if="lf.ha_enabled" :transform="`translate(${-lf.width/2 + 6}, ${-lf.height/2 + 5})`">
              <rect width="28" height="14" rx="3" fill="#f97316" opacity="0.9" />
              <text x="14" y="11" text-anchor="middle" font-size="8" font-weight="700" fill="#fff">HA</text>
            </g>
          </g>

          <!-- 5️⃣ 高亮脉冲动画（选中资源时显示） -->
          <g v-if="highlightedLeafId" class="highlight-pulse"
            :transform="`translate(${getPos(highlightedLeafId)?.x ?? 0}, ${getPos(highlightedLeafId)?.y ?? 0})`">
            <rect :x="-(getLeafWidth(highlightedLeafId))/2 - 6"
              :y="-(getLeafHeight(highlightedLeafId))/2 - 6"
              :width="getLeafWidth(highlightedLeafId) + 12"
              :height="getLeafHeight(highlightedLeafId) + 12"
              rx="14" fill="none" stroke="#409eff" stroke-width="3" opacity="0.8">
              <animate attributeName="stroke-width" values="3;6;3" dur="1.5s" repeatCount="indefinite" />
              <animate attributeName="opacity" values="0.8;0.3;0.8" dur="1.5s" repeatCount="indefinite" />
            </rect>
            <rect :x="-(getLeafWidth(highlightedLeafId))/2 - 10"
              :y="-(getLeafHeight(highlightedLeafId))/2 - 10"
              :width="getLeafWidth(highlightedLeafId) + 20"
              :height="getLeafHeight(highlightedLeafId) + 20"
              rx="16" fill="none" stroke="#409eff" stroke-width="2" opacity="0">
              <animate attributeName="opacity" values="0;0.4;0" dur="1.5s" repeatCount="indefinite" />
            </rect>
          </g>
        </g>
      </svg>
    </div>

    <!-- 图例 -->
    <div class="legend-bar">
      <span v-for="item in legendItems" :key="item.type" class="legend-item" @click="toggleType(item.type)">
        <span class="legend-dot" :style="{ background: item.color }"></span>{{ item.label }}
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, computed, watch, nextTick, reactive } from 'vue'
import { useI18n } from 'vue-i18n'
import { forceSimulation, forceCollide, forceX, forceY } from 'd3-force'
import { getDependencyGraph, type DependencyGraph } from '@/api/dependency'
import { useClusterStore } from '@/stores/cluster'
import { getVMs, type VMInfo } from '@/api/vms'
import { getContainers, type ContainerInfo } from '@/api/containers'

const { t } = useI18n()
const clusterStore = useClusterStore()

// ─── 响应式状态 ───
const loading = ref(false)
const initDone = ref(false)
const loadGeneration = ref(0) // 防止 loadData 并发竞态
const svgRef = ref<SVGSVGElement>()
const selectedNode = ref<any>(null)
const zoomPercent = ref(100)

const selectedResourceType = ref<'all' | 'vm' | 'container' | ''>('')
const selectedResourceId = ref<number | undefined>(undefined)
const vmList = ref<VMInfo[]>([])
const containerList = ref<ContainerInfo[]>([])
const hiddenTypes = ref(new Set<string>())
const highlightedLeafId = ref<string>('')

// ─── 缩放/平移状态 ───
const scale = ref(1)
const panX = ref(0)
const panY = ref(0)
const minScale = 0.2
const maxScale = 4

// ─── 拖拽状态 ───
const dragTargetType = ref<'cluster' | 'node' | 'leaf' | 'canvas' | ''>('')
const dragTargetId = ref<string>('')
let dragStartClientX = 0
let dragStartClientY = 0
let dragStartSceneX = 0
let dragStartSceneY = 0
let dragMoved = false

// ─── 图数据结构 ───
interface HNode {
  id: string; type: string; name: string; width: number; height: number;
  x: number; y: number; children: HNode[]; leafs: HNode[];
  [key: string]: any
}
interface EdgeData { d: string; color: string; dashed: boolean; label?: string; mx?: number; my?: number }
interface Pos { x: number; y: number; w: number; h: number }

const clusterNode = ref<HNode | null>(null)
const pveNodes = ref<HNode[]>([])
const leafList = ref<HNode[]>([])
const childMap = ref<Map<string, string[]>>(new Map())
const nodeParentMap = ref<Map<string, string>>(new Map())
const edgeData = ref<EdgeData[]>([])
const graphData = ref<DependencyGraph>({ nodes: [], edges: [] })

// 位置数据（响应式 Record，模板直接读取 positions[id].x / .y / .w / .h）
const positions = reactive<Record<string, Pos>>({})
function getPos(id: string): Pos | undefined { return positions[id] }
function setPos(id: string, x: number, y: number) {
  const p = positions[id]
  if (p) { p.x = x; p.y = y }
}

// ─── 计算属性 ───
const clusterPos = computed(() => {
  if (!clusterNode.value) return { x: 0, y: 0, w: 0, h: 0 }
  return getPos(clusterNode.value.id) || { x: 0, y: 0, w: 0, h: 0 }
})

const resourceOptions = computed(() => {
  if (selectedResourceType.value === 'vm') return vmList.value.map(vm => ({
    id: vm.id, name: vm.name, vmid: vm.vmid, ha_enabled: vm.ha_enabled, ha_group: vm.ha_group
  })).sort((a, b) => a.vmid - b.vmid)
  if (selectedResourceType.value === 'container') return containerList.value.map(ct => ({
    id: ct.id, name: ct.name, vmid: ct.vmid, ha_enabled: ct.ha_enabled, ha_group: ct.ha_group
  })).sort((a, b) => a.vmid - b.vmid)
  return []
})

// ─── 颜色和图例 ───
const typeColors: Record<string, { fill: string; stroke: string }> = {
  cluster: { fill: 'rgba(79,70,229,0.10)', stroke: '#4f46e5' },
  node: { fill: 'rgba(64,158,255,0.08)', stroke: '#409eff' },
  vm: { fill: 'rgba(103,194,58,0.12)', stroke: '#67c23a' },
  container: { fill: 'rgba(230,162,60,0.12)', stroke: '#e6a23c' },
  storage: { fill: 'rgba(245,108,108,0.10)', stroke: '#f56c6c' },
  network: { fill: 'rgba(139,92,246,0.10)', stroke: '#8b5cf6' },
  ceph: { fill: 'rgba(6,182,212,0.10)', stroke: '#06b6d4' },
  ha: { fill: 'rgba(249,115,22,0.12)', stroke: '#f97316' },
  sdn_zone: { fill: 'rgba(236,72,153,0.10)', stroke: '#ec4899' },
  sdn_vnet: { fill: 'rgba(236,72,153,0.08)', stroke: '#ec4899' },
  sdn_subnet: { fill: 'rgba(236,72,153,0.06)', stroke: '#ec4899' },
}
function getColors(type: string) { return typeColors[type] || { fill: 'rgba(144,147,153,0.08)', stroke: '#909399' } }

const legendItems = computed(() => [
  { type: 'cluster', label: t('smartAnalysis.dependencyMapping.legendCluster'), color: '#4f46e5' },
  { type: 'node', label: t('smartAnalysis.dependencyMapping.legendNode'), color: '#409eff' },
  { type: 'vm', label: t('smartAnalysis.dependencyMapping.legendVM'), color: '#67c23a' },
  { type: 'container', label: t('smartAnalysis.dependencyMapping.legendContainer'), color: '#e6a23c' },
  { type: 'storage', label: t('smartAnalysis.dependencyMapping.legendStorage'), color: '#f56c6c' },
  { type: 'network', label: t('smartAnalysis.dependencyMapping.legendNetwork'), color: '#8b5cf6' },
  { type: 'ceph', label: t('smartAnalysis.dependencyMapping.legendCeph'), color: '#06b6d4' },
  { type: 'ha', label: 'HA 故障转移', color: '#f97316' },
  { type: 'sdn_zone', label: t('smartAnalysis.dependencyMapping.legendSDN'), color: '#ec4899' },
])

function toggleType(type: string) {
  const s = new Set(hiddenTypes.value)
  if (s.has(type)) s.delete(type); else s.add(type)
  hiddenTypes.value = s
  // 重新布局以反映隐藏/显示状态
  nextTick(() => {
    layoutGraph()
    fitView()
  })
}

function getSubLabel(n: any): string {
  if (n.type === 'node') return n.ip_address || ''
  if (n.type === 'vm' || n.type === 'container') {
    const b = `${n.cpu_cores || 0}核 ${n.memory_mb ? (n.memory_mb / 1024).toFixed(0) + 'G' : ''}`
    return n.ha_enabled ? `${b} · HA:${n.ha_group}` : b
  }
  if (n.type === 'storage') return `${n.total_gb || 0}GB ${n.storage_type || ''}`
  if (n.type === 'network') return `${n.net_type || ''} ${n.address || ''}`
  if (n.type === 'ceph') return `${n.health || ''} ${n.total_osds || 0} OSD`
  if (n.type === 'ha') return `成员: ${n.member_count || '?'}`
  if (n.type === 'sdn_zone') return `类型: ${n.zone_type || '?'}`
  if (n.type === 'sdn_vnet') return `VLAN: ${n.vlan || '?'}`
  if (n.type === 'sdn_subnet') return `网关: ${n.gateway || '?'}`
  return ''
}

function truncatedName(node: HNode): string {
  const maxW = node.width - 16
  const approxChars = Math.floor(maxW / 7)
  return node.name.length > approxChars ? node.name.slice(0, approxChars - 3) + '...' : node.name
}

function getLeafWidth(id: string): number {
  const lf = leafList.value.find(l => l.id === id)
  return lf?.width ?? 180
}
function getLeafHeight(id: string): number {
  const lf = leafList.value.find(l => l.id === id)
  return lf?.height ?? 52
}

// ─── 层次结构构建（纯算法，不涉及 DOM） ───
const nodeSizes: Record<string, [number, number]> = {
  cluster: [180, 60], node: [160, 56], vm: [180, 52], container: [180, 52],
  storage: [180, 52], network: [175, 52], ceph: [160, 52], ha: [150, 48],
  sdn_zone: [140, 48], sdn_vnet: [130, 44], sdn_subnet: [130, 44],
}

function buildHierarchy(apiData: DependencyGraph) {
  const raw = apiData.nodes
  const cluster = raw.find(n => n.type === 'cluster')
  if (!cluster) return

  const nodeMap = new Map<string, HNode>()
  raw.forEach(n => {
    const [w, h] = nodeSizes[n.type] || [140, 44]
    nodeMap.set(n.id, { id: n.id, type: n.type, name: n.name, width: w, height: h, x: 0, y: 0, children: [], leafs: [], ...n })
  })

  const nodes = raw.filter(n => n.type === 'node').map(n => nodeMap.get(n.id)!)
  const leafNodes = raw.filter(n => !['cluster', 'node'].includes(n.type))

  leafNodes.forEach(n => {
    const hNode = nodeMap.get(n.id)!
    if (n.node_id != null) {
      const parent = nodes.find(nd => String(nd.node_id) === String(n.node_id))
      if (parent) { parent.leafs.push(hNode); return }
    }
    if (cluster) nodeMap.get(cluster.id)!.leafs.push(hNode)
  })

  // 预计算每个 node 的尺寸（增大间距和内边距）
  const pad = 36, childW = 180, childH = 52, gap = 22, netW = 175
  nodes.forEach(node => {
    const vms = node.leafs.filter(c => ['vm', 'container'].includes(c.type))
    const nets = node.leafs.filter(c => c.type === 'network')
    const stors = node.leafs.filter(c => c.type === 'storage')
    if (vms.length === 0 && nets.length === 0 && stors.length === 0) {
      node.width = 200; node.height = 70; return
    }
    const cols = Math.max(1, Math.min(vms.length, 5))
    const vmRows = Math.ceil(vms.length / cols)
    const vmAreaW = cols * (childW + gap) - gap
    const vmAreaH = vmRows * (childH + gap) - gap
    const netAreaW = nets.length > 0 ? netW + gap : 0
    const storRowH = stors.length > 0 ? childH + gap : 0
    node.width = Math.max(pad * 2 + vmAreaW + netAreaW, pad * 2 + stors.length * (childW + gap) - gap, 200)
    node.height = pad + 32 + 16 + vmAreaH + storRowH + pad
  })

  // 预计算 cluster 尺寸（增大外边距）
  let clusterW: number, clusterH: number
  if (nodes.length === 1) {
    const n = nodes[0]
    clusterW = n.width + pad * 2 + 60
    clusterH = n.height + pad * 2 + 80 + 50
  } else {
    const maxW = Math.max(...nodes.map(n => n.width))
    const gap2 = 50
    clusterW = maxW + pad * 2 + gap2 * 2
    clusterH = nodes.reduce((s, n) => s + n.height + gap2, 0) + 100
  }

  const clusterHNode = nodeMap.get(cluster.id)!
  clusterHNode.width = Math.max(clusterW, 350)
  clusterHNode.height = Math.max(clusterH, 250)

  clusterNode.value = clusterHNode
  pveNodes.value = nodes
  leafList.value = leafNodes.map(n => nodeMap.get(n.id)!)

  // 父子索引
  const cMap = new Map<string, string[]>()
  nodes.forEach(nd => {
    cMap.set(nd.id, nd.leafs.map(c => c.id))
  })
  childMap.value = cMap

  const npMap = new Map<string, string>()
  nodes.forEach(nd => nd.leafs.forEach(c => npMap.set(c.id, nd.id)))
  nodeParentMap.value = npMap
}

// ─── 边数据生成 ───
function edgeStyle(type: string): { color: string; dashed: boolean } {
  if (type === 'cluster-node') return { color: '#409eff', dashed: false }
  if (type === 'vm-network' || type === 'container-network') return { color: '#8b5cf6', dashed: true }
  if (type === 'vm-storage' || type === 'container-storage') return { color: '#f56c6c', dashed: true }
  if (type === 'cluster-ceph') return { color: '#06b6d4', dashed: false }
  if (type.includes('ha')) return { color: '#f97316', dashed: true }
  if (type === 'cluster-sdn' || type === 'zone-vnet' || type === 'vnet-subnet') return { color: '#ec4899', dashed: false }
  return { color: '#909399', dashed: false }
}

function computeEdges() {
  const apiEdges = graphData.value.edges
  const edges: EdgeData[] = []
  apiEdges.forEach(e => {
    // 跳过父子层级边（视觉包含已表达归属）
    if (['cluster-node', 'node-storage', 'node-network', 'node-vm', 'node-container'].includes(e.type)) return
    const sp = getPos(e.source)
    const tp = getPos(e.target)
    if (!sp || !tp) return
    const dx = tp.x - sp.x
    const dy = tp.y - sp.y
    const dist = Math.sqrt(dx * dx + dy * dy) || 1
    const x1 = sp.x + (dx / dist) * (sp.w / 2)
    const y1 = sp.y + (dy / dist) * (sp.h / 2)
    const x2 = tp.x - (dx / dist) * (tp.w / 2)
    const y2 = tp.y - (dy / dist) * (tp.h / 2)
    const mx = (x1 + x2) / 2
    const my = (y1 + y2) / 2
    const off = Math.min(dist * 0.15, 50)
    const d = `M${x1},${y1} Q${mx + (-dy / dist) * off},${my + (dx / dist) * off} ${x2},${y2}`
    const s = edgeStyle(e.type)
    const label = e.type === 'ha-failover' ? 'HA' : undefined
    edges.push({ d, color: s.color, dashed: s.dashed, label, mx, my })
  })
  edgeData.value = edges
}

// ─── 布局定位（纯算法） ───
function layoutGraph() {
  if (!clusterNode.value) return
  const container = svgRef.value?.parentElement
  if (!container) return
  const svgW = container.clientWidth
  const svgH = container.clientHeight
  const cx = svgW / 2, cy = svgH / 2
  const pad = 36, childW = 180, childH = 52, gap = 22, netW = 175

  // 初始化 positions
  positions[clusterNode.value.id] = {
    x: cx - clusterNode.value.width / 2,
    y: cy - clusterNode.value.height / 2,
    w: clusterNode.value.width,
    h: clusterNode.value.height,
  }

  let ny = positions[clusterNode.value.id].y + pad + 42
  pveNodes.value.forEach(nd => {
    const npX = positions[clusterNode.value.id].x + (positions[clusterNode.value.id].w - nd.width) / 2
    const npY = ny
    positions[nd.id] = { x: npX, y: npY, w: nd.width, h: nd.height }
    ny += nd.height + 40

    // 布局子节点
    const vms = nd.leafs.filter(c => ['vm', 'container'].includes(c.type))
    const nets = nd.leafs.filter(c => c.type === 'network')
    const stors = nd.leafs.filter(c => c.type === 'storage')
    const innerX = npX + pad
    const innerY = npY + pad + 36
    const innerW = nd.width - pad * 2
    const innerH = nd.height - pad * 2 - 36

    // 网络（右侧列）
    let netX = npX + nd.width - pad - netW / 2 - 12
    nets.forEach((n, i) => {
      positions[n.id] = {
        x: netX, y: innerY + innerH / 2 + (i - (nets.length - 1) / 2) * (childH + 14),
        w: n.width, h: n.height,
      }
    })

    // 存储（底部行）
    const storY = npY + nd.height - pad - childH / 2
    stors.forEach((s, i) => {
      const totalW = stors.length * (childW + gap) - gap
      const startX = npX + (nd.width - totalW) / 2
      positions[s.id] = {
        x: startX + i * (childW + gap) + childW / 2,
        y: storY,
        w: s.width, h: s.height,
      }
    })

    // VM/容器（网格，最多5列）
    vms.forEach(vm => {
      const cols = Math.max(1, Math.min(vms.length, 5))
      const idx = vms.indexOf(vm)
      const row = Math.floor(idx / cols), col = idx % cols
      const vmAreaW = cols * (childW + gap) - gap
      const startX = innerX + (innerW - netW - (nets.length > 0 ? gap : 0) - vmAreaW) / 2
      positions[vm.id] = {
        x: startX + col * (childW + gap) + childW / 2,
        y: innerY + row * (childH + gap) + childH / 2,
        w: childW, h: childH,
      }
    })

    // 力模拟碰撞避免
    if (vms.length > 1) {
      const sim = forceSimulation<HNode>(vms)
        .force('collision', forceCollide<HNode>().radius(() => Math.max(childW, childH) * 0.6).strength(0.8))
        .force('x', forceX<HNode>(d => d.x!).strength(0.6))
        .force('y', forceY<HNode>(d => d.y!).strength(0.6))
        .stop()
      for (let i = 0; i < 80; i++) sim.tick()
      vms.forEach(vm => {
        const hw = childW / 2, hh = childH / 2
        vm.x = Math.max(innerX + hw, Math.min(innerX + innerW - nets.length * (netW + gap) - hw, vm.x!))
        vm.y = Math.max(innerY + hh, Math.min(innerY + innerH - (stors.length > 0 ? childH + gap : 0) - hh, vm.y!))
        setPos(vm.id, vm.x!, vm.y!)
      })
    }
  })

  // HA 节点在集群下方
  // 集群级叶子（node_id 不匹配任何节点的 storage/network 等）
  // 策略：放到选中资源所在节点内（或第一个节点），节点自动扩大
  const clusterLeafs = leafList.value.filter(lf => !nodeParentMap.value.has(lf.id))
  if (clusterLeafs.length > 0) {
    // 找到目标节点：选中资源所在节点，或第一个节点
    let targetNd = pveNodes.value[0]
    if (highlightedLeafId) {
      const hlParent = nodeParentMap.value.get(highlightedLeafId)
      if (hlParent) targetNd = pveNodes.value.find(nd => nd.id === hlParent) || targetNd
    }
    // 如果有资源选中，找其所在节点
    if (!targetNd && pveNodes.value.length > 0) targetNd = pveNodes.value[0]
    if (targetNd) {
      // 把未匹配叶子加入目标节点的 leafs
      clusterLeafs.forEach(lf => {
        targetNd!.leafs.push(lf)
        nodeParentMap.value.set(lf.id, targetNd!.id)
      })
      // 重新计算目标节点尺寸
      const vms = targetNd.leafs.filter(c => ['vm', 'container'].includes(c.type))
      const nets = targetNd.leafs.filter(c => c.type === 'network')
      const stors = targetNd.leafs.filter(c => c.type === 'storage')
      const cols = Math.max(1, Math.min(vms.length, 5))
      const vmRows = Math.ceil(vms.length / cols)
      const vmAreaW = cols * (childW + gap) - gap
      const vmAreaH = vmRows * (childH + gap) - gap
      const netAreaW = nets.length > 0 ? netW + gap : 0
      const storRowH = stors.length > 0 ? childH + gap : 0
      targetNd.width = Math.max(pad * 2 + vmAreaW + netAreaW, pad * 2 + stors.length * (childW + gap) - gap, 200)
      targetNd.height = Math.max(pad + 32 + 16 + vmAreaH + storRowH + pad, 70)
      // 更新节点位置
      const np = positions[targetNd.id]
      np.w = targetNd.width
      np.h = targetNd.height
      // 重新布局该节点的子节点
      const innerX = np.x + pad
      const innerY = np.y + pad + 36
      const innerW = np.width - pad * 2
      const innerH = np.height - pad * 2 - 36
      // 网络（右侧列）
      let netX = np.x + np.width - pad - netW / 2 - 12
      nets.forEach((n, i) => {
        positions[n.id] = {
          x: netX, y: innerY + innerH / 2 + (i - (nets.length - 1) / 2) * (childH + 14),
          w: n.width, h: n.height,
        }
      })
      // 存储（底部行）
      const storY = np.y + np.height - pad - childH / 2
      stors.forEach((s, i) => {
        const totalW = stors.length * (childW + gap) - gap
        const startX = np.x + (np.width - totalW) / 2
        positions[s.id] = {
          x: startX + i * (childW + gap) + childW / 2,
          y: storY,
          w: s.width, h: s.height,
        }
      })
      // VM/容器（网格，最多5列）
      vms.forEach(vm => {
        const idx = vms.indexOf(vm)
        const row = Math.floor(idx / cols), col = idx % cols
        const vmAreaTotalW = cols * (childW + gap) - gap
        const startX = innerX + (innerW - netW - (nets.length > 0 ? gap : 0) - vmAreaTotalW) / 2
        positions[vm.id] = {
          x: startX + col * (childW + gap) + childW / 2,
          y: innerY + row * (childH + gap) + childH / 2,
          w: childW, h: childH,
        }
      })
    }
  }

  // 确保所有节点和子节点都被正确包含
  pveNodes.value.forEach(nd => recalcParent(nd.id))
  resolveNodeCollisions()
  pveNodes.value.forEach(nd => resolveLeafCollisions(nd.id))
  shrinkClusterToFit()
  computeEdges()
}

// ─── 碰撞检测与约束算法 ───
const LABEL_AREA_H = 44
const INNER_PAD = 36
const TITLE_H = 42

function rectsOverlap(ax: number, ay: number, aw: number, ah: number, bx: number, by: number, bw: number, bh: number) {
  return ax < bx + bw && ax + aw > bx && ay < by + bh && ay + ah > by
}

function recalcParent(nodeId: string) {
  const np = getPos(nodeId)
  const childIds = childMap.value.get(nodeId) || []
  if (!np || childIds.length === 0) return
  const edgePad = 26
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity
  childIds.forEach(cid => {
    const cp = getPos(cid)
    if (!cp) return
    minX = Math.min(minX, cp.x - cp.w / 2 - edgePad)
    minY = Math.min(minY, cp.y - cp.h / 2 - edgePad)
    maxX = Math.max(maxX, cp.x + cp.w / 2 + edgePad)
    maxY = Math.max(maxY, cp.y + cp.h / 2 + edgePad)
  })
  if (minX !== Infinity) {
    // 中心坐标：center = (min + max) / 2，宽高 = max - min
    np.x = (minX + maxX) / 2
    np.y = (minY + maxY) / 2
    np.w = Math.max(maxX - minX, 180)
    np.h = Math.max(maxY - minY, 64)
  }
}

function resolveLeafCollisions(parentId: string) {
  const childIds = childMap.value.get(parentId) || []
  for (let i = 0; i < childIds.length; i++) {
    for (let j = i + 1; j < childIds.length; j++) {
      const a = getPos(childIds[i]), b = getPos(childIds[j])
      if (!a || !b) continue
      const ax = a.x - a.w / 2, ay = a.y - a.h / 2
      const bx = b.x - b.w / 2, by = b.y - b.h / 2
      if (rectsOverlap(ax, ay, a.w, a.h, bx, by, b.w, b.h)) {
        const overlapX = Math.min(ax + a.w - bx, bx + b.w - ax)
        const overlapY = Math.min(ay + a.h - by, by + b.h - ay)
        if (overlapX < overlapY) {
          const push = overlapX / 2 + 1
          if (a.x < b.x) { a.x -= push; b.x += push } else { a.x += push; b.x -= push }
        } else {
          const push = overlapY / 2 + 1
          if (a.y < b.y) { a.y -= push; b.y += push } else { a.y += push; b.y -= push }
        }
      }
    }
  }
}

function resolveNodeCollisions() {
  const nodes = pveNodes.value
  for (let i = 0; i < nodes.length; i++) {
    for (let j = i + 1; j < nodes.length; j++) {
      const a = getPos(nodes[i].id), b = getPos(nodes[j].id)
      if (!a || !b) continue
      const ax = a.x - a.w / 2, ay = a.y - a.h / 2
      const bx = b.x - b.w / 2, by = b.y - b.h / 2
      if (rectsOverlap(ax, ay, a.w, a.h, bx, by, b.w, b.h)) {
        const overlapY = Math.min(ay + a.h - by, by + b.h - ay)
        const push = overlapY / 2 + 2
        if (a.y < b.y) { a.y -= push; b.y += push } else { a.y += push; b.y -= push }
      }
    }
  }
}

function shrinkClusterToFit() {
  if (!clusterNode.value) return
  const cp = getPos(clusterNode.value.id)
  if (!cp) return
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity

  pveNodes.value.forEach(nd => {
    const np = getPos(nd.id)
    if (!np) return
    minX = Math.min(minX, np.x - np.w / 2)
    minY = Math.min(minY, np.y - np.h / 2)
    maxX = Math.max(maxX, np.x + np.w / 2)
    maxY = Math.max(maxY, np.y + np.h / 2)
  })

  leafList.value.forEach(lf => {
    if (nodeParentMap.value.has(lf.id)) return
    const lp = getPos(lf.id)
    if (!lp) return
    minX = Math.min(minX, lp.x - lf.width / 2)
    minY = Math.min(minY, lp.y - lf.height / 2)
    maxX = Math.max(maxX, lp.x + lf.width / 2)
    maxY = Math.max(maxY, lp.y + lf.height / 2)
  })

  if (minX !== Infinity) {
    cp.x = minX - INNER_PAD
    cp.y = minY - INNER_PAD - TITLE_H
    cp.w = Math.max(300, maxX - minX + INNER_PAD * 2)
    cp.h = Math.max(200, maxY - minY + INNER_PAD * 2 + TITLE_H)
  }
}

function containAndShrinkCluster() {
  if (!clusterNode.value) return
  const cp = getPos(clusterNode.value.id)
  if (!cp) return

  // 约束所有 pveNodes 在集群内
  pveNodes.value.forEach(nd => {
    const np = getPos(nd.id)
    if (!np) return
    const hw = np.w / 2, hh = np.h / 2
    const clampedX = Math.max(cp.x + INNER_PAD + hw, Math.min(cp.x + cp.w - INNER_PAD - hw, np.x))
    const clampedY = Math.max(cp.y + INNER_PAD + TITLE_H + hh, Math.min(cp.y + cp.h - INNER_PAD - hh, np.y))
    const dx = clampedX - np.x, dy = clampedY - np.y
    np.x = clampedX; np.y = clampedY
    nd.leafs.forEach(c => { const lp = getPos(c.id); if (lp) { lp.x += dx; lp.y += dy } })
  })

  // 约束集群级叶子节点
  leafList.value.forEach(lf => {
    if (nodeParentMap.value.has(lf.id)) return
    const lp = getPos(lf.id)
    if (!lp) return
    const hw = lf.width / 2, hh = lf.height / 2
    lp.x = Math.max(cp.x + INNER_PAD + hw, Math.min(cp.x + cp.w - INNER_PAD - hw, lp.x))
    lp.y = Math.max(cp.y + INNER_PAD + TITLE_H + hh, Math.min(cp.y + cp.h - INNER_PAD - hh, lp.y))
  })

  shrinkClusterToFit()
}

// ─── 坐标转换（client 像素 → scene 坐标） ───
function clientToScene(clientX: number, clientY: number): { x: number; y: number } {
  const rect = svgRef.value!.getBoundingClientRect()
  return {
    x: (clientX - rect.left - panX.value) / scale.value,
    y: (clientY - rect.top - panY.value) / scale.value,
  }
}

// ─── 拖拽处理 ───
function onSvgMouseDown(e: MouseEvent) {
  if ((e.target as Element).tagName !== 'svg') return
  dragTargetType.value = 'canvas'
  dragStartClientX = e.clientX
  dragStartClientY = e.clientY
  dragMoved = false
}

function onClusterMouseDown(e: MouseEvent) {
  dragTargetType.value = 'cluster'
  dragTargetId.value = ''
  dragStartClientX = e.clientX
  dragStartClientY = e.clientY
  dragMoved = false
}

function onNodeMouseDown(e: MouseEvent, nodeId: string) {
  dragTargetType.value = 'node'
  dragTargetId.value = nodeId
  const scene = clientToScene(e.clientX, e.clientY)
  const p = getPos(nodeId)
  if (p) {
    dragStartSceneX = scene.x - p.x
    dragStartSceneY = scene.y - p.y
  }
  dragStartClientX = e.clientX
  dragStartClientY = e.clientY
  dragMoved = false
}

function onLeafMouseDown(e: MouseEvent, leafId: string) {
  dragTargetType.value = 'leaf'
  dragTargetId.value = leafId
  const scene = clientToScene(e.clientX, e.clientY)
  const p = getPos(leafId)
  if (p) {
    dragStartSceneX = scene.x - p.x
    dragStartSceneY = scene.y - p.y
  }
  dragStartClientX = e.clientX
  dragStartClientY = e.clientY
  dragMoved = false
}

function onMouseMove(e: MouseEvent) {
  const dt = dragTargetType.value
  if (!dt) return
  dragMoved = true
  const dx = e.clientX - dragStartClientX
  const dy = e.clientY - dragStartClientY

  if (dt === 'canvas') {
    panX.value += dx
    panY.value += dy
    dragStartClientX = e.clientX
    dragStartClientY = e.clientY
    return
  }

  // 场景坐标增量（除 scale，因为 mouse delta 在 client 空间）
  const sdx = dx / scale.value
  const sdy = dy / scale.value

  if (dt === 'cluster') {
    // 移动整个场景
    const cp = clusterNode.value && getPos(clusterNode.value.id)
    if (!cp) return
    Object.keys(positions).forEach(id => {
      positions[id].x += sdx
      positions[id].y += sdy
    })
    dragStartClientX = e.clientX
    dragStartClientY = e.clientY
    computeEdges()
    return
  }

  if (dt === 'node') {
    const nd = pveNodes.value.find(n => n.id === dragTargetId.value)
    const np = getPos(dragTargetId.value)
    if (!np) return
    // 自由移动（不限制在集群内）
    np.x += sdx
    np.y += sdy
    // 子级跟随
    nd?.leafs.forEach(c => { const lp = getPos(c.id); if (lp) { lp.x += sdx; lp.y += sdy } })
    recalcParent(dragTargetId.value)
    resolveNodeCollisions()
    pveNodes.value.forEach(n => resolveLeafCollisions(n.id))
    // 集群自动扩大/缩小以包裹所有子节点
    shrinkClusterToFit()
    dragStartClientX = e.clientX
    dragStartClientY = e.clientY
    computeEdges()
    return
  }

  if (dt === 'leaf') {
    const lp = getPos(dragTargetId.value)
    if (!lp) return
    // 自由移动（不限制在父级或集群内）
    lp.x += sdx
    lp.y += sdy
    // 父级自动扩大以包裹子节点
    const parentId = nodeParentMap.value.get(dragTargetId.value)
    if (parentId) {
      recalcParent(parentId)
    }
    resolveNodeCollisions()
    pveNodes.value.forEach(n => resolveLeafCollisions(n.id))
    shrinkClusterToFit()
    dragStartClientX = e.clientX
    dragStartClientY = e.clientY
    computeEdges()
    return
  }
}

function onMouseUp() {
  dragTargetType.value = ''
  dragTargetId.value = ''
}

function onLeafClick(leafId: string) {
  if (dragMoved) return // 拖拽时不触发详情
  const lf = leafList.value.find(l => l.id === leafId)
  if (!lf) return
  showDetails(lf)
}

// ─── 详情面板 ───
function showDetails(node: HNode) {
  const d: Record<string, string> = {}
  if (node.type === 'node') {
    d[t('smartAnalysis.dependencyMapping.cpuLoad')] = node.cpu_load != null ? `${Number(node.cpu_load).toFixed(1)}%` : '-'
    d[t('smartAnalysis.dependencyMapping.memory')] = node.memory_usage_pct ? `${node.memory_usage_pct.toFixed(1)}%` : '-'
    d[t('smartAnalysis.dependencyMapping.ip')] = node.ip_address || '-'
    d[t('smartAnalysis.dependencyMapping.status')] = node.status || '-'
  } else if (node.type === 'vm' || node.type === 'container') {
    d[t('smartAnalysis.dependencyMapping.vmid')] = String(node.vmid || '-')
    d[t('smartAnalysis.dependencyMapping.cpuCores')] = String(node.cpu_cores || '-')
    d[t('smartAnalysis.dependencyMapping.memory')] = node.memory_mb ? `${(node.memory_mb / 1024).toFixed(1)} GB` : '-'
    d[t('smartAnalysis.dependencyMapping.status')] = node.status || '-'
    if (node.ha_enabled) d['HA'] = `${t('smartAnalysis.dependencyMapping.legendHA')} · ${node.ha_group || '-'}`
  } else if (node.type === 'storage') {
    d[t('smartAnalysis.dependencyMapping.type')] = node.storage_type || '-'
    d[t('smartAnalysis.dependencyMapping.totalCapacity')] = node.total_gb ? `${node.total_gb} GB` : '-'
    d[t('smartAnalysis.dependencyMapping.used')] = node.used_gb ? `${node.used_gb} GB` : '-'
  } else if (node.type === 'network') {
    d[t('smartAnalysis.dependencyMapping.type')] = node.net_type || '-'
    d[t('smartAnalysis.dependencyMapping.address')] = node.address || '-'
  } else if (node.type === 'ceph') {
    d[t('smartAnalysis.dependencyMapping.health')] = node.health || '-'
    d[t('smartAnalysis.dependencyMapping.osdCount')] = String(node.total_osds || '-')
  }
  selectedNode.value = { name: node.name, type: node.type, details: d }
}

// ─── 缩放控制 ───
function zoomBy(k: number) {
  const newScale = Math.max(minScale, Math.min(maxScale, scale.value * k))
  const rect = svgRef.value?.getBoundingClientRect()
  if (rect) {
    const mx = rect.width / 2
    const my = rect.height / 2
    panX.value = mx - (mx - panX.value) * (newScale / scale.value)
    panY.value = my - (my - panY.value) * (newScale / scale.value)
  }
  scale.value = newScale
}

function zoomTo(k: number) {
  const rect = svgRef.value?.getBoundingClientRect()
  if (rect) {
    const mx = rect.width / 2
    const my = rect.height / 2
    panX.value = mx - (mx - panX.value) * (k / scale.value)
    panY.value = my - (my - panY.value) * (k / scale.value)
  }
  scale.value = k
}

function fitView() {
  const ids = Object.keys(positions)
  if (!ids.length) return
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity
  ids.forEach(id => {
    const p = positions[id]
    minX = Math.min(minX, p.x - p.w / 2)
    minY = Math.min(minY, p.y - p.h / 2)
    maxX = Math.max(maxX, p.x + p.w / 2)
    maxY = Math.max(maxY, p.y + p.h / 2)
  })
  const rect = svgRef.value!.getBoundingClientRect()
  const pad = 60
  const contentW = maxX - minX + pad * 2
  const contentH = maxY - minY + pad * 2
  // 确保图不超出画布，使用更保守的缩放
  const k = Math.min(rect.width / contentW, rect.height / contentH, 1.2)
  const centerX = (minX + maxX) / 2
  const centerY = (minY + maxY) / 2
  scale.value = Math.max(minScale, Math.min(maxScale, k))
  // 偏右显示，留出左侧空间给选择器和详情面板
  panX.value = rect.width * 0.6 - centerX * scale.value
  panY.value = rect.height / 2 - centerY * scale.value
}

function onWheel(e: WheelEvent) {
  const delta = e.deltaY > 0 ? -0.08 : 0.08
  const newScale = Math.max(minScale, Math.min(maxScale, scale.value + delta))
  const rect = svgRef.value!.getBoundingClientRect()
  const mx = e.clientX - rect.left
  const my = e.clientY - rect.top
  panX.value = mx - (mx - panX.value) * (newScale / scale.value)
  panY.value = my - (my - panY.value) * (newScale / scale.value)
  scale.value = newScale
}

// ─── 资源选择 ───
function onResourceTypeChange() {
  selectedResourceId.value = undefined
  highlightedLeafId.value = ''
  // 仅重置下拉列表，不刷新图
}

/** 选择具体资源 → 加载图（只包含该资源）并高亮 */
function onResourceChange() {
  if (!selectedResourceId.value) {
    // 清空选择 → 回到只有集群+节点的图
    highlightedLeafId.value = ''
    loadData()
    return
  }
  loadData()
}

/** 平移视图使指定叶子节点居中显示，并调整缩放以展示上下文 */
function panToLeaf(leafId: string) {
  const pos = getPos(leafId)
  if (!pos || !svgRef.value) return
  const rect = svgRef.value.getBoundingClientRect()
  
  // 计算包含该叶子节点及其父节点的包围盒
  const parentId = nodeParentMap.value.get(leafId)
  const parentPos = parentId ? getPos(parentId) : null
  
  let minX = pos.x - pos.w / 2
  let minY = pos.y - pos.h / 2
  let maxX = pos.x + pos.w / 2
  let maxY = pos.y + pos.h / 2
  
  // 如果有父节点，扩展包围盒以包含父节点
  if (parentPos) {
    minX = Math.min(minX, parentPos.x - parentPos.w / 2)
    minY = Math.min(minY, parentPos.y - parentPos.h / 2)
    maxX = Math.max(maxX, parentPos.x + parentPos.w / 2)
    maxY = Math.max(maxY, parentPos.y + parentPos.h / 2)
  }
  
  const contentW = maxX - minX
  const contentH = maxY - minY
  
  // 目标：占画布70%的宽或高
  const targetW = rect.width * 0.7
  const targetH = rect.height * 0.7
  const k = Math.min(targetW / contentW, targetH / contentH, 1.2)
  
  scale.value = Math.max(minScale, Math.min(maxScale, k))
  
  const centerX = (minX + maxX) / 2
  const centerY = (minY + maxY) / 2
  // 居中显示
  panX.value = rect.width / 2 - centerX * scale.value
  panY.value = rect.height / 2 - centerY * scale.value
}

async function loadResourceLists() {
  const cid = clusterStore.currentClusterId
  if (!cid) return
  try {
    const [vms, cts] = await Promise.all([getVMs({ cluster_id: cid }), getContainers({ cluster_id: cid })])
    vmList.value = vms; containerList.value = cts
  } catch (e) { console.error(e) }
}

async function loadData() {
  const gen = ++loadGeneration.value // 递增世代号，后续异步操作检查是否过期
  loading.value = true
  initDone.value = false
  highlightedLeafId.value = ''
  selectedNode.value = null
  // 清理旧数据
  Object.keys(positions).forEach(k => delete positions[k])
  edgeData.value = []
  clusterNode.value = null
  pveNodes.value = []
  leafList.value = []
  childMap.value = new Map()
  nodeParentMap.value = new Map()
  scale.value = 1; panX.value = 0; panY.value = 0

  try {
    if (!clusterStore.clusterList.length) await clusterStore.fetchClusters()
    if (gen !== loadGeneration.value) return // fetchClusters 可能触发 watcher，已过期则退出

    const params: any = { cluster_id: clusterStore.currentClusterId }
    if (selectedResourceType.value && selectedResourceId.value) {
      params.resource_type = selectedResourceType.value
      params.resource_id = selectedResourceId.value
    }
    graphData.value = await getDependencyGraph(params)
    if (gen !== loadGeneration.value) return
    if (!graphData.value.nodes.length) { loading.value = false; return }

    buildHierarchy(graphData.value)
    await nextTick()
    layoutGraph()
    // 先计算自适应位置，再渲染，避免图形先出现在原点再跳到居中
    if (selectedResourceType.value && selectedResourceId.value) {
      const leaf = leafList.value[0]
      if (leaf) {
        highlightedLeafId.value = leaf.id
        // 延迟一帧再调整视图，确保布局已生效
        await nextTick()
        panToLeaf(leaf.id)
      }
    } else {
      fitView()
    }
    initDone.value = true
    // 具体资源详情在渲染完成后显示
    if (selectedResourceType.value && selectedResourceId.value) {
      const leaf = leafList.value[0]
      if (leaf) showDetails(leaf)
    }
  } catch (e) { console.error(e) }
  finally { loading.value = false }
}

// ─── 生命周期 ───
onMounted(async () => {
  await loadResourceLists()
  await nextTick()
  await loadData()
})

onBeforeUnmount(() => {
  // 清理所有引用
  Object.keys(positions).forEach(k => delete positions[k])
})

watch(() => clusterStore.currentClusterId, async () => {
  selectedNode.value = null
  selectedResourceType.value = ''
  selectedResourceId.value = undefined
  highlightedLeafId.value = ''
  await loadResourceLists()
  await loadData()
})
</script>

<style scoped>
.page-container { width: 100%; height: 100%; display: flex; flex-direction: column; position: relative; }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; flex-wrap: wrap; gap: 12px; }
.page-title { font-size: 24px; font-weight: 700; color: var(--text-heading); margin: 0; }
.page-desc { font-size: 14px; color: var(--text-muted); margin: 4px 0 0; }
.toolbar { display: flex; align-items: center; gap: 0; background: var(--bg-secondary, #f5f7fa); border: 1px solid var(--border-color, #e4e7ed); border-radius: 8px; padding: 4px 8px; height: 36px; }
.toolbar-group { display: flex; align-items: center; gap: 4px; padding: 0 6px; }
.toolbar-divider { width: 1px; height: 18px; background: var(--border-color, #dcdfe6); flex-shrink: 0; }
.toolbar-btn { width: 26px; height: 26px; display: flex; align-items: center; justify-content: center; border: 1px solid var(--border-color, #dcdfe6); border-radius: 6px; background: var(--bg-card, #fff); color: var(--text-primary, #303133); font-size: 14px; cursor: pointer; transition: all 0.15s; line-height: 1; }
.toolbar-btn:hover { border-color: #409eff; color: #409eff; }
.toolbar-btn:active { transform: scale(0.92); }
.toolbar-zoom-val { font-size: 12px; color: var(--text-muted, #909399); min-width: 36px; text-align: center; font-variant-numeric: tabular-nums; user-select: none; }
.toolbar-btn-text { height: 26px; padding: 0 10px; display: flex; align-items: center; justify-content: center; border: 1px solid var(--border-color, #dcdfe6); border-radius: 6px; background: var(--bg-card, #fff); color: var(--text-secondary, #606266); font-size: 12px; cursor: pointer; transition: all 0.15s; white-space: nowrap; }
.toolbar-btn-text:hover { border-color: #409eff; color: #409eff; }
.toolbar-btn-text:active { transform: scale(0.92); }

.graph-container { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 16px; flex: 1; display: flex; flex-direction: column; min-height: 0; overflow: hidden; position: relative; }
.unified-panel { position: absolute; top: 12px; left: 12px; z-index: 10; display: flex; flex-direction: column; gap: 8px; background: var(--bg-card, #fff); border: 1px solid var(--border-color, #e4e7ed); border-radius: 10px; padding: 10px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); max-width: 260px; }
.panel-section { display: flex; flex-direction: column; gap: 8px; }
.panel-section .selector-item { display: flex; align-items: center; gap: 8px; }
.panel-section .selector-label { font-size: 12px; color: var(--text-secondary, #606266); white-space: nowrap; min-width: 56px; text-align: right; }
.panel-detail { border-top: 1px solid var(--border-color, #e4e7ed); padding-top: 10px; }
.empty-state { display: flex; align-items: center; justify-content: center; flex: 1; }
.graph-svg { display: block; width: 100%; flex: 1; min-height: 0; cursor: grab; }
.graph-svg:active { cursor: grabbing; }
.graph-svg .svg-text-primary { fill: var(--text-heading, #13141a); }
.graph-svg .svg-text-muted { fill: var(--text-muted, #787c8a); }

/* 背景节点 */
.bg-node { cursor: grab; }
.bg-node:active { cursor: grabbing; }
.bg-node.dragging rect { stroke-width: 3; filter: brightness(1.05); }
.bg-node:hover rect { filter: brightness(1.05); stroke-width: 3; }

/* 集群背景 */
.bg-cluster { cursor: grab; }
.bg-cluster:active { cursor: grabbing; }

/* 叶子卡片 */
.leaf-card { cursor: pointer; }
.leaf-card.dragging rect { stroke-width: 3; filter: brightness(1.1); }
.leaf-card:hover rect { stroke-width: 3; }

/* 图例 */
.legend-bar { display: flex; align-items: center; gap: 6px; margin-top: 16px; padding: 8px 14px; background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 10px; flex-wrap: wrap; }
.legend-item { display: flex; align-items: center; gap: 5px; font-size: 12px; color: var(--text-secondary); padding: 4px 10px; border-radius: 6px; cursor: pointer; transition: all 0.2s; user-select: none; border: 1px solid transparent; }
.legend-item:hover { background: rgba(64,158,255,0.06); }
.legend-dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }

/* 详情面板（统一面板内） */
.panel-detail .detail-header { display: flex; align-items: center; justify-content: space-between; padding: 0 0 8px; }
.panel-detail .detail-header h3 { margin: 0; font-size: 14px; font-weight: 600; color: var(--text-heading); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.panel-detail .detail-close { width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; border: none; background: transparent; color: var(--text-muted); font-size: 16px; cursor: pointer; border-radius: 6px; transition: all 0.2s; }
.panel-detail .detail-close:hover { background: rgba(245,108,108,0.1); color: #f56c6c; }
.panel-detail .detail-body { padding: 0; }
.panel-detail .detail-row { display: flex; justify-content: space-between; align-items: center; padding: 6px 0; border-bottom: 1px dashed var(--border-color); }
.panel-detail .detail-row:last-child { border-bottom: none; }
.panel-detail .detail-label { font-size: 12px; color: var(--text-muted); }
.panel-detail .detail-value { font-size: 12px; color: var(--text-primary); font-weight: 500; }
.fade-enter-active, .fade-leave-active { transition: all 0.3s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; transform: translateY(-10px); }
</style>
