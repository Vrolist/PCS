<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ t('nav.complianceReport') }}</h2>
        <p class="page-desc">{{ t('compliance.subtitle') }}</p>
      </div>
      <div class="header-actions">
        <el-button type="primary" :icon="Download" @click="exportPDF" :loading="exporting">
          {{ t('compliance.exportPdf') }}
        </el-button>
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

// ── PDF 导出 ──
async function exportPDF() {
  if (!data.value) return
  exporting.value = true
  try {
    const { jsPDF } = await import('jspdf')
    const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' })
    const d = data.value!
    const lm = 14
    const pw = 182
    let y = 20

    // Header
    doc.setFillColor(64, 158, 255)
    doc.rect(lm, y - 4, pw, 1.5, 'F')
    y += 6
    doc.setFontSize(18)
    doc.setFont('helvetica', 'bold')
    doc.text('Compliance Audit Report', lm, y)
    y += 6
    doc.setFontSize(9)
    doc.setFont('helvetica', 'normal')
    doc.setTextColor(120)
    doc.text(`Generated: ${formatTime(d.generated_at)}`, lm, y)
    doc.setTextColor(0)
    y += 10

    // Score Card
    doc.setDrawColor(220)
    doc.setFillColor(250, 250, 250)
    doc.roundedRect(lm, y, pw, 28, 3, 3, 'FD')
    doc.setFontSize(28)
    doc.setFont('helvetica', 'bold')
    doc.text(String(d.overall_score), lm + 15, y + 18)
    doc.setFontSize(10)
    doc.setFont('helvetica', 'normal')
    doc.text(gradeText(d.overall_grade), lm + 15, y + 24)
    doc.setFontSize(9)
    const stats = [
      `Total Checks: ${d.summary.total_checks}`,
      `Passed: ${d.summary.passed_checks}`,
      `Pass Rate: ${d.summary.pass_rate}%`,
      `Compliant: ${d.summary.compliant}/${d.summary.categories_count}`,
    ]
    stats.forEach((s, i) => doc.text(s, lm + 65, y + 7 + i * 5))
    y += 36

    // Categories Table (manual drawing)
    doc.setFontSize(12)
    doc.setFont('helvetica', 'bold')
    doc.text('Compliance Breakdown', lm, y)
    y += 6

    const colWidths = [40, 20, 20, 30, 30] // Category, Weight, Score, Grade, Passed
    const headers = ['Category', 'Weight', 'Score', 'Grade', 'Passed']
    const colX = colWidths.reduce<number[]>((acc, w) => { acc.push((acc.length ? acc[acc.length - 1] : lm) + w); return acc }, [])

    // Table header
    doc.setFillColor(64, 158, 255)
    doc.rect(lm, y, pw, 7, 'F')
    doc.setTextColor(255)
    doc.setFontSize(8)
    doc.setFont('helvetica', 'bold')
    headers.forEach((h, i) => {
      const x = i === 0 ? lm + 2 : colX[i - 1] + 2
      doc.text(h, x, y + 5)
    })
    doc.setTextColor(0)
    y += 7

    // Table rows
    doc.setFont('helvetica', 'normal')
    d.categories.forEach((cat, ri) => {
      if (y > 275) { doc.addPage(); y = 20 }
      if (ri % 2 === 0) { doc.setFillColor(248, 249, 250); doc.rect(lm, y, pw, 6, 'F') }
      const row = [cat.label, `${cat.weight}%`, String(cat.score), gradeText(cat.grade), `${cat.passed_checks}/${cat.total_checks}`]
      row.forEach((cell, ci) => {
        const x = ci === 0 ? lm + 2 : colX[ci - 1] + 2
        doc.text(cell, x, y + 4.5)
      })
      y += 6
    })
    y += 8

    // Recommendations
    if (d.recommendations.length) {
      if (y > 250) { doc.addPage(); y = 20 }
      doc.setFontSize(12)
      doc.setFont('helvetica', 'bold')
      doc.text('Improvement Recommendations', lm, y)
      y += 6
      doc.setFontSize(8)
      doc.setFont('helvetica', 'normal')
      d.recommendations.forEach((rec, i) => {
        if (y > 275) { doc.addPage(); y = 20 }
        const lines = doc.splitTextToSize(`${i + 1}. ${rec}`, pw)
        doc.text(lines, lm, y)
        y += lines.length * 4 + 2
      })
    }

    // Footer
    const pageCount = doc.getNumberOfPages()
    for (let i = 1; i <= pageCount; i++) {
      doc.setPage(i)
      doc.setFontSize(7)
      doc.setTextColor(160)
      doc.text('PVE Cluster Scan - Compliance Audit Report', lm, 290)
      doc.text(`Page ${i}/${pageCount}`, 196, 290)
      doc.setFillColor(64, 158, 255)
      doc.rect(lm, 292, pw, 1, 'F')
    }

    const clusterName = clusterStore.clusterList.find(c => c.id === clusterStore.currentClusterId)?.name || 'cluster'
    doc.save(`${clusterName}-compliance-${Date.now()}.pdf`)
  } catch (e) {
    console.error('Export failed:', e)
    ElMessage.error(t('compliance.exportError'))
  } finally {
    exporting.value = false
  }
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
