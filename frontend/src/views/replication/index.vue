<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ t('advanced.replication.title') }}</h2>
        <p class="page-desc">{{ t('advanced.replication.subtitle') }}</p>
      </div>
    </div>
    <el-card shadow="hover">
      <el-empty :description="t('advanced.replication.comingSoon')">
        <template #image>
          <el-icon :size="64" style="color: var(--text-muted)"><CopyDocument /></el-icon>
        </template>
      </el-empty>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { CopyDocument } from '@element-plus/icons-vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
</script>

<style scoped>
.page-container { max-width: 1400px; margin: 0 auto; }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.page-title { font-size: 24px; font-weight: 700; color: var(--text-heading); margin: 0; }
.page-desc { font-size: 14px; color: var(--text-muted); margin: 4px 0 0; }
</style>
