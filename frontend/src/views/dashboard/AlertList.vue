<template>
  <div class="alert-card">
    <div class="alert-card-header">
      <span class="alert-card-title">最近告警</span>
      <el-badge v-if="alerts.length > 0" :value="alerts.length" :max="99" type="danger" />
    </div>
    <div class="alert-list">
      <div v-if="loading" class="alert-loading">
        <el-icon class="is-loading" :size="20"><Loading /></el-icon>
      </div>
      <div v-else-if="alerts.length === 0" class="alert-empty">
        <span>暂无告警</span>
      </div>
      <div
        v-for="(alert, index) in alerts"
        :key="index"
        class="alert-item"
        :class="`alert-${alert.severity}`"
      >
        <div class="alert-dot" />
        <div class="alert-content">
          <span class="alert-title">{{ alert.title }}</span>
          <span class="alert-time">{{ formatTime(alert.created_at) }}</span>
        </div>
        <el-tag :type="tagType(alert.severity)" size="small" effect="dark">
          {{ tagLabel(alert.severity) }}
        </el-tag>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Loading } from '@element-plus/icons-vue'
import { getDashboardAlerts } from '@/api/dashboard'
import type { DashboardAlert } from '@/api/dashboard'

const loading = ref(true)
const alerts = ref<DashboardAlert[]>([])

onMounted(async () => {
  try {
    alerts.value = await getDashboardAlerts(10)
  } catch {
    // error handled by interceptor
  } finally {
    loading.value = false
  }
})

function formatTime(iso: string) {
  const d = new Date(iso)
  const now = new Date()
  const diff = (now.getTime() - d.getTime()) / 1000
  if (diff < 60) return '刚刚'
  if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`
  if (diff < 86400) return `${Math.floor(diff / 3600)}小时前`
  return `${Math.floor(diff / 86400)}天前`
}

function tagType(severity: string) {
  const map: Record<string, string> = { critical: 'danger', warning: 'warning', info: 'info' }
  return (map[severity] || 'info') as 'danger' | 'warning' | 'success' | 'info'
}

function tagLabel(severity: string) {
  return { critical: '严重', warning: '警告', info: '信息' }[severity] || severity
}
</script>

<style scoped>
.alert-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  overflow: hidden;
}
.alert-card-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 20px 24px; border-bottom: 1px solid var(--border-color);
}
.alert-card-title { font-size: 16px; font-weight: 600; color: var(--text-primary); }
.alert-list { display: flex; flex-direction: column; height: 270px; overflow-y: auto; }
.alert-loading, .alert-empty {
  display: flex; align-items: center; justify-content: center; height: 100%;
  color: var(--text-secondary); font-size: 14px;
}
.alert-item {
  display: flex; align-items: center; gap: 14px; padding: 16px;
  border-bottom: 1px solid var(--border-color); transition: background-color 0.2s;
}
.alert-item:last-child { border-bottom: none; }
.alert-item:hover { background: rgba(64, 158, 255, 0.05); }
.dark .alert-item:hover { background: rgba(64, 158, 255, 0.08); }
.alert-critical { border-left: 4px solid #f56c6c; }
.alert-warning { border-left: 4px solid #e6a23c; }
.alert-info { border-left: 4px solid #409eff; }
.alert-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.alert-critical .alert-dot { background-color: #f56c6c; box-shadow: 0 0 6px rgba(245, 108, 108, 0.5); }
.alert-warning .alert-dot { background-color: #e6a23c; box-shadow: 0 0 6px rgba(230, 162, 60, 0.5); }
.alert-info .alert-dot { background-color: #409eff; box-shadow: 0 0 6px rgba(64, 158, 255, 0.5); }
.alert-content {
  flex: 1; display: flex; align-items: center; justify-content: space-between;
  gap: 12px; min-width: 0;
}
.alert-title {
  font-size: 14px; color: var(--text-primary);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.alert-time { font-size: 13px; color: var(--text-muted); white-space: nowrap; flex-shrink: 0; }
</style>
