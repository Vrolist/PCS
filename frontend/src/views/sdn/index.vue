<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">软件定义网络</h2>
        <p class="page-desc">虚拟网络与子网管理</p>
      </div>
    </div>
    <el-card shadow="hover">
      <el-empty description="SDN 功能开发中">
        <template #image>
          <el-icon :size="64" style="color: var(--text-muted)"><Share /></el-icon>
        </template>
      </el-empty>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { Share } from '@element-plus/icons-vue'
</script>

<style scoped>
.page-container { max-width: 1400px; margin: 0 auto; }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.page-title { font-size: 24px; font-weight: 700; color: var(--text-heading); margin: 0; }
.page-desc { font-size: 14px; color: var(--text-muted); margin: 4px 0 0; }
</style>
