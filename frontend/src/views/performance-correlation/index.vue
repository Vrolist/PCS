<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ t('smartAnalysis.performanceCorrelation.title') }}</h2>
        <p class="page-desc">{{ t('smartAnalysis.performanceCorrelation.subtitle') }}</p>
      </div>
      <div class="header-controls">
        <el-select v-model="timeRange" size="default" style="width: 130px" @change="loadData">
          <el-option :label="t('smartAnalysis.performanceCorrelation.last7Days')" :value="7" />
          <el-option :label="t('smartAnalysis.performanceCorrelation.last15Days')" :value="15" />
          <el-option :label="t('smartAnalysis.performanceCorrelation.last30Days')" :value="30" />
        </el-select>
      </div>
    </div>

    <div v-if="loading" v-loading="true" style="min-height: 500px" />

    <el-card v-else shadow="hover" class="chart-card">
      <el-tabs v-model="activeTab" class="correlation-tabs">
        <!-- Tab 1: 趋势图 -->
        <el-tab-pane name="trend">
          <template #label>
            <span class="tab-label">{{ t('smartAnalysis.performanceCorrelation.nodeTrend') }}</span>
          </template>
          <div v-if="activeTab === 'trend'" class="tab-chart-wrap">
            <div class="trend-toolbar">
              <el-radio-group v-model="selectedMetric" size="small">
                <el-radio-button value="cpu">CPU 负载</el-radio-button>
                <el-radio-button value="mem">内存使用</el-radio-button>
                <el-radio-button value="io">磁盘 IO</el-radio-button>
              </el-radio-group>
              <span class="trend-hint">{{ metricHint }}</span>
            </div>
            <v-chart :option="nodeTrendOption" autoresize class="tab-chart" />
          </div>
        </el-tab-pane>

        <!-- Tab 2: 散点图 -->
        <el-tab-pane name="scatter">
          <template #label>
            <span class="tab-label">{{ t('smartAnalysis.performanceCorrelation.cpuVsMemory') }}</span>
          </template>
          <div v-if="activeTab === 'scatter'" class="tab-chart-wrap">
            <p class="tab-desc">{{ t('smartAnalysis.performanceCorrelation.cpuVsMemoryDesc') }}</p>
            <v-chart :option="scatterOption" autoresize class="tab-chart" />
          </div>
        </el-tab-pane>

        <!-- Tab 3: 热力图 -->
        <el-tab-pane name="heatmap">
          <template #label>
            <span class="tab-label">{{ t('smartAnalysis.performanceCorrelation.correlationHeatmap') }}</span>
          </template>
          <div v-if="activeTab === 'heatmap'" class="tab-chart-wrap">
            <p class="tab-desc">{{ t('smartAnalysis.performanceCorrelation.correlationHeatmapDesc') }}</p>
            <v-chart :option="heatmapOption" autoresize class="tab-chart" />
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import VChart from 'vue-echarts'
import * as echarts from 'echarts'
import { useThemeStore } from '@/stores/theme'
import { useClusterStore } from '@/stores/cluster'
import { getCorrelationData, type CorrelationData } from '@/api/dashboard'

const { t } = useI18n()
const themeStore = useThemeStore()
const clusterStore = useClusterStore()

const loading = ref(false)
const timeRange = ref(7)
const activeTab = ref('trend')
const selectedMetric = ref<'cpu' | 'mem' | 'io'>('cpu')
const rawData = ref<CorrelationData>({ node_trends: [], current: [], correlation_matrix: [] })

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

const METRIC_CONFIG = {
  cpu: { key: 'cpu_load' as const, suffix: '%', name: 'CPU 负载', max: 100 },
  mem: { key: 'memory_usage_pct' as const, suffix: '%', name: '内存使用', max: 100 },
  io: { key: 'disk_io_delay_ms' as const, suffix: 'ms', name: '磁盘 IO 延迟', max: undefined },
}

const metricHint = computed(() => {
  const cfg = METRIC_CONFIG[selectedMetric.value]
  return `${cfg.name}（${cfg.suffix}）— 各节点对比`
})

async function loadData() {
  const clusterId = clusterStore.currentClusterId || undefined
  loading.value = true
  try {
    rawData.value = await getCorrelationData(clusterId, timeRange.value)
  } catch {
    rawData.value = { node_trends: [], current: [], correlation_matrix: [] }
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
watch(() => clusterStore.currentClusterId, loadData)

// ── 1. 趋势图（指标切换，每条线 = 一个节点）──
const nodeTrendOption = computed(() => {
  const trends = rawData.value.node_trends
  if (!trends.length) return {}

  const cfg = METRIC_CONFIG[selectedMetric.value]
  const allTs = [...new Set(trends.flatMap(t => t.timestamps))].sort()
  const series = trends.map((node, ni) => ({
    name: node.node_name,
    type: 'line' as const, smooth: true, symbol: 'none',
    data: alignData(allTs, node.timestamps, node[cfg.key]),
    lineStyle: { color: NODE_COLORS[ni % NODE_COLORS.length], width: 2.5 },
    itemStyle: { color: NODE_COLORS[ni % NODE_COLORS.length] },
    areaStyle: {
      color: {
        type: 'linear' as const, x: 0, y: 0, x2: 0, y2: 1,
        colorStops: [
          { offset: 0, color: `${NODE_COLORS[ni % NODE_COLORS.length]}25` },
          { offset: 1, color: `${NODE_COLORS[ni % NODE_COLORS.length]}03` },
        ],
      },
    },
  }))

  return {
    tooltip: { trigger: 'axis' as const, ...tooltipStyle.value },
    legend: { top: 0, textStyle: { color: textColor.value, fontSize: 12 } },
    grid: { left: 55, right: 30, bottom: 30, top: 50 },
    xAxis: {
      type: 'category' as const, data: allTs, boundaryGap: false,
      axisLine: { lineStyle: { color: axisColor.value } },
      axisLabel: { color: textColor.value, fontSize: 11 },
    },
    yAxis: {
      type: 'value' as const, max: cfg.max,
      name: cfg.suffix, nameTextStyle: { color: textColor.value },
      axisLabel: { formatter: `{value}${cfg.suffix}`, color: textColor.value },
      splitLine: { lineStyle: { color: lineColor.value, type: 'dashed' as const } },
    },
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
    label: { show: true, formatter: s.node_name, position: 'top' as const, color: textColor.value, fontSize: 12 },
  }))

  return {
    tooltip: {
      ...tooltipStyle.value,
      formatter: (p: any) => {
        const d = p.data
        return `<b>${d.name}</b><br/>CPU: ${d.value[0]?.toFixed(1)}%<br/>MEM: ${d.value[1]?.toFixed(1)}%<br/>VM+CT: ${d.value[2]}`
      },
    },
    grid: { left: 60, right: 30, bottom: 40, top: 30 },
    xAxis: { type: 'value' as const, name: 'CPU %', max: 100, nameTextStyle: { color: textColor.value }, axisLabel: { formatter: '{value}%', color: textColor.value }, splitLine: { lineStyle: { color: lineColor.value, type: 'dashed' as const } }, axisLine: { lineStyle: { color: axisColor.value } } },
    yAxis: { type: 'value' as const, name: 'MEM %', max: 100, nameTextStyle: { color: textColor.value }, axisLabel: { formatter: '{value}%', color: textColor.value }, splitLine: { lineStyle: { color: lineColor.value, type: 'dashed' as const } }, axisLine: { lineStyle: { color: axisColor.value } } },
    series: [{ type: 'scatter', symbolSize: (val: number[]) => Math.max(20, Math.min(60, val[2] * 6 + 16)), data }],
  }
})

// ── 3. 相关性热力图（后端计算）──
const heatmapOption = computed(() => {
  const matrix = rawData.value.correlation_matrix
  if (!matrix?.length) return {}

  const labels = ['CPU', 'MEM', 'IO', 'Disk']
  const heatData: number[][] = []
  for (let i = 0; i < matrix.length; i++) {
    for (let j = 0; j < matrix[i].length; j++) {
      heatData.push([j, i, Math.round(matrix[i][j] * 100) / 100])
    }
  }

  return {
    tooltip: {
      ...tooltipStyle.value,
      formatter: (p: any) => `${labels[p.data[1]]} ↔ ${labels[p.data[0]]}<br/>r = <b>${p.data[2]}</b>`,
    },
    grid: { left: 80, right: 40, bottom: 50, top: 20 },
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
      label: { show: true, fontSize: 13, fontWeight: 'bold' as const, color: '#333' },
    }],
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
  margin-bottom: 24px;
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
  min-height: 500px;
}
.tab-label {
  font-size: 14px;
  font-weight: 500;
}
.tab-desc {
  font-size: 12px;
  color: var(--text-muted);
  margin: 0 0 12px;
}
.tab-chart-wrap {
  padding: 8px 0;
}
.tab-chart {
  width: 100%;
  height: 460px;
}
.trend-toolbar {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 12px;
}
.trend-hint {
  font-size: 12px;
  color: var(--text-muted);
}
</style>
