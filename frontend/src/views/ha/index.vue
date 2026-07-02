<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">HA 高可用</h2>
        <p class="page-desc">高可用资源组管理与状态监控</p>
      </div>
    </div>
    <el-card shadow="hover">
      <el-empty description="HA 高可用功能开发中">
        <template #image>
          <el-icon :size="64" style="color: var(--text-muted)"><Connection /></el-icon>
        </template>
      </el-empty>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { Connection } from '@element-plus/icons-vue'
</script>

<style scoped>
.page-container { max-width: 1400px; margin: 0 auto; }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.page-title { font-size: 24px; font-weight: 700; color: var(--text-heading); margin: 0; }
.page-desc { font-size: 14px; color: var(--text-muted); margin: 4px 0 0; }
</style>
