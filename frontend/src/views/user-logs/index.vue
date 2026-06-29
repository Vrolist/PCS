<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">操作日志</h2>
        <p class="page-desc">查看用户操作记录</p>
      </div>
    </div>
    <el-card shadow="hover">
      <el-empty description="暂无操作日志" />
    </el-card>
  </div>
</template>

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
