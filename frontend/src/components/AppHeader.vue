<template>
  <header class="app-header">
    <div class="header-left">
      <el-icon class="collapse-btn" @click="appStore.toggleSidebar" :size="28">
        <Fold v-if="!appStore.sidebarCollapsed" />
        <Expand v-else />
      </el-icon>
      <el-breadcrumb separator="/">
        <el-breadcrumb-item v-for="item in breadcrumbItems" :key="item">
          {{ item }}
        </el-breadcrumb-item>
      </el-breadcrumb>
    </div>
    <div class="header-right">
      <button class="header-icon-btn" @click="themeStore.toggle" :title="themeStore.theme === 'dark' ? '切换到亮色' : '切换到暗色'">
        <el-icon :size="16"><Sunny v-if="themeStore.theme === 'dark'" /><Moon v-else /></el-icon>
      </button>
      <el-dropdown trigger="click">
        <div class="user-avatar-wrap">
          <el-avatar :size="30" icon="UserFilled" class="user-avatar" />
          <span class="username">{{ authStore.user?.username || 'buladou' }}</span>
        </div>
        <template #dropdown>
          <el-dropdown-menu class="header-dropdown">
            <el-dropdown-item @click="$router.push('/settings')">
              <el-icon><User /></el-icon>
              <span>用户信息</span>
            </el-dropdown-item>
            <el-dropdown-item @click="$router.push('/change-password')">
              <el-icon><Key /></el-icon>
              <span>修改密码</span>
            </el-dropdown-item>
            <el-dropdown-item divided v-if="authStore.user?.is_superuser" @click="goAdmin">
              <el-icon><Setting /></el-icon>
              <span>管理后台</span>
            </el-dropdown-item>
            <el-dropdown-item divided @click="handleLogout">
              <el-icon><SwitchButton /></el-icon>
              <span>退出登录</span>
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore } from '@/stores/theme'
import { createAdminSession } from '@/api/auth'
import { Fold, Expand, Sunny, Moon, User, Key, Setting, SwitchButton } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()
const authStore = useAuthStore()
const themeStore = useThemeStore()

const breadcrumbItems = computed(() => {
  const items: string[] = []
  if (route.meta?.title) {
    items.push(route.meta.title as string)
  }
  return items
})

function handleLogout() {
  authStore.logout()
  router.push('/login')
}

async function goAdmin() {
  try {
    await createAdminSession()
  } catch {
    // session 创建失败也允许跳转（可能已存在）
  }
  window.open('/admin/', '_blank')
}
</script>

<style scoped>
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  padding: 0 24px;
  height: 56px;
  flex-shrink: 0;
  transition: background 0.3s, border-color 0.3s;
}
.header-left {
  display: flex;
  align-items: center;
  gap: 4px;
}
.collapse-btn {
  cursor: pointer;
  color: var(--text-muted);
  padding: 8px;
  border-radius: 8px;
  transition: all 0.2s;
}
.collapse-btn:hover {
  color: var(--primary-color);
  background: rgba(64, 158, 255, 0.08);
}
.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}
.header-icon-btn {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: 1px solid var(--border-color);
  background: transparent;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  transition: all 0.2s;
}
.header-icon-btn:hover {
  border-color: var(--primary-color);
  color: var(--primary-color);
  background: rgba(64, 158, 255, 0.06);
}
.user-avatar-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 12px 4px 4px;
  border-radius: 20px;
  cursor: pointer;
  transition: background 0.2s;
}
.user-avatar-wrap:hover {
  background: rgba(64, 158, 255, 0.08);
}
.user-avatar {
  background: linear-gradient(135deg, #409eff, #8b5cf6);
}
.username {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
}

/* ===== 下拉菜单美化 ===== */
:deep(.header-dropdown) {
  min-width: 160px;
  border-radius: 12px;
  padding: 6px;
  border: 1px solid var(--border-color);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}
:deep(.header-dropdown .el-dropdown-menu__item) {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  border-radius: 8px;
  font-size: 13px;
  transition: all 0.15s ease;
}
:deep(.header-dropdown .el-dropdown-menu__item .el-icon) {
  font-size: 16px;
  color: var(--text-muted);
}
:deep(.header-dropdown .el-dropdown-menu__item:hover) {
  background: rgba(64, 158, 255, 0.08);
  color: var(--primary-color);
}
:deep(.header-dropdown .el-dropdown-menu__item:hover .el-icon) {
  color: var(--primary-color);
}
:deep(.header-dropdown .el-dropdown-menu__item--divided) {
  margin-top: 4px;
  padding-top: 8px;
  border-top: 1px solid var(--border-color);
}
</style>
