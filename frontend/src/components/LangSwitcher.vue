<template>
  <el-dropdown trigger="click" @command="handleLangChange">
    <button class="lang-btn" :title="t('header.language')">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><line x1="4" y1="22" x2="4" y2="15"/></svg>
      <span class="lang-current">{{ currentLangLabel }}</span>
    </button>
    <template #dropdown>
      <el-dropdown-menu class="lang-dropdown">
        <el-dropdown-item v-for="lang in languages" :key="lang.value" :command="lang.value" :class="{ 'is-active-lang': currentLang === lang.value }">
          <span>{{ lang.label }}</span>
          <el-icon v-if="currentLang === lang.value" style="margin-left: auto;"><Check /></el-icon>
        </el-dropdown-item>
      </el-dropdown-menu>
    </template>
  </el-dropdown>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { setLocale } from '@/i18n'
import { Check } from '@element-plus/icons-vue'

const { t, locale } = useI18n()

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

const currentLangLabel = computed(() => {
  return languages.find((l) => l.value === currentLang.value)?.label ?? '中文'
})

function handleLangChange(lang: string) {
  setLocale(lang)
}
</script>

<style scoped>
.lang-btn {
  height: 36px;
  padding: 0 12px;
  border-radius: 8px;
  border: 1px solid var(--border-color);
  background: var(--bg-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--text-secondary);
  transition: all 0.2s;
}
.lang-btn:hover {
  border-color: #409eff;
  color: #409eff;
}
.lang-current {
  font-size: 13px;
  font-weight: 500;
}
:deep(.lang-dropdown) {
  min-width: 130px;
  border-radius: 12px;
  padding: 6px;
  border: 1px solid var(--border-color);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}
:deep(.lang-dropdown .el-dropdown-menu__item) {
  border-radius: 8px;
  padding: 8px 14px;
  font-size: 13px;
  transition: all 0.15s ease;
}
:deep(.lang-dropdown .el-dropdown-menu__item:hover) {
  background: rgba(64, 158, 255, 0.08);
  color: var(--primary-color);
}
:deep(.is-active-lang) {
  color: var(--primary-color) !important;
  font-weight: 500;
}
</style>
