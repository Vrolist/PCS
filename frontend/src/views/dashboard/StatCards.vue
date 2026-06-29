<template>
  <div class="stat-cards-row">
    <div
      v-for="card in cards"
      :key="card.label"
      class="stat-card"
    >
      <div class="stat-card__icon" :style="{ color: card.color, background: card.bg }">
        <el-icon :size="24">
          <component :is="card.icon" />
        </el-icon>
      </div>
      <div class="stat-card__body">
        <span class="stat-card__value">{{ card.value }}</span>
        <span class="stat-card__label">{{ card.label }}</span>
      </div>
      <div class="stat-card__trend" :class="card.trendUp ? 'trend--up' : 'trend--down'">
        <el-icon :size="12">
          <Top v-if="card.trendUp" />
          <Bottom v-else />
        </el-icon>
        <span>{{ card.trend }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Setting, Monitor, Cloudy, WarningFilled, Top, Bottom } from '@element-plus/icons-vue'

interface StatCard {
  label: string
  value: number
  icon: typeof Setting
  color: string
  bg: string
  trend: string
  trendUp: boolean
}

const cards: StatCard[] = [
  {
    label: '集群总数',
    value: 3,
    icon: Setting,
    color: '#409eff',
    bg: 'rgba(64, 158, 255, 0.10)',
    trend: '+1 本周',
    trendUp: true,
  },
  {
    label: '在线节点',
    value: 12,
    icon: Monitor,
    color: '#67c23a',
    bg: 'rgba(103, 194, 58, 0.10)',
    trend: '+2 本周',
    trendUp: true,
  },
  {
    label: '虚拟机',
    value: 25,
    icon: Cloudy,
    color: '#e6a23c',
    bg: 'rgba(230, 162, 60, 0.10)',
    trend: '+3 本周',
    trendUp: true,
  },
  {
    label: '告警',
    value: 2,
    icon: WarningFilled,
    color: '#f56c6c',
    bg: 'rgba(245, 108, 108, 0.10)',
    trend: '-1 本周',
    trendUp: false,
  },
]
</script>

<style scoped>
.stat-cards-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
}

@media (max-width: 1200px) {
  .stat-cards-row {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .stat-cards-row {
    grid-template-columns: 1fr;
  }
}

.stat-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  position: relative;
  backdrop-filter: blur(12px);
  transition: transform 0.25s ease, box-shadow 0.25s ease;
  cursor: default;
}

.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.25);
}

.stat-card__icon {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-card__body {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-card__value {
  font-size: 32px;
  font-weight: 700;
  line-height: 1;
  color: var(--text-primary);
}

.stat-card__label {
  font-size: 14px;
  color: var(--text-secondary);
}

.stat-card__trend {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  font-weight: 500;
  width: fit-content;
}

.trend--up {
  color: #67c23a;
}

.trend--down {
  color: #f56c6c;
}
</style>
