import request from './request'

export function login(data: { username: string; password: string }) {
  return request.post('/auth/login/', data)
}

export function register(data: { username: string; password: string; email?: string }) {
  return request.post('/auth/register/', data)
}

export function getUserInfo() {
  return request.get('/auth/user/')
}
