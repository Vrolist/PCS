<template>
  <div class="dashboard">
    <div class="dash-header">
      <div>
        <h2 class="dash-title">{{ t('dashboard.title') }}</h2>
        <p class="dash-subtitle">{{ t('dashboard.welcomeBack') }}，{{ authStore.user?.username || 'buladou' }}</p>
      </div>
      <div class="dash-actions">
      </div>
    </div>

    <div class="dash-section">
      <StatCards />
    </div>

    <div class="dash-row-split">
      <div class="dash-col-alert">
        <AlertList />
      </div>
      <div class="dash-col-trend">
        <TrendChart />
      </div>
    </div>

    <div class="dash-section">
      <NodeTable />
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import StatCards from './StatCards.vue'
import TrendChart from './TrendChart.vue'
import NodeTable from './NodeTable.vue'
import AlertList from './AlertList.vue'

const { t } = useI18n()
const authStore = useAuthStore()
</script>

<style scoped>
.dashboard {
  max-width: 1400px;
  margin: 0 auto;
}
.dash-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 28px;
}
.dash-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-heading);
  margin: 0;
}
.dash-subtitle {
  font-size: 14px;
  color: var(--text-muted);
  margin: 4px 0 0;
}
.dash-actions {
  display: flex;
  gap: 12px;
}
.dash-section {
  margin-bottom: 28px;
}
.dash-row-split {
  display: grid;
  grid-template-columns: 380px 1fr;
  gap: 28px;
  align-items: start;
}
.dash-col-trend {
  min-width: 0;
}
.dash-col-table {
  min-width: 0;
  overflow-x: auto;
}
@media (max-width: 1200px) {
  .dash-row-split {
    grid-template-columns: 1fr;
  }
}
</style>
