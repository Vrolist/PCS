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
let simulation: d3.Simulation<D3Node, D3Edge> | null = null

// D3 数据类型
interface D3Node {
  id: string; type: string; name: string; x?: number; y?: number;
  fx?: number | null; fy?: number | null; nodeType?: string;
  width: number; height: number; [key: string]: any;
}
interface D3Edge { source: string | D3Node; target: string | D3Node; type: string; color: string; dashed: boolean }

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

/** 构建 D3 数据 */
function buildGraph(apiData: DependencyGraph) {
  const nodes: D3Node[] = []
  const edges: D3Edge[] = []

  apiData.nodes.forEach(n => {
    const [w, h] = nodeSizes[n.type] || [140, 44]
    nodes.push({ id: n.id, type: n.type, name: n.name, width: w, height: h, ...n })
  })

  // 过滤: node-storage / node-network / node-vm / node-container
  apiData.edges.forEach(e => {
    if (['node-storage', 'node-network', 'node-vm', 'node-container'].includes(e.type)) return
    const s = edgeStyle(e.type)
    edges.push({ source: e.source, target: e.target, type: e.type, ...s })
  })

  return { nodes, edges }
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

  const { nodes, edges } = buildGraph(graphData.value)
  if (!nodes.length) return

  const container = svgRef.value!.parentElement!
  const width = container.clientWidth
  const height = container.clientHeight

  // 力导向模拟
  simulation = d3.forceSimulation<D3Node>(nodes)
    .force('link', d3.forceLink<D3Node, D3Edge>(edges).id(d => d.id).distance(160))
    .force('charge', d3.forceManyBody().strength(-400))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collision', d3.forceCollide().radius(d => Math.max(d.width, d.height) * 0.7))
    .force('x', d3.forceX(width / 2).strength(0.05))
    .force('y', d3.forceY(height / 2).strength(0.05))
    .alphaDecay(0.03)

  // 边层
  const edgeG = g.append('g').attr('class', 'edges')
  const edgeSel = edgeG.selectAll<SVGPathElement, D3Edge>('path')
    .data(edges, d => `${typeof d.source === 'string' ? d.source : d.source.id}-${typeof d.target === 'string' ? d.target : d.target.id}`)
    .join('path')
    .attr('fill', 'none')
    .attr('stroke', d => d.color)
    .attr('stroke-width', 2)
    .attr('stroke-dasharray', d => d.dashed ? '6,3' : '')
    .attr('marker-end', 'url(#arrowhead)')

  // 节点层
  const nodeG = g.append('g').attr('class', 'nodes')
  const nodeSel = nodeG.selectAll<SVGGElement, D3Node>('g')
    .data(nodes, d => d.id)
    .join('g')
    .style('cursor', 'pointer')
    .style('opacity', 0)
    .call(d3.drag<SVGGElement, D3Node>()
      .on('start', (event, d) => {
        if (!event.active) simulation!.alphaTarget(0.3).restart()
        d.fx = d.x; d.fy = d.y
      })
      .on('drag', (event, d) => { d.fx = event.x; d.fy = event.y })
      .on('end', (event, d) => {
        if (!event.active) simulation!.alphaTarget(0)
        d.fx = null; d.fy = null
      })
    )
    .on('click', (_, d) => showDetails(d))

  // 入场动画
  nodeSel.transition().duration(500).delay((_, i) => i * 30).style('opacity', 1)

  // 节点矩形
  nodeSel.append('rect')
    .attr('width', d => d.width).attr('height', d => d.height)
    .attr('x', d => -d.width / 2).attr('y', d => -d.height / 2)
    .attr('rx', d => d.type === 'cluster' ? 16 : d.type === 'node' ? 12 : 10)
    .attr('fill', d => getColors(d.type).fill)
    .attr('stroke', d => getColors(d.type).stroke)
    .attr('stroke-width', 2)
    .attr('stroke-dasharray', d => d.type === 'node' ? '6,3' : '')
    .attr('filter', 'url(#shadow)')

  // 节点主标签
  nodeSel.append('text')
    .attr('text-anchor', 'middle')
    .attr('y', d => {
      const sub = getSubLabel(d)
      return sub ? -5 : 0
    })
    .attr('dy', '0.35em')
    .attr('fill', 'var(--text-heading)')
    .attr('font-size', d => d.type === 'cluster' ? 14 : 12)
    .attr('font-weight', d => d.type === 'cluster' || d.type === 'node' ? 700 : 600)
    .attr('class', 'svg-text-primary')
    .text(d => d.name)
    .each(function(d) {
      // 截断长文本
      const maxW = d.width - 16
      const self = d3.select(this)
      while ((this as SVGTextElement).getComputedTextLength() > maxW && self.text()!.length > 3) {
        self.text(self.text()!.slice(0, -4) + '...')
      }
    })

  // 节点副标签
  nodeSel.filter(d => !!getSubLabel(d))
    .append('text')
    .attr('text-anchor', 'middle')
    .attr('y', 10)
    .attr('fill', 'var(--text-muted)')
    .attr('font-size', 10)
    .attr('class', 'svg-text-muted')
    .text(d => getSubLabel(d))

  // HA 徽章
  nodeSel.filter(d => d.ha_enabled)
    .append('g').attr('transform', d => `${-d.width / 2 + 6}, ${-d.height / 2 + 5}`)
    .each(function() {
      const badge = d3.select(this)
      badge.append('rect').attr('width', 28).attr('height', 14).attr('rx', 3).attr('fill', '#f97316').attr('opacity', 0.9)
      badge.append('text').attr('x', 14).attr('y', 11).attr('text-anchor', 'middle')
        .attr('font-size', 8).attr('font-weight', 700).attr('fill', '#fff').text('HA')
    })

  // Hover 效果
  nodeSel.on('mouseenter', function() {
    d3.select(this).select('rect').transition().duration(150)
      .attr('stroke-width', 3).attr('filter', 'url(#shadow)')
  }).on('mouseleave', function(_, d) {
    d3.select(this).select('rect').transition().duration(150)
      .attr('stroke-width', 2)
  })

  // 模拟 tick
  simulation.on('tick', () => {
    edgeSel.interrupt().attr('d', d => {
      const s = d.source as D3Node, tgt = d.target as D3Node
      const sx = s.x!, sy = s.y!, tx = tgt.x!, ty = tgt.y!
      const dx = tx - sx, dy = ty - sy
      const dist = Math.sqrt(dx * dx + dy * dy) || 1
      // 从源边缘到目标边缘
      const sox = (dx / dist) * (s.width / 2)
      const soy = (dy / dist) * (s.height / 2)
      const tox = -(dx / dist) * (tgt.width / 2)
      const toy = -(dy / dist) * (tgt.height / 2)
      const x1 = sx + sox, y1 = sy + soy
      const x2 = tx + tox, y2 = ty + toy
      const mx = (x1 + x2) / 2, my = (y1 + y2) / 2
      // 贝塞尔曲线偏移
      const offset = Math.min(dist * 0.2, 60)
      const nx = -dy / dist * offset, ny = dx / dist * offset
      return `M${x1},${y1} Q${mx + nx},${my + ny} ${x2},${y2}`
    })
    nodeSel.attr('transform', d => `translate(${d.x},${d.y})`)
  })

  // 初始自适应
  setTimeout(() => fitView(), 800)
}

function showDetails(node: D3Node) {
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
  g.selectAll<SVGGElement, D3Node>('g.nodes g').style('opacity', function(_, i) {
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
  simulation?.stop()
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
