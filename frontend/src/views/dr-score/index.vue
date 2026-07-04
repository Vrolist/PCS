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

// ── PDF 导出 (jsPDF — helvetica 字体，英文标签) ──
const EN_GRADE: Record<string, string> = { excellent: 'Excellent', good: 'Good', fair: 'Fair', danger: 'Danger' }

async function exportPDF() {
  if (!data.value) return
  exporting.value = true
  try {
    const { jsPDF } = await import('jspdf')
    const d = data.value
    const now = new Date()
    const exportTime = `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-${String(now.getDate()).padStart(2,'0')} ${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}:${String(now.getSeconds()).padStart(2,'0')}`
    const clusterName = clusterStore.currentCluster?.name || 'All Clusters'

    const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' })
    const W = 210, M = 16, CW = W - M * 2
    const sc = d.cluster_score
    const sg = EN_GRADE[d.cluster_grade] || d.cluster_grade
    const sColor: [number, number, number] = sc >= 80 ? [103, 194, 58] : sc >= 60 ? [64, 158, 255] : sc >= 40 ? [230, 162, 60] : [245, 108, 108]
    const C = {
      text: [26, 26, 46] as [number, number, number],
      sub: [85, 85, 119] as [number, number, number],
      light: [136, 136, 153] as [number, number, number],
      bg: [248, 249, 252] as [number, number, number],
      border: [226, 228, 234] as [number, number, number],
      primary: [64, 158, 255] as [number, number, number],
      success: [103, 194, 58] as [number, number, number],
      warning: [230, 162, 60] as [number, number, number],
      danger: [245, 108, 108] as [number, number, number],
    }
    const tc = (c: [number, number, number]) => doc.setTextColor(c[0], c[1], c[2])
    const fc = (c: [number, number, number]) => doc.setFillColor(c[0], c[1], c[2])
    const dc = (c: [number, number, number]) => doc.setDrawColor(c[0], c[1], c[2])
    const scC = (s: number): [number, number, number] => s >= 80 ? C.success : s >= 60 ? C.primary : s >= 40 ? C.warning : C.danger

    let y = 14

    // === Top decorative line ===
    fc(C.primary)
    doc.rect(0, 0, W, 1.5, 'F')

    // === Title ===
    y = 22; doc.setFont('helvetica', 'bold'); doc.setFontSize(22); tc(C.text)
    doc.text('Disaster Recovery Readiness Report', W / 2, y, { align: 'center' })
    y += 7; doc.setFont('helvetica', 'normal'); doc.setFontSize(10); tc(C.sub)
    doc.text(clusterName, W / 2, y, { align: 'center' })
    y += 5; dc(C.primary); doc.setLineWidth(0.6)
    doc.line(M + 40, y, W - M - 40, y)
    y += 7; doc.setFontSize(7); tc(C.light)
    doc.text('PVE Cluster Scan Platform', M, y)
    doc.text(exportTime, W - M, y, { align: 'right' })
    y += 10

    // === Score card ===
    fc(C.bg); doc.roundedRect(M, y, CW, 28, 3, 3, 'F')
    // Big score
    doc.setFont('helvetica', 'bold'); doc.setFontSize(36); tc(sColor)
    doc.text(String(sc), M + 35, y + 18, { align: 'center' })
    doc.setFont('helvetica', 'normal'); doc.setFontSize(7); tc(C.light)
    doc.text('Overall Score', M + 35, y + 25, { align: 'center' })
    // Divider
    dc(C.border); doc.setLineWidth(0.3); doc.line(M + 60, y + 4, M + 60, y + 24)
    // Grade
    doc.setFont('helvetica', 'bold'); doc.setFontSize(14); tc(sColor)
    doc.text(sg, M + 88, y + 14, { align: 'center' })
    doc.setFont('helvetica', 'normal'); doc.setFontSize(7); tc(C.light)
    doc.text('Grade', M + 88, y + 22, { align: 'center' })
    // Divider
    doc.line(M + 115, y + 4, M + 115, y + 24)
    // Distribution
    const distItems = [
      { label: 'Excellent', count: d.summary.excellent, color: C.success },
      { label: 'Good', count: d.summary.good, color: C.primary },
      { label: 'Fair', count: d.summary.fair, color: C.warning },
      { label: 'Danger', count: d.summary.danger, color: C.danger },
    ]
    const distW = (CW - 115) / 4
    distItems.forEach((item, i) => {
      const ix = M + 115 + i * distW + distW / 2
      doc.setFont('helvetica', 'bold'); doc.setFontSize(16); tc(item.color)
      doc.text(String(item.count), ix, y + 14, { align: 'center' })
      doc.setFont('helvetica', 'normal'); doc.setFontSize(6.5); tc(C.light)
      doc.text(item.label, ix, y + 21, { align: 'center' })
    })
    y += 33
    doc.setFontSize(7); tc(C.light)
    doc.text(`Total Resources: ${d.summary.total_resources}`, W / 2, y, { align: 'center' })
    y += 10

    // === Dimension table ===
    doc.setFont('helvetica', 'bold'); doc.setFontSize(11); tc(C.text)
    doc.text('Score Breakdown', M, y)
    y += 2; doc.setLineWidth(0.3); doc.line(M, y, W - M, y)
    y += 5

    const dims = [
      { name: 'HA Protection', weight: 30, max: 30, key: 'ha' },
      { name: 'Snapshot', weight: 20, max: 20, key: 'snapshot' },
      { name: 'Backup', weight: 20, max: 20, key: 'backup' },
      { name: 'QEMU Agent', weight: 15, max: 15, key: 'agent' },
      { name: 'Network Redundancy', weight: 15, max: 15, key: 'network' },
    ]
    fc(C.bg); doc.rect(M, y, CW, 6, 'F')
    doc.setFont('helvetica', 'bold'); doc.setFontSize(7); tc(C.sub)
    doc.text('Dimension', M + 2, y + 4.5)
    doc.text('Weight', M + 55, y + 4.5)
    doc.text('Avg', M + 78, y + 4.5)
    doc.text('Max', M + 100, y + 4.5)
    doc.text('Coverage', M + 120, y + 4.5)
    y += 6

    const resArr = d.resources
    const n = resArr.length || 1
    dims.forEach(dim => {
      const sum = resArr.reduce((a, r) => a + (r.breakdown as any)[dim.key], 0)
      const avg = sum / n
      const pct = Math.round((avg / dim.max) * 100)
      const c = scC(avg / dim.max * 100)
      doc.setFont('helvetica', 'normal'); doc.setFontSize(7.5); tc(C.text)
      doc.text(dim.name, M + 2, y + 4.5)
      tc(C.light); doc.text(`${dim.weight}%`, M + 55, y + 4.5)
      tc(c); doc.setFont('helvetica', 'bold'); doc.text(avg.toFixed(1), M + 78, y + 4.5)
      doc.setFont('helvetica', 'normal'); tc(C.light); doc.text(String(dim.max), M + 100, y + 4.5)
      // Progress bar
      const barX = M + 120, barW = 50
      fc([238, 238, 242]); doc.roundedRect(barX, y + 2, barW, 2.5, 1, 1, 'F')
      fc(c); doc.roundedRect(barX, y + 2, barW * pct / 100, 2.5, 1, 1, 'F')
      tc(c); doc.setFont('helvetica', 'bold'); doc.setFontSize(6.5)
      doc.text(`${pct}%`, barX + barW + 3, y + 4)
      dc(C.border); doc.setLineWidth(0.1); doc.line(M, y + 6, W - M, y + 6)
      y += 6
    })
    y += 8

    // === Resource ranking ===
    doc.setFont('helvetica', 'bold'); doc.setFontSize(11); tc(C.text)
    doc.text('Resource Ranking (Top 20)', M, y)
    y += 2; doc.setLineWidth(0.3); doc.line(M, y, W - M, y)
    y += 5

    const sorted = [...resArr].sort((a, b) => a.score - b.score).slice(0, 20)
    const drawHeader = (yy: number) => {
      fc(C.bg); doc.rect(M, yy, CW, 6, 'F')
      doc.setFont('helvetica', 'bold'); doc.setFontSize(6.5); tc(C.sub)
      doc.text('#', M + 1, yy + 4.5)
      doc.text('Type', M + 8, yy + 4.5)
      doc.text('ID', M + 24, yy + 4.5)
      doc.text('Name', M + 36, yy + 4.5)
      doc.text('Node', M + 76, yy + 4.5)
      doc.text('HA', M + 96, yy + 4.5)
      doc.text('Snap', M + 108, yy + 4.5)
      doc.text('Bkp', M + 120, yy + 4.5)
      doc.text('Agent', M + 132, yy + 4.5)
      doc.text('Net', M + 146, yy + 4.5)
      doc.text('Score', M + 158, yy + 4.5)
      doc.text('Grade', M + 172, yy + 4.5)
      return yy + 6
    }
    y = drawHeader(y)

    sorted.forEach((r, i) => {
      if (y > 275) { doc.addPage(); y = 14; y = drawHeader(y) }
      if (i % 2 === 0) { fc([250, 250, 252]); doc.rect(M, y, CW, 5.5, 'F') }
      doc.setFont('helvetica', 'normal'); doc.setFontSize(6.5)
      tc(C.light); doc.text(String(i + 1), M + 1, y + 4)
      // Type badge
      const tpc = r.type === 'vm' ? C.success : C.primary
      fc(tpc); doc.roundedRect(M + 8, y + 0.5, 14, 4, 1, 1, 'F')
      doc.setTextColor(255, 255, 255); doc.setFontSize(5.5)
      doc.text(r.type.toUpperCase(), M + 15, y + 3.5, { align: 'center' })
      doc.setFontSize(6.5); tc(C.text)
      doc.text(String(r.vmid), M + 24, y + 4)
      doc.text(r.name.substring(0, 15), M + 36, y + 4)
      tc(C.light); doc.text(r.node.substring(0, 10), M + 76, y + 4)
      // Scores
      const cell = (v: number, x: number) => {
        if (v > 0) { tc(C.success); doc.text(String(v), x, y + 4, { align: 'center' }) }
        else { tc(C.danger); doc.text('-', x, y + 4, { align: 'center' }) }
      }
      cell(r.breakdown.ha, M + 100)
      cell(r.breakdown.snapshot, M + 114)
      cell(r.breakdown.backup, M + 126)
      if (r.type === 'lxc') { tc(C.light); doc.text('N/A', M + 138, y + 4, { align: 'center' }) }
      else cell(r.breakdown.agent, M + 138)
      cell(r.breakdown.network, M + 152)
      tc(scC(r.score)); doc.setFont('helvetica', 'bold'); doc.setFontSize(8)
      doc.text(String(r.score), M + 163, y + 4, { align: 'center' })
      doc.setFontSize(6); tc(scC(r.score))
      doc.text(EN_GRADE[r.grade] || r.grade, M + 178, y + 4, { align: 'center' })
      y += 5.5
    })
    y += 8

    // === Footer ===
    y += 6
    if (y > 275) { doc.addPage(); y = 14 }
    dc(C.border); doc.setLineWidth(0.3); doc.line(M, y, W - M, y)
    y += 5
    doc.setFont('helvetica', 'normal'); doc.setFontSize(6.5); tc(C.light)
    doc.text('PVE Cluster Scan Platform - Disaster Recovery Readiness Report', W / 2, y, { align: 'center' })
    doc.text(exportTime, W / 2, y + 4, { align: 'center' })
    // Bottom decorative line
    fc(C.success); doc.rect(0, 295.5, W, 1.5, 'F')

    const ts = `${now.getFullYear()}${String(now.getMonth()+1).padStart(2,'0')}${String(now.getDate()).padStart(2,'0')}${String(now.getHours()).padStart(2,'0')}${String(now.getMinutes()).padStart(2,'0')}`
    const cName = clusterStore.currentCluster?.name || 'all'
    doc.save(`${cName}-dr-score-${ts}.pdf`)
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
