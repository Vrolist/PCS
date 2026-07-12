<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ t('smartAnalysis.changeTracking.title') }}</h2>
        <p class="page-desc">{{ t('smartAnalysis.changeTracking.subtitle') }}</p>
      </div>
      <div class="header-actions">
        <el-select v-model="days" style="width: 120px" @change="fetchChanges">
          <el-option :value="1" label="1 天" />
          <el-option :value="3" label="3 天" />
          <el-option :value="7" label="7 天" />
          <el-option :value="14" label="14 天" />
          <el-option :value="30" label="30 天" />
        </el-select>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stat-cards" v-if="changes.length > 0">
      <div class="stat-card">
        <div class="stat-icon" style="background: linear-gradient(135deg, #409eff, #79bbff)">
          <el-icon size="20"><component :is="'Switch'" /></el-icon>
        </div>
        <div class="stat-info">
          <span class="stat-value">{{ changes.length }}</span>
          <span class="stat-label">变更总数</span>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: linear-gradient(135deg, #67c23a, #95d475)">
          <el-icon size="20"><component :is="'InfoFilled'" /></el-icon>
        </div>
        <div class="stat-info">
          <span class="stat-value">{{ infoCount }}</span>
          <span class="stat-label">信息</span>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: linear-gradient(135deg, #e6a23c, #f0c78a)">
          <el-icon size="20"><component :is="'Warning'" /></el-icon>
        </div>
        <div class="stat-info">
          <span class="stat-value">{{ warningCount }}</span>
          <span class="stat-label">警告</span>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: linear-gradient(135deg, #f56c6c, #fab6b6)">
          <el-icon size="20"><component :is="'CircleClose'" /></el-icon>
        </div>
        <div class="stat-info">
          <span class="stat-value">{{ criticalCount }}</span>
          <span class="stat-label">严重</span>
        </div>
      </div>
    </div>

    <!-- 变更列表 -->
    <el-card shadow="hover" v-loading="loading">
      <template v-if="changes.length > 0">
        <!-- 筛选 -->
        <div class="filter-bar">
          <el-checkbox-group v-model="typeFilter" @change="applyFilter">
            <el-checkbox-button value="all">全部</el-checkbox-button>
            <el-checkbox-button value="disk">磁盘</el-checkbox-button>
            <el-checkbox-button value="memory">内存</el-checkbox-button>
            <el-checkbox-button value="cpu">CPU</el-checkbox-button>
            <el-checkbox-button value="storage">存储池</el-checkbox-button>
            <el-checkbox-button value="storage_added">存储增加</el-checkbox-button>
            <el-checkbox-button value="storage_removed">存储移除</el-checkbox-button>
            <el-checkbox-button value="network">网络</el-checkbox-button>
            <el-checkbox-button value="node_added">节点增加</el-checkbox-button>
            <el-checkbox-button value="node_removed">节点移除</el-checkbox-button>
            <el-checkbox-button value="vm_count">VM/容器</el-checkbox-button>
          </el-checkbox-group>
        </div>

        <!-- 时间线 -->
        <el-timeline>
          <el-timeline-item
            v-for="item in filteredChanges"
            :key="item.type + item.detected_at + item.node"
            :timestamp="formatTime(item.detected_at)"
            :type="severityType(item.severity)"
            :hollow="false"
            placement="top"
          >
            <div class="change-item">
              <div class="change-header">
                <el-tag :type="severityType(item.severity)" size="small" effect="dark">
                  {{ severityLabel(item.severity) }}
                </el-tag>
                <el-tag :type="changeTagType(item.type)" size="small" effect="plain" class="type-tag">
                  {{ changeTypeLabel(item.type) }}
                </el-tag>
                <span v-if="item.node" class="node-badge">{{ item.node }}</span>
              </div>
              <div class="change-title">{{ item.title }}</div>
              <div class="change-detail">{{ item.detail }}</div>
            </div>
          </el-timeline-item>
        </el-timeline>
      </template>
      <el-empty v-else :description="'暂无变更记录'" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import request from '@/api/request'
import { useClusterStore } from '@/stores/cluster'

const { t } = useI18n()
const clusterStore = useClusterStore()

interface ChangeItem {
  type: string
  severity: 'info' | 'warning' | 'critical'
  node: string
  title: string
  detail: string
  old_value: string | number
  new_value: string | number
  unit: string
  detected_at: string
}

const loading = ref(false)
const days = ref(7)
const changes = ref<ChangeItem[]>([])
const typeFilter = ref<string[]>(['all'])

const infoCount = computed(() => changes.value.filter(c => c.severity === 'info').length)
const warningCount = computed(() => changes.value.filter(c => c.severity === 'warning').length)
const criticalCount = computed(() => changes.value.filter(c => c.severity === 'critical').length)

const filteredChanges = computed(() => {
  if (typeFilter.value.includes('all')) return changes.value
  return changes.value.filter(c => typeFilter.value.includes(c.type))
})

function applyFilter() {
  // v-model 自动更新
}

function severityType(severity: string) {
  const map: Record<string, string> = { info: 'primary', warning: 'warning', critical: 'danger' }
  return map[severity] || 'info'
}

function severityLabel(severity: string) {
  const map: Record<string, string> = { info: '信息', warning: '警告', critical: '严重' }
  return map[severity] || severity
}

function changeTagType(type: string) {
  const map: Record<string, string> = {
    disk: 'success', memory: 'primary', cpu: 'warning',
    storage: 'success', storage_added: 'success', storage_removed: 'danger',
    network: 'info',
    node_added: 'success', node_removed: 'danger',
    vm_count: 'primary', container_count: 'primary',
  }
  return map[type] || ''
}

function changeTypeLabel(type: string) {
  const map: Record<string, string> = {
    disk: '磁盘', memory: '内存', cpu: 'CPU',
    storage: '存储池', storage_added: '存储增加', storage_removed: '存储移除',
    network: '网络',
    node_added: '节点增加', node_removed: '节点移除',
    vm_count: '虚拟机', container_count: '容器',
  }
  return map[type] || type
}

function formatTime(iso: string) {
  const d = new Date(iso)
  return d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

async function fetchChanges() {
  const cid = clusterStore.currentClusterId
  if (!cid) return
  loading.value = true
  try {
    const res = await request.get('/scanner/changes/', {
      params: { cluster_id: cid, days: days.value },
    })
    changes.value = res.changes || []
  } catch (e) {
    console.error('Failed to fetch changes:', e)
  } finally {
    loading.value = false
  }
}

onMounted(fetchChanges)
watch(() => clusterStore.currentClusterId, fetchChanges)
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
}

/* 统计卡片 */
.stat-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}
.stat-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 18px 20px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
}
.stat-icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
}
.stat-info {
  display: flex;
  flex-direction: column;
}
.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-heading);
  line-height: 1.2;
}
.stat-label {
  font-size: 13px;
  color: var(--text-muted);
  margin-top: 2px;
}

/* 筛选栏 */
.filter-bar {
  margin-bottom: 20px;
}

/* 变更项 */
.change-item {
  padding: 4px 0;
}
.change-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.type-tag {
  margin-left: 4px;
}
.node-badge {
  font-size: 12px;
  color: var(--text-muted);
  background: var(--bg-secondary);
  padding: 1px 8px;
  border-radius: 10px;
}
.change-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-heading);
  margin-bottom: 4px;
}
.change-detail {
  font-size: 13px;
  color: var(--text-muted);
}

/* 时间线样式调整 */
:deep(.el-timeline) {
  padding-left: 2px;
}
:deep(.el-timeline-item__wrapper) {
  padding-left: 20px;
}
</style>
