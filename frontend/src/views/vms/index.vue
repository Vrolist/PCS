<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">虚拟机</h2>
        <p class="page-desc">查看和管理所有 PVE 虚拟机实例</p>
      </div>
    </div>
    <el-card shadow="hover">
      <el-empty description="暂无虚拟机数据，请先部署 Agent 采集数据" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
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
</style>
