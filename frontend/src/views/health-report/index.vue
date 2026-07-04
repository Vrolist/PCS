<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ t('reportCenter.healthReport.title') }}</h2>
        <p class="page-desc">{{ t('reportCenter.healthReport.subtitle') }}</p>
      </div>
      <div class="header-actions">
        <el-select v-model="timeRange" size="default" style="width: 120px" @change="loadData">
          <el-option :label="t('healthReport.auto')" :value="0" />
          <el-option :label="t('healthReport.last3Days')" :value="3" />
          <el-option :label="t('healthReport.last7Days')" :value="7" />
          <el-option :label="t('healthReport.last14Days')" :value="14" />
          <el-option :label="t('healthReport.last30Days')" :value="30" />
        </el-select>
        <el-button @click="loadData" :icon="Refresh" circle />
        <el-button @click="exportPDF" :icon="Download" :loading="exporting">
          {{ t('healthReport.exportPDF') }}
        </el-button>
      </div>
    </div>

    <!-- 数据充足度提示 -->
    <el-alert
      v-if="report && report.summary.data_adequacy !== 'sufficient'"
      :title="adequacyTitle"
      :description="adequacyDesc"
      :type="adequacyType"
      show-icon
      :closable="false"
      class="adequacy-alert"
    />

    <div v-loading="loading">
      <!-- 顶部：总分 + 维度评分 -->
      <div class="score-section" v-if="report">
        <div class="overall-score-card">
          <div class="score-ring">
            <el-progress
              type="dashboard"
              :percentage="report.overall_score"
              :color="scoreColor(report.overall_score)"
              :width="140"
              :stroke-width="12"
            >
              <template #default="{ percentage }">
                <div class="score-inner">
                  <span class="score-number">{{ percentage }}</span>
                  <span class="score-label">{{ t('healthReport.overallScore') }}</span>
                </div>
              </template>
            </el-progress>
          </div>
          <div class="score-grade">{{ scoreGrade(report.overall_score) }}</div>
        </div>

        <div class="dimension-scores">
          <div class="dim-card" v-for="dim in dimensionCards" :key="dim.key">
            <div class="dim-header">
              <span class="dim-icon" :style="{ background: dim.gradient }">
                <el-icon><component :is="dim.icon" /></el-icon>
              </span>
              <span class="dim-label">{{ dim.label }}</span>
            </div>
            <div class="dim-score-row">
              <span class="dim-score" :style="{ color: scoreColor(dim.score) }">{{ dim.score }}</span>
              <el-progress
                :percentage="dim.score"
                :color="scoreColor(dim.score)"
                :stroke-width="6"
                :show-text="false"
                style="flex: 1"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- 资产概览 -->
      <div class="assets-section" v-if="report">
        <h3 class="section-title">{{ t('healthReport.assetOverview') }}</h3>
        <div class="asset-cards">
          <div class="asset-card">
            <div class="asset-icon" style="background: linear-gradient(135deg, #409eff, #79bbff)">
              <el-icon><Cpu /></el-icon>
            </div>
            <div class="asset-info">
              <span class="asset-value">{{ report.assets.online_nodes }}/{{ report.assets.total_nodes }}</span>
              <span class="asset-label">{{ t('healthReport.onlineNodes') }}</span>
            </div>
          </div>
          <div class="asset-card">
            <div class="asset-icon" style="background: linear-gradient(135deg, #67c23a, #95d475)">
              <el-icon><Monitor /></el-icon>
            </div>
            <div class="asset-info">
              <span class="asset-value">{{ report.assets.running_vms }}/{{ report.assets.total_vms }}</span>
              <span class="asset-label">{{ t('healthReport.runningVMs') }}</span>
            </div>
          </div>
          <div class="asset-card">
            <div class="asset-icon" style="background: linear-gradient(135deg, #8b5cf6, #a78bfa)">
              <el-icon><Box /></el-icon>
            </div>
            <div class="asset-info">
              <span class="asset-value">{{ report.assets.running_lxc }}/{{ report.assets.total_lxc }}</span>
              <span class="asset-label">{{ t('healthReport.runningContainers') }}</span>
            </div>
          </div>
          <div class="asset-card">
            <div class="asset-icon" style="background: linear-gradient(135deg, #e6a23c, #f0c78a)">
              <el-icon><Coin /></el-icon>
            </div>
            <div class="asset-info">
              <span class="asset-value">{{ fmtStorage(report.assets.used_storage_gb) }}/{{ fmtStorage(report.assets.total_storage_gb) }}</span>
              <span class="asset-label">{{ t('healthReport.storageUsage') }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 趋势图 -->
      <div class="trend-section" v-if="report && report.trends.dates.length > 1">
        <h3 class="section-title">{{ t('healthReport.resourceTrend') }}</h3>
        <v-chart :option="chartOption" autoresize class="trend-chart" />
      </div>
      <div class="trend-section" v-else-if="report && report.trends.dates.length <= 1">
        <h3 class="section-title">{{ t('healthReport.resourceTrend') }}</h3>
        <el-empty :description="t('healthReport.noTrendData')" />
      </div>

      <!-- 风险预警 -->
      <div class="issues-section" v-if="report">
        <h3 class="section-title">
          {{ t('healthReport.riskAlerts') }}
          <el-tag v-if="report.issues.length" :type="report.issues.some(i => i.severity === 'critical') ? 'danger' : 'warning'" size="small" style="margin-left: 8px">
            {{ report.issues.length }}
          </el-tag>
        </h3>
        <el-table
          v-if="report.issues.length"
          :data="report.issues"
          stripe
          style="width: 100%"
          :max-height="400"
        >
          <el-table-column :label="t('healthReport.severity')" width="100">
            <template #default="{ row }">
              <el-tag :type="row.severity === 'critical' ? 'danger' : 'warning'" size="small">
                {{ row.severity === 'critical' ? t('healthReport.critical') : t('healthReport.warning') }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="resource" :label="t('healthReport.resource')" width="200" />
          <el-table-column prop="detail" :label="t('healthReport.detail')" />
        </el-table>
        <el-empty v-else :description="t('healthReport.noIssues')" />
      </div>

      <!-- 概要统计 -->
      <div class="summary-section" v-if="report">
        <h3 class="section-title">{{ t('healthReport.reportSummary') }}</h3>
        <div class="summary-grid">
          <div class="summary-item">
            <span class="summary-label">{{ t('healthReport.reportPeriod') }}</span>
            <span class="summary-value">{{ report.summary.days }} {{ t('common.days') }}</span>
          </div>
          <div class="summary-item">
            <span class="summary-label">{{ t('healthReport.scanCount') }}</span>
            <span class="summary-value">{{ report.summary.scan_count }}</span>
          </div>
          <div class="summary-item">
            <span class="summary-label">{{ t('healthReport.avgCPU') }}</span>
            <span class="summary-value">{{ report.summary.avg_cpu }}%</span>
          </div>
          <div class="summary-item">
            <span class="summary-label">{{ t('healthReport.avgMemory') }}</span>
            <span class="summary-value">{{ report.summary.avg_mem }}%</span>
          </div>
          <div class="summary-item">
            <span class="summary-label">{{ t('healthReport.totalAlerts') }}</span>
            <span class="summary-value">{{ report.summary.total_alerts }}</span>
          </div>
          <div class="summary-item">
            <span class="summary-label">{{ t('healthReport.unresolvedAlerts') }}</span>
            <span class="summary-value" :class="{ 'text-danger': report.summary.unresolved_alerts > 0 }">
              {{ report.summary.unresolved_alerts }}
            </span>
          </div>
          <div class="summary-item">
            <span class="summary-label">{{ t('healthReport.backupJobs') }}</span>
            <span class="summary-value">{{ report.summary.backup_enabled }}/{{ report.summary.backup_total }}</span>
          </div>
          <div class="summary-item">
            <span class="summary-label">{{ t('healthReport.storageIssues') }}</span>
            <span class="summary-value" :class="{ 'text-danger': report.summary.storage_issue_count > 0 }">
              {{ report.summary.storage_issue_count }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import * as echarts from 'echarts'
import VChart from 'vue-echarts'
import { Refresh, Cpu, Monitor, Box, Coin, Bell, FolderOpened, DataAnalysis, Download } from '@element-plus/icons-vue'
import { useThemeStore } from '@/stores/theme'
import { useClusterStore } from '@/stores/cluster'
import { getHealthReport, type HealthReportData } from '@/api/dashboard'

const { t } = useI18n()
const themeStore = useThemeStore()
const clusterStore = useClusterStore()
const loading = ref(false)
const exporting = ref(false)
const timeRange = ref(0)
const report = ref<HealthReportData | null>(null)

async function loadData() {
  loading.value = true
  try {
    const clusterId = clusterStore.currentClusterId || undefined
    report.value = await getHealthReport(clusterId, timeRange.value)
  } catch {
    report.value = null
  } finally {
    loading.value = false
  }
}

async function exportPDF() {
  if (!report.value) return

  exporting.value = true
  try {
    const html2pdf = (await import('html2pdf.js')).default
    const element = document.querySelector('.page-container')
    if (!element) return

    const clusterName = clusterStore.currentClusterName || 'all'
    const date = new Date().toISOString().slice(0, 10)
    const filename = `health-report-${clusterName}-${date}.pdf`

    const opt = {
      margin: [10, 10, 10, 10],
      filename,
      image: { type: 'jpeg', quality: 0.98 },
      html2canvas: { scale: 2, useCORS: true, logging: false },
      jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' as const },
      pagebreak: { mode: ['avoid-all', 'css', 'legacy'] }
    }

    await html2pdf().set(opt).from(element).save()
  } catch (err) {
    console.error('Export PDF failed:', err)
    ElMessage.error(t('healthReport.exportFailed'))
  } finally {
    exporting.value = false
  }
}

watch(() => clusterStore.currentClusterId, loadData)
onMounted(loadData)

function scoreColor(score: number): string {
  if (score >= 90) return '#67c23a'
  if (score >= 70) return '#409eff'
  if (score >= 50) return '#e6a23c'
  return '#f56c6c'
}

function scoreGrade(score: number): string {
  if (score >= 90) return t('healthReport.gradeExcellent')
  if (score >= 70) return t('healthReport.gradeGood')
  if (score >= 50) return t('healthReport.gradeFair')
  return t('healthReport.gradePoor')
}

function fmtStorage(gb: number): string {
  if (gb >= 1024) return (gb / 1024).toFixed(1) + ' TB'
  return gb.toFixed(0) + ' GB'
}

const dimensionCards = computed(() => {
  if (!report.value) return []
  const s = report.value.scores
  return [
    { key: 'node', label: t('healthReport.dimNode'), icon: Cpu, gradient: 'linear-gradient(135deg, #409eff, #79bbff)', score: s.node.score },
    { key: 'resource', label: t('healthReport.dimResource'), icon: DataAnalysis, gradient: 'linear-gradient(135deg, #8b5cf6, #a78bfa)', score: s.resource.score },
    { key: 'alert', label: t('healthReport.dimAlert'), icon: Bell, gradient: 'linear-gradient(135deg, #e6a23c, #f0c78a)', score: s.alert.score },
    { key: 'backup', label: t('healthReport.dimBackup'), icon: FolderOpened, gradient: 'linear-gradient(135deg, #67c23a, #95d475)', score: s.backup.score },
    { key: 'completeness', label: t('healthReport.dimCompleteness'), icon: Monitor, gradient: 'linear-gradient(135deg, #909399, #b4b8bf)', score: s.completeness.score },
  ]
})

const adequacyType = computed(() => {
  if (!report.value) return 'warning'
  const d = report.value.summary.data_adequacy
  if (d === 'insufficient') return 'error'
  if (d === 'limited') return 'warning'
  return 'info'
})

const adequacyTitle = computed(() => {
  if (!report.value) return ''
  const d = report.value.summary.data_adequacy
  const map: Record<string, string> = {
    insufficient: t('healthReport.adequacyInsufficient'),
    limited: t('healthReport.adequacyLimited'),
    moderate: t('healthReport.adequacyModerate'),
  }
  return map[d] || ''
})

const adequacyDesc = computed(() => {
  if (!report.value) return ''
  const d = report.value.summary.data_adequacy
  const days = report.value.summary.actual_days
  const map: Record<string, string> = {
    insufficient: t('healthReport.adequacyInsufficientDesc'),
    limited: t('healthReport.adequacyLimitedDesc', { days }),
    moderate: t('healthReport.adequacyModerateDesc', { days }),
  }
  return map[d] || ''
})

const chartOption = computed(() => {
  if (!report.value || report.value.trends.dates.length <= 1) return {}
  const trends = report.value.trends
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
      data: trends.dates,
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
    series: [
      {
        name: 'CPU',
        type: 'line',
        smooth: true,
        data: trends.cpu,
        itemStyle: { color: '#409eff' },
        lineStyle: { color: '#409eff', width: 2 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(64, 158, 255, 0.35)' },
            { offset: 1, color: 'rgba(64, 158, 255, 0.02)' },
          ]),
        },
      },
      {
        name: t('healthReport.memory'),
        type: 'line',
        smooth: true,
        data: trends.memory,
        itemStyle: { color: '#8b5cf6' },
        lineStyle: { color: '#8b5cf6', width: 2 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(139, 92, 246, 0.35)' },
            { offset: 1, color: 'rgba(139, 92, 246, 0.02)' },
          ]),
        },
      },
    ],
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
.adequacy-alert {
  margin-bottom: 20px;
}

/* 评分区域 */
.score-section {
  display: flex;
  gap: 24px;
  margin-bottom: 24px;
}
@media (max-width: 900px) {
  .score-section { flex-direction: column; }
}
.overall-score-card {
  background: var(--bg-card, var(--bg-primary));
  border: 1px solid var(--border-color);
  border-radius: 16px;
  padding: 32px 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 200px;
}
.score-ring {
  margin-bottom: 12px;
}
.score-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
}
.score-number {
  font-size: 36px;
  font-weight: 800;
  color: var(--text-heading);
  line-height: 1;
}
.score-label {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 4px;
}
.score-grade {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-heading);
}
.dimension-scores {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
}
.dim-card {
  background: var(--bg-card, var(--bg-primary));
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 16px;
  transition: box-shadow 0.2s;
}
.dim-card:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
}
.dim-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}
.dim-icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 16px;
  flex-shrink: 0;
}
.dim-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-heading);
}
.dim-score-row {
  display: flex;
  align-items: center;
  gap: 12px;
}
.dim-score {
  font-size: 24px;
  font-weight: 700;
  min-width: 40px;
}

/* 资产概览 */
.assets-section, .trend-section, .issues-section, .summary-section {
  background: var(--bg-card, var(--bg-primary));
  border: 1px solid var(--border-color);
  border-radius: 16px;
  padding: 20px 24px;
  margin-bottom: 20px;
}
.section-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-heading);
  margin: 0 0 16px 0;
  display: flex;
  align-items: center;
}
.asset-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}
@media (max-width: 900px) {
  .asset-cards { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 500px) {
  .asset-cards { grid-template-columns: 1fr; }
}
.asset-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px;
  background: var(--bg-secondary, var(--bg-primary));
  border-radius: 12px;
}
.asset-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 20px;
  flex-shrink: 0;
}
.asset-info {
  display: flex;
  flex-direction: column;
}
.asset-value {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-heading);
}
.asset-label {
  font-size: 12px;
  color: var(--text-muted);
}

/* 趋势图 */
.trend-chart {
  width: 100%;
  height: 300px;
}

/* 概要统计 */
.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}
@media (max-width: 900px) {
  .summary-grid { grid-template-columns: repeat(2, 1fr); }
}
.summary-item {
  display: flex;
  flex-direction: column;
  padding: 12px 16px;
  background: var(--bg-secondary, var(--bg-primary));
  border-radius: 10px;
}
.summary-label {
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 4px;
}
.summary-value {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-heading);
}
.text-danger {
  color: #f56c6c;
}
</style>
