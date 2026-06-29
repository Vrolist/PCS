<template>
  <div class="stat-cards-row">
    <div v-for="card in cards" :key="card.label" class="stat-card">
      <div class="stat-card__icon" :style="{ color: card.color, background: card.bg }">
        <el-icon :size="24"><component :is="card.icon" /></el-icon>
      </div>
      <div class="stat-card__body">
        <span class="stat-card__value">{{ card.value }}</span>
        <span class="stat-card__label">{{ card.label }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Setting, Monitor, Cloudy, WarningFilled } from '@element-plus/icons-vue'
import { getDashboardStats } from '@/api/dashboard'
import type { DashboardStats } from '@/api/dashboard'

const stats = ref<DashboardStats>({
  total_clusters: 0, total_nodes: 0, online_nodes: 0, total_vms: 0, active_alerts: 0,
})

const cards = ref([
  { label: '集群总数', value: 0, icon: Setting, color: '#409eff', bg: 'rgba(64, 158, 255, 0.10)' },
  { label: '在线节点', value: 0, icon: Monitor, color: '#67c23a', bg: 'rgba(103, 194, 58, 0.10)' },
  { label: '虚拟机', value: 0, icon: Cloudy, color: '#e6a23c', bg: 'rgba(230, 162, 60, 0.10)' },
  { label: '告警', value: 0, icon: WarningFilled, color: '#f56c6c', bg: 'rgba(245, 108, 108, 0.10)' },
])

onMounted(async () => {
  try {
    const data = await getDashboardStats()
    stats.value = data
    cards.value[0].value = data.total_clusters
    cards.value[1].value = data.online_nodes
    cards.value[2].value = data.total_vms
    cards.value[3].value = data.active_alerts
  } catch {
    // error handled by interceptor
  }
})
</script>

<style scoped>
.stat-cards-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}
@media (max-width: 1200px) { .stat-cards-row { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 640px) { .stat-cards-row { grid-template-columns: 1fr; } }

.stat-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 14px;
  padding: 16px 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  transition: transform 0.25s ease, box-shadow 0.25s ease;
  cursor: default;
}
.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
}
.stat-card__icon {
  width: 40px; height: 40px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.stat-card__body { display: flex; flex-direction: column; gap: 2px; flex: 1; }
.stat-card__value { font-size: 24px; font-weight: 700; line-height: 1.2; color: var(--text-primary); }
.stat-card__label { font-size: 14px; color: var(--text-secondary); }
</style>
