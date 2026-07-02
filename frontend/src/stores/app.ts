import { defineStore } from 'pinia'
import { ref } from 'vue'

const MIN_WIDTH = 180
const MAX_WIDTH = 400
const DEFAULT_WIDTH = 220

export const useAppStore = defineStore('app', () => {
  const sidebarCollapsed = ref(false)
  const sidebarWidth = ref(
    Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, Number(localStorage.getItem('sidebar_width')) || DEFAULT_WIDTH))
  )
  const breadcrumb = ref<string[]>([])

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  function setSidebarWidth(width: number) {
    sidebarWidth.value = Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, width))
    localStorage.setItem('sidebar_width', String(sidebarWidth.value))
  }

  function setBreadcrumb(items: string[]) {
    breadcrumb.value = items
  }

  return { sidebarCollapsed, sidebarWidth, toggleSidebar, setSidebarWidth, setBreadcrumb }
})
