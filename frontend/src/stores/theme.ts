import { defineStore } from 'pinia'
import { ref } from 'vue'

type Theme = 'light' | 'dark'

export const useThemeStore = defineStore('theme', () => {
  const theme = ref<Theme>((localStorage.getItem('theme') as Theme) || 'dark')

  function applyTheme(t: Theme) {
    theme.value = t
    localStorage.setItem('theme', t)
    if (t === 'dark') {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }

  function toggle() {
    applyTheme(theme.value === 'light' ? 'dark' : 'light')
  }

  function init() {
    applyTheme(theme.value)
  }

  return { theme, toggle, init }
})
