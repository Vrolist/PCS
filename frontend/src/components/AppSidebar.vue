<template>
  <el-menu
    :default-active="route.path"
    :collapse="appStore.sidebarCollapsed"
    router
    class="sidebar-menu"
    :class="{ 'is-dark': themeStore.theme === 'dark' }"
  >
    <div class="sidebar-logo" :class="{ collapsed: appStore.sidebarCollapsed }" @click="$router.push('/')" style="cursor: pointer">
      <div class="logo-icon-box">
        <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <rect x="2" y="2" width="20" height="20" rx="2" ry="2"></rect>
          <line x1="6" y1="8" x2="18" y2="8"></line>
          <line x1="6" y1="12" x2="18" y2="12"></line>
          <line x1="6" y1="16" x2="18" y2="16"></line>
          <circle cx="6" cy="6" r="1" fill="currentColor" stroke="none"></circle>
        </svg>
      </div>
      <transition name="fade">
        <div v-if="!appStore.sidebarCollapsed" class="logo-text-group">
          <span class="logo-main">PCS</span>
          <span class="logo-sub"><span class="accent">P</span>ve<span class="accent">C</span>luster<span class="accent">S</span>can</span>
        </div>
      </transition>
    </div>

    <!-- 集群 -->
    <div class="menu-section">
      <span v-if="!appStore.sidebarCollapsed" class="menu-label">集群</span>
    </div>

    <el-menu-item index="/dashboard" class="sidebar-item">
      <div class="item-icon-wrap">
        <el-icon><Monitor /></el-icon>
      </div>
      <template #title><span>控制台</span></template>
    </el-menu-item>

    <el-menu-item index="/dashboard/clusters" class="sidebar-item">
      <div class="item-icon-wrap">
        <el-icon><Connection /></el-icon>
      </div>
      <template #title><span>集群管理</span></template>
    </el-menu-item>

    <!-- 集群切换 -->
    <div v-if="!appStore.sidebarCollapsed" class="cluster-switcher">
      <el-select
        :model-value="clusterStore.currentClusterId"
        placeholder="选择集群"
        size="small"
        class="cluster-select"
        @change="clusterStore.setCluster"
      >
        <el-option
          v-for="c in clusterStore.clusterList"
          :key="c.id"
          :label="c.name"
          :value="c.id"
        />
        <template #prefix>
          <el-icon><Connection /></el-icon>
        </template>
      </el-select>
    </div>

    <!-- 折叠态：tooltip 显示当前集群名 -->
    <el-tooltip v-else :content="clusterStore.currentCluster?.name || '选择集群'" placement="right">
      <div class="cluster-switcher-collapsed">
        <el-icon @click="appStore.sidebarCollapsed = false"><Connection /></el-icon>
      </div>
    </el-tooltip>

    <!-- 基本信息 -->
    <div class="menu-section">
      <span v-if="!appStore.sidebarCollapsed" class="menu-label">基本信息</span>
    </div>

    <el-menu-item index="/dashboard/nodes" class="sidebar-item">
      <div class="item-icon-wrap">
        <el-icon><Cpu /></el-icon>
      </div>
      <template #title><span>节点管理</span></template>
    </el-menu-item>

    <el-menu-item index="/dashboard/vms" class="sidebar-item">
      <div class="item-icon-wrap">
        <el-icon><Cpu /></el-icon>
      </div>
      <template #title><span>虚拟机</span></template>
    </el-menu-item>

    <el-menu-item index="/dashboard/containers" class="sidebar-item">
      <div class="item-icon-wrap">
        <el-icon><Box /></el-icon>
      </div>
      <template #title><span>容器</span></template>
    </el-menu-item>

    <el-menu-item index="/dashboard/storage" class="sidebar-item">
      <div class="item-icon-wrap">
        <el-icon><Coin /></el-icon>
      </div>
      <template #title><span>存储管理</span></template>
    </el-menu-item>

    <el-menu-item index="/dashboard/networks" class="sidebar-item">
      <div class="item-icon-wrap">
        <el-icon><Connection /></el-icon>
      </div>
      <template #title><span>网络接口</span></template>
    </el-menu-item>

    <!-- 进阶信息 -->
    <div class="menu-section">
      <span v-if="!appStore.sidebarCollapsed" class="menu-label">进阶信息</span>
    </div>

    <el-menu-item index="/dashboard/network-topology" class="sidebar-item">
      <div class="item-icon-wrap">
        <el-icon><Share /></el-icon>
      </div>
      <template #title><span>网络拓扑</span></template>
    </el-menu-item>

    <el-menu-item index="/dashboard/ceph" class="sidebar-item">
      <div class="item-icon-wrap">
        <el-icon><Box /></el-icon>
      </div>
      <template #title><span>Ceph 存储</span></template>
    </el-menu-item>

    <!-- 运维检测 -->
    <div class="menu-section">
      <span v-if="!appStore.sidebarCollapsed" class="menu-label">运维检测</span>
    </div>

    <el-menu-item index="/dashboard/alerts" class="sidebar-item">
      <div class="item-icon-wrap">
        <el-icon><Bell /></el-icon>
      </div>
      <template #title><span>告警中心</span></template>
    </el-menu-item>

    <el-menu-item index="/dashboard/services" class="sidebar-item">
      <div class="item-icon-wrap">
        <el-icon><Service /></el-icon>
      </div>
      <template #title><span>运维服务</span></template>
    </el-menu-item>

    <!-- 用户信息 -->
    <div class="menu-section">
      <span v-if="!appStore.sidebarCollapsed" class="menu-label">用户信息</span>
    </div>

    <el-menu-item index="/dashboard/settings" class="sidebar-item">
      <div class="item-icon-wrap">
        <el-icon><User /></el-icon>
      </div>
      <template #title><span>用户信息</span></template>
    </el-menu-item>

    <el-menu-item index="/dashboard/user-logs" class="sidebar-item">
      <div class="item-icon-wrap">
        <el-icon><Document /></el-icon>
      </div>
      <template #title><span>操作日志</span></template>
    </el-menu-item>

    <el-menu-item index="/dashboard/user-notifications" class="sidebar-item">
      <div class="item-icon-wrap">
        <el-icon><Bell /></el-icon>
      </div>
      <template #title><span>通知设置</span></template>
    </el-menu-item>
  </el-menu>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { useThemeStore } from '@/stores/theme'
import { useClusterStore } from '@/stores/cluster'
import { Monitor, Connection, Cpu, Box, Bell, Service, User, Document, Coin, Share } from '@element-plus/icons-vue'

const route = useRoute()
const appStore = useAppStore()
const themeStore = useThemeStore()
const clusterStore = useClusterStore()

onMounted(() => {
  if (!clusterStore.clusterList.length) {
    clusterStore.fetchClusters()
  }
})
</script>

<style scoped>
.sidebar-menu {
  height: 100vh;
  border-right: none;
  overflow-y: auto;
  overflow-x: hidden;
  width: 100%;
}
.sidebar-menu::-webkit-scrollbar {
  width: 0;
}
.sidebar-logo {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px 20px 16px;
  margin-bottom: 8px;
  min-height: 68px;
}
.sidebar-logo.collapsed {
  justify-content: center;
  padding: 20px 0 16px;
}
.logo-icon-box {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  background: linear-gradient(135deg, #409eff, #8b5cf6);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.3);
}
.logo-text-group {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  white-space: nowrap;
}
.logo-main {
  font-size: 18px;
  font-weight: 700;
  line-height: 1.2;
}
.logo-sub {
  font-size: 10px;
  letter-spacing: 0.5px;
}
.accent {
  color: #409eff;
  font-weight: 600;
}
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.2s;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}
.menu-section {
  padding: 16px 20px 6px;
}
.menu-label {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 1.5px;
  font-weight: 600;
}
.sidebar-item {
  margin: 2px 12px;
  border-radius: 10px;
  height: 42px;
  line-height: 42px;
  padding-left: 12px !important;
  transition: all 0.2s ease;
}
.sidebar-item .el-icon {
  font-size: 18px;
  margin: 0;
}
.sidebar-item:hover {
  background: rgba(64, 158, 255, 0.1) !important;
}
.sidebar-item.is-active {
  background: linear-gradient(135deg, rgba(64, 158, 255, 0.2), rgba(139, 92, 246, 0.15)) !important;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.15);
}
.sidebar-item.is-active .item-icon-wrap {
  background: linear-gradient(135deg, #409eff, #8b5cf6);
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.4);
  color: #fff;
}
.item-icon-wrap {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 10px;
  flex-shrink: 0;
  transition: all 0.2s ease;
}

/* 集群切换 */
.cluster-switcher {
  padding: 0 16px 8px;
}
.cluster-select {
  width: 100%;
}
.cluster-switcher-collapsed {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 36px;
  margin: 0 6px 4px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}
.cluster-switcher-collapsed:hover {
  background: rgba(64, 158, 255, 0.1);
}
.cluster-switcher-collapsed .el-icon {
  font-size: 18px;
}

/* 压缩模式：图标居中 */
.sidebar-menu.el-menu--collapse .sidebar-item {
  margin: 2px 6px;
  padding: 0 !important;
  display: flex !important;
  align-items: center;
  justify-content: center;
  line-height: normal;
}
.sidebar-menu.el-menu--collapse .sidebar-item :deep(.el-menu-tooltip__trigger) {
  display: flex !important;
  align-items: center;
  justify-content: center;
  padding: 0 !important;
  margin: 0 !important;
  flex: none;
  line-height: normal;
}
.sidebar-menu.el-menu--collapse .sidebar-item .item-icon-wrap {
  margin: 0 !important;
  flex: none;
}

/* ===== 亮色主题（默认） ===== */
.sidebar-menu {
  --el-menu-bg-color: transparent;
  --el-menu-text-color: #4e5159;
  --el-menu-hover-bg-color: rgba(64, 158, 255, 0.08);
  --el-menu-hover-text-color: #409eff;
  --el-menu-active-color: #409eff;
  background: var(--bg-secondary) !important;
}
.sidebar-logo {
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
}
.logo-main {
  color: #1d1e24;
}
.logo-sub {
  color: rgba(0, 0, 0, 0.35);
}
.menu-label {
  color: rgba(0, 0, 0, 0.3);
}
.sidebar-item:hover {
  background: rgba(64, 158, 255, 0.08) !important;
}
.sidebar-item.is-active {
  color: #409eff !important;
}
.sidebar-item.is-active .item-icon-wrap {
  background: linear-gradient(135deg, #409eff, #8b5cf6);
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.4);
  color: #fff;
}
.item-icon-wrap {
  background: rgba(0, 0, 0, 0.05);
  color: #606266;
}

/* ===== 暗色主题 ===== */
.sidebar-menu.is-dark {
  --el-menu-bg-color: transparent;
  --el-menu-text-color: rgba(255, 255, 255, 0.6);
  --el-menu-hover-bg-color: rgba(64, 158, 255, 0.1);
  --el-menu-hover-text-color: rgba(255, 255, 255, 0.85);
  --el-menu-active-color: #fff;
  background: var(--bg-secondary) !important;
}
.sidebar-menu.is-dark .sidebar-logo {
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}
.sidebar-menu.is-dark .logo-main {
  color: #fff;
}
.sidebar-menu.is-dark .logo-sub {
  color: rgba(255, 255, 255, 0.4);
}
.sidebar-menu.is-dark .menu-label {
  color: rgba(255, 255, 255, 0.25);
}
.sidebar-menu.is-dark .sidebar-item:hover {
  background: rgba(64, 158, 255, 0.1) !important;
}
.sidebar-menu.is-dark .sidebar-item.is-active {
  color: #fff !important;
}
.sidebar-menu.is-dark .sidebar-item.is-active .item-icon-wrap {
  background: linear-gradient(135deg, #409eff, #8b5cf6);
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.4);
  color: #fff;
}
.sidebar-menu.is-dark .item-icon-wrap {
  background: rgba(255, 255, 255, 0.06);
  color: rgba(255, 255, 255, 0.6);
}
</style>
