<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ t('smartAnalysis.drScore.title') }}</h2>
        <p class="page-desc">{{ t('smartAnalysis.drScore.subtitle') }}</p>
      </div>
      <div class="header-actions">
        <el-button @click="loadData" :icon="Refresh" circle />
        <el-button @click="exportPDF" :icon="Download" :loading="exporting">
          {{ t('healthReport.exportPDF') }}
        </el-button>
      </div>
    </div>

    <div v-loading="loading">
      <!-- 顶部：总分 + 摘要统计 -->
      <div class="top-section" v-if="data">
        <div class="overall-card">
          <div class="score-ring-wrapper">
            <el-progress
              type="dashboard"
              :percentage="data.cluster_score"
              :color="scoreColor(data.cluster_score)"
              :width="160"
              :stroke-width="14"
            >
              <template #default="{ percentage }">
                <div class="score-inner">
                  <span class="score-number">{{ percentage }}</span>
                  <span class="score-label">{{ t('smartAnalysis.drScore.clusterScore') }}</span>
                </div>
              </template>
            </el-progress>
          </div>
          <div class="grade-badge" :style="{ background: gradeGradient(data.cluster_grade) }">
            {{ gradeLabel(data.cluster_grade) }}
          </div>
        </div>

        <div class="summary-cards">
          <div
            class="summary-card"
            :class="{ active: filter === 'all' && activeSummary === 'excellent' }"
            @click="toggleSummary('excellent')"
          >
            <div class="summary-ring">
              <svg viewBox="0 0 36 36">
                <path class="ring-bg" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                <path class="ring-fill" :style="{ stroke: '#67c23a', strokeDasharray: `${pctExcellent}, 100` }"
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
              </svg>
              <span class="ring-num" style="color: #67c23a">{{ data.summary.excellent }}</span>
            </div>
            <div class="summary-meta">
              <span class="summary-label">{{ t('smartAnalysis.drScore.excellent') }}</span>
              <span class="summary-pct" style="color: #67c23a">{{ pctExcellent }}%</span>
            </div>
            <div class="summary-bar" style="background: #67c23a"></div>
          </div>

          <div
            class="summary-card"
            :class="{ active: filter === 'all' && activeSummary === 'good' }"
            @click="toggleSummary('good')"
          >
            <div class="summary-ring">
              <svg viewBox="0 0 36 36">
                <path class="ring-bg" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                <path class="ring-fill" :style="{ stroke: '#409eff', strokeDasharray: `${pctGood}, 100` }"
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
              </svg>
              <span class="ring-num" style="color: #409eff">{{ data.summary.good }}</span>
            </div>
            <div class="summary-meta">
              <span class="summary-label">{{ t('smartAnalysis.drScore.good') }}</span>
              <span class="summary-pct" style="color: #409eff">{{ pctGood }}%</span>
            </div>
            <div class="summary-bar" style="background: #409eff"></div>
          </div>

          <div
            class="summary-card"
            :class="{ active: filter === 'fair' }"
            @click="filter = 'fair'"
          >
            <div class="summary-ring">
              <svg viewBox="0 0 36 36">
                <path class="ring-bg" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                <path class="ring-fill" :style="{ stroke: '#e6a23c', strokeDasharray: `${pctFair}, 100` }"
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
              </svg>
              <span class="ring-num" style="color: #e6a23c">{{ data.summary.fair }}</span>
            </div>
            <div class="summary-meta">
              <span class="summary-label">{{ t('smartAnalysis.drScore.fair') }}</span>
              <span class="summary-pct" style="color: #e6a23c">{{ pctFair }}%</span>
            </div>
            <div class="summary-bar" style="background: #e6a23c"></div>
          </div>

          <div
            class="summary-card danger-card"
            :class="{ active: filter === 'danger' }"
            @click="filter = 'danger'"
          >
            <div class="summary-ring">
              <svg viewBox="0 0 36 36">
                <path class="ring-bg" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                <path class="ring-fill" :style="{ stroke: '#f56c6c', strokeDasharray: `${pctDanger}, 100` }"
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
              </svg>
              <span class="ring-num" style="color: #f56c6c">{{ data.summary.danger }}</span>
            </div>
            <div class="summary-meta">
              <span class="summary-label">{{ t('smartAnalysis.drScore.danger') }}</span>
              <span class="summary-pct" style="color: #f56c6c">{{ pctDanger }}%</span>
            </div>
            <div class="summary-bar" style="background: #f56c6c"></div>
          </div>
        </div>
      </div>

      <!-- 评分维度分布 -->
      <div class="breakdown-section" v-if="data && data.resources.length > 0">
        <h3 class="section-title">{{ t('smartAnalysis.drScore.scoreBreakdown') }}</h3>
        <div class="breakdown-cards">
          <div class="bd-card" v-for="dim in breakdownDims" :key="dim.key">
            <div class="bd-header">
              <span class="bd-icon" :style="{ background: dim.gradient }">
                <el-icon><component :is="dim.icon" /></el-icon>
              </span>
              <div class="bd-info">
                <span class="bd-label">{{ dim.label }}</span>
                <span class="bd-weight">{{ dim.weight }}{{ t('smartAnalysis.drScore.scoreWeight') }}</span>
              </div>
            </div>
            <div class="bd-score-row">
              <span class="bd-avg" :style="{ color: scoreColor(dim.avg) }">{{ dim.avg.toFixed(0) }}</span>
              <span class="bd-max">/ {{ dim.max }}</span>
            </div>
            <el-progress
              :percentage="(dim.avg / dim.max) * 100"
              :color="scoreColor(dim.avg)"
              :stroke-width="6"
              :show-text="false"
            />
          </div>
        </div>
      </div>

      <!-- 资源排行表格 -->
      <div class="ranking-section" v-if="data">
        <div class="ranking-header">
          <h3 class="section-title">{{ t('smartAnalysis.drScore.resourceRanking') }}</h3>
          <el-radio-group v-model="filter" size="small">
            <el-radio-button value="all">{{ t('smartAnalysis.drScore.filterAll') }}</el-radio-button>
            <el-radio-button value="fair">{{ t('smartAnalysis.drScore.filterFair') }}</el-radio-button>
            <el-radio-button value="danger">{{ t('smartAnalysis.drScore.filterDanger') }}</el-radio-button>
          </el-radio-group>
        </div>
        <el-table
          v-if="filteredResources.length > 0"
          :data="filteredResources"
          stripe
          :max-height="500"
          :default-sort="{ prop: 'score', order: 'ascending' }"
        >
          <el-table-column :label="t('smartAnalysis.drScore.rank')" width="60" type="index" :index="rankIndex" />
          <el-table-column :label="t('smartAnalysis.drScore.type')" width="80">
            <template #default="{ row }">
              <el-tag :type="row.type === 'vm' ? 'success' : 'primary'" size="small">
                {{ row.type === 'vm' ? t('smartAnalysis.drScore.vm') : t('smartAnalysis.drScore.lxc') }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="vmid" label="ID" width="70" />
          <el-table-column prop="name" :label="t('smartAnalysis.drScore.resource')" min-width="140" />
          <el-table-column prop="node" :label="t('smartAnalysis.drScore.node')" width="100" />
          <el-table-column :label="t('smartAnalysis.drScore.status')" width="80">
            <template #default="{ row }">
              <el-tag :type="row.status === 'running' ? 'success' : 'info'" size="small">
                {{ row.status === 'running' ? t('smartAnalysis.drScore.running') : t('smartAnalysis.drScore.stopped') }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column :label="t('smartAnalysis.drScore.ha')" width="70" align="center">
            <template #default="{ row }">
              <span :class="row.breakdown.ha > 0 ? 'check' : 'cross'">
                {{ row.breakdown.ha > 0 ? row.breakdown.ha : '—' }}
              </span>
            </template>
          </el-table-column>
          <el-table-column :label="t('smartAnalysis.drScore.snapshot')" width="70" align="center">
            <template #default="{ row }">
              <span :class="row.breakdown.snapshot > 0 ? 'check' : 'cross'">
                {{ row.breakdown.snapshot > 0 ? row.breakdown.snapshot : '—' }}
              </span>
            </template>
          </el-table-column>
          <el-table-column :label="t('smartAnalysis.drScore.backup')" width="70" align="center">
            <template #default="{ row }">
              <span :class="row.breakdown.backup > 0 ? 'check' : 'cross'">
                {{ row.breakdown.backup > 0 ? row.breakdown.backup : '—' }}
              </span>
            </template>
          </el-table-column>
          <el-table-column :label="t('smartAnalysis.drScore.agent')" width="80" align="center">
            <template #default="{ row }">
              <span :class="row.breakdown.agent > 0 ? 'check' : 'cross'">
                {{ row.breakdown.agent > 0 ? row.breakdown.agent : (row.type === 'lxc' ? 'N/A' : '—') }}
              </span>
            </template>
          </el-table-column>
          <el-table-column :label="t('smartAnalysis.drScore.network')" width="80" align="center">
            <template #default="{ row }">
              <span :class="row.breakdown.network > 0 ? 'check' : 'cross'">
                {{ row.breakdown.network > 0 ? row.breakdown.network : '—' }}
              </span>
            </template>
          </el-table-column>
          <el-table-column :label="t('smartAnalysis.drScore.missing')" min-width="160">
            <template #default="{ row }">
              <template v-if="row.missing.length > 0">
                <el-tag v-for="m in row.missing" :key="m" type="danger" size="small" class="missing-tag">{{ m }}</el-tag>
              </template>
              <span v-else class="check">{{ t('smartAnalysis.drScore.noMissing') }}</span>
            </template>
          </el-table-column>
          <el-table-column :label="t('smartAnalysis.drScore.clusterScore')" width="100" sortable sort-by="score">
            <template #default="{ row }">
              <span class="resource-score" :style="{ color: scoreColor(row.score) }">{{ row.score }}</span>
            </template>
          </el-table-column>
          <el-table-column :label="t('smartAnalysis.drScore.grade')" width="80">
            <template #default="{ row }">
              <span class="grade-dot" :style="{ background: gradeColor(row.grade) }"></span>
              {{ gradeLabel(row.grade) }}
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-else :description="t('smartAnalysis.drScore.noResources')" />
      </div>

      <!-- 改进建议 -->
      <div class="recommendations-section" v-if="data && data.recommendations.length > 0">
        <h3 class="section-title">
          {{ t('smartAnalysis.drScore.recommendations') }}
          <el-tag type="warning" size="small" style="margin-left: 8px">{{ data.recommendations.length }}</el-tag>
        </h3>
        <div class="recommendation-list">
          <div
            class="recommendation-item"
            v-for="(rec, idx) in data.recommendations"
            :key="idx"
            :style="{ borderLeftColor: recColors[idx % recColors.length] }"
          >
            <div class="rec-number" :style="{ background: recColors[idx % recColors.length] }">{{ idx + 1 }}</div>
            <div class="rec-body">
              <div class="rec-text">{{ rec }}</div>
              <div class="rec-priority">
                <el-icon :style="{ color: recColors[idx % recColors.length] }"><Warning /></el-icon>
                <span :style="{ color: recColors[idx % recColors.length] }">{{ recPriority(idx) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 无数据 -->
      <el-empty v-if="!loading && !data" :description="t('smartAnalysis.drScore.noResources')" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { Refresh, Download, Warning, Connection, Camera, FolderOpened, Monitor, Share } from '@element-plus/icons-vue'
import { useThemeStore } from '@/stores/theme'
import { useClusterStore } from '@/stores/cluster'
import { getDRScore, type DRScoreData, type DRScoreResource } from '@/api/dashboard'

const { t } = useI18n()
const themeStore = useThemeStore()
const clusterStore = useClusterStore()
const loading = ref(false)
const exporting = ref(false)
const data = ref<DRScoreData | null>(null)
const filter = ref<'all' | 'fair' | 'danger'>('all')
const activeSummary = ref<string | null>(null)
const recColors = ['#f56c6c', '#e6a23c', '#409eff', '#8b5cf6', '#67c23a']

async function loadData() {
  loading.value = true
  try {
    const clusterId = clusterStore.currentClusterId || undefined
    data.value = await getDRScore(clusterId)
  } catch {
    data.value = null
  } finally {
    loading.value = false
  }
}

watch(() => clusterStore.currentClusterId, loadData)
onMounted(loadData)

function toggleSummary(grade: string) {
  if (filter.value === 'all' && activeSummary.value === grade) {
    activeSummary.value = null
  } else {
    filter.value = 'all'
    activeSummary.value = grade
  }
}

// ── 百分比 ──
const total = computed(() => data.value?.summary.total_resources || 1)
const pctExcellent = computed(() => data.value ? Math.round(data.value.summary.excellent / total.value * 100) : 0)
const pctGood = computed(() => data.value ? Math.round(data.value.summary.good / total.value * 100) : 0)
const pctFair = computed(() => data.value ? Math.round(data.value.summary.fair / total.value * 100) : 0)
const pctDanger = computed(() => data.value ? Math.round(data.value.summary.danger / total.value * 100) : 0)

// ── 筛选后的资源 ──
const filteredResources = computed(() => {
  if (!data.value) return []
  let res = data.value.resources
  if (filter.value === 'fair') res = res.filter(r => r.grade === 'fair' || r.grade === 'danger')
  else if (filter.value === 'danger') res = res.filter(r => r.grade === 'danger')
  if (filter.value === 'all' && activeSummary.value) {
    res = res.filter(r => r.grade === activeSummary.value)
  }
  return res
})

function rankIndex(index: number) {
  return index + 1
}

function recPriority(idx: number): string {
  if (idx === 0) return '高优先级'
  if (idx === 1) return '中优先级'
  return '建议改进'
}

// ── 维度统计 ──
const breakdownDims = computed(() => {
  if (!data.value || data.value.resources.length === 0) return []
  const res = data.value.resources
  const n = res.length
  const dims = [
    { key: 'ha', label: t('smartAnalysis.drScore.ha'), weight: 30, max: 30, icon: Connection, gradient: 'linear-gradient(135deg, #409eff, #79bbff)' },
    { key: 'snapshot', label: t('smartAnalysis.drScore.snapshot'), weight: 20, max: 20, icon: Camera, gradient: 'linear-gradient(135deg, #8b5cf6, #a78bfa)' },
    { key: 'backup', label: t('smartAnalysis.drScore.backup'), weight: 20, max: 20, icon: FolderOpened, gradient: 'linear-gradient(135deg, #67c23a, #95d475)' },
    { key: 'agent', label: t('smartAnalysis.drScore.agent'), weight: 15, max: 15, icon: Monitor, gradient: 'linear-gradient(135deg, #e6a23c, #f0c78a)' },
    { key: 'network', label: t('smartAnalysis.drScore.network'), weight: 15, max: 15, icon: Share, gradient: 'linear-gradient(135deg, #909399, #b4b8bf)' },
  ]
  return dims.map(d => {
    const sum = res.reduce((acc, r) => acc + (r.breakdown as any)[d.key], 0)
    return { ...d, avg: sum / n }
  })
})

// ── 颜色与等级 ──
function scoreColor(score: number): string {
  if (score >= 80) return '#67c23a'
  if (score >= 60) return '#409eff'
  if (score >= 40) return '#e6a23c'
  return '#f56c6c'
}

function gradeColor(grade: string): string {
  if (grade === 'excellent') return '#67c23a'
  if (grade === 'good') return '#409eff'
  if (grade === 'fair') return '#e6a23c'
  return '#f56c6c'
}

function gradeGradient(grade: string): string {
  if (grade === 'excellent') return 'linear-gradient(135deg, #67c23a, #95d475)'
  if (grade === 'good') return 'linear-gradient(135deg, #409eff, #79bbff)'
  if (grade === 'fair') return 'linear-gradient(135deg, #e6a23c, #f0c78a)'
  return 'linear-gradient(135deg, #f56c6c, #fab6b6)'
}

function gradeLabel(grade: string): string {
  const map: Record<string, string> = {
    excellent: t('smartAnalysis.drScore.gradeExcellent'),
    good: t('smartAnalysis.drScore.gradeGood'),
    fair: t('smartAnalysis.drScore.gradeFair'),
    danger: t('smartAnalysis.drScore.gradeDanger'),
  }
  return map[grade] || grade
}

function fmtDT(iso: string | null | undefined): string {
  if (!iso) return 'N/A'
  const d = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

// ── PDF 导出 (jsPDF — helvetica 字体，英文标签) ──
const EN_GRADE: Record<string, string> = { excellent: 'Excellent', good: 'Good', fair: 'Fair', danger: 'Danger' }

async function exportPDF() {
  if (!data.value) return
  exporting.value = true
  try {
    const { jsPDF } = await import('jspdf')
    const d = data.value

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
      const dt = new Date(isoStr)
      return `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, '0')}-${String(dt.getDate()).padStart(2, '0')} ${String(dt.getHours()).padStart(2, '0')}:${String(dt.getMinutes()).padStart(2, '0')}:${String(dt.getSeconds()).padStart(2, '0')}`
    }

    // 分数颜色函数
    function scoreColorHex(score: number): string {
      if (score >= 80) return colors.success
      if (score >= 60) return colors.primary
      if (score >= 40) return colors.warning
      return colors.danger
    }

    const now = new Date()
    const pcsVersion = `v${d.platform_version || 'N/A'}`
    const agentVersion = `v${d.agent_version || 'N/A'}`
    const periodStart = d.data_period?.earliest ? formatDateTime(d.data_period.earliest) : 'N/A'
    const periodEnd = d.data_period?.latest ? formatDateTime(d.data_period.latest) : 'N/A'
    const exportTime = formatDateTime(now.toISOString())
    const clusterName = clusterStore.currentCluster?.name || 'All Clusters'

    let y = margin

    // === 报告头部 ===
    // 标题
    doc.setFontSize(24)
    setColor(colors.text)
    doc.setFont('helvetica', 'bold')
    doc.text('Disaster Recovery Readiness Report', pageWidth / 2, y + 8, { align: 'center' })

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
    const sc = d.cluster_score
    const sg = EN_GRADE[d.cluster_grade] || d.cluster_grade
    const scoreHex = scoreColorHex(sc)

    // 评分卡片背景
    setFillColor(colors.background)
    doc.roundedRect(margin, y, contentWidth, 30, 3, 3, 'F')

    // 评分数字
    doc.setFontSize(36)
    setColor(scoreHex)
    doc.setFont('helvetica', 'bold')
    doc.text(String(sc), pageWidth / 2 - 15, y + 18, { align: 'center' })

    // 评分标签
    doc.setFontSize(12)
    setColor(colors.textSecondary)
    doc.setFont('helvetica', 'normal')
    doc.text('Overall Score', pageWidth / 2 - 15, y + 25, { align: 'center' })

    // 等级
    doc.setFontSize(14)
    setColor(scoreHex)
    doc.setFont('helvetica', 'bold')
    doc.text(sg, pageWidth / 2 + 25, y + 18, { align: 'center' })

    y += 38

    // === 维度评分卡片 ===
    const dimensions = [
      { name: 'HA Protection', max: 30, key: 'ha' },
      { name: 'Snapshot', max: 20, key: 'snapshot' },
      { name: 'Backup', max: 20, key: 'backup' },
      { name: 'QEMU Agent', max: 15, key: 'agent' },
      { name: 'Network', max: 15, key: 'network' },
    ]

    const resArr = d.resources
    const resCount = resArr.length || 1
    const cardWidth = (contentWidth - 20) / 5
    const cardHeight = 25

    dimensions.forEach((dim, index) => {
      const x = margin + index * (cardWidth + 5)
      const sum = resArr.reduce((a, r) => a + (r.breakdown as any)[dim.key], 0)
      const avg = sum / resCount
      const dimColor = scoreColorHex(avg)

      // 卡片背景
      setFillColor(colors.background)
      doc.roundedRect(x, y, cardWidth, cardHeight, 2, 2, 'F')

      // 顶部颜色条
      setFillColor(dimColor)
      doc.rect(x, y, cardWidth, 2, 'F')

      // 分数
      doc.setFontSize(20)
      setColor(dimColor)
      doc.setFont('helvetica', 'bold')
      doc.text(avg.toFixed(0), x + cardWidth / 2, y + 12, { align: 'center' })

      // 名称
      doc.setFontSize(8)
      setColor(colors.textSecondary)
      doc.setFont('helvetica', 'normal')
      doc.text(dim.name, x + cardWidth / 2, y + 18, { align: 'center' })

      // 最大分值
      doc.setFontSize(7)
      setColor(colors.textLight)
      doc.text(`Max: ${dim.max}`, x + cardWidth / 2, y + 22, { align: 'center' })
    })

    y += cardHeight + 8

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
      { label: 'Total Resources', value: String(d.summary.total_resources), color: colors.primary },
      { label: 'Excellent', value: String(d.summary.excellent), color: colors.success },
      { label: 'Good', value: String(d.summary.good), color: colors.primary },
      { label: 'Fair / Danger', value: `${d.summary.fair} / ${d.summary.danger}`, color: d.summary.danger > 0 ? colors.danger : colors.warning },
    ]

    const summaryCardWidth = (contentWidth - 20) / 4

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

    // === 改进建议 ===
    const recs = d.recommendations || []
    if (recs.length > 0) {
      // 检查是否需要换页
      if (y > pageHeight - 50) {
        doc.addPage()
        y = margin
      }

      doc.setFontSize(11)
      setColor(colors.text)
      doc.setFont('helvetica', 'bold')
      doc.text('Recommendations', margin, y + 5)

      // 分隔线
      setDrawColor(colors.border)
      doc.setLineWidth(0.2)
      doc.line(margin, y + 7, margin + contentWidth, y + 7)

      y += 10

      const recColorArr = [colors.danger, colors.warning, colors.primary, '#8b5cf6', colors.success, colors.danger, colors.warning, colors.primary]
      const maxRecs = recs.slice(0, 8)
      maxRecs.forEach((rec, idx) => {
        // 检查是否需要换页
        if (y > pageHeight - 20) {
          doc.addPage()
          y = margin
        }

        const recColor = recColorArr[idx % recColorArr.length]
        const cleanRec = rec.replace(/[\u4e00-\u9fff]/g, '').trim() || rec

        // 编号圆形徽章
        setFillColor(recColor)
        doc.circle(margin + 5, y + 2.5, 3, 'F')
        doc.setFontSize(7)
        doc.setTextColor(255, 255, 255)
        doc.setFont('helvetica', 'bold')
        doc.text(String(idx + 1), margin + 5, y + 3.5, { align: 'center' })

        // 建议文本
        setColor(colors.text)
        doc.setFontSize(8)
        doc.setFont('helvetica', 'normal')
        const splitText = doc.splitTextToSize(cleanRec, contentWidth - 16)
        doc.text(splitText, margin + 11, y + 3.5)

        y += Math.max(splitText.length * 4, 6) + 2
      })

      y += 5
    }

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
    doc.save(`${clusterNameForFile}-dr-score-${timestamp}.pdf`)

    ElMessage.success(t('healthReport.exportSuccess'))
  } catch (err) {
    console.error('Export failed:', err)
    ElMessage.error(t('healthReport.exportFailed'))
  } finally {
    exporting.value = false
  }
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

/* 顶部区域 */
.top-section {
  display: flex;
  gap: 24px;
  margin-bottom: 24px;
}
@media (max-width: 900px) {
  .top-section { flex-direction: column; }
}
.overall-card {
  background: var(--bg-card, var(--bg-primary));
  border: 1px solid var(--border-color);
  border-radius: 16px;
  padding: 32px 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 200px;
}
.score-ring-wrapper {
  margin-bottom: 16px;
}
.score-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
}
.score-number {
  font-size: 40px;
  font-weight: 800;
  color: var(--text-heading);
  line-height: 1;
}
.score-label {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 4px;
}
.grade-badge {
  padding: 6px 28px;
  border-radius: 20px;
  color: #fff;
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 2px;
}

/* 摘要卡片 */
.summary-cards {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}
@media (max-width: 600px) {
  .summary-cards { grid-template-columns: repeat(2, 1fr); }
}
.summary-card {
  background: var(--bg-card, var(--bg-primary));
  border: 2px solid transparent;
  border-radius: 14px;
  padding: 18px 16px;
  cursor: pointer;
  transition: all 0.25s ease;
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}
.summary-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.12);
}
.summary-card.active {
  border-color: var(--el-color-primary);
  box-shadow: 0 0 0 3px rgba(64, 158, 255, 0.15);
}
.summary-card.danger-card:hover {
  box-shadow: 0 6px 20px rgba(245, 108, 108, 0.2);
}
.summary-card.danger-card.active {
  border-color: #f56c6c;
  box-shadow: 0 0 0 3px rgba(245, 108, 108, 0.15);
}

/* 环形图 */
.summary-ring {
  position: relative;
  width: 56px;
  height: 56px;
}
.summary-ring svg {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}
.ring-bg {
  fill: none;
  stroke: var(--border-color, #e4e7ed);
  stroke-width: 3;
}
.ring-fill {
  fill: none;
  stroke-width: 3;
  stroke-linecap: round;
  transition: stroke-dasharray 0.6s ease;
}
.ring-num {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 18px;
  font-weight: 800;
  line-height: 1;
}

.summary-meta {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}
.summary-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-heading);
}
.summary-pct {
  font-size: 12px;
  font-weight: 700;
}
.summary-bar {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 3px;
}

/* 维度分布 */
.breakdown-section {
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
.breakdown-cards {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 16px;
}
@media (max-width: 900px) {
  .breakdown-cards { grid-template-columns: repeat(3, 1fr); }
}
@media (max-width: 500px) {
  .breakdown-cards { grid-template-columns: repeat(2, 1fr); }
}
.bd-card {
  background: var(--bg-secondary, var(--bg-primary));
  border-radius: 12px;
  padding: 16px;
}
.bd-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}
.bd-icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 18px;
  flex-shrink: 0;
}
.bd-info {
  display: flex;
  flex-direction: column;
}
.bd-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-heading);
}
.bd-weight {
  font-size: 11px;
  color: var(--text-muted);
}
.bd-score-row {
  display: flex;
  align-items: baseline;
  gap: 4px;
  margin-bottom: 8px;
}
.bd-avg {
  font-size: 28px;
  font-weight: 800;
  line-height: 1;
}
.bd-max {
  font-size: 13px;
  color: var(--text-muted);
}

/* 排行表格 */
.ranking-section {
  background: var(--bg-card, var(--bg-primary));
  border: 1px solid var(--border-color);
  border-radius: 16px;
  padding: 20px 24px;
  margin-bottom: 20px;
}
.ranking-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.ranking-header .section-title {
  margin: 0;
}
.check {
  color: #67c23a;
  font-weight: 600;
}
.cross {
  color: #f56c6c;
}
.resource-score {
  font-size: 18px;
  font-weight: 700;
}
.grade-dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-right: 6px;
  vertical-align: middle;
}
.missing-tag {
  margin: 2px 4px 2px 0;
}

/* 改进建议 */
.recommendations-section {
  background: var(--bg-card, var(--bg-primary));
  border: 1px solid var(--border-color);
  border-radius: 16px;
  padding: 20px 24px;
  margin-bottom: 20px;
}
.recommendation-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.recommendation-item {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 16px 18px;
  background: var(--bg-secondary, var(--bg-primary));
  border-radius: 12px;
  border-left: 4px solid #e6a23c;
  transition: transform 0.2s, box-shadow 0.2s;
}
.recommendation-item:hover {
  transform: translateX(4px);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
}
.rec-number {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 13px;
  font-weight: 700;
  flex-shrink: 0;
  margin-top: 2px;
}
.rec-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.rec-text {
  font-size: 14px;
  color: var(--text-body);
  line-height: 1.7;
}
.rec-priority {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  font-weight: 600;
}
</style>
