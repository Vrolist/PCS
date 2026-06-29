<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">系统设置</h2>
        <p class="page-desc">管理账户和系统配置</p>
      </div>
    </div>
    <el-empty description="系统设置功能开发中" />
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
.page-container {
  max-width: 1400px;
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
</style>
