import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getUserInfo } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const user = ref<any>(null)

  const isLoggedIn = computed(() => !!token.value)

  function setToken(val: string) {
    token.value = val
    localStorage.setItem('token', val)
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
  }

  async function fetchUser() {
    try {
      user.value = await getUserInfo()
    } catch {
      logout()
    }
  }

  return { token, user, isLoggedIn, setToken, logout, fetchUser }
})
