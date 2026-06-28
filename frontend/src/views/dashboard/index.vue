<template>
  <div class="dashboard">
    <h2 class="page-title">首页总览</h2>

    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stat-cards">
      <el-col :span="6" v-for="card in statCards" :key="card.label">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-card-inner">
            <div class="stat-info">
              <p class="stat-value">{{ card.value }}</p>
              <p class="stat-label">{{ card.label }}</p>
            </div>
            <el-icon :size="40" :color="card.color">
              <component :is="card.icon" />
            </el-icon>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 集群状态 -->
    <el-card shadow="hover" class="section-card">
      <template #header>
        <span>集群列表</span>
      </template>
      <el-empty description="暂无集群数据，请先创建一个集群" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
const statCards = [
  { label: '集群总数', value: 0, icon: 'Setting', color: '#409eff' },
  { label: '在线节点', value: 0, icon: 'Monitor', color: '#67c23a' },
  { label: '虚拟机', value: 0, icon: 'Cloudy', color: '#e6a23c' },
  { label: '告警', value: 0, icon: 'WarningFilled', color: '#f56c6c' },
]
</script>

<style scoped>
.dashboard {
  max-width: 1200px;
}
.page-title {
  font-size: 22px;
  font-weight: 600;
  margin-bottom: 24px;
  color: #303133;
}
.stat-cards {
  margin-bottom: 24px;
}
.stat-card-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #303133;
  margin: 0;
}
.stat-label {
  font-size: 14px;
  color: #909399;
  margin: 4px 0 0 0;
}
.section-card {
  margin-bottom: 24px;
}
</style>
