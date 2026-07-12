<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ t('smartAnalysis.performanceCorrelation.title') }}</h2>
        <p class="page-desc">{{ t('smartAnalysis.performanceCorrelation.subtitle') }}</p>
      </div>
      <div class="header-controls">
        <el-select v-model="selectedNode" size="default" clearable :placeholder="t('smartAnalysis.performanceCorrelation.selectNode')" style="width: 180px">
          <el-option :label="t('smartAnalysis.performanceCorrelation.allNodes')" value="" />
          <el-option v-for="n in nodeNames" :key="n" :label="n" :value="n" />
        </el-select>
        <el-select v-model="timeRange" size="default" style="width: 130px" @change="loadData">
          <el-option :label="t('smartAnalysis.performanceCorrelation.last7Days')" :value="7" />
          <el-option :label="t('smartAnalysis.performanceCorrelation.last15Days')" :value="15" />
          <el-option :label="t('smartAnalysis.performanceCorrelation.last30Days')" :value="30" />
        </el-select>
      </div>
    </div>

    <div v-if="loading" v-loading="true" style="min-height: 400px" />

    <template v-else>
      <!-- 1. 节点多指标趋势 — 首屏立即渲染 -->
      <el-card shadow="hover" class="chart-card">
        <template #header>
          <div class="card-header">
            <div>
              <span class="card-title">{{ t('smartAnalysis.performanceCorrelation.nodeTrend') }}</span>
              <span class="card-desc">{{ t('smartAnalysis.performanceCorrelation.nodeTrendDesc') }}</span>
            </div>
          </div>
        </template>
        <v-chart :option="nodeTrendOption" autoresize class="chart-area" />
      </el-card>

      <!-- 2. CPU vs 内存散点 + 3. 相关性热力图 — 延迟渲染 -->
      <div ref="scatterRowRef" class="row-split">
        <el-card shadow="hover" class="chart-card half">
          <template #header>
            <div class="card-header">
              <div>
                <span class="card-title">{{ t('smartAnalysis.performanceCorrelation.cpuVsMemory') }}</span>
                <span class="card-desc">{{ t('smartAnalysis.performanceCorrelation.cpuVsMemoryDesc') }}</span>
              </div>
            </div>
          </template>
          <div v-if="scatterVisible" class="chart-area-wrapper">
            <v-chart :option="scatterOption" autoresize class="chart-area" />
          </div>
          <div v-else class="chart-placeholder" />
        </el-card>

        <el-card shadow="hover" class="chart-card half">
          <template #header>
            <div class="card-header">
              <div>
                <span class="card-title">{{ t('smartAnalysis.performanceCorrelation.correlationHeatmap') }}</span>
                <span class="card-desc">{{ t('smartAnalysis.performanceCorrelation.correlationHeatmapDesc') }}</span>
              </div>
            </div>
          </template>
          <div v-if="scatterVisible" class="chart-area-wrapper">
            <v-chart :option="heatmapOption" autoresize class="chart-area" />
          </div>
          <div v-else class="chart-placeholder" />
        </el-card>
      </div>

      <!-- 4. 存储使用趋势 — 延迟渲染 -->
      <div ref="storageRef">
        <el-card v-if="storageVisible" shadow="hover" class="chart-card">
          <template #header>
            <div class="card-header">
              <div>
                <span class="card-title">{{ t('smartAnalysis.performanceCorrelation.storageTrend') }}</span>
                <span class="card-desc">{{ t('smartAnalysis.performanceCorrelation.storageTrendDesc') }}</span>
              </div>
            </div>
          </template>
          <v-chart :option="storageTrendOption" autoresize class="chart-area" />
        </el-card>
        <div v-else class="chart-placeholder-block" />
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import * as echarts from 'echarts'
import VChart from 'vue-echarts'
import { useThemeStore } from '@/stores/theme'
import { useClusterStore } from '@/stores/cluster'
import { getCorrelationData, type CorrelationData } from '@/api/dashboard'

const { t } = useI18n()
const themeStore = useThemeStore()
const clusterStore = useClusterStore()

const loading = ref(false)
const timeRange = ref(7)
const selectedNode = ref('')
const rawData = ref<CorrelationData>({ node_trends: [], current: [], storage: [], correlation_matrix: [] })

// ── 延迟渲染状态 ──
const scatterVisible = ref(false)
const storageVisible = ref(false)
const scatterRowRef = ref<HTMLElement | null>(null)
const storageRef = ref<HTMLElement | null>(null)
let observer: IntersectionObserver | null = null

const isDark = computed(() => themeStore.theme === 'dark')
const textColor = computed(() => isDark.value ? '#a0a0c0' : '#606266')
const axisColor = computed(() => isDark.value ? '#2a2a50' : '#d9dce4')
const lineColor = computed(() => isDark.value ? 'rgba(42, 42, 80, 0.6)' : 'rgba(200, 200, 220, 0.5)')
const tooltipBg = computed(() => isDark.value ? 'rgba(30, 30, 72, 0.92)' : 'rgba(255, 255, 255, 0.96)')
const tooltipBorder = computed(() => isDark.value ? '#2a2a50' : '#e2e5ed')
const tooltipText = computed(() => isDark.value ? '#e0e0f0' : '#303133')

const tooltipStyle = computed(() => ({
  backgroundColor: tooltipBg.value,
  borderColor: tooltipBorder.value,
  textStyle: { color: tooltipText.value },
}))

const NODE_COLORS = ['#409eff', '#8b5cf6', '#f59e0b', '#10b981', '#ef4444', '#06b6d4', '#ec4899', '#84cc16']

const nodeNames = computed(() => rawData.value.node_trends.map(n => n.node_name))

const filteredTrends = computed(() => {
  if (!selectedNode.value) return rawData.value.node_trends
  return rawData.value.node_trends.filter(n => n.node_name === selectedNode.value)
})

async function loadData() {
  const clusterId = clusterStore.currentClusterId || undefined
  loading.value = true
  try {
    rawData.value = await getCorrelationData(clusterId, timeRange.value)
  } catch {
    rawData.value = { node_trends: [], current: [], storage: [], correlation_matrix: [] }
  } finally {
    loading.value = false
  }
}

// ── IntersectionObserver 设置 ──
function setupObserver() {
  observer = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      if (entry.isIntersecting) {
        if (entry.target === scatterRowRef.value) scatterVisible.value = true
        if (entry.target === storageRef.value) storageVisible.value = true
        observer?.unobserve(entry.target)
      }
    }
  }, { rootMargin: '200px' })

  if (scatterRowRef.value) observer.observe(scatterRowRef.value)
  if (storageRef.value) observer.observe(storageRef.value)
}

onMounted(() => {
  loadData()
})

onUnmounted(() => {
  observer?.disconnect()
})

watch(() => clusterStore.currentClusterId, () => { scatterVisible.value = false; storageVisible.value = false; loadData() })

// 数据加载完成后，DOM 渲染完毕，再设置 observer
watch(loading, (val) => {
  if (!val) {
    nextTick(setupObserver)
  }
})

// ── 1. 节点多指标趋势图 ──
const nodeTrendOption = computed(() => {
  const trends = filteredTrends.value
  if (!trends.length) return {}

  const allTs = [...new Set(trends.flatMap(t => t.timestamps))].sort()
  const series: any[] = []

  trends.forEach((node, ni) => {
    const color = NODE_COLORS[ni % NODE_COLORS.length]
    const prefix = trends.length > 1 ? `${node.node_name} ` : ''

    series.push({
      name: `${prefix}${t('smartAnalysis.performanceCorrelation.cpuLoad')}`,
      type: 'line', smooth: true, symbol: 'none',
      data: alignData(allTs, node.timestamps, node.cpu_load),
      lineStyle: { color, width: 2 }, itemStyle: { color }, yAxisIndex: 0,
    })

    const memColor = NODE_COLORS[(ni + trends.length) % NODE_COLORS.length]
    series.push({
      name: `${prefix}${t('smartAnalysis.performanceCorrelation.memoryUsage')}`,
      type: 'line', smooth: true, symbol: 'none',
      data: alignData(allTs, node.timestamps, node.memory_usage_pct),
      lineStyle: { color: memColor, width: 2, type: 'dashed' as const },
      itemStyle: { color: memColor }, yAxisIndex: 1,
    })

    const diskColor = NODE_COLORS[(ni + trends.length * 2) % NODE_COLORS.length]
    series.push({
      name: `${prefix}${t('smartAnalysis.performanceCorrelation.diskIO')}`,
      type: 'line', smooth: true, symbol: 'none',
      data: alignData(allTs, node.timestamps, node.disk_io_delay_ms),
      lineStyle: { color: diskColor, width: 1.5, type: 'dotted' as const },
      itemStyle: { color: diskColor }, yAxisIndex: 2,
    })
  })

  return {
    tooltip: { trigger: 'axis' as const, ...tooltipStyle.value, axisPointer: { type: 'cross' as const } },
    legend: { top: 0, type: 'scroll' as const, textStyle: { color: textColor.value } },
    grid: { left: 50, right: 80, bottom: 30, top: 50 },
    xAxis: {
      type: 'category' as const, data: allTs, boundaryGap: false,
      axisLine: { lineStyle: { color: axisColor.value } },
      axisLabel: { color: textColor.value, fontSize: 11 },
    },
    yAxis: [
      { type: 'value' as const, position: 'left' as const, max: 100, name: 'CPU %', nameTextStyle: { color: textColor.value }, axisLabel: { formatter: '{value}%', color: textColor.value }, splitLine: { lineStyle: { color: lineColor.value, type: 'dashed' as const } } },
      { type: 'value' as const, position: 'right' as const, max: 100, name: 'MEM %', nameTextStyle: { color: textColor.value }, axisLabel: { formatter: '{value}%', color: textColor.value }, splitLine: { show: false } },
      { type: 'value' as const, position: 'right' as const, offset: 50, name: 'IO ms', nameTextStyle: { color: textColor.value }, axisLabel: { color: textColor.value }, splitLine: { show: false } },
    ],
    series,
  }
})

// ── 2. CPU vs 内存散点图 ──
const scatterOption = computed(() => {
  const snapshot = rawData.value.current
  if (!snapshot.length) return {}

  const data = snapshot.map((s, i) => ({
    name: s.node_name,
    value: [s.cpu_load || 0, s.memory_usage_pct || 0, (s.total_vms + s.total_lxc) || 1],
    itemStyle: { color: NODE_COLORS[i % NODE_COLORS.length] },
    label: { show: true, formatter: s.node_name, position: 'top' as const, color: textColor.value, fontSize: 11 },
  }))

  return {
    tooltip: {
      ...tooltipStyle.value,
      formatter: (p: any) => {
        const d = p.data
        return `<b>${d.name}</b><br/>CPU: ${d.value[0]?.toFixed(1)}%<br/>${t('smartAnalysis.performanceCorrelation.memoryUsage')}: ${d.value[1]?.toFixed(1)}%<br/>${t('smartAnalysis.performanceCorrelation.vmCount')}+${t('smartAnalysis.performanceCorrelation.lxcCount')}: ${d.value[2]}`
      },
    },
    grid: { left: 60, right: 30, bottom: 40, top: 30 },
    xAxis: { type: 'value' as const, name: 'CPU %', max: 100, nameTextStyle: { color: textColor.value }, axisLabel: { formatter: '{value}%', color: textColor.value }, splitLine: { lineStyle: { color: lineColor.value, type: 'dashed' as const } } },
    yAxis: { type: 'value' as const, name: 'MEM %', max: 100, nameTextStyle: { color: textColor.value }, axisLabel: { formatter: '{value}%', color: textColor.value }, splitLine: { lineStyle: { color: lineColor.value, type: 'dashed' as const } } },
    series: [{ type: 'scatter', symbolSize: (val: number[]) => Math.max(20, Math.min(60, val[2] * 6 + 16)), data }],
  }
})

// ── 3. 相关性热力图（直接使用后端计算的 correlation_matrix）──
const heatmapOption = computed(() => {
  const matrix = rawData.value.correlation_matrix
  if (!matrix?.length) return {}

  const labels = ['CPU', t('smartAnalysis.performanceCorrelation.memoryUsage'), t('smartAnalysis.performanceCorrelation.diskIO'), t('smartAnalysis.performanceCorrelation.rootfs')]

  const heatData: number[][] = []
  for (let i = 0; i < matrix.length; i++) {
    for (let j = 0; j < matrix[i].length; j++) {
      heatData.push([j, i, Math.round(matrix[i][j] * 100) / 100])
    }
  }

  return {
    tooltip: {
      ...tooltipStyle.value,
      formatter: (p: any) => {
        const [x, y, val] = p.data
        return `${labels[y]} ↔ ${labels[x]}<br/>r = <b>${val}</b>`
      },
    },
    grid: { left: 90, right: 40, bottom: 50, top: 20 },
    xAxis: {
      type: 'category' as const, data: labels, position: 'bottom' as const,
      axisLine: { lineStyle: { color: axisColor.value } },
      axisLabel: { color: textColor.value, rotate: 30 },
    },
    yAxis: {
      type: 'category' as const, data: labels,
      axisLine: { lineStyle: { color: axisColor.value } },
      axisLabel: { color: textColor.value },
    },
    visualMap: {
      min: -1, max: 1, calculable: true, orient: 'horizontal' as const,
      left: 'center', bottom: 0, itemWidth: 14, itemHeight: 120,
      textStyle: { color: textColor.value },
      inRange: { color: ['#ef4444', '#fbbf24', '#e5e7eb', '#86efac', '#22c55e'] },
    },
    series: [{
      type: 'heatmap', data: heatData,
      label: { show: true, fontSize: 12, fontWeight: 'bold' as const, color: '#333' },
      emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.3)' } },
    }],
  }
})

// ── 4. 存储使用趋势 ──
const storageTrendOption = computed(() => {
  const storageData = rawData.value.storage
  if (!storageData.length) return {}

  const allTs = [...new Set(storageData.flatMap(s => s.timestamps))].sort()

  const series = storageData.map((s, i) => ({
    name: `${s.node_name}/${s.storage_name}`,
    type: 'line' as const, smooth: true, symbol: 'none',
    data: alignData(allTs, s.timestamps, s.used_fraction?.map(v => v !== null ? v * 100 : null)),
    lineStyle: { width: 2 },
    itemStyle: { color: NODE_COLORS[i % NODE_COLORS.length] },
    areaStyle: {
      color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
        { offset: 0, color: `${NODE_COLORS[i % NODE_COLORS.length]}40` },
        { offset: 1, color: `${NODE_COLORS[i % NODE_COLORS.length]}05` },
      ]),
    },
  }))

  return {
    tooltip: { trigger: 'axis' as const, ...tooltipStyle.value },
    legend: { top: 0, type: 'scroll' as const, textStyle: { color: textColor.value } },
    grid: { left: 50, right: 30, bottom: 30, top: 50 },
    xAxis: {
      type: 'category' as const, data: allTs, boundaryGap: false,
      axisLine: { lineStyle: { color: axisColor.value } },
      axisLabel: { color: textColor.value, fontSize: 11 },
    },
    yAxis: {
      type: 'value' as const, max: 100,
      axisLabel: { formatter: '{value}%', color: textColor.value },
      splitLine: { lineStyle: { color: lineColor.value, type: 'dashed' as const } },
    },
    series,
  }
})

// ── 工具函数 ──
function alignData(allTs: string[], srcTs: string[], srcVal: (number | null)[] | undefined): (number | null)[] {
  if (!srcVal) return allTs.map(() => null)
  const map = new Map<string, number | null>()
  srcTs.forEach((t, i) => map.set(t, srcVal[i]))
  return allTs.map(t => map.get(t) ?? null)
}
</script>

<style scoped>
.page-container {
  max-width: 1400px;
  margin: 0 auto;
}
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 28px;
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
.header-controls {
  display: flex;
  gap: 12px;
  align-items: center;
}
.chart-card {
  margin-bottom: 20px;
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.card-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-heading);
}
.card-desc {
  display: block;
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 2px;
}
.chart-area {
  width: 100%;
  height: 340px;
}
.chart-area-wrapper {
  width: 100%;
  height: 340px;
}
.chart-placeholder {
  width: 100%;
  height: 340px;
}
.chart-placeholder-block {
  width: 100%;
  height: 400px;
}
.row-split {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 20px;
}
.row-split .half {
  margin-bottom: 0;
}
@media (max-width: 900px) {
  .row-split {
    grid-template-columns: 1fr;
  }
}
</style>
