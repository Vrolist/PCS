<template>
  <div class="layout-container">
    <aside
      class="layout-sidebar"
      :class="{ collapsed: appStore.sidebarCollapsed }"
      :style="{ width: appStore.sidebarCollapsed ? '64px' : appStore.sidebarWidth + 'px' }"
    >
      <AppSidebar />
    </aside>
    <div
      v-show="!appStore.sidebarCollapsed"
      class="sidebar-resize-handle"
      @mousedown="onDragStart"
    />
    <div class="layout-main">
      <AppHeader />
      <main class="main-content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import AppSidebar from '@/components/AppSidebar.vue'
import AppHeader from '@/components/AppHeader.vue'
import { useAppStore } from '@/stores/app'
import { useAuthStore } from '@/stores/auth'

const appStore = useAppStore()
const authStore = useAuthStore()

let dragging = false

function onDragStart(e: MouseEvent) {
  e.preventDefault()
  dragging = true
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
  document.addEventListener('mousemove', onDragMove)
  document.addEventListener('mouseup', onDragEnd)
}

function onDragMove(e: MouseEvent) {
  if (!dragging) return
  appStore.setSidebarWidth(e.clientX)
}

function onDragEnd() {
  dragging = false
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
  document.removeEventListener('mousemove', onDragMove)
  document.removeEventListener('mouseup', onDragEnd)
}

onMounted(() => {
  if (authStore.isLoggedIn && !authStore.user) {
    authStore.fetchUser()
  }
})

onUnmounted(() => {
  document.removeEventListener('mousemove', onDragMove)
  document.removeEventListener('mouseup', onDragEnd)
})
</script>

<style scoped>
.layout-container {
  display: flex;
  height: 100vh;
  overflow: hidden;
}
.layout-sidebar {
  flex-shrink: 0;
  overflow: hidden;
  transition: width 0.3s;
  border-right: 1px solid var(--border-color);
}
.sidebar-resize-handle {
  width: 3px;
  flex-shrink: 0;
  cursor: col-resize;
  background: transparent;
  transition: background 0.2s;
  position: relative;
  z-index: 10;
}
.sidebar-resize-handle::after {
  content: '';
  position: absolute;
  top: 0;
  bottom: 0;
  left: -3px;
  right: -3px;
}
.sidebar-resize-handle:hover {
  background: #409eff;
}
.layout-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  overflow: hidden;
}
.main-content {
  flex: 1;
  background: var(--bg-primary);
  padding: 24px;
  overflow-y: auto;
  transition: background 0.3s;
}
.main-content > :first-child {
  min-height: 100%;
}
</style>
