<template>
  <div class="trend-chart-card">
    <div class="trend-chart-header">
      <h3 class="trend-chart-title">资源趋势</h3>
      <div class="trend-chart-filters">
        <el-select v-model="clusterFilter" size="small" placeholder="全部集群" clearable style="width: 140px" @change="loadTrends">
          <el-option v-for="c in clusterList" :key="c.id" :label="c.name" :value="c.id" />
        </el-select>
        <el-select v-model="timeRange" size="small" class="time-range-select" @change="loadTrends">
          <el-option label="近 7 天" value="7" />
          <el-option label="近 15 天" value="15" />
        </el-select>
      </div>
    </div>
    <div class="trend-chart-body">
      <v-chart :option="chartOption" autoresize class="trend-chart" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import * as echarts from 'echarts'
import VChart from 'vue-echarts'
import { useThemeStore } from '@/stores/theme'
import { getDashboardTrends } from '@/api/dashboard'
import { getClusters, type Cluster } from '@/api/clusters'

const timeRange = ref('7')
const themeStore = useThemeStore()
const clusterFilter = ref<number | ''>('')
const clusterList = ref<Cluster[]>([])

const dates = ref<string[]>([])
const cpuData = ref<number[]>([])
const memoryData = ref<number[]>([])

async function loadTrends() {
  try {
    const data = await getDashboardTrends(Number(timeRange.value), clusterFilter.value || undefined)
    dates.value = data.dates
    cpuData.value = data.cpu_avg
    memoryData.value = data.memory_avg
  } catch {
    // empty chart on error
  }
}

onMounted(async () => {
  try {
    const res = await getClusters()
    clusterList.value = res.results
  } catch {} finally {
    loadTrends()
  }
})

const chartOption = computed(() => {
  const isDark = themeStore.theme === 'dark'
  const textColor = isDark ? '#a0a0c0' : '#606266'
  const lineColor = isDark ? 'rgba(42, 42, 80, 0.6)' : 'rgba(200, 200, 220, 0.5)'
  const axisColor = isDark ? '#2a2a50' : '#d9dce4'
  const tooltipBg = isDark ? 'rgba(30, 30, 72, 0.92)' : 'rgba(255, 255, 255, 0.96)'
  const tooltipBorder = isDark ? '#2a2a50' : '#e2e5ed'
  const tooltipText = isDark ? '#e0e0f0' : '#303133'

  return {
    tooltip: {
      trigger: 'axis' as const,
      backgroundColor: tooltipBg,
      borderColor: tooltipBorder,
      textStyle: { color: tooltipText }
    },
    legend: {
      top: 0, right: 0,
      textStyle: { color: textColor }
    },
    grid: { left: 40, right: 20, bottom: 30, top: 40 },
    xAxis: {
      type: 'category' as const,
      boundaryGap: false,
      data: dates.value,
      axisLine: { lineStyle: { color: axisColor } },
      axisTick: { lineStyle: { color: axisColor } },
      axisLabel: { color: textColor }
    },
    yAxis: {
      type: 'value' as const,
      max: 100,
      axisLabel: { formatter: '{value}%', color: textColor },
      splitLine: { lineStyle: { color: lineColor, type: 'dashed' as const } }
    },
    series: [
      {
        name: 'CPU 使用率',
        type: 'line',
        smooth: true,
        data: cpuData.value,
        itemStyle: { color: '#409eff' },
        lineStyle: { color: '#409eff', width: 2 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(64, 158, 255, 0.35)' },
            { offset: 1, color: 'rgba(64, 158, 255, 0.02)' }
          ])
        }
      },
      {
        name: '内存使用率',
        type: 'line',
        smooth: true,
        data: memoryData.value,
        itemStyle: { color: '#8b5cf6' },
        lineStyle: { color: '#8b5cf6', width: 2 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(139, 92, 246, 0.35)' },
            { offset: 1, color: 'rgba(139, 92, 246, 0.02)' }
          ])
        }
      }
    ]
  }
})
</script>

<style scoped>
.trend-chart-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  overflow: hidden;
  transition: background-color 0.3s, border-color 0.3s;
}
.trend-chart-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 20px 24px 0;
}
.trend-chart-title { font-size: 16px; font-weight: 600; color: var(--text-heading); margin: 0; }
.trend-chart-filters { display: flex; gap: 8px; align-items: center; }
.time-range-select { width: 120px; }
.trend-chart-body { padding: 8px 16px 16px; }
.trend-chart { width: 100%; height: 260px; }
</style>
