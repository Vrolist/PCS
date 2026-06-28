<template>
  <el-menu
    :default-active="route.path"
    :collapse="appStore.sidebarCollapsed"
    background-color="#304156"
    text-color="#bfcbd9"
    active-text-color="#409eff"
    router
    class="sidebar-menu"
  >
    <div class="sidebar-logo">
      <span v-if="!appStore.sidebarCollapsed" class="logo-text">PVE 集群扫描</span>
      <span v-else class="logo-text logo-mini">P</span>
    </div>

    <el-menu-item index="/dashboard">
      <el-icon><Monitor /></el-icon>
      <span>控制台</span>
    </el-menu-item>

    <el-menu-item index="/clusters">
      <el-icon><Setting /></el-icon>
      <span>集群管理</span>
    </el-menu-item>
  </el-menu>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'
import { useAppStore } from '@/stores/app'

const route = useRoute()
const appStore = useAppStore()
</script>

<style scoped>
.sidebar-menu {
  height: 100vh;
  border-right: none;
  overflow-y: auto;
  overflow-x: hidden;
}
.sidebar-logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}
.logo-text {
  color: #fff;
  font-size: 18px;
  font-weight: 600;
  white-space: nowrap;
}
.logo-mini {
  font-size: 24px;
}
</style>
