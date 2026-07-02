<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">数据复制</h2>
        <p class="page-desc">跨节点存储复制任务管理</p>
      </div>
    </div>
    <el-card shadow="hover">
      <el-empty description="Replication 功能开发中">
        <template #image>
          <el-icon :size="64" style="color: var(--text-muted)"><CopyDocument /></el-icon>
        </template>
      </el-empty>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { CopyDocument } from '@element-plus/icons-vue'
</script>

<style scoped>
.page-container { max-width: 1400px; margin: 0 auto; }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.page-title { font-size: 24px; font-weight: 700; color: var(--text-heading); margin: 0; }
.page-desc { font-size: 14px; color: var(--text-muted); margin: 4px 0 0; }
</style>
