<template>
  <div class="clusters-page">
    <div class="page-header">
      <h2 class="page-title">集群管理</h2>
      <el-button type="primary" @click="showCreate = true">新建集群</el-button>
    </div>

    <el-card shadow="hover">
      <el-empty description="暂无集群，点击上方按钮创建" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const showCreate = ref(false)
</script>

<style scoped>
.clusters-page {
  max-width: 1200px;
}
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}
.page-title {
  font-size: 22px;
  font-weight: 600;
  color: #303133;
  margin: 0;
}
</style>
