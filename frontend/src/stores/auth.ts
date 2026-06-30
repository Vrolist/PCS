import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getUserInfo } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const refreshTokenVal = ref(localStorage.getItem('refreshToken') || '')
  const user = ref<any>(null)

  const isLoggedIn = computed(() => !!token.value)

  function setToken(val: string) {
    token.value = val
    localStorage.setItem('token', val)
  }

  function setRefreshToken(val: string) {
    refreshTokenVal.value = val
    localStorage.setItem('refreshToken', val)
  }

  function logout() {
    token.value = ''
    refreshTokenVal.value = ''
    user.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('refreshToken')
  }

  async function fetchUser() {
    try {
      user.value = await getUserInfo()
    } catch {
      logout()
    }
  }

  return { token, refreshTokenVal, user, isLoggedIn, setToken, setRefreshToken, logout, fetchUser }
})
