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
          <el-select v-model="selectedResourceId" :placeholder="t('smartAnalysis.dependencyMapping.selectResourcePlaceholder')" filterable clearable @change="onResourceChange" style="width: 200px" size="small">
            <el-option v-for="item in resourceOptions" :key="item.id" :label="`${item.name} (${item.vmid})`" :value="item.id" />
          </el-select>
        </div>
      </div>
      <div v-if="!loading && !graphData.nodes.length" class="empty-state">
        <el-empty :description="!selectedResourceType || !selectedResourceId ? '请先选择虚拟机/容器' : t('smartAnalysis.dependencyMapping.emptyDesc')" />
      </div>
      <svg ref="svgRef" class="graph-svg"></svg>
    </div>

    <div class="legend-bar">
      <span v-for="item in legendItems" :key="item.type" class="legend-item" @click="toggleType(item.type)">
        <span class="legend-dot" :style="{ background: item.color }"></span>{{ item.label }}
      </span>
    </div>

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
import { ref, onMounted, onBeforeUnmount, computed, watch, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import * as d3 from 'd3'
import { getDependencyGraph, type DependencyGraph } from '@/api/dependency'
import { useClusterStore } from '@/stores/cluster'
import { getVMs, type VMInfo } from '@/api/vms'
import { getContainers, type ContainerInfo } from '@/api/containers'

const { t } = useI18n()
const clusterStore = useClusterStore()

const loading = ref(false)
const graphData = ref<DependencyGraph>({ nodes: [], edges: [] })
const selectedNode = ref<any>(null)
const svgRef = ref<SVGSVGElement>()
const zoomPercent = ref(100)

const selectedResourceType = ref<'all' | 'vm' | 'container' | ''>('')
const selectedResourceId = ref<number | undefined>(undefined)
const vmList = ref<VMInfo[]>([])
const containerList = ref<ContainerInfo[]>([])
const hiddenTypes = ref(new Set<string>())

let svg: d3.Selection<SVGSVGElement, unknown, null, undefined> | null = null
let g: d3.Selection<SVGGElement, unknown, null, undefined> | null = null
let zoomBehavior: d3.ZoomBehavior<SVGSVGElement, unknown> | null = null

// D3 数据类型
interface D3Edge { source: string | HNode; target: string | HNode; type: string; color: string; dashed: boolean }

const resourceOptions = computed(() => {
  if (selectedResourceType.value === 'vm') return vmList.value.map(vm => ({ id: vm.id, name: vm.name, vmid: vm.vmid }))
  if (selectedResourceType.value === 'container') return containerList.value.map(ct => ({ id: ct.id, name: ct.name, vmid: ct.vmid }))
  return []
})

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
  updateVisibility()
}

// 颜色
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

function getSubLabel(n: any): string {
  if (n.type === 'node') return `${n.cpu_load ? (n.cpu_load * 100).toFixed(0) + '%' : ''} ${n.ip_address || ''}`.trim()
  if (n.type === 'vm' || n.type === 'container') {
    const b = `${n.cpu_cores || 0}核 ${n.memory_mb ? (n.memory_mb / 1024).toFixed(0) + 'G' : ''}`
    return n.ha_enabled ? `${b} · HA:${n.ha_group}` : b
  }
  if (n.type === 'storage') return `${n.total_gb || 0}GB ${n.storage_type || ''}`
  if (n.type === 'network') return `${n.net_type || ''} ${n.address || ''}`
  if (n.type === 'ceph') return `${n.health || ''} ${n.total_osds || 0} OSD`
  if (n.type === 'ha') return `成员: ${n.member_count || '?'}`
  return ''
}

function edgeStyle(type: string): { color: string; dashed: boolean } {
  if (type === 'cluster-node') return { color: '#409eff', dashed: false }
  if (type === 'vm-network' || type === 'container-network') return { color: '#8b5cf6', dashed: true }
  if (type === 'vm-storage' || type === 'container-storage') return { color: '#f56c6c', dashed: true }
  if (type === 'cluster-ceph') return { color: '#06b6d4', dashed: false }
  if (type.includes('ha')) return { color: '#f97316', dashed: true }
  if (type === 'cluster-sdn' || type === 'zone-vnet' || type === 'vnet-subnet') return { color: '#ec4899', dashed: false }
  return { color: '#909399', dashed: false }
}

const nodeSizes: Record<string, [number, number]> = {
  cluster: [160, 56], node: [150, 52], vm: [170, 48], container: [170, 48],
  storage: [170, 48], network: [170, 48], ceph: [150, 48], ha: [140, 44],
  sdn_zone: [130, 44], sdn_vnet: [120, 40], sdn_subnet: [120, 40],
}

/** 层次结构 */
interface HNode {
  id: string; type: string; name: string; width: number; height: number;
  x: number; y: number; children: HNode[]; leafs: HNode[];
  [key: string]: any;
}

/** 预计算层次布局 */
function buildHierarchy(apiData: DependencyGraph): { hierarchy: HNode[]; leafs: HNode[]; edges: D3Edge[]; haNodes: HNode[] } {
  const raw = apiData.nodes
  const cluster = raw.find(n => n.type === 'cluster')
  if (!cluster) return { hierarchy: [], leafs: [], edges: [], haNodes: [] }

  const nodeMap = new Map<string, HNode>()
  raw.forEach(n => {
    const [w, h] = nodeSizes[n.type] || [140, 44]
    nodeMap.set(n.id, { id: n.id, type: n.type, name: n.name, width: w, height: h, x: 0, y: 0, children: [], leafs: [], ...n })
  })

  const nodes = raw.filter(n => n.type === 'node').map(n => nodeMap.get(n.id)!)
  const leafNodes = raw.filter(n => !['cluster', 'node'].includes(n.type))
  const haNodes: HNode[] = []
  const nonHaLeafs: HNode[] = []

  leafNodes.forEach(n => {
    const hNode = nodeMap.get(n.id)!
    if (n.type === 'ha') { haNodes.push(hNode); return }
    nonHaLeafs.push(hNode)
    if (n.node_id != null) {
      const parent = nodes.find(nd => nd.node_id === n.node_id)
      if (parent) { parent.leafs.push(hNode); return }
    }
    // cluster-level children (ceph, sdn)
    if (cluster) nodeMap.get(cluster.id)!.leafs.push(hNode)
  })

  // 预计算每个 node 的布局
  const pad = 28, childW = 170, childH = 48, gap = 16, netW = 160
  nodes.forEach(node => {
    const vms = node.leafs.filter(c => ['vm', 'container'].includes(c.type))
    const nets = node.leafs.filter(c => c.type === 'network')
    const stors = node.leafs.filter(c => c.type === 'storage')

    if (vms.length === 0 && nets.length === 0 && stors.length === 0) {
      node.width = 180; node.height = 64; return
    }

    const cols = Math.max(1, Math.min(vms.length, 3))
    const vmRows = Math.ceil(vms.length / cols)
    const vmAreaW = cols * (childW + gap) - gap
    const vmAreaH = vmRows * (childH + gap) - gap
    const netAreaW = nets.length > 0 ? netW + gap : 0
    const storRowH = stors.length > 0 ? childH + gap : 0
    node.width = Math.max(pad * 2 + vmAreaW + netAreaW, pad * 2 + stors.length * (childW + gap) - gap, 180)
    node.height = pad + 28 + 12 + vmAreaH + storRowH + pad
  })

  // 预计算 cluster 尺寸
  let clusterW: number, clusterH: number
  if (nodes.length === 1) {
    const n = nodes[0]
    clusterW = n.width + pad * 2 + 40
    clusterH = n.height + pad * 2 + 60 + 40
  } else {
    const maxW = Math.max(...nodes.map(n => n.width))
    const gap2 = 40
    clusterW = maxW + pad * 2 + gap2 * 2
    clusterH = nodes.reduce((s, n) => s + n.height + gap2, 0) + 80
  }

  const clusterHNode = nodeMap.get(cluster.id)!
  clusterHNode.width = Math.max(clusterW, 300)
  clusterHNode.height = Math.max(clusterH, 200)

  return { hierarchy: [clusterHNode, ...nodes], leafs: nonHaLeafs, edges: buildEdges(apiData), haNodes }
}

function buildEdges(apiData: DependencyGraph): D3Edge[] {
  const edges: D3Edge[] = []
  apiData.edges.forEach(e => {
    // 过滤所有父子层级边（层级关系由嵌套布局表达，不需要连线）
    if (['cluster-node', 'node-storage', 'node-network', 'node-vm', 'node-container'].includes(e.type)) return
    const s = edgeStyle(e.type)
    edges.push({ source: e.source, target: e.target, type: e.type, ...s })
  })
  return edges
}

/** 初始化 D3 */
function initD3() {
  if (!svgRef.value) return
  const container = svgRef.value.parentElement!
  const width = container.clientWidth
  const height = container.clientHeight

  svg = d3.select(svgRef.value)
    .attr('width', '100%')
    .attr('height', '100%')
    .attr('viewBox', `0 0 ${width} ${height}`)

  // 滤镜
  const defs = svg.append('defs')
  defs.append('marker')
    .attr('id', 'arrowhead').attr('markerWidth', 10).attr('markerHeight', 7)
    .attr('refX', 10).attr('refY', 3.5).attr('orient', 'auto')
    .append('polygon').attr('points', '0 0, 10 3.5, 0 7').attr('fill', 'var(--text-muted)').attr('class', 'svg-arrow')
  const shadow = defs.append('filter').attr('id', 'shadow').attr('x', '-20%').attr('y', '-20%').attr('width', '140%').attr('height', '140%')
  shadow.append('feDropShadow').attr('dx', 0).attr('dy', 3).attr('stdDeviation', 5).attr('flood-color', 'rgba(0,0,0,0.15)')

  // 缩放
  g = svg.append('g')
  zoomBehavior = d3.zoom<SVGSVGElement, unknown>()
    .scaleExtent([0.2, 4])
    .on('zoom', (event) => {
      g!.attr('transform', event.transform)
      zoomPercent.value = Math.round(event.transform.k * 100)
    })
  svg.call(zoomBehavior)
}

/** 渲染图 */
function renderGraph() {
  if (!g || !svg) return
  g.selectAll('*').remove()

  const { hierarchy, leafs, edges, haNodes } = buildHierarchy(graphData.value)
  if (!hierarchy.length) return

  const container = svgRef.value!.parentElement!
  const svgW = container.clientWidth, svgH = container.clientHeight
  const cx = svgW / 2, cy = svgH / 2
  const pad = 28, childW = 170, childH = 48, gap = 16, netW = 160

  // ── 位置存储（可变，拖拽时更新） ──
  interface Pos { x: number; y: number; w: number; h: number }
  const pos = new Map<string, Pos>()
  function getPos(id: string) { return pos.get(id)! }
  function setPos(id: string, x: number, y: number) { const p = pos.get(id)!; p.x = x; p.y = y }

  // ── 1. 定位 cluster 和 nodes ──
  const clusterNode = hierarchy.find(n => n.type === 'cluster')!
  const pveNodes = hierarchy.filter(n => n.type === 'node')
  clusterNode.x = cx - clusterNode.width / 2
  clusterNode.y = cy - clusterNode.height / 2
  pos.set(clusterNode.id, { x: clusterNode.x, y: clusterNode.y, w: clusterNode.width, h: clusterNode.height })

  let ny = clusterNode.y + pad + 36
  pveNodes.forEach(nd => {
    nd.x = clusterNode.x + (clusterNode.width - nd.width) / 2
    nd.y = ny
    pos.set(nd.id, { x: nd.x, y: nd.y, w: nd.width, h: nd.height })
    ny += nd.height + 30
  })

  // ── 2. 父子关系索引 ──
  const childMap = new Map<string, string[]>()
  pveNodes.forEach(nd => { childMap.set(nd.id, nd.leafs.map(c => c.id)) })
  const nodeParentMap = new Map<string, string>()
  pveNodes.forEach(nd => nd.leafs.forEach(c => nodeParentMap.set(c.id, nd.id)))

  // ── 3. 定位 leaf 子节点 ──
  const allLeafs: HNode[] = []
  pveNodes.forEach(nd => {
    const vms = nd.leafs.filter(c => ['vm', 'container'].includes(c.type))
    const nets = nd.leafs.filter(c => c.type === 'network')
    const stors = nd.leafs.filter(c => c.type === 'storage')
    const innerX = nd.x + pad, innerY = nd.y + pad + 32
    const innerW = nd.width - pad * 2, innerH = nd.height - pad * 2 - 32

    let netX = nd.x + nd.width - pad - netW / 2 - 10
    nets.forEach((n, i) => {
      n.x = netX; n.y = innerY + innerH / 2 + (i - (nets.length - 1) / 2) * (childH + 10)
      pos.set(n.id, { x: n.x, y: n.y, w: n.width, h: n.height }); allLeafs.push(n)
    })

    const storY = nd.y + nd.height - pad - childH / 2
    stors.forEach((s, i) => {
      const totalW = stors.length * (childW + gap) - gap
      const startX = nd.x + (nd.width - totalW) / 2
      s.x = startX + i * (childW + gap) + childW / 2; s.y = storY
      pos.set(s.id, { x: s.x, y: s.y, w: s.width, h: s.height }); allLeafs.push(s)
    })

    vms.forEach(vm => {
      const cols = Math.max(1, Math.min(vms.length, 3))
      const idx = vms.indexOf(vm)
      const row = Math.floor(idx / cols), col = idx % cols
      const vmAreaW = cols * (childW + gap) - gap
      const startX = innerX + (innerW - netW - (nets.length > 0 ? gap : 0) - vmAreaW) / 2
      vm.x = startX + col * (childW + gap) + childW / 2
      vm.y = innerY + row * (childH + gap) + childH / 2
      pos.set(vm.id, { x: vm.x, y: vm.y, w: vm.width, h: vm.height }); allLeafs.push(vm)
    })

    if (vms.length > 1) {
      const sim = d3.forceSimulation<HNode>(vms)
        .force('collision', d3.forceCollide<HNode>().radius(() => Math.max(childW, childH) * 0.55).strength(0.8))
        .force('x', d3.forceX<HNode>(d => d.x!).strength(0.6))
        .force('y', d3.forceY<HNode>(d => d.y!).strength(0.6))
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

  haNodes.forEach((ha, i) => {
    ha.x = clusterNode.x + clusterNode.width / 2 + (i - (haNodes.length - 1) / 2) * 180
    ha.y = clusterNode.y + clusterNode.height + 60
    pos.set(ha.id, { x: ha.x, y: ha.y, w: ha.width, h: ha.height }); allLeafs.push(ha)
  })

  // 确保所有节点和子节点都被正确包含
  pveNodes.forEach(nd => expandParent(nd.id))
  resolveNodeCollisions()
  pveNodes.forEach(nd => resolveLeafCollisions(nd.id))

  // ── 4. 边路径计算函数 ──
  function edgePath(sId: string, tId: string): string {
    const sp = getPos(sId), tp = getPos(tId)
    if (!sp || !tp) return ''
    const dx = tp.x - sp.x, dy = tp.y - sp.y
    const dist = Math.sqrt(dx * dx + dy * dy) || 1
    const x1 = sp.x + (dx / dist) * (sp.w / 2), y1 = sp.y + (dy / dist) * (sp.h / 2)
    const x2 = tp.x - (dx / dist) * (tp.w / 2), y2 = tp.y - (dy / dist) * (tp.h / 2)
    const mx = (x1 + x2) / 2, my = (y1 + y2) / 2
    const off = Math.min(dist * 0.15, 50)
    return `M${x1},${y1} Q${mx + (-dy / dist) * off},${my + (dx / dist) * off} ${x2},${y2}`
  }

  // ── 5. 渲染层次背景（可拖拽） ──
  const bgG = g.append('g').attr('class', 'backgrounds')

  // Cluster 背景拖拽组
  const clusterG = bgG.append('g').style('cursor', 'grab')
  clusterG.append('rect').attr('rx', 20)
    .attr('fill', getColors('cluster').fill).attr('stroke', getColors('cluster').stroke)
    .attr('stroke-width', 2.5).attr('stroke-dasharray', '8,4')
  clusterG.append('text').attr('fill', 'var(--text-heading)').attr('font-size', 15)
    .attr('font-weight', 700).attr('class', 'svg-text-primary').text(clusterNode.name)

  function updateClusterG() {
    const p = getPos(clusterNode.id)
    clusterG.select('rect').attr('x', p.x).attr('y', p.y).attr('width', p.w).attr('height', p.h)
    clusterG.select('text').attr('x', p.x + 16).attr('y', p.y + 26)
  }
  updateClusterG()

  // Cluster 拖拽：移动所有子元素
  clusterG.call(d3.drag<SVGGElement, unknown>()
    .on('start', function() { d3.select(this).style('cursor', 'grabbing') })
    .on('drag', function(event) {
      const dx = event.dx, dy = event.dy
      // 移动 cluster
      const cp = getPos(clusterNode.id); cp.x += dx; cp.y += dy
      // 移动所有 node
      pveNodes.forEach(nd => { const np = getPos(nd.id); np.x += dx; np.y += dy })
      // 移动所有 leaf
      allLeafs.forEach(lf => { const lp = getPos(lf.id); lp.x += dx; lp.y += dy })
      updateAll()
    })
    .on('end', function() { d3.select(this).style('cursor', 'grab') })
  )

  // Node 背景拖拽组
  const nodeGroups = new Map<string, d3.Selection<SVGGElement, unknown, SVGGElement, unknown>>()
  pveNodes.forEach(nd => {
    const ng = bgG.append('g').style('cursor', 'grab')
    ng.append('rect').attr('rx', 14)
      .attr('fill', getColors('node').fill).attr('stroke', getColors('node').stroke)
      .attr('stroke-width', 2).attr('stroke-dasharray', '6,3')
    ng.append('text').attr('fill', 'var(--text-heading)').attr('font-size', 13)
      .attr('font-weight', 700).attr('class', 'svg-text-primary')
      .text(`${nd.name}  ${getSubLabel(nd)}`)
    nodeGroups.set(nd.id, ng)

    ng.call(d3.drag<SVGGElement, unknown>()
      .on('start', function() { d3.select(this).style('cursor', 'grabbing') })
      .on('drag', function(event) {
        const dx = event.dx, dy = event.dy
        const np = getPos(nd.id); np.x += dx; np.y += dy
        nd.leafs.forEach(c => { const lp = getPos(c.id); lp.x += dx; lp.y += dy })
        expandParent(nd.id)
        resolveNodeCollisions()
        pveNodes.forEach(n => resolveLeafCollisions(n.id))
        updateAll()
      })
      .on('end', function() { d3.select(this).style('cursor', 'grab') })
    )
  })

  function updateNodeGs() {
    pveNodes.forEach(nd => {
      const p = getPos(nd.id), ng = nodeGroups.get(nd.id)!
      ng.select('rect').attr('x', p.x).attr('y', p.y).attr('width', p.w).attr('height', p.h)
      ng.select('text').attr('x', p.x + 12).attr('y', p.y + 22)
    })
  }

  // ── 6. 父节点边界扩充（不覆盖标签区域） ──
  const LABEL_AREA_H = 40  // 标签占用的顶部区域高度

  function expandParent(nodeId: string) {
    const np = getPos(nodeId)
    const childIds = childMap.get(nodeId) || []
    const edgePad = 20
    let maxRight = np.x + np.w, maxBottom = np.y + np.h
    childIds.forEach(cid => {
      const cp = getPos(cid)
      maxRight = Math.max(maxRight, cp.x + cp.w / 2 + edgePad)
      maxBottom = Math.max(maxBottom, cp.y + cp.h / 2 + edgePad)
    })
    if (maxRight > np.x + np.w) np.w = maxRight - np.x
    if (maxBottom > np.y + np.h) np.h = maxBottom - np.y
  }

  // ── 6b. 同级碰撞检测 ──
  function rectsOverlap(ax: number, ay: number, aw: number, ah: number, bx: number, by: number, bw: number, bh: number) {
    return ax < bx + bw && ax + aw > bx && ay < by + bh && ay + ah > by
  }

  function resolveLeafCollisions(parentId: string) {
    const childIds = childMap.get(parentId) || []
    for (let i = 0; i < childIds.length; i++) {
      for (let j = i + 1; j < childIds.length; j++) {
        const a = getPos(childIds[i]), b = getPos(childIds[j])
        if (!a || !b) continue
        const aw = a.w, ah = a.h, bw = b.w, bh = b.h
        const ax = a.x - aw / 2, ay = a.y - ah / 2
        const bx = b.x - bw / 2, by = b.y - bh / 2
        if (rectsOverlap(ax, ay, aw, ah, bx, by, bw, bh)) {
          const overlapX = Math.min(ax + aw - bx, bx + bw - ax)
          const overlapY = Math.min(ay + ah - by, by + bh - ay)
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
    for (let i = 0; i < pveNodes.length; i++) {
      for (let j = i + 1; j < pveNodes.length; j++) {
        const a = getPos(pveNodes[i].id), b = getPos(pveNodes[j].id)
        if (!a || !b) continue
        const ax = a.x, ay = a.y, bx = b.x, by = b.y
        if (rectsOverlap(ax, ay, a.w, a.h, bx, by, b.w, b.h)) {
          const overlapY = Math.min(ay + a.h - by, by + b.h - ay)
          const push = overlapY / 2 + 2
          if (a.y < b.y) { a.y -= push; b.y += push } else { a.y += push; b.y -= push }
        }
      }
    }
  }

  // ── 7. 渲染边 ──
  const edgeG = g.append('g').attr('class', 'edges')
  const edgePaths: { el: d3.Selection<SVGPathElement, unknown, SVGGElement, unknown>; srcId: string; tgtId: string }[] = []
  edges.forEach(e => {
    const srcId = typeof e.source === 'string' ? e.source : (e.source as any).id
    const tgtId = typeof e.target === 'string' ? e.target : (e.target as any).id
    if (!pos.has(srcId) || !pos.has(tgtId)) return
    const p = edgeG.append('path')
      .attr('fill', 'none').attr('stroke', e.color)
      .attr('stroke-width', e.dashed ? 1.5 : 2)
      .attr('stroke-dasharray', e.dashed ? '6,3' : '')
      .attr('marker-end', 'url(#arrowhead)')
      .attr('d', edgePath(srcId, tgtId))
      .style('opacity', 0)
    p.transition().duration(500).delay(200).style('opacity', 0.85)
    edgePaths.push({ el: p, srcId, tgtId })
  })

  // ── 8. 渲染叶子节点卡片（可拖拽） ──
  const nodeG = g.append('g').attr('class', 'nodes')
  const nodeSel = nodeG.selectAll<SVGGElement, HNode>('g')
    .data(allLeafs, d => d.id)
    .join('g')
    .style('cursor', 'pointer').style('opacity', 0)
    .on('click', (_, d) => showDetails(d))

  nodeSel.transition().duration(400).delay((_, i) => 100 + i * 30).style('opacity', 1)

  nodeSel.append('rect')
    .attr('width', d => d.width).attr('height', d => d.height)
    .attr('x', d => -d.width / 2).attr('y', d => -d.height / 2)
    .attr('rx', 10)
    .attr('fill', d => getColors(d.type).fill)
    .attr('stroke', d => getColors(d.type).stroke)
    .attr('stroke-width', 2).attr('filter', 'url(#shadow)')

  nodeSel.append('text')
    .attr('text-anchor', 'middle')
    .attr('y', d => getSubLabel(d) ? -5 : 0)
    .attr('dy', '0.35em')
    .attr('fill', 'var(--text-heading)').attr('font-size', 12).attr('font-weight', 600)
    .attr('class', 'svg-text-primary')
    .text(d => d.name)
    .each(function(d) {
      const maxW = d.width - 16, self = d3.select(this)
      while ((this as SVGTextElement).getComputedTextLength() > maxW && self.text()!.length > 3)
        self.text(self.text()!.slice(0, -4) + '...')
    })

  nodeSel.filter(d => !!getSubLabel(d))
    .append('text').attr('text-anchor', 'middle').attr('y', 10)
    .attr('fill', 'var(--text-muted)').attr('font-size', 10).attr('class', 'svg-text-muted')
    .text(d => getSubLabel(d))

  nodeSel.filter(d => d.ha_enabled)
    .append('g').each(function() {
      const badge = d3.select(this)
      badge.append('rect').attr('width', 28).attr('height', 14).attr('rx', 3).attr('fill', '#f97316').attr('opacity', 0.9)
      badge.append('text').attr('x', 14).attr('y', 11).attr('text-anchor', 'middle')
        .attr('font-size', 8).attr('font-weight', 700).attr('fill', '#fff').text('HA')
    })

  // Hover 效果
  nodeSel.on('mouseenter', function() {
    d3.select(this).select('rect').transition().duration(150).attr('stroke-width', 3)
  }).on('mouseleave', function() {
    d3.select(this).select('rect').transition().duration(150).attr('stroke-width', 2)
  })

  // 叶子节点拖拽
  nodeSel.call(d3.drag<SVGGElement, HNode>()
    .on('start', function() { d3.select(this).raise().select('rect').attr('stroke-width', 3) })
    .on('drag', function(event, d) {
      const lp = getPos(d.id)
      const newX = lp.x + event.dx, newY = lp.y + event.dy
      const hw = d.width / 2, hh = d.height / 2

      // 约束在父节点内
      const parentId = nodeParentMap.get(d.id)
      if (parentId) {
        const np = getPos(parentId)
        const minX = np.x + pad + hw
        const minY = np.y + pad + 32 + hh
        // 计算如果子节点移动到新位置，父节点需要扩展的量
        const needRight = newX + hw - (np.x + np.w - pad)
        const needBottom = newY + hh - (np.y + np.h - pad)

        // 右边界：允许扩展
        if (needRight > 0) np.w += needRight
        // 下边界：允许扩展
        if (needBottom > 0) np.h += needBottom

        // 左/上边界：硬约束（不允许覆盖标签区域）
        lp.x = Math.max(minX, newX)
        lp.y = Math.max(minY, newY)

        // 约束同级节点不重叠
        resolveLeafCollisions(parentId)
        expandParent(parentId)
      } else {
        lp.x = newX; lp.y = newY
      }

      // 约束节点间不重叠
      resolveNodeCollisions()
      // 同步子节点跟随父节点移动后，重新检查所有节点的子节点碰撞
      pveNodes.forEach(nd => resolveLeafCollisions(nd.id))

      updateAll()
    })
    .on('end', function() { d3.select(this).select('rect').attr('stroke-width', 2) })
  )

  // ── 9. 统一更新函数 ──
  function updateNodePositions() {
    nodeG.selectAll<SVGGElement, HNode>('g')
      .attr('transform', d => {
        const p = getPos(d.id); return p ? `translate(${p.x},${p.y})` : ''
      })
    // 更新 HA badge 位置
    nodeG.selectAll<SVGGElement, HNode>('g').each(function(d) {
      const badge = d3.select(this).select('g')
      if (!badge.empty()) badge.attr('transform', `${-d.width / 2 + 6}, ${-d.height / 2 + 5}`)
    })
  }

  function updateAll() {
    updateClusterG()
    updateNodeGs()
    edgePaths.forEach(ep => ep.el.interrupt().attr('d', edgePath(ep.srcId, ep.tgtId)).style('opacity', 0.85))
    updateNodePositions()
  }

  // 初始自适应
  setTimeout(() => fitView(), 600)
}

function showDetails(node: HNode) {
  const d: Record<string, string> = {}
  if (node.type === 'node') {
    d[t('smartAnalysis.dependencyMapping.cpuLoad')] = node.cpu_load ? `${(node.cpu_load * 100).toFixed(1)}%` : '-'
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
  } else if (node.type === 'ha') {
    d[t('smartAnalysis.dependencyMapping.haGroup')] = node.ha_group || node.name || '-'
    if (node.member_count) d['成员数量'] = String(node.member_count)
  }
  selectedNode.value = { name: node.name, type: node.type, details: d }
}

function updateVisibility() {
  if (!g) return
  g.selectAll<SVGGElement, HNode>('g.nodes g').style('opacity', function() {
    const node = d3.select(this).datum()
    return hiddenTypes.value.has(node.type) ? 0.1 : 1
  })
}

// 缩放控制
function zoomBy(k: number) { svg && zoomBehavior && svg.transition().duration(300).call(zoomBehavior.scaleBy, k) }
function zoomTo(k: number) { svg && zoomBehavior && svg.transition().duration(300).call(zoomBehavior.scaleTo, k) }
function fitView() {
  if (!g || !svg || !zoomBehavior) return
  const bounds = (g.node() as SVGGElement).getBBox()
  if (bounds.width === 0) return
  const container = svgRef.value!.parentElement!
  const w = container.clientWidth, h = container.clientHeight
  const pad = 60
  const k = Math.min(w / (bounds.width + pad * 2), h / (bounds.height + pad * 2), 2)
  const tx = w / 2 - (bounds.x + bounds.width / 2) * k
  const ty = h / 2 - (bounds.y + bounds.height / 2) * k
  svg.transition().duration(500).call(zoomBehavior.transform, d3.zoomIdentity.translate(tx, ty).scale(k))
}

// 数据加载
function onResourceTypeChange() {
  selectedResourceId.value = undefined
  if (!selectedResourceType.value) { graphData.value = { nodes: [], edges: [] }; return }
  loadData()
}
function onResourceChange() {
  if (!selectedResourceId.value) { graphData.value = { nodes: [], edges: [] }; return }
  loadData()
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
  if (!selectedResourceType.value || !selectedResourceId.value) { graphData.value = { nodes: [], edges: [] }; return }
  loading.value = true
  try {
    if (!clusterStore.clusterList.length) await clusterStore.fetchClusters()
    graphData.value = await getDependencyGraph({
      cluster_id: clusterStore.currentClusterId,
      resource_type: selectedResourceType.value,
      resource_id: selectedResourceId.value,
    })
    await nextTick()
    renderGraph()
  } catch (e) { console.error(e) }
  finally { loading.value = false }
}

onMounted(async () => {
  await loadResourceLists()
  await nextTick()
  initD3()
})
onBeforeUnmount(() => {
  svg?.selectAll('*').remove()
})
watch(() => clusterStore.currentClusterId, async () => {
  selectedNode.value = null
  graphData.value = { nodes: [], edges: [] }
  selectedResourceType.value = ''
  selectedResourceId.value = undefined
  g?.selectAll('*').remove()
  await loadResourceLists()
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
.resource-selector-overlay { position: absolute; top: 12px; left: 12px; z-index: 10; display: flex; flex-direction: column; gap: 8px; background: var(--bg-card, #fff); border: 1px solid var(--border-color, #e4e7ed); border-radius: 10px; padding: 10px 12px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); }
.resource-selector-overlay .selector-item { display: flex; align-items: center; gap: 8px; }
.resource-selector-overlay .selector-label { font-size: 12px; color: var(--text-secondary, #606266); white-space: nowrap; min-width: 56px; text-align: right; }
.empty-state { display: flex; align-items: center; justify-content: center; flex: 1; }
.graph-svg { display: block; width: 100%; flex: 1; min-height: 0; }
.graph-svg .svg-text-primary { fill: var(--text-heading, #13141a); }
.graph-svg .svg-text-muted { fill: var(--text-muted, #787c8a); }
.graph-svg .svg-arrow { fill: var(--text-muted, #787c8a); }
.graph-svg path { stroke-opacity: 0.85; }
.legend-bar { display: flex; align-items: center; gap: 6px; margin-top: 16px; padding: 8px 14px; background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 10px; flex-wrap: wrap; }
.legend-item { display: flex; align-items: center; gap: 5px; font-size: 12px; color: var(--text-secondary); padding: 4px 10px; border-radius: 6px; cursor: pointer; transition: all 0.2s; user-select: none; border: 1px solid transparent; }
.legend-item:hover { background: rgba(64,158,255,0.06); }
.legend-dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
.detail-panel { position: absolute; right: 20px; top: 80px; width: 300px; background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); z-index: 100; }
.detail-header { display: flex; align-items: center; justify-content: space-between; padding: 16px; border-bottom: 1px solid var(--border-color); }
.detail-header h3 { margin: 0; font-size: 16px; font-weight: 600; color: var(--text-heading); }
.detail-close { width: 28px; height: 28px; display: flex; align-items: center; justify-content: center; border: none; background: transparent; color: var(--text-muted); font-size: 18px; cursor: pointer; border-radius: 6px; transition: all 0.2s; }
.detail-close:hover { background: rgba(245,108,108,0.1); color: #f56c6c; }
.detail-body { padding: 16px; }
.detail-row { display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px dashed var(--border-color); }
.detail-row:last-child { border-bottom: none; }
.detail-label { font-size: 13px; color: var(--text-muted); }
.detail-value { font-size: 13px; color: var(--text-primary); font-weight: 500; }
.slide-enter-active, .slide-leave-active { transition: all 0.3s ease; }
.slide-enter-from, .slide-leave-to { transform: translateX(20px); opacity: 0; }
</style>
