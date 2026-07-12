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
        <!-- <el-button @click="exportPDF" :icon="Download" :loading="exporting">
          {{ t('healthReport.exportPDF') }}
        </el-button> -->
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
import { ElMessage } from 'element-plus'
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
    const { jsPDF } = await import('jspdf')
    const r = report.value

    // A4 尺寸 (mm)
    const pageWidth = 210
    const pageHeight = 297
    const margin = 15
    const contentWidth = pageWidth - margin * 2

    // 创建 PDF 文档
    const doc = new jsPDF({
      orientation: 'portrait',
      unit: 'mm',
      format: 'a4'
    })

    // 颜色定义
    const colors = {
      primary: '#409eff',
      success: '#67c23a',
      warning: '#e6a23c',
      danger: '#f56c6c',
      text: '#333333',
      textSecondary: '#666666',
      textLight: '#999999',
      background: '#f8f9fa',
      border: '#eeeeee'
    }

    // 辅助函数：设置颜色
    const setColor = (color: string) => {
      const hex = color.replace('#', '')
      const r = parseInt(hex.substr(0, 2), 16)
      const g = parseInt(hex.substr(2, 2), 16)
      const b = parseInt(hex.substr(4, 2), 16)
      doc.setTextColor(r, g, b)
    }

    const setDrawColor = (color: string) => {
      const hex = color.replace('#', '')
      const r = parseInt(hex.substr(0, 2), 16)
      const g = parseInt(hex.substr(2, 2), 16)
      const b = parseInt(hex.substr(4, 2), 16)
      doc.setDrawColor(r, g, b)
    }

    const setFillColor = (color: string) => {
      const hex = color.replace('#', '')
      const r = parseInt(hex.substr(0, 2), 16)
      const g = parseInt(hex.substr(2, 2), 16)
      const b = parseInt(hex.substr(4, 2), 16)
      doc.setFillColor(r, g, b)
    }

    // 格式化时间
    const formatDateTime = (isoStr: string) => {
      const d = new Date(isoStr)
      return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}`
    }

    const now = new Date()
    const pcsVersion = `v${r.platform_version || 'N/A'}`
    const agentVersion = `v${r.agent_version || 'N/A'}`
    const periodStart = r.data_period?.earliest ? formatDateTime(r.data_period.earliest) : 'N/A'
    const periodEnd = r.data_period?.latest ? formatDateTime(r.data_period.latest) : 'N/A'
    const exportTime = formatDateTime(now.toISOString())
    const clusterName = clusterStore.currentCluster?.name || t('healthReport.allClusters')

    let y = margin

    // === 报告头部 ===
    // 标题
    doc.setFontSize(24)
    setColor(colors.text)
    doc.setFont('helvetica', 'bold')
    doc.text('PVE Cluster Health Report', pageWidth / 2, y + 8, { align: 'center' })

    // 集群名称
    doc.setFontSize(16)
    setColor(colors.textSecondary)
    doc.setFont('helvetica', 'normal')
    doc.text(clusterName, pageWidth / 2, y + 18, { align: 'center' })

    // 分隔线
    y += 25
    setDrawColor(colors.primary)
    doc.setLineWidth(0.8)
    doc.line(margin, y, pageWidth - margin, y)

    // 版本信息
    y += 8
    doc.setFontSize(9)
    setColor(colors.textSecondary)

    // 左侧信息
    doc.setFont('helvetica', 'bold')
    doc.text('PCS Version:', margin, y)
    doc.setFont('helvetica', 'normal')
    doc.text(pcsVersion, margin + 25, y)

    doc.setFont('helvetica', 'bold')
    doc.text('PCS-Agent Version:', margin, y + 5)
    doc.setFont('helvetica', 'normal')
    doc.text(agentVersion, margin + 35, y + 5)

    // 右侧信息
    doc.setFont('helvetica', 'bold')
    doc.text('Report Period:', pageWidth / 2 + 10, y)
    doc.setFont('helvetica', 'normal')
    doc.text(`${periodStart} ~ ${periodEnd}`, pageWidth / 2 + 35, y)

    doc.setFont('helvetica', 'bold')
    doc.text('Export Time:', pageWidth / 2 + 10, y + 5)
    doc.setFont('helvetica', 'normal')
    doc.text(exportTime, pageWidth / 2 + 32, y + 5)

    y += 15

    // === 总体评分 ===
    const scoreColor = r.overall_score >= 90 ? colors.success :
      r.overall_score >= 70 ? colors.primary :
      r.overall_score >= 50 ? colors.warning : colors.danger

    const scoreGrade = r.overall_score >= 90 ? 'Healthy' :
      r.overall_score >= 70 ? 'Good' :
      r.overall_score >= 50 ? 'Fair' : 'Critical'

    // 评分卡片背景
    setFillColor(colors.background)
    doc.roundedRect(margin, y, contentWidth, 30, 3, 3, 'F')

    // 评分数字
    doc.setFontSize(36)
    setColor(scoreColor)
    doc.setFont('helvetica', 'bold')
    doc.text(String(r.overall_score), pageWidth / 2 - 15, y + 18, { align: 'center' })

    // 评分标签
    doc.setFontSize(12)
    setColor(colors.textSecondary)
    doc.setFont('helvetica', 'normal')
    doc.text('Overall Score', pageWidth / 2 - 15, y + 25, { align: 'center' })

    // 等级
    doc.setFontSize(14)
    setColor(scoreColor)
    doc.setFont('helvetica', 'bold')
    doc.text(scoreGrade, pageWidth / 2 + 25, y + 18, { align: 'center' })

    y += 38

    // === 维度评分 ===
    const dimensions = [
      { name: 'Node Health', score: r.scores.node.score, weight: r.scores.node.weight },
      { name: 'Resource Usage', score: r.scores.resource.score, weight: r.scores.resource.weight },
      { name: 'Alert Status', score: r.scores.alert.score, weight: r.scores.alert.weight },
      { name: 'Backup Status', score: r.scores.backup.score, weight: r.scores.backup.weight },
      { name: 'Data Completeness', score: r.scores.completeness.score, weight: r.scores.completeness.weight }
    ]

    const cardWidth = (contentWidth - 20) / 5
    const cardHeight = 25

    dimensions.forEach((dim, index) => {
      const x = margin + index * (cardWidth + 5)

      // 卡片背景
      setFillColor(colors.background)
      doc.roundedRect(x, y, cardWidth, cardHeight, 2, 2, 'F')

      // 顶部颜色条
      const dimColor = dim.score >= 90 ? colors.success :
        dim.score >= 70 ? colors.primary :
        dim.score >= 50 ? colors.warning : colors.danger
      setFillColor(dimColor)
      doc.rect(x, y, cardWidth, 2, 'F')

      // 分数
      doc.setFontSize(20)
      setColor(dimColor)
      doc.setFont('helvetica', 'bold')
      doc.text(String(dim.score), x + cardWidth / 2, y + 12, { align: 'center' })

      // 名称
      doc.setFontSize(8)
      setColor(colors.textSecondary)
      doc.setFont('helvetica', 'normal')
      doc.text(dim.name, x + cardWidth / 2, y + 18, { align: 'center' })

      // 权重
      doc.setFontSize(7)
      setColor(colors.textLight)
      doc.text(`Weight: ${(dim.weight * 100).toFixed(0)}%`, x + cardWidth / 2, y + 22, { align: 'center' })
    })

    y += cardHeight + 8

    // === 资产概览 ===
    setFillColor(colors.background)
    doc.roundedRect(margin, y, contentWidth, 25, 3, 3, 'F')

    doc.setFontSize(11)
    setColor(colors.text)
    doc.setFont('helvetica', 'bold')
    doc.text('Asset Overview', margin + 5, y + 7)

    // 分隔线
    setDrawColor(colors.border)
    doc.setLineWidth(0.2)
    doc.line(margin + 5, y + 9, margin + contentWidth - 5, y + 9)

    // 资产卡片
    const assets = [
      { label: 'Online Nodes', value: `${r.assets.online_nodes}/${r.assets.total_nodes}`, color: colors.primary },
      { label: 'Running VMs', value: `${r.assets.running_vms}/${r.assets.total_vms}`, color: colors.success },
      { label: 'Running Containers', value: `${r.assets.running_lxc}/${r.assets.total_lxc}`, color: colors.success },
      { label: 'Storage Usage', value: `${fmtStorage(r.assets.used_storage_gb)}/${fmtStorage(r.assets.total_storage_gb)}`, color: colors.primary }
    ]

    const assetCardWidth = (contentWidth - 30) / 4

    assets.forEach((asset, index) => {
      const x = margin + 10 + index * (assetCardWidth + 5)

      // 卡片背景
      doc.setFillColor(255, 255, 255)
      doc.roundedRect(x, y + 12, assetCardWidth, 10, 2, 2, 'F')

      // 数值
      doc.setFontSize(12)
      setColor(asset.color)
      doc.setFont('helvetica', 'bold')
      doc.text(asset.value, x + assetCardWidth / 2, y + 18, { align: 'center' })

      // 标签
      doc.setFontSize(7)
      setColor(colors.textSecondary)
      doc.setFont('helvetica', 'normal')
      doc.text(asset.label, x + assetCardWidth / 2, y + 22, { align: 'center' })
    })

    y += 30

    // === 资源趋势图表 ===
    if (r.trends.dates.length > 1) {
      doc.setFontSize(11)
      setColor(colors.text)
      doc.setFont('helvetica', 'bold')
      doc.text('Resource Trend', margin, y + 5)

      // 分隔线
      setDrawColor(colors.border)
      doc.setLineWidth(0.2)
      doc.line(margin, y + 7, margin + contentWidth, y + 7)

      y += 10

      // 获取 ECharts 图表并转为图片
      const chartEl = document.querySelector('.trend-chart canvas') as HTMLCanvasElement
      if (chartEl) {
        try {
          const imgData = chartEl.toDataURL('image/png', 1.0)
          const chartWidth = contentWidth
          const chartHeight = 45
          doc.addImage(imgData, 'PNG', margin, y, chartWidth, chartHeight)
          y += chartHeight + 5
        } catch (e) {
          console.warn('Failed to export chart:', e)
          y += 5
        }
      }
    }

    // === 风险预警 ===
    if (r.issues.length > 0) {
      doc.setFontSize(11)
      setColor(colors.text)
      doc.setFont('helvetica', 'bold')
      doc.text('Risk Alerts', margin, y + 5)

      // 分隔线
      setDrawColor(colors.border)
      doc.setLineWidth(0.2)
      doc.line(margin, y + 7, margin + contentWidth, y + 7)

      y += 10

      // 表头
      setFillColor(colors.background)
      doc.rect(margin, y, contentWidth, 6, 'F')

      doc.setFontSize(8)
      setColor(colors.text)
      doc.setFont('helvetica', 'bold')
      doc.text('Severity', margin + 3, y + 4)
      doc.text('Resource', margin + 25, y + 4)
      doc.text('Detail', margin + 65, y + 4)

      y += 6

      // 表格内容
      const issues = r.issues.slice(0, 8) // 最多显示 8 条
      issues.forEach((issue) => {
        // 检查是否需要换页
        if (y > pageHeight - 30) {
          doc.addPage()
          y = margin
        }

        // 背景
        doc.setFillColor(255, 255, 255)
        doc.rect(margin, y, contentWidth, 5, 'F')

        // 边框
        setDrawColor(colors.border)
        doc.setLineWidth(0.1)
        doc.line(margin, y + 5, margin + contentWidth, y + 5)

        // 严重程度标签
        const severityColor = issue.severity === 'critical' ? colors.danger : colors.warning
        setFillColor(severityColor)
        doc.roundedRect(margin + 2, y + 1, 15, 3, 1, 1, 'F')
        doc.setFontSize(6)
        doc.setTextColor(255, 255, 255)
        doc.text(issue.severity.toUpperCase(), margin + 9.5, y + 3.5, { align: 'center' })

        // 资源
        doc.setFontSize(7)
        setColor(colors.text)
        doc.text(issue.resource.substring(0, 20), margin + 25, y + 3.5)

        // 详情
        setColor(colors.textSecondary)
        doc.text(issue.detail.substring(0, 60), margin + 65, y + 3.5)

        y += 5
      })

      y += 5
    }

    // === 报告概要 ===
    // 检查是否需要换页
    if (y > pageHeight - 50) {
      doc.addPage()
      y = margin
    }

    setFillColor(colors.background)
    doc.roundedRect(margin, y, contentWidth, 25, 3, 3, 'F')

    doc.setFontSize(11)
    setColor(colors.text)
    doc.setFont('helvetica', 'bold')
    doc.text('Report Summary', margin + 5, y + 7)

    // 分隔线
    setDrawColor(colors.border)
    doc.setLineWidth(0.2)
    doc.line(margin + 5, y + 9, margin + contentWidth - 5, y + 9)

    // 概要数据
    const summaryItems = [
      { label: 'Scan Count', value: String(r.summary.scan_count), color: colors.primary },
      { label: 'Avg CPU', value: `${r.summary.avg_cpu.toFixed(1)}%`, color: colors.success },
      { label: 'Avg Memory', value: `${r.summary.avg_mem.toFixed(1)}%`, color: colors.success },
      { label: 'Total Alerts', value: String(r.summary.total_alerts), color: colors.warning },
      { label: 'Unresolved', value: String(r.summary.unresolved_alerts), color: r.summary.unresolved_alerts > 0 ? colors.danger : colors.success },
      { label: 'Storage Issues', value: String(r.summary.storage_issue_count), color: r.summary.storage_issue_count > 0 ? colors.warning : colors.success }
    ]

    const summaryCardWidth = (contentWidth - 20) / 6

    summaryItems.forEach((item, index) => {
      const x = margin + 5 + index * (summaryCardWidth + 3)

      // 卡片背景
      doc.setFillColor(255, 255, 255)
      doc.roundedRect(x, y + 12, summaryCardWidth, 10, 2, 2, 'F')

      // 数值
      doc.setFontSize(11)
      setColor(item.color)
      doc.setFont('helvetica', 'bold')
      doc.text(item.value, x + summaryCardWidth / 2, y + 18, { align: 'center' })

      // 标签
      doc.setFontSize(6)
      setColor(colors.textSecondary)
      doc.setFont('helvetica', 'normal')
      doc.text(item.label, x + summaryCardWidth / 2, y + 22, { align: 'center' })
    })

    y += 30

    // === 页脚 ===
    // 检查是否需要换页
    if (y > pageHeight - 20) {
      doc.addPage()
      y = margin
    }

    // 分隔线
    setDrawColor(colors.border)
    doc.setLineWidth(0.3)
    doc.line(margin, y, pageWidth - margin, y)

    y += 5
    doc.setFontSize(8)
    setColor(colors.textLight)
    doc.setFont('helvetica', 'normal')
    doc.text('Generated by PVE Cluster Scan Platform', pageWidth / 2, y, { align: 'center' })
    doc.text(exportTime, pageWidth / 2, y + 4, { align: 'center' })

    // 生成文件名并下载
    const clusterNameForFile = clusterStore.currentCluster?.name || 'all'
    const timestamp = `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}${String(now.getHours()).padStart(2, '0')}${String(now.getMinutes()).padStart(2, '0')}${String(now.getSeconds()).padStart(2, '0')}`
    doc.save(`${clusterNameForFile}-health-report-${timestamp}.pdf`)

    ElMessage.success(t('healthReport.exportSuccess'))
  } catch (err) {
    console.error('Export failed:', err)
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
