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

    <div class="menu-section">
      <span v-if="!appStore.sidebarCollapsed" class="menu-label">集群</span>
    </div>

    <el-menu-item index="/dashboard" class="sidebar-item">
      <div class="item-icon-wrap">
        <el-icon><Monitor /></el-icon>
      </div>
      <template #title><span>控制台</span></template>
    </el-menu-item>

    <el-menu-item index="/clusters" class="sidebar-item">
      <div class="item-icon-wrap">
        <el-icon><Connection /></el-icon>
      </div>
      <template #title><span>集群管理</span></template>
    </el-menu-item>

    <el-menu-item index="/nodes" class="sidebar-item">
      <div class="item-icon-wrap">
        <el-icon><Cpu /></el-icon>
      </div>
      <template #title><span>节点管理</span></template>
    </el-menu-item>

    <el-menu-item index="/vms" class="sidebar-item">
      <div class="item-icon-wrap">
        <el-icon><Cpu /></el-icon>
      </div>
      <template #title><span>虚拟机</span></template>
    </el-menu-item>

    <el-menu-item index="/containers" class="sidebar-item">
      <div class="item-icon-wrap">
        <el-icon><Box /></el-icon>
      </div>
      <template #title><span>容器</span></template>
    </el-menu-item>

    <div class="menu-section">
      <span v-if="!appStore.sidebarCollapsed" class="menu-label">运维</span>
    </div>

    <el-menu-item index="/alerts" class="sidebar-item">
      <div class="item-icon-wrap">
        <el-icon><Bell /></el-icon>
      </div>
      <template #title><span>告警中心</span></template>
    </el-menu-item>

    <el-menu-item index="/services" class="sidebar-item">
      <div class="item-icon-wrap">
        <el-icon><Service /></el-icon>
      </div>
      <template #title><span>运维服务</span></template>
    </el-menu-item>

    <div class="menu-section">
      <span v-if="!appStore.sidebarCollapsed" class="menu-label">用户</span>
    </div>

    <el-menu-item index="/settings" class="sidebar-item">
      <div class="item-icon-wrap">
        <el-icon><User /></el-icon>
      </div>
      <template #title><span>用户信息</span></template>
    </el-menu-item>

    <el-menu-item index="/user-logs" class="sidebar-item">
      <div class="item-icon-wrap">
        <el-icon><Document /></el-icon>
      </div>
      <template #title><span>操作日志</span></template>
    </el-menu-item>

    <el-menu-item index="/user-notifications" class="sidebar-item">
      <div class="item-icon-wrap">
        <el-icon><Bell /></el-icon>
      </div>
      <template #title><span>通知设置</span></template>
    </el-menu-item>
  </el-menu>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { useThemeStore } from '@/stores/theme'

const route = useRoute()
const appStore = useAppStore()
const themeStore = useThemeStore()
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
  background: linear-gradient(180deg, #f0f2f5 0%, #e8eaef 50%, #f0f2f5 100%) !important;
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
  background: linear-gradient(180deg, #0f1729 0%, #1a1f3a 50%, #0f1729 100%) !important;
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
