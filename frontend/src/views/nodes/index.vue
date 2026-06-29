<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">节点管理</h2>
        <p class="page-desc">管理和监控 PVE 集群节点状态</p>
      </div>
    </div>
    <el-empty description="暂无节点数据，请先部署 Agent 采集数据" />
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
