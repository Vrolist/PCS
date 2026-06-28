<template>
  <el-container class="layout-container">
    <!-- 侧边栏 -->
    <AppSidebar />
    <!-- 主区域 -->
    <el-container>
      <!-- 顶栏 -->
      <AppHeader />
      <!-- 内容区 -->
      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import AppSidebar from '@/components/AppSidebar.vue'
import AppHeader from '@/components/AppHeader.vue'
</script>

<style scoped>
.layout-container {
  height: 100vh;
}
.main-content {
  background: #f5f7fa;
  padding: 20px;
  overflow-y: auto;
}
</style>
