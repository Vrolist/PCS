import request from './request'

export interface AdminUser {
  id: number
  username: string
  email: string
  phone: string
  company: string
  date_joined: string
  is_superuser: boolean
  is_active: boolean
}

export function getAdminUsers() {
  return request.get<any, { results: AdminUser[] }>('/auth/admin/users/')
}

export function createAdminUser(data: {
  username: string
  email: string
  password: string
  password2: string
  phone?: string
  company?: string
}) {
  return request.post<any, AdminUser>('/auth/admin/users/', data)
}

export function getAdminUser(id: number) {
  return request.get<any, AdminUser>(`/auth/admin/users/${id}/`)
}

export function updateAdminUser(id: number, data: Partial<AdminUser>) {
  return request.patch<any, AdminUser>(`/auth/admin/users/${id}/`, data)
}

export function deleteAdminUser(id: number) {
  return request.delete(`/auth/admin/users/${id}/`)
}

export function adminChangePassword(id: number, data: { new_password: string; new_password2: string }) {
  return request.post(`/auth/admin/users/${id}/change-password/`, data)
}

export function adminToggleUserActive(id: number) {
  return request.post<any, { detail: string; is_active: boolean }>(`/auth/admin/users/${id}/toggle-active/`)
}

export function getRegistrationStatus() {
  return request.get<any, { enabled: boolean }>('/auth/registration-status/')
}

export function toggleRegistration() {
  return request.post<any, { detail: string; enabled: boolean }>('/auth/toggle-registration/')
}
