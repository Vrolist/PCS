<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ t('networkTopology.title') }}</h2>
        <p class="page-desc">{{ t('networkTopology.subtitle') }}</p>
      </div>
      <div class="toolbar">
        <div class="toolbar-group">
          <button class="toolbar-btn" @click="zoomIn" :title="t('networkTopology.zoomIn')">+</button>
          <span class="toolbar-zoom-val">{{ Math.round(zoomLevel * 100) }}%</span>
          <button class="toolbar-btn" @click="zoomOut" :title="t('networkTopology.zoomOut')">-</button>
        </div>
        <span class="toolbar-divider"></span>
        <div class="toolbar-group">
          <button class="toolbar-btn-text" @click="resetView">{{ t('networkTopology.reset') }}</button>
        </div>
      </div>
    </div>

    <div class="topology-container" v-loading="loading">
      <div v-if="!loading && !graphData.nodes.length" class="empty-state">
        <el-empty :description="t('networkTopology.emptyDesc')" />
      </div>
      <div v-else ref="svgContainer" class="topology-canvas"></div>
    </div>

    <!-- 图例 -->
    <div class="legend-bar">
      <span class="legend-item legend-static">
        <span class="legend-dot" style="background:#4f46e5"></span>{{ t('networkTopology.legendNode') }}
      </span>
      <span class="legend-sep"></span>
      <template v-for="item in legendItems" :key="item.type">
        <span v-if="item.type !== 'node'"
          class="legend-item"
          :class="{ 'is-hidden': hiddenTypes.has(item.type) }"
          @click="toggleType(item.type)">
          <span class="legend-dot" :style="{ background: item.color }"></span>{{ item.label }}
        </span>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import * as d3 from 'd3'
import { getNetworkList, type NetworkInterface } from '@/api/networks'
import { useClusterStore } from '@/stores/cluster'

const { t } = useI18n()
const clusterStore = useClusterStore()

const loading = ref(true)
const svgContainer = ref<HTMLElement>()
const zoomLevel = ref(1)

// 图例过滤
const hiddenTypes = ref(new Set<string>())
const legendItems = computed(() => [
  { type: 'node', label: t('networkTopology.legendNode'), color: '#4f46e5' },
  { type: 'eth', label: t('networkTopology.legendPhysical'), color: '#409eff' },
  { type: 'bridge', label: t('networkTopology.legendBridge'), color: '#67c23a' },
  { type: 'bond', label: t('networkTopology.legendBond'), color: '#e6a23c' },
  { type: 'vlan', label: 'VLAN', color: '#8b5cf6' },
  { type: 'other', label: t('networkTopology.legendOther'), color: '#909399' }
])

function toggleType(type: string) {
  const s = new Set(hiddenTypes.value)
  if (s.has(type)) s.delete(type)
  else s.add(type)
  hiddenTypes.value = s
  updateGraph()
}

// 图数据结构
interface GraphNode extends d3.SimulationNodeDatum {
  id: string
  name: string
  type: 'node' | 'iface'
  ifaceType?: string
  nodeName?: string
  address?: string
  status?: string
  bridgePorts?: string
  bondSlaves?: string
  radius: number
}

interface GraphLink extends d3.SimulationLinkDatum<GraphNode> {
  source: string | GraphNode
  target: string | GraphNode
  type: 'node-iface' | 'bridge-port' | 'bond-slave'
}

const graphData = ref<{ nodes: GraphNode[]; links: GraphLink[] }>({ nodes: [], links: [] })

// D3 元素引用
let svg: d3.Selection<SVGSVGElement, unknown, null, undefined>
let g: d3.Selection<SVGGElement, unknown, null, undefined>
let simulation: d3.Simulation<GraphNode, GraphLink>
let zoomBehavior: d3.ZoomBehavior<SVGSVGElement, unknown>

// 颜色映射
const ifaceColors: Record<string, string> = {
  eth: '#409eff',
  bridge: '#67c23a',
  bond: '#e6a23c',
  vlan: '#8b5cf6',
  other: '#909399'
}

/** 构建图数据 */
function buildGraph(data: NetworkInterface[]) {
  const nodes: GraphNode[] = []
  const links: GraphLink[] = []
  const nodeMap = new Map<string, GraphNode>()
  const ifaceMap = new Map<string, GraphNode>()

  // 按节点分组
  const groups = new Map<string, NetworkInterface[]>()
  data.forEach(iface => {
    const list = groups.get(iface.node_name) || []
    list.push(iface)
    groups.set(iface.node_name, list)
  })

  // 创建节点
  groups.forEach((ifaces, nodeName) => {
    const node: GraphNode = {
      id: `node-${nodeName}`,
      name: nodeName,
      type: 'node',
      radius: 30
    }
    nodes.push(node)
    nodeMap.set(nodeName, node)

    // 创建接口
    ifaces.forEach(iface => {
      if (hiddenTypes.value.has(iface.type === 'eth' ? 'eth' : iface.type)) return
      
      const ifaceNode: GraphNode = {
        id: `iface-${iface.id}`,
        name: iface.name,
        type: 'iface',
        ifaceType: iface.type,
        nodeName: iface.node_name,
        address: iface.address,
        status: iface.status,
        bridgePorts: iface.bridge_ports,
        bondSlaves: iface.bond_slaves,
        radius: 15
      }
      nodes.push(ifaceNode)
      ifaceMap.set(`${nodeName}-${iface.name}`, ifaceNode)

      // 节点到接口的连接
      links.push({
        source: `node-${nodeName}`,
        target: `iface-${iface.id}`,
        type: 'node-iface'
      })
    })

    // 处理 bridge -> ports 连接
    ifaces.filter(i => i.type === 'bridge').forEach(bridge => {
      const ports = (bridge.bridge_ports || '').split(/\s+/).filter(Boolean)
      ports.forEach(portName => {
        const portIface = ifaceMap.get(`${nodeName}-${portName}`)
        if (portIface) {
          links.push({
            source: `iface-${bridge.id}`,
            target: `iface-${portIface.id}`,
            type: 'bridge-port'
          })
        }
      })
    })

    // 处理 bond -> slaves 连接
    ifaces.filter(i => i.type === 'bond').forEach(bond => {
      const slaves = (bond.bond_slaves || '').split(/\s+/).filter(Boolean)
      slaves.forEach(slaveName => {
        const slaveIface = ifaceMap.get(`${nodeName}-${slaveName}`)
        if (slaveIface) {
          links.push({
            source: `iface-${bond.id}`,
            target: `iface-${slaveIface.id}`,
            type: 'bond-slave'
          })
        }
      })
    })
  })

  // 过滤掉引用不存在节点的连线（避免 D3 force 模拟报错）
  const validNodeIds = new Set(nodes.map(n => n.id))
  const validLinks = links.filter(l => {
    const sid = typeof l.source === 'string' ? l.source : (l.source as GraphNode).id
    const tid = typeof l.target === 'string' ? l.target : (l.target as GraphNode).id
    return validNodeIds.has(sid) && validNodeIds.has(tid)
  })

  graphData.value = { nodes, links: validLinks }
}

/** 初始化 SVG */
function initSvg() {
  if (!svgContainer.value) return

  const container = svgContainer.value
  const width = container.clientWidth
  const height = container.clientHeight

  // 清空容器
  d3.select(container).selectAll('*').remove()

  // 创建 SVG
  svg = d3.select(container)
    .append('svg')
    .attr('width', '100%')
    .attr('height', '100%')
    .attr('viewBox', `0 0 ${width} ${height}`)

  // 创建缩放组
  g = svg.append('g')

  // 定义缩放行为
  zoomBehavior = d3.zoom<SVGSVGElement, unknown>()
    .scaleExtent([0.3, 3])
    .on('zoom', (event) => {
      g.attr('transform', event.transform)
      zoomLevel.value = event.transform.k
    })

  svg.call(zoomBehavior)

  // 创建力导向模拟
  simulation = d3.forceSimulation<GraphNode>()
    .force('link', d3.forceLink<GraphNode, GraphLink>().id(d => d.id).distance(100))
    .force('charge', d3.forceManyBody().strength(-300))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collision', d3.forceCollide().radius(d => (d as GraphNode).radius + 10))
    .force('x', d3.forceX(width / 2).strength(0.1))
    .force('y', d3.forceY(height / 2).strength(0.1))

  // 添加箭头定义
  svg.append('defs').append('marker')
    .attr('id', 'arrowhead')
    .attr('viewBox', '-0 -5 10 10')
    .attr('refX', 20)
    .attr('refY', 0)
    .attr('orient', 'auto')
    .attr('markerWidth', 6)
    .attr('markerHeight', 6)
    .append('path')
    .attr('d', 'M0,-5L10,0L0,5')
    .attr('fill', '#999')
}

/** 更新图 */
function updateGraph() {
  if (!g || !simulation) return

  // 先停止旧模拟，防止 D3 内部残留引用
  simulation.stop()
  simulation.on('tick', null)

  buildGraph(filteredData.value)
  const { nodes, links } = graphData.value

  // 清空现有元素
  g.selectAll('*').remove()

  // 创建连线
  const link = g.append('g')
    .attr('class', 'links')
    .selectAll('line')
    .data(links)
    .enter()
    .append('line')
    .attr('stroke', d => {
      if (d.type === 'bridge-port') return '#67c23a'
      if (d.type === 'bond-slave') return '#e6a23c'
      return '#999'
    })
    .attr('stroke-opacity', 0.6)
    .attr('stroke-width', 2)
    .attr('stroke-dasharray', d => d.type === 'node-iface' ? '5,5' : 'none')

  // 创建节点组
  const node = g.append('g')
    .attr('class', 'nodes')
    .selectAll('g')
    .data(nodes)
    .enter()
    .append('g')
    .attr('class', 'node')
    .call(d3.drag<SVGGElement, GraphNode>()
      .on('start', dragstarted)
      .on('drag', dragged)
      .on('end', dragended)
    )

  // 节点圆形
  node.append('circle')
    .attr('r', d => d.radius)
    .attr('fill', d => {
      if (d.type === 'node') return '#4f46e5'
      return ifaceColors[d.ifaceType || 'other'] || '#909399'
    })
    .attr('stroke', '#fff')
    .attr('stroke-width', 2)
    .attr('cursor', 'pointer')
    .on('mouseover', function(event, d) {
      d3.select(this)
        .transition()
        .duration(200)
        .attr('r', d.radius * 1.2)
        .attr('stroke-width', 3)
    })
    .on('mouseout', function(event, d) {
      d3.select(this)
        .transition()
        .duration(200)
        .attr('r', d.radius)
        .attr('stroke-width', 2)
    })

  // 状态指示器（接口）
  node.filter(d => d.type === 'iface' && d.status)
    .append('circle')
    .attr('cx', d => d.radius * 0.7)
    .attr('cy', d => -d.radius * 0.7)
    .attr('r', 5)
    .attr('fill', d => d.status === 'up' ? '#67c23a' : '#f56c6c')
    .attr('stroke', '#fff')
    .attr('stroke-width', 1.5)

  // 节点标签
  node.append('text')
    .attr('dy', d => d.type === 'node' ? 4 : 30)
    .attr('text-anchor', 'middle')
    .attr('font-size', d => d.type === 'node' ? '12px' : '10px')
    .attr('font-weight', d => d.type === 'node' ? '600' : '400')
    .attr('fill', d => d.type === 'node' ? '#fff' : '#333')
    .text(d => d.name)

  // IP 地址标签（接口）
  node.filter(d => d.type === 'iface' && d.address)
    .append('text')
    .attr('dy', 42)
    .attr('text-anchor', 'middle')
    .attr('font-size', '9px')
    .attr('fill', '#666')
    .text(d => d.address?.split('/')[0] || '')

  // 更新模拟
  simulation.nodes(nodes)
  simulation.force<d3.ForceLink<GraphNode, GraphLink>>('link')!.links(links)
  simulation.alpha(1).restart()

  // 更新位置
  simulation.on('tick', () => {
    link
      .attr('x1', d => (d.source as GraphNode).x!)
      .attr('y1', d => (d.source as GraphNode).y!)
      .attr('x2', d => (d.target as GraphNode).x!)
      .attr('y2', d => (d.target as GraphNode).y!)

    node.attr('transform', d => `translate(${d.x},${d.y})`)
  })
}

// 拖拽函数
function dragstarted(event: d3.D3DragEvent<SVGGElement, GraphNode, GraphNode>, d: GraphNode) {
  if (!event.active) simulation.alphaTarget(0.3).restart()
  d.fx = d.x
  d.fy = d.y
}

function dragged(event: d3.D3DragEvent<SVGGElement, GraphNode, GraphNode>, d: GraphNode) {
  d.fx = event.x
  d.fy = event.y
}

function dragended(event: d3.D3DragEvent<SVGGElement, GraphNode, GraphNode>, d: GraphNode) {
  if (!event.active) simulation.alphaTarget(0)
  d.fx = null
  d.fy = null
}

// 缩放控制
function zoomIn() {
  svg.transition().duration(300).call(zoomBehavior.scaleBy, 1.2)
}

function zoomOut() {
  svg.transition().duration(300).call(zoomBehavior.scaleBy, 0.8)
}

function resetView() {
  svg.transition().duration(500).call(
    zoomBehavior.transform,
    d3.zoomIdentity
  )
  simulation.alpha(1).restart()
}

const topologyData = ref<NetworkInterface[]>([])
const filteredData = computed(() => {
  if (!clusterStore.currentClusterId) return topologyData.value
  const name = clusterStore.currentCluster?.name
  if (!name) return topologyData.value
  return topologyData.value.filter(n => n.cluster_name === name)
})

watch(filteredData, () => {
  updateGraph()
})

watch(() => clusterStore.currentClusterId, () => {
  updateGraph()
})

// 窗口大小变化时重新初始化
let resizeTimer: ReturnType<typeof setTimeout>
function handleResize() {
  clearTimeout(resizeTimer)
  resizeTimer = setTimeout(() => {
    initSvg()
    updateGraph()
  }, 200)
}

onMounted(async () => {
  loading.value = true
  try {
    if (!clusterStore.clusterList.length) await clusterStore.fetchClusters()
    topologyData.value = await getNetworkList()
    await nextTick()
    initSvg()
    updateGraph()
  } catch (e) {
    console.error('Failed to load topology:', e)
  } finally {
    loading.value = false
  }

  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  if (simulation) simulation.stop()
})
</script>

<style scoped>
.page-container { width: 100%; height: 100%; display: flex; flex-direction: column; }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px; flex-wrap: wrap; gap: 12px; }
.page-title { font-size: 24px; font-weight: 700; color: var(--text-heading); margin: 0; }
.page-desc { font-size: 14px; color: var(--text-muted); margin: 4px 0 0; }

/* 工具栏 */
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

/* 图例 */
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
.legend-dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; transition: all .2s; }
.legend-sep { width: 1px; height: 16px; background: var(--border-color); padding: 0; cursor: default; }
.legend-static { cursor: default; }
.legend-static:hover { background: transparent; }
</style>
