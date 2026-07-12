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
      <!-- 节点多指标趋势 -->
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

      <!-- CPU vs 内存散点 + 指标相关性热力图 -->
      <div class="row-split">
        <el-card shadow="hover" class="chart-card half">
          <template #header>
            <div class="card-header">
              <div>
                <span class="card-title">{{ t('smartAnalysis.performanceCorrelation.cpuVsMemory') }}</span>
                <span class="card-desc">{{ t('smartAnalysis.performanceCorrelation.cpuVsMemoryDesc') }}</span>
              </div>
            </div>
          </template>
          <v-chart :option="scatterOption" autoresize class="chart-area" />
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
          <v-chart :option="heatmapOption" autoresize class="chart-area" />
        </el-card>
      </div>

      <!-- 存储使用趋势 -->
      <el-card shadow="hover" class="chart-card">
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
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import * as echarts from 'echarts'
import VChart from 'vue-echarts'
import { useThemeStore } from '@/stores/theme'
import { useClusterStore } from '@/stores/cluster'
import { getCorrelationData, type CorrelationData, type CorrelationNodeTrend, type CorrelationSnapshot } from '@/api/dashboard'

const { t } = useI18n()
const themeStore = useThemeStore()
const clusterStore = useClusterStore()

const loading = ref(false)
const timeRange = ref(7)
const selectedNode = ref('')
const rawData = ref<CorrelationData>({ node_trends: [], current: [], storage: [] })

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
const METRIC_LABELS = ['CPU', t('smartAnalysis.performanceCorrelation.memoryUsage'), t('smartAnalysis.performanceCorrelation.diskIO'), t('smartAnalysis.performanceCorrelation.rootfs')]

const nodeNames = computed(() => rawData.value.node_trends.map(n => n.node_name))

// 过滤后的趋势数据
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
    rawData.value = { node_trends: [], current: [], storage: [] }
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
watch(() => clusterStore.currentClusterId, loadData)

// ── 1. 节点多指标趋势图 ──
const nodeTrendOption = computed(() => {
  const trends = filteredTrends.value
  if (!trends.length) return {}

  // 合并所有时间戳
  const allTs = [...new Set(trends.flatMap(t => t.timestamps))].sort()

  const series: any[] = []
  const legendData: string[] = []

  trends.forEach((node, ni) => {
    const color = NODE_COLORS[ni % NODE_COLORS.length]
    const prefix = trends.length > 1 ? `${node.node_name} ` : ''

    // CPU
    legendData.push(`${prefix}${t('smartAnalysis.performanceCorrelation.cpuLoad')}`)
    series.push({
      name: `${prefix}${t('smartAnalysis.performanceCorrelation.cpuLoad')}`,
      type: 'line', smooth: true, symbol: 'none',
      data: alignData(allTs, node.timestamps, node.cpu_load),
      lineStyle: { color, width: 2 },
      itemStyle: { color },
      yAxisIndex: 0,
    })

    // Memory
    const memColor = NODE_COLORS[(ni + trends.length) % NODE_COLORS.length]
    legendData.push(`${prefix}${t('smartAnalysis.performanceCorrelation.memoryUsage')}`)
    series.push({
      name: `${prefix}${t('smartAnalysis.performanceCorrelation.memoryUsage')}`,
      type: 'line', smooth: true, symbol: 'none',
      data: alignData(allTs, node.timestamps, node.memory_usage_pct),
      lineStyle: { color: memColor, width: 2, type: 'dashed' as const },
      itemStyle: { color: memColor },
      yAxisIndex: 1,
    })

    // Disk I/O
    const diskColor = NODE_COLORS[(ni + trends.length * 2) % NODE_COLORS.length]
    legendData.push(`${prefix}${t('smartAnalysis.performanceCorrelation.diskIO')}`)
    series.push({
      name: `${prefix}${t('smartAnalysis.performanceCorrelation.diskIO')}`,
      type: 'line', smooth: true, symbol: 'none',
      data: alignData(allTs, node.timestamps, node.disk_io_delay_ms),
      lineStyle: { color: diskColor, width: 1.5, type: 'dotted' as const },
      itemStyle: { color: diskColor },
      yAxisIndex: 2,
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
      {
        type: 'value' as const, position: 'left' as const, max: 100,
        name: 'CPU %', nameTextStyle: { color: textColor.value },
        axisLabel: { formatter: '{value}%', color: textColor.value },
        splitLine: { lineStyle: { color: lineColor.value, type: 'dashed' as const } },
      },
      {
        type: 'value' as const, position: 'right' as const, max: 100,
        name: 'MEM %', nameTextStyle: { color: textColor.value },
        axisLabel: { formatter: '{value}%', color: textColor.value },
        splitLine: { show: false },
      },
      {
        type: 'value' as const, position: 'right' as const, offset: 50,
        name: 'IO ms', nameTextStyle: { color: textColor.value },
        axisLabel: { color: textColor.value },
        splitLine: { show: false },
      },
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
    xAxis: {
      type: 'value' as const, name: 'CPU %', max: 100,
      nameTextStyle: { color: textColor.value },
      axisLabel: { formatter: '{value}%', color: textColor.value },
      splitLine: { lineStyle: { color: lineColor.value, type: 'dashed' as const } },
    },
    yAxis: {
      type: 'value' as const, name: 'MEM %', max: 100,
      nameTextStyle: { color: textColor.value },
      axisLabel: { formatter: '{value}%', color: textColor.value },
      splitLine: { lineStyle: { color: lineColor.value, type: 'dashed' as const } },
    },
    series: [{
      type: 'scatter',
      symbolSize: (val: number[]) => Math.max(20, Math.min(60, val[2] * 6 + 16)),
      data,
    }],
  }
})

// ── 3. 相关性热力图 ──
const heatmapOption = computed(() => {
  const trends = rawData.value.node_trends
  if (!trends.length) return {}

  // 收集各指标的所有有效值
  const metrics: { key: keyof CorrelationNodeTrend; label: string }[] = [
    { key: 'cpu_load', label: 'CPU' },
    { key: 'memory_usage_pct', label: t('smartAnalysis.performanceCorrelation.memoryUsage') },
    { key: 'disk_io_delay_ms', label: t('smartAnalysis.performanceCorrelation.diskIO') },
    { key: 'rootfs_used_gb', label: t('smartAnalysis.performanceCorrelation.rootfs') },
  ]

  // 将所有节点的时序数据拼接成统一数组
  const allSeries: (number | null)[][] = metrics.map(() => [])
  trends.forEach(node => {
    metrics.forEach((m, mi) => {
      const arr = node[m.key] as (number | null)[]
      allSeries[mi].push(...arr)
    })
  })

  // 计算 Pearson 相关系数
  const n = metrics.length
  const matrix: number[][] = Array.from({ length: n }, () => Array(n).fill(0))
  for (let i = 0; i < n; i++) {
    for (let j = 0; j < n; j++) {
      if (i === j) {
        matrix[i][j] = 1
      } else {
        matrix[i][j] = pearson(allSeries[i], allSeries[j])
      }
    }
  }

  // 转换为 ECharts heatmap 数据格式
  const heatData: number[][] = []
  for (let i = 0; i < n; i++) {
    for (let j = 0; j < n; j++) {
      heatData.push([j, i, Math.round(matrix[i][j] * 100) / 100])
    }
  }

  const labels = metrics.map(m => m.label)

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
      inRange: {
        color: ['#ef4444', '#fbbf24', '#e5e7eb', '#86efac', '#22c55e'],
      },
    },
    series: [{
      type: 'heatmap',
      data: heatData,
      label: { show: true, color: '#333', fontSize: 12, fontWeight: 'bold' as const },
      emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0, 0, 0, 0.3)' } },
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

function pearson(xs: (number | null)[], ys: (number | null)[]): number {
  const pairs: [number, number][] = []
  const len = Math.min(xs.length, ys.length)
  for (let i = 0; i < len; i++) {
    if (xs[i] != null && ys[i] != null) {
      pairs.push([xs[i]!, ys[i]!])
    }
  }
  const n = pairs.length
  if (n < 3) return 0

  const sumX = pairs.reduce((s, p) => s + p[0], 0)
  const sumY = pairs.reduce((s, p) => s + p[1], 0)
  const sumXY = pairs.reduce((s, p) => s + p[0] * p[1], 0)
  const sumX2 = pairs.reduce((s, p) => s + p[0] * p[0], 0)
  const sumY2 = pairs.reduce((s, p) => s + p[1] * p[1], 0)

  const denom = Math.sqrt((n * sumX2 - sumX * sumX) * (n * sumY2 - sumY * sumY))
  if (denom === 0) return 0
  return (n * sumXY - sumX * sumY) / denom
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
