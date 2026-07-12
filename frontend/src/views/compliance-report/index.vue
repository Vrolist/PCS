<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ t('nav.complianceReport') }}</h2>
        <p class="page-desc">{{ t('compliance.subtitle') }}</p>
      </div>
      <div class="header-actions">
        <!-- <el-button type="primary" :icon="Download" @click="exportPDF" :loading="exporting">
          {{ t('compliance.exportPdf') }}
        </el-button> -->
      </div>
    </div>

    <div v-if="loading" v-loading="true" style="height: 300px"></div>

    <template v-else-if="data">
      <!-- 总分卡片 -->
      <div class="score-overview">
        <div class="score-ring-wrap">
          <svg viewBox="0 0 120 120" class="score-ring">
            <circle cx="60" cy="60" r="52" fill="none" stroke="var(--bg-secondary)" stroke-width="10" />
            <circle cx="60" cy="60" r="52" fill="none" :stroke="gradeColor(data.overall_grade)" stroke-width="10"
              stroke-linecap="round" :stroke-dasharray="dash" :stroke-dashoffset="dashOffset"
              transform="rotate(-90 60 60)" class="ring-progress" />
          </svg>
          <div class="score-center">
            <div class="score-num" :style="{ color: gradeColor(data.overall_grade) }">{{ data.overall_score }}</div>
            <div class="score-label">{{ gradeText(data.overall_grade) }}</div>
          </div>
        </div>
        <div class="summary-cards">
          <div class="summary-item">
            <div class="summary-num">{{ data.summary.total_checks }}</div>
            <div class="summary-desc">{{ t('compliance.totalChecks') }}</div>
          </div>
          <div class="summary-item passed">
            <div class="summary-num">{{ data.summary.passed_checks }}</div>
            <div class="summary-desc">{{ t('compliance.passed') }}</div>
          </div>
          <div class="summary-item rate">
            <div class="summary-num">{{ data.summary.pass_rate }}%</div>
            <div class="summary-desc">{{ t('compliance.passRate') }}</div>
          </div>
          <div class="summary-item compliant">
            <div class="summary-num">{{ data.summary.compliant }}/{{ data.summary.categories_count }}</div>
            <div class="summary-desc">{{ t('compliance.compliantCategories') }}</div>
          </div>
        </div>
      </div>

      <!-- 维度详情 -->
      <h3 class="section-title">{{ t('compliance.categoryBreakdown') }}</h3>
      <div class="category-grid">
        <div v-for="cat in data.categories" :key="cat.name" class="category-card">
          <div class="cat-header">
            <span class="cat-label">{{ cat.label }}</span>
            <span class="cat-weight">{{ cat.weight }}%</span>
          </div>
          <div class="cat-score-row">
            <span class="cat-score" :style="{ color: gradeColor(cat.grade) }">{{ cat.score }}</span>
            <span class="cat-grade-tag" :style="{ background: gradeColor(cat.grade) + '22', color: gradeColor(cat.grade) }">
              {{ gradeText(cat.grade) }}
            </span>
          </div>
          <div class="cat-bar-wrap">
            <div class="cat-bar" :style="{ width: cat.score + '%', background: gradeColor(cat.grade) }"></div>
          </div>
          <div class="cat-checks">
            {{ t('compliance.passedLabel') }}: {{ cat.passed_checks }}/{{ cat.total_checks }}
          </div>
          <div v-if="cat.issues.length" class="cat-issues">
            <div v-for="(issue, i) in cat.issues" :key="i" class="cat-issue">
              <el-icon class="issue-icon"><WarningFilled /></el-icon>
              <span>{{ issue }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 改进建议 -->
      <div v-if="data.recommendations.length" class="recommendations-section">
        <h3 class="section-title">
          {{ t('compliance.recommendations') }}
          <el-tag type="warning" size="small" style="margin-left: 8px">{{ data.recommendations.length }}</el-tag>
        </h3>
        <div class="recommendation-list">
          <div v-for="(rec, i) in data.recommendations" :key="i" class="recommendation-item">
            <div class="rec-index" :style="{ background: recIndexColor(i) }">{{ i + 1 }}</div>
            <div class="rec-text">{{ rec }}</div>
            <el-tag :type="rec.startsWith('[防火墙') ? 'danger' : 'warning'" size="small" effect="light">
              {{ t('compliance.improve') }}
            </el-tag>
          </div>
        </div>
      </div>

      <!-- 页脚 -->
      <div class="report-footer">
        <span>{{ t('compliance.generatedAt') }}: {{ formatTime(data.generated_at) }}</span>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { Download, WarningFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getComplianceReport, type ComplianceData } from '@/api/dashboard'
import { useClusterStore } from '@/stores/cluster'
// jsPDF 在 exportPDF 中动态 import

const { t } = useI18n()
const clusterStore = useClusterStore()

const loading = ref(false)
const exporting = ref(false)
const data = ref<ComplianceData | null>(null)

// ── 环形图 ──
const circumference = 2 * Math.PI * 52
const dash = computed(() => `${circumference}`)
const dashOffset = computed(() => {
  const pct = data.value ? data.value.overall_score / 100 : 0
  return `${circumference * (1 - pct)}`
})

function gradeColor(grade: string) {
  const map: Record<string, string> = {
    compliant: '#67c23a', mostly: '#409eff', partial: '#e6a23c', non_compliant: '#f56c6c',
  }
  return map[grade] || '#909399'
}

function gradeText(grade: string) {
  const map: Record<string, string> = {
    compliant: t('compliance.grades.compliant'),
    mostly: t('compliance.grades.mostly'),
    partial: t('compliance.grades.partial'),
    non_compliant: t('compliance.grades.nonCompliant'),
  }
  return map[grade] || grade
}

function recIndexColor(i: number) {
  const colors = ['#f56c6c', '#e6a23c', '#409eff', '#67c23a', '#909399']
  return colors[i % colors.length]
}

function formatTime(iso: string) {
  if (!iso) return '-'
  return new Date(iso).toLocaleString()
}

function fmtDT(iso: string | null | undefined): string {
  if (!iso) return 'N/A'
  const d = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

// ── 加载数据 ──
async function loadData() {
  loading.value = true
  try {
    const res = await getComplianceReport(clusterStore.currentClusterId || undefined)
    data.value = res
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.error || 'Load failed')
  } finally {
    loading.value = false
  }
}

watch(() => clusterStore.currentClusterId, () => loadData())
onMounted(() => loadData())

// ── PDF 导出 (English only, no recommendations) ──
const gradeLabelEN: Record<string, string> = {
  compliant: 'Compliant', mostly: 'Mostly', partial: 'Partial', non_compliant: 'Non-Compliant',
}
const categoryLabelEN: Record<string, string> = {
  ha_compliance: 'HA Compliance', backup_compliance: 'Backup Compliance',
  firewall_compliance: 'Firewall Compliance', storage_compliance: 'Storage Compliance',
  network_compliance: 'Network Compliance', alert_compliance: 'Alert Compliance',
}

async function exportPDF() {
  if (!data.value) return

  exporting.value = true
  try {
    const { jsPDF } = await import('jspdf')
    const d = data.value!

    // A4 dimensions (mm)
    const pageWidth = 210
    const pageHeight = 297
    const margin = 15
    const contentWidth = pageWidth - margin * 2

    const doc = new jsPDF({
      orientation: 'portrait',
      unit: 'mm',
      format: 'a4'
    })

    // Colors
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

    // Helper functions
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

    const formatDateTime = (isoStr: string) => {
      const date = new Date(isoStr)
      return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}:${String(date.getSeconds()).padStart(2, '0')}`
    }

    function gradeColorEN(grade: string): string {
      if (grade === 'compliant') return '#67c23a'
      if (grade === 'mostly') return '#409eff'
      if (grade === 'partial') return '#e6a23c'
      return '#f56c6c'
    }

    const now = new Date()
    const pcsVersion = `v${d.platform_version || 'N/A'}`
    const agentVersion = `v${d.agent_version || 'N/A'}`
    const periodStart = d.data_period?.earliest ? formatDateTime(d.data_period.earliest) : 'N/A'
    const periodEnd = d.data_period?.latest ? formatDateTime(d.data_period.latest) : 'N/A'
    const exportTime = formatDateTime(now.toISOString())
    const clusterName = clusterStore.clusterList.find(c => c.id === clusterStore.currentClusterId)?.name || 'All Clusters'

    let y = margin

    // === Header ===
    doc.setFontSize(24)
    setColor(colors.text)
    doc.setFont('helvetica', 'bold')
    doc.text('Compliance Audit Report', pageWidth / 2, y + 8, { align: 'center' })

    doc.setFontSize(16)
    setColor(colors.textSecondary)
    doc.setFont('helvetica', 'normal')
    doc.text(clusterName, pageWidth / 2, y + 18, { align: 'center' })

    y += 25
    setDrawColor(colors.primary)
    doc.setLineWidth(0.8)
    doc.line(margin, y, pageWidth - margin, y)

    // Metadata
    y += 8
    doc.setFontSize(9)
    setColor(colors.textSecondary)

    doc.setFont('helvetica', 'bold')
    doc.text('PCS Version:', margin, y)
    doc.setFont('helvetica', 'normal')
    doc.text(pcsVersion, margin + 25, y)

    doc.setFont('helvetica', 'bold')
    doc.text('PCS-Agent Version:', margin, y + 5)
    doc.setFont('helvetica', 'normal')
    doc.text(agentVersion, margin + 35, y + 5)

    doc.setFont('helvetica', 'bold')
    doc.text('Report Period:', pageWidth / 2 + 10, y)
    doc.setFont('helvetica', 'normal')
    doc.text(`${periodStart} ~ ${periodEnd}`, pageWidth / 2 + 35, y)

    doc.setFont('helvetica', 'bold')
    doc.text('Export Time:', pageWidth / 2 + 10, y + 5)
    doc.setFont('helvetica', 'normal')
    doc.text(exportTime, pageWidth / 2 + 32, y + 5)

    y += 15

    // === Overall Score Card ===
    const scoreColor = gradeColorEN(d.overall_grade)
    const scoreGrade = gradeLabelEN[d.overall_grade] || d.overall_grade

    setFillColor(colors.background)
    doc.roundedRect(margin, y, contentWidth, 30, 3, 3, 'F')

    doc.setFontSize(36)
    setColor(scoreColor)
    doc.setFont('helvetica', 'bold')
    doc.text(String(d.overall_score), pageWidth / 2 - 15, y + 18, { align: 'center' })

    doc.setFontSize(12)
    setColor(colors.textSecondary)
    doc.setFont('helvetica', 'normal')
    doc.text('Overall Score', pageWidth / 2 - 15, y + 25, { align: 'center' })

    doc.setFontSize(14)
    setColor(scoreColor)
    doc.setFont('helvetica', 'bold')
    doc.text(scoreGrade, pageWidth / 2 + 25, y + 18, { align: 'center' })

    y += 38

    // === Dimension Score Cards (6 categories) ===
    const cardWidth = (contentWidth - 25) / 6
    const cardHeight = 32

    d.categories.forEach((cat, index) => {
      const x = margin + index * (cardWidth + 5)

      setFillColor(colors.background)
      doc.roundedRect(x, y, cardWidth, cardHeight, 2, 2, 'F')

      const catColor = gradeColorEN(cat.grade)

      // Top color bar
      setFillColor(catColor)
      doc.rect(x, y, cardWidth, 2, 'F')

      // Score number
      doc.setFontSize(20)
      setColor(catColor)
      doc.setFont('helvetica', 'bold')
      doc.text(String(cat.score), x + cardWidth / 2, y + 12, { align: 'center' })

      // Category name
      doc.setFontSize(8)
      setColor(colors.textSecondary)
      doc.setFont('helvetica', 'normal')
      const label = categoryLabelEN[cat.name] || cat.name
      doc.text(label, x + cardWidth / 2, y + 18, { align: 'center' })

      // Weight
      doc.setFontSize(7)
      setColor(colors.textLight)
      doc.text(`Weight: ${cat.weight}%`, x + cardWidth / 2, y + 23, { align: 'center' })

      // Grade tag
      doc.setFontSize(7)
      setColor(catColor)
      doc.setFont('helvetica', 'bold')
      doc.text(gradeLabelEN[cat.grade] || cat.grade, x + cardWidth / 2, y + 29, { align: 'center' })
    })

    y += cardHeight + 8

    // === Summary Section ===
    setFillColor(colors.background)
    doc.roundedRect(margin, y, contentWidth, 25, 3, 3, 'F')

    doc.setFontSize(11)
    setColor(colors.text)
    doc.setFont('helvetica', 'bold')
    doc.text('Report Summary', margin + 5, y + 7)

    setDrawColor(colors.border)
    doc.setLineWidth(0.2)
    doc.line(margin + 5, y + 9, margin + contentWidth - 5, y + 9)

    const summaryItems = [
      { label: 'Total Checks', value: String(d.summary.total_checks), color: colors.primary },
      { label: 'Passed Checks', value: String(d.summary.passed_checks), color: colors.success },
      { label: 'Pass Rate', value: `${d.summary.pass_rate}%`, color: colors.success },
      { label: 'Compliant Categories', value: `${d.summary.compliant}/${d.summary.categories_count}`, color: colors.primary }
    ]

    const summaryCardWidth = (contentWidth - 20) / 4

    summaryItems.forEach((item, index) => {
      const x = margin + 5 + index * (summaryCardWidth + 5)

      doc.setFillColor(255, 255, 255)
      doc.roundedRect(x, y + 12, summaryCardWidth, 10, 2, 2, 'F')

      doc.setFontSize(11)
      setColor(item.color)
      doc.setFont('helvetica', 'bold')
      doc.text(item.value, x + summaryCardWidth / 2, y + 18, { align: 'center' })

      doc.setFontSize(6)
      setColor(colors.textSecondary)
      doc.setFont('helvetica', 'normal')
      doc.text(item.label, x + summaryCardWidth / 2, y + 22, { align: 'center' })
    })

    y += 32

    // === Compliance Table ===
    doc.setFontSize(11)
    setColor(colors.text)
    doc.setFont('helvetica', 'bold')
    doc.text('Compliance Breakdown', margin, y + 5)

    setDrawColor(colors.border)
    doc.setLineWidth(0.2)
    doc.line(margin, y + 7, margin + contentWidth, y + 7)

    y += 10

    // Table header
    const colWidths = [44, 18, 18, 28, 34]
    const headers = ['Category', 'Weight', 'Score', 'Grade', 'Passed']
    const colX = colWidths.reduce<number[]>((acc, w) => { acc.push((acc.length ? acc[acc.length - 1] : margin) + w); return acc }, [])

    setFillColor(colors.primary)
    doc.rect(margin, y, contentWidth, 7, 'F')
    doc.setTextColor(255, 255, 255)
    doc.setFontSize(8)
    doc.setFont('helvetica', 'bold')
    headers.forEach((h, i) => {
      const x = i === 0 ? margin + 2 : colX[i - 1] + 2
      doc.text(h, x, y + 5)
    })
    doc.setTextColor(0, 0, 0)
    y += 7

    // Table rows
    doc.setFont('helvetica', 'normal')
    d.categories.forEach((cat, ri) => {
      if (y > 275) { doc.addPage(); y = margin }

      if (ri % 2 === 0) {
        setFillColor(colors.background)
        doc.rect(margin, y, contentWidth, 6, 'F')
      }

      const label = categoryLabelEN[cat.name] || cat.name
      const row = [label, `${cat.weight}%`, String(cat.score), gradeLabelEN[cat.grade] || cat.grade, `${cat.passed_checks}/${cat.total_checks}`]
      row.forEach((cell, ci) => {
        const x = ci === 0 ? margin + 2 : colX[ci - 1] + 2
        if (ci === 3) {
          setColor(gradeColorEN(cat.grade))
          doc.setFont('helvetica', 'bold')
          doc.text(cell, x, y + 4.5)
          doc.setFont('helvetica', 'normal')
          setColor(colors.text)
        } else {
          doc.text(cell, x, y + 4.5)
        }
      })
      y += 6
    })

    y += 5

    // === Footer ===
    if (y > pageHeight - 20) {
      doc.addPage()
      y = margin
    }

    setDrawColor(colors.border)
    doc.setLineWidth(0.3)
    doc.line(margin, y, pageWidth - margin, y)

    y += 5
    doc.setFontSize(8)
    setColor(colors.textLight)
    doc.setFont('helvetica', 'normal')
    doc.text('Generated by PVE Cluster Scan Platform', pageWidth / 2, y, { align: 'center' })
    doc.text(exportTime, pageWidth / 2, y + 4, { align: 'center' })

    // Save
    const clusterNameForFile = clusterStore.clusterList.find(c => c.id === clusterStore.currentClusterId)?.name || 'all'
    const timestamp = `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}${String(now.getHours()).padStart(2, '0')}${String(now.getMinutes()).padStart(2, '0')}${String(now.getSeconds()).padStart(2, '0')}`
    doc.save(`${clusterNameForFile}-compliance-${timestamp}.pdf`)

    ElMessage.success(t('compliance.exportSuccess'))
  } catch (e) {
    console.error('Export failed:', e)
    ElMessage.error(t('compliance.exportError'))
  } finally {
    exporting.value = false
  }
}

function hexToRgb(hex: string): [number, number, number] {
  const h = hex.replace('#', '')
  return [parseInt(h.substring(0, 2), 16), parseInt(h.substring(2, 4), 16), parseInt(h.substring(4, 6), 16)]
}
</script>

<style scoped>
.page-container { max-width: 1400px; margin: 0 auto; }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 28px; }
.page-title { font-size: 24px; font-weight: 700; color: var(--text-heading); margin: 0; }
.page-desc { font-size: 14px; color: var(--text-muted); margin: 4px 0 0; }
.header-actions { display: flex; gap: 8px; }

/* 总分 */
.score-overview { display: flex; align-items: center; gap: 40px; padding: 28px 32px; background: var(--bg-secondary); border-radius: 12px; margin-bottom: 28px; }
.score-ring-wrap { position: relative; width: 120px; height: 120px; flex-shrink: 0; }
.score-ring { width: 100%; height: 100%; }
.ring-progress { transition: stroke-dashoffset 0.8s ease; }
.score-center { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; }
.score-num { font-size: 32px; font-weight: 800; line-height: 1; }
.score-label { font-size: 12px; color: var(--text-muted); margin-top: 4px; }
.summary-cards { display: flex; gap: 32px; flex: 1; justify-content: space-around; }
.summary-item { text-align: center; }
.summary-num { font-size: 24px; font-weight: 700; color: var(--text-heading); }
.summary-desc { font-size: 12px; color: var(--text-muted); margin-top: 4px; }

/* 维度卡片 */
.section-title { font-size: 16px; font-weight: 600; color: var(--text-heading); margin: 0 0 16px; display: flex; align-items: center; }
.category-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; margin-bottom: 28px; }
.category-card { background: var(--bg-secondary); border-radius: 10px; padding: 20px; transition: transform 0.2s; }
.category-card:hover { transform: translateY(-2px); }
.cat-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.cat-label { font-size: 14px; font-weight: 600; color: var(--text-heading); }
.cat-weight { font-size: 12px; color: var(--text-muted); background: var(--bg-primary); padding: 2px 8px; border-radius: 10px; }
.cat-score-row { display: flex; align-items: baseline; gap: 10px; margin-bottom: 10px; }
.cat-score { font-size: 28px; font-weight: 800; line-height: 1; }
.cat-grade-tag { font-size: 11px; padding: 2px 8px; border-radius: 10px; font-weight: 600; }
.cat-bar-wrap { height: 6px; background: var(--bg-primary); border-radius: 3px; margin-bottom: 8px; overflow: hidden; }
.cat-bar { height: 100%; border-radius: 3px; transition: width 0.6s ease; }
.cat-checks { font-size: 12px; color: var(--text-muted); margin-bottom: 8px; }
.cat-issues { display: flex; flex-direction: column; gap: 4px; }
.cat-issue { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--el-text-color-regular); }
.issue-icon { color: var(--el-color-warning); flex-shrink: 0; }

/* 建议 */
.recommendations-section { margin-bottom: 28px; }
.recommendation-list { display: flex; flex-direction: column; gap: 10px; }
.recommendation-item { display: flex; align-items: center; gap: 12px; padding: 14px 18px; background: var(--bg-secondary); border-radius: 10px; border-left: 3px solid transparent; transition: all 0.2s; }
.recommendation-item:hover { border-left-color: var(--el-color-warning); transform: translateX(4px); }
.rec-index { width: 24px; height: 24px; border-radius: 50%; color: #fff; font-size: 12px; font-weight: 700; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.rec-text { flex: 1; font-size: 13px; line-height: 1.5; color: var(--el-text-color-regular); }

/* 页脚 */
.report-footer { text-align: center; font-size: 12px; color: var(--text-muted); padding: 16px 0; }
</style>
