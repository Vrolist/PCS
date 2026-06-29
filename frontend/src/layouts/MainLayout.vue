<template>
  <div class="layout-container">
    <aside class="layout-sidebar" :class="{ collapsed: appStore.sidebarCollapsed }">
      <AppSidebar />
    </aside>
    <div class="layout-main">
      <AppHeader />
      <main class="main-content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import AppSidebar from '@/components/AppSidebar.vue'
import AppHeader from '@/components/AppHeader.vue'
import { useAppStore } from '@/stores/app'
import { useAuthStore } from '@/stores/auth'

const appStore = useAppStore()
const authStore = useAuthStore()

onMounted(() => {
  if (authStore.isLoggedIn && !authStore.user) {
    authStore.fetchUser()
  }
})
</script>

<style scoped>
.layout-container {
  display: flex;
  height: 100vh;
  overflow: hidden;
}
.layout-sidebar {
  width: 220px;
  flex-shrink: 0;
  overflow: hidden;
  transition: width 0.3s;
  border-right: 1px solid var(--border-color);
}
.layout-sidebar.collapsed {
  width: 64px;
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
</style>
