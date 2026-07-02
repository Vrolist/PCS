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
      <button class="header-icon-btn" @click="themeStore.toggle" :title="themeStore.theme === 'dark' ? t('header.switchToLight') : t('header.switchToDark')">
        <el-icon :size="16"><Sunny v-if="themeStore.theme === 'dark'" /><Moon v-else /></el-icon>
      </button>
      <el-dropdown trigger="click" @command="handleLangChange">
        <button class="header-icon-btn" :title="t('header.language')">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><line x1="4" y1="22" x2="4" y2="15"/></svg>
        </button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item v-for="lang in languages" :key="lang.value" :command="lang.value" :class="{ 'is-active-lang': currentLang === lang.value }">
              <span>{{ lang.label }}</span>
              <el-icon v-if="currentLang === lang.value" style="margin-left: auto;"><Check /></el-icon>
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
      <el-dropdown trigger="click">
        <div class="user-avatar-wrap">
          <el-avatar :size="30" icon="UserFilled" class="user-avatar" />
          <span class="username">{{ authStore.user?.username || 'buladou' }}</span>
        </div>
        <template #dropdown>
          <el-dropdown-menu class="header-dropdown">
            <el-dropdown-item @click="$router.push('/dashboard/settings')">
              <el-icon><User /></el-icon>
              <span>{{ t('header.userProfile') }}</span>
            </el-dropdown-item>
            <el-dropdown-item @click="$router.push('/dashboard/change-password')">
              <el-icon><Key /></el-icon>
              <span>{{ t('header.changePassword') }}</span>
            </el-dropdown-item>
            <el-dropdown-item divided v-if="authStore.user?.is_superuser" @click="goAdmin">
              <el-icon><Setting /></el-icon>
              <span>{{ t('header.adminPanel') }}</span>
            </el-dropdown-item>
            <el-dropdown-item divided @click="handleLogout">
              <el-icon><SwitchButton /></el-icon>
              <span>{{ t('header.logout') }}</span>
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore } from '@/stores/theme'
import { createAdminSession } from '@/api/auth'
import { setLocale } from '@/i18n'
import { Fold, Expand, Sunny, Moon, User, Key, Setting, SwitchButton, Check } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()
const authStore = useAuthStore()
const themeStore = useThemeStore()
const { t, locale } = useI18n()

const breadcrumbItems = computed(() => {
  const items: string[] = []
  const titleKey = route.meta?.titleKey as string
  if (titleKey) {
    items.push(t(titleKey))
  } else if (route.meta?.title) {
    items.push(route.meta.title as string)
  }
  return items
})

// 语言切换
const currentLang = computed(() => locale.value)
const languages = [
  { value: 'zh-CN', label: '中文' },
  { value: 'en', label: 'English' },
  { value: 'ja', label: '日本語' },
  { value: 'ko', label: '한국어' },
  { value: 'de', label: 'Deutsch' },
  { value: 'ru', label: 'Русский' },
  { value: 'fr', label: 'Français' },
  { value: 'pt-BR', label: 'Português' },
]
function handleLangChange(lang: string) {
  setLocale(lang)
}

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
:deep(.is-active-lang) {
  color: var(--primary-color) !important;
  font-weight: 500;
}
</style>
