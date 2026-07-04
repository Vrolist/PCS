<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ t('smartAnalysis.capacityPlanning.title') }}</h2>
        <p class="page-desc">{{ t('smartAnalysis.capacityPlanning.subtitle') }}</p>
      </div>
      <div class="header-actions">
        <el-select v-model="timeRange" size="default" style="width: 120px" @change="loadData">
          <el-option label="7 天" :value="7" />
          <el-option label="15 天" :value="15" />
          <el-option label="30 天" :value="30" />
        </el-select>
      </div>
    </div>

    <!-- 预测卡片 -->
    <div class="pred-cards" v-loading="loading">
      <div class="pred-card" v-for="dim in dimensions" :key="dim.key">
        <div class="pred-card-header">
          <span class="pred-card-icon" :style="{ background: dim.gradient }">
            <el-icon><component :is="dim.icon" /></el-icon>
          </span>
          <span class="pred-card-label">{{ dim.label }}</span>
          <span class="pred-trend-tag" :class="dim.trendClass">{{ dim.trendText }}</span>
        </div>
        <div class="pred-card-body">
          <div class="pred-current">
            <span class="pred-value">{{ dim.currentDisplay }}</span>
            <span class="pred-unit">{{ dim.unit }}</span>
          </div>
          <div class="pred-progress" v-if="dim.pct !== null">
            <el-progress :percentage="dim.pct" :color="dim.color" :stroke-width="8" :show-text="false" />
          </div>
          <div class="pred-detail">
            <template v-if="dim.daysUntilFull !== null">
              <span class="pred-full-date">
                {{ t('smartAnalysis.capacityPlanning.daysUntilFull', { days: dim.daysUntilFull }) }}
              </span>
              <span class="pred-date">{{ dim.predictedDate }}</span>
            </template>
            <template v-else-if="dim.slopeDisplay">
              <span class="pred-slope">{{ dim.slopeDisplay }}</span>
            </template>
            <template v-else>
              <span class="pred-no-data">{{ t('smartAnalysis.capacityPlanning.noPrediction') }}</span>
            </template>
          </div>
        </div>
      </div>
    </div>

    <!-- 趋势图表 -->
    <div class="chart-section">
      <div class="chart-header">
        <h3 class="chart-title">{{ t('smartAnalysis.capacityPlanning.trendChart') }}</h3>
        <el-checkbox-group v-model="visibleSeries" size="small" @change="updateChart">
          <el-checkbox-button v-for="s in allSeries" :key="s.key" :value="s.key" :label="s.label" />
        </el-checkbox-group>
      </div>
      <v-chart :option="chartOption" autoresize class="prediction-chart" />
      <div class="chart-footer">
        <span class="chart-note">{{ t('smartAnalysis.capacityPlanning.chartNote') }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import * as echarts from 'echarts'
import VChart from 'vue-echarts'
import { useThemeStore } from '@/stores/theme'
import { useClusterStore } from '@/stores/cluster'
import { getPredictions, type Predictions, type PredictionDimension } from '@/api/dashboard'
import { Cpu, Coin, Box, Memo } from '@element-plus/icons-vue'

const { t } = useI18n()
const themeStore = useThemeStore()
const clusterStore = useClusterStore()
const loading = ref(false)
const timeRange = ref(30)
const predictions = ref<Predictions | null>(null)
const visibleSeries = ref(['cpu', 'memory', 'storage', 'rootfs'])

/** 自动适配 GB → TB → PB */
function fmtSize(gb: number | null | undefined): { value: string; unit: string } {
  if (gb === null || gb === undefined) return { value: '--', unit: 'GB' }
  if (gb >= 1024 * 1024) return { value: (gb / 1024 / 1024).toFixed(1), unit: 'PB' }
  if (gb >= 1024) return { value: (gb / 1024).toFixed(1), unit: 'TB' }
  return { value: gb.toFixed(0), unit: 'GB' }
}

/** 斜率也跟着自动适配 */
function fmtSlope(gbPerDay: number | null | undefined): string {
  if (gbPerDay === null || gbPerDay === undefined) return ''
  if (Math.abs(gbPerDay) >= 1024) return `${t('smartAnalysis.capacityPlanning.perDay')} ${(gbPerDay / 1024).toFixed(1)} TB`
  return `${t('smartAnalysis.capacityPlanning.perDay')} ${gbPerDay} GB`
}

const allSeries = [
  { key: 'cpu', label: 'CPU' },
  { key: 'memory', label: t('smartAnalysis.capacityPlanning.memory') },
  { key: 'storage', label: t('smartAnalysis.capacityPlanning.storage') },
  { key: 'rootfs', label: t('smartAnalysis.capacityPlanning.rootfs') },
]

async function loadData() {
  loading.value = true
  try {
    const clusterId = clusterStore.currentClusterId || undefined
    predictions.value = await getPredictions(clusterId, timeRange.value)
  } catch {
    predictions.value = null
  } finally {
    loading.value = false
  }
}

watch(() => clusterStore.currentClusterId, loadData)

onMounted(loadData)

function getTrendInfo(dim: PredictionDimension) {
  const trend = dim.trend
  const slope = dim.slope_per_day ?? dim.slope_gb_per_day
  if (trend === 'rising') return { class: 'trend-rising', text: t('smartAnalysis.capacityPlanning.trendRising') + (slope ? ` ↑${Math.abs(slope)}` : '') }
  if (trend === 'declining') return { class: 'trend-declining', text: t('smartAnalysis.capacityPlanning.trendDeclining') + (slope ? ` ↓${Math.abs(slope)}` : '') }
  if (trend === 'stable') return { class: 'trend-stable', text: t('smartAnalysis.capacityPlanning.trendStable') }
  return { class: '', text: '--' }
}

interface DimCard {
  key: string
  label: string
  icon: any
  gradient: string
  color: string
  currentDisplay: string
  unit: string
  pct: number | null
  daysUntilFull: number | null
  predictedDate: string
  slopeDisplay: string
  trendClass: string
  trendText: string
}

const dimensions = computed<DimCard[]>(() => {
  if (!predictions.value) return []
  const p = predictions.value

  const cpuTrend = getTrendInfo(p.cpu)
  const memTrend = getTrendInfo(p.memory)
  const storTrend = getTrendInfo(p.storage)
  const rootTrend = getTrendInfo(p.rootfs)

  return [
    {
      key: 'cpu',
      label: 'CPU',
      icon: Cpu,
      gradient: 'linear-gradient(135deg, #409eff, #79bbff)',
      color: '#409eff',
      currentDisplay: p.cpu.current !== null ? `${p.cpu.current}%` : '--',
      unit: '',
      pct: p.cpu.current,
      daysUntilFull: p.cpu.days_until_full,
      predictedDate: p.cpu.predicted_full_date || '',
      slopeDisplay: p.cpu.slope_per_day !== null ? `${t('smartAnalysis.capacityPlanning.perDay')} ${p.cpu.slope_per_day}%` : '',
      trendClass: cpuTrend.class,
      trendText: cpuTrend.text,
    },
    {
      key: 'memory',
      label: t('smartAnalysis.capacityPlanning.memory'),
      icon: Memo,
      gradient: 'linear-gradient(135deg, #8b5cf6, #a78bfa)',
      color: '#8b5cf6',
      currentDisplay: p.memory.current !== null ? `${p.memory.current}%` : '--',
      unit: p.memory.total_mb ? `(${(p.memory.total_mb / 1024).toFixed(0)} GB)` : '',
      pct: p.memory.current,
      daysUntilFull: p.memory.days_until_full,
      predictedDate: p.memory.predicted_full_date || '',
      slopeDisplay: p.memory.slope_per_day !== null ? `${t('smartAnalysis.capacityPlanning.perDay')} ${p.memory.slope_per_day}%` : '',
      trendClass: memTrend.class,
      trendText: memTrend.text,
    },
    {
      key: 'storage',
      label: t('smartAnalysis.capacityPlanning.storage'),
      icon: Coin,
      gradient: 'linear-gradient(135deg, #e6a23c, #f0c78a)',
      color: '#e6a23c',
      currentDisplay: fmtSize(p.storage.current_used_gb).value,
      unit: p.storage.total_gb ? `/ ${fmtSize(p.storage.total_gb).value} ${fmtSize(p.storage.total_gb).unit}` : 'GB',
      pct: p.storage.current_pct ?? null,
      daysUntilFull: p.storage.days_until_full,
      predictedDate: p.storage.predicted_full_date || '',
      slopeDisplay: fmtSlope(p.storage.slope_gb_per_day),
      trendClass: storTrend.class,
      trendText: storTrend.text,
    },
    {
      key: 'rootfs',
      label: t('smartAnalysis.capacityPlanning.rootfs'),
      icon: Box,
      gradient: 'linear-gradient(135deg, #67c23a, #95d475)',
      color: '#67c23a',
      currentDisplay: fmtSize(p.rootfs.current_used_gb).value,
      unit: p.rootfs.total_gb ? `/ ${fmtSize(p.rootfs.total_gb).value} ${fmtSize(p.rootfs.total_gb).unit}` : 'GB',
      pct: p.rootfs.current_pct ?? null,
      daysUntilFull: p.rootfs.days_until_full,
      predictedDate: p.rootfs.predicted_full_date || '',
      slopeDisplay: fmtSlope(p.rootfs.slope_gb_per_day),
      trendClass: rootTrend.class,
      trendText: rootTrend.text,
    },
  ]
})

function updateChart() {
  // vue-echarts 会自动响应 computed 变化
}

const chartOption = computed(() => {
  if (!predictions.value) return {}
  const p = predictions.value
  const isDark = themeStore.theme === 'dark'
  const textColor = isDark ? '#a0a0c0' : '#606266'
  const lineColor = isDark ? 'rgba(42, 42, 80, 0.6)' : 'rgba(200, 200, 220, 0.5)'
  const axisColor = isDark ? '#2a2a50' : '#d9dce4'
  const tooltipBg = isDark ? 'rgba(30, 30, 72, 0.92)' : 'rgba(255, 255, 255, 0.96)'
  const tooltipBorder = isDark ? '#2a2a50' : '#e2e5ed'
  const tooltipText = isDark ? '#e0e0f0' : '#303133'

  const seriesConfigs: Record<string, { dim: PredictionDimension; color: string; label: string }> = {
    cpu: { dim: p.cpu, color: '#409eff', label: 'CPU' },
    memory: { dim: p.memory, color: '#8b5cf6', label: t('smartAnalysis.capacityPlanning.memory') },
    storage: { dim: p.storage, color: '#e6a23c', label: t('smartAnalysis.capacityPlanning.storage') },
    rootfs: { dim: p.rootfs, color: '#67c23a', label: t('smartAnalysis.capacityPlanning.rootfs') },
  }

  // 收集所有日期
  const allDates = new Set<string>()
  for (const key of visibleSeries.value) {
    const cfg = seriesConfigs[key]
    if (!cfg) continue
    cfg.dim.chart.dates.forEach(d => allDates.add(d))
    cfg.dim.chart.predicted_dates.forEach(d => allDates.add(d))
  }
  const sortedDates = Array.from(allDates).sort()

  const series: any[] = []
  for (const key of visibleSeries.value) {
    const cfg = seriesConfigs[key]
    if (!cfg) continue
    const { dim, color, label } = cfg

    // 历史数据
    const historyData = new Map(dim.chart.dates.map((d, i) => [d, dim.chart.values[i]]))
    // 预测数据
    const predictData = new Map(dim.chart.predicted_dates.map((d, i) => [d, dim.chart.predicted_values[i]]))

    series.push({
      name: label,
      type: 'line',
      smooth: true,
      symbol: 'none',
      data: sortedDates.map(d => historyData.get(d) ?? null),
      itemStyle: { color },
      lineStyle: { color, width: 2 },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: color.replace(')', ', 0.25)').replace('rgb', 'rgba') },
          { offset: 1, color: color.replace(')', ', 0.02)').replace('rgb', 'rgba') },
        ]),
      },
    })

    // 预测虚线
    const hasPrediction = dim.chart.predicted_dates.length > 0
    if (hasPrediction) {
      series.push({
        name: `${label} (${t('smartAnalysis.capacityPlanning.prediction')})`,
        type: 'line',
        smooth: true,
        symbol: 'none',
        lineStyle: { color, width: 2, type: 'dashed' },
        itemStyle: { color },
        data: sortedDates.map(d => {
          if (predictData.has(d)) return predictData.get(d)
          if (historyData.has(d)) return null
          return null
        }),
      })
    }
  }

  // 85% / 95% 阈值线
  const markLine = {
    silent: true,
    symbol: 'none',
    lineStyle: { type: 'dashed' as const, width: 1 },
    data: [
      { yAxis: 85, label: { formatter: '85%', position: 'end' as const, color: '#e6a23c', fontSize: 11 }, lineStyle: { color: 'rgba(230, 162, 60, 0.5)' } },
      { yAxis: 95, label: { formatter: '95%', position: 'end' as const, color: '#f56c6c', fontSize: 11 }, lineStyle: { color: 'rgba(245, 108, 108, 0.5)' } },
    ],
  }

  if (series.length > 0) {
    // 在第一个 series 上添加 markLine
    series[0].markLine = markLine
  }

  return {
    tooltip: {
      trigger: 'axis' as const,
      backgroundColor: tooltipBg,
      borderColor: tooltipBorder,
      textStyle: { color: tooltipText },
    },
    legend: {
      top: 0, right: 0,
      textStyle: { color: textColor },
    },
    grid: { left: 50, right: 20, bottom: 30, top: 40 },
    xAxis: {
      type: 'category' as const,
      boundaryGap: false,
      data: sortedDates,
      axisLine: { lineStyle: { color: axisColor } },
      axisTick: { lineStyle: { color: axisColor } },
      axisLabel: { color: textColor },
    },
    yAxis: {
      type: 'value' as const,
      max: 100,
      axisLabel: { formatter: '{value}%', color: textColor },
      splitLine: { lineStyle: { color: lineColor, type: 'dashed' as const } },
    },
    series,
  }
})
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
.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

/* 预测卡片 */
.pred-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}
@media (max-width: 1200px) {
  .pred-cards { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 768px) {
  .pred-cards { grid-template-columns: 1fr; }
}
.pred-card {
  background: var(--bg-card, var(--bg-primary));
  border: 1px solid var(--border-color);
  border-radius: 16px;
  padding: 20px;
  transition: box-shadow 0.2s;
}
.pred-card:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
}
.pred-card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
}
.pred-card-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 18px;
  flex-shrink: 0;
}
.pred-card-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-heading);
  flex: 1;
}
.pred-trend-tag {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 500;
}
.trend-rising {
  background: rgba(245, 108, 108, 0.12);
  color: #f56c6c;
}
.trend-declining {
  background: rgba(103, 194, 58, 0.12);
  color: #67c23a;
}
.trend-stable {
  background: rgba(144, 147, 153, 0.12);
  color: #909399;
}
.pred-card-body {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.pred-current {
  display: flex;
  align-items: baseline;
  gap: 4px;
}
.pred-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-heading);
  line-height: 1;
}
.pred-unit {
  font-size: 13px;
  color: var(--text-muted);
}
.pred-progress {
  margin: 2px 0;
}
.pred-detail {
  font-size: 12px;
  color: var(--text-muted);
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.pred-full-date {
  color: #e6a23c;
  font-weight: 500;
}
.pred-date {
  font-size: 11px;
  color: var(--text-muted);
}
.pred-slope {
  color: var(--text-muted);
}
.pred-no-data {
  color: var(--text-muted);
  font-style: italic;
}

/* 图表 */
.chart-section {
  background: var(--bg-card, var(--bg-primary));
  border: 1px solid var(--border-color);
  border-radius: 16px;
  overflow: hidden;
}
.chart-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px 0;
  flex-wrap: wrap;
  gap: 12px;
}
.chart-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-heading);
  margin: 0;
}
.prediction-chart {
  width: 100%;
  height: 360px;
}
.chart-footer {
  padding: 0 24px 16px;
}
.chart-note {
  font-size: 11px;
  color: var(--text-muted);
  font-style: italic;
}
</style>
