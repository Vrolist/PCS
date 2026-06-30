import axios from 'axios'
import { ElMessage } from 'element-plus'

const request = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

// 是否正在刷新 token
let isRefreshing = false
// 等待刷新的请求队列
let pendingRequests: Array<(token: string) => void> = []

function addPendingRequest(callback: (token: string) => void) {
  pendingRequests.push(callback)
}

function retryPendingRequests(newToken: string) {
  pendingRequests.forEach(cb => cb(newToken))
  pendingRequests = []
}

// 请求拦截器：附上 token
request.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器：统一错误处理 + 自动续期
request.interceptors.response.use(
  (response) => response.data,
  async (error) => {
    const status = error.response?.status
    const originalRequest = error.config

    // 401 且不是刷新请求本身 → 尝试自动续期
    if (status === 401 && !originalRequest._isRetry) {
      const refreshToken = localStorage.getItem('refreshToken')

      if (!refreshToken) {
        // 没有 refresh token → 直接跳登录
        localStorage.removeItem('token')
        localStorage.removeItem('refreshToken')
        window.location.href = '/login'
        return Promise.reject(error)
      }

      if (isRefreshing) {
        // 正在刷新中，加入等待队列
        return new Promise((resolve) => {
          addPendingRequest((newToken: string) => {
            originalRequest.headers.Authorization = `Bearer ${newToken}`
            resolve(request(originalRequest))
          })
        })
      }

      isRefreshing = true
      originalRequest._isRetry = true

      try {
        // 直接调用 axios（绕过拦截器）刷新 token
        const res = await axios.post('/api/auth/token/refresh/', {
          refresh: refreshToken,
        })

        const { access, refresh: newRefresh } = res.data
        localStorage.setItem('token', access)
        if (newRefresh) {
          localStorage.setItem('refreshToken', newRefresh)
        }

        // 重试所有等待中的请求
        retryPendingRequests(access)

        // 重试当前请求
        originalRequest.headers.Authorization = `Bearer ${access}`
        return request(originalRequest)
      } catch (refreshError) {
        // refresh token 也过期 → 跳登录
        localStorage.removeItem('token')
        localStorage.removeItem('refreshToken')
        window.location.href = '/login'
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }

    const msg = error.response?.data?.detail || error.message
    ElMessage.error(msg)
    return Promise.reject(error)
  },
)

export default request
