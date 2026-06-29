<template>
  <div class="alert-card">
    <div class="alert-card-header">
      <span class="alert-card-title">最近告警</span>
      <el-badge :value="alerts.length" :max="99" type="danger" />
    </div>
    <div class="alert-list">
      <div
        v-for="(alert, index) in alerts"
        :key="index"
        class="alert-item"
        :class="`alert-${alert.severity}`"
      >
        <div class="alert-dot" />
        <div class="alert-content">
          <span class="alert-title">{{ alert.title }}</span>
          <span class="alert-time">{{ alert.time }}</span>
        </div>
        <el-tag
          :type="tagType(alert.severity)"
          size="small"
          effect="dark"
        >
          {{ tagLabel(alert.severity) }}
        </el-tag>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Alert {
  title: string
  time: string
  severity: 'critical' | 'warning' | 'resolved' | 'info'
}

const alerts: Alert[] = [
  { title: 'pve-2 CPU 使用率超过 80%', time: '5分钟前', severity: 'critical' },
  { title: 'pve-1 磁盘使用率超过 90%', time: '1小时前', severity: 'warning' },
  { title: 'pve-3 内存使用率超过 85%', time: '2小时前', severity: 'warning' },
  { title: 'pve-2 Ceph OSD 恢复正常', time: '3小时前', severity: 'resolved' },
  { title: 'pve-4 系统更新可用', time: '1天前', severity: 'info' },
]

function tagType(severity: Alert['severity']) {
  const map: Record<Alert['severity'], string> = {
    critical: 'danger',
    warning: 'warning',
    resolved: 'success',
    info: 'info',
  }
  return map[severity] as 'danger' | 'warning' | 'success' | 'info'
}

function tagLabel(severity: Alert['severity']) {
  const map: Record<Alert['severity'], string> = {
    critical: '严重',
    warning: '警告',
    resolved: '已恢复',
    info: '信息',
  }
  return map[severity]
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
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-color);
}

.alert-card-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.alert-list {
  display: flex;
  flex-direction: column;
}

.alert-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px;
  border-bottom: 1px solid var(--border-color);
  cursor: pointer;
  transition: background-color 0.2s;
}

.alert-item:last-child {
  border-bottom: none;
}

.alert-item:hover {
  background: rgba(64, 158, 255, 0.05);
}

.dark .alert-item:hover {
  background: rgba(64, 158, 255, 0.08);
}

.alert-critical {
  border-left: 4px solid #f56c6c;
}

.alert-warning {
  border-left: 4px solid #e6a23c;
}

.alert-resolved {
  border-left: 4px solid #67c23a;
}

.alert-info {
  border-left: 4px solid #409eff;
}

.alert-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.alert-critical .alert-dot {
  background-color: #f56c6c;
  box-shadow: 0 0 6px rgba(245, 108, 108, 0.5);
}

.alert-warning .alert-dot {
  background-color: #e6a23c;
  box-shadow: 0 0 6px rgba(230, 162, 60, 0.5);
}

.alert-resolved .alert-dot {
  background-color: #67c23a;
  box-shadow: 0 0 6px rgba(103, 194, 58, 0.5);
}

.alert-info .alert-dot {
  background-color: #409eff;
  box-shadow: 0 0 6px rgba(64, 158, 255, 0.5);
}

.alert-content {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-width: 0;
}

.alert-title {
  font-size: 14px;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.alert-time {
  font-size: 13px;
  color: var(--text-muted);
  white-space: nowrap;
  flex-shrink: 0;
}
</style>
