import request from './request'

export function login(data: { username: string; password: string }) {
  return request.post('/auth/login/', data)
}

export function register(data: { username: string; email: string; password: string; password2: string }) {
  return request.post('/auth/register/', data)
}

export function getUserInfo() {
  return request.get('/auth/user/')
}

export function passwordReset(data: { email: string }) {
  return request.post('/auth/password-reset/', data)
}

export function passwordResetConfirm(data: { code: string; new_password: string; new_password2: string }) {
  return request.post('/auth/password-reset/confirm/', data)
}

export function changePassword(data: { new_password: string; new_password2: string }) {
  return request.post('/auth/change-password/', data)
}

export function updateUserInfo(data: { phone?: string; company?: string }) {
  return request.patch('/auth/user/', data)
}

export function createAdminSession() {
  return request.post('/auth/create-admin-session/', {}, { withCredentials: true })
}

export interface UserLog {
  id: number
  username: string
  action: string
  action_display: string
  resource_type: string
  resource_id: string
  detail: string
  ip_address: string
  created_at: string
}

export interface UserLogResponse {
  count: number
  page: number
  page_size: number
  results: UserLog[]
}

export function getUserLogs(params: { page?: number; page_size?: number; action?: string }) {
  return request.get<any, UserLogResponse>('/auth/logs/', { params })
}
