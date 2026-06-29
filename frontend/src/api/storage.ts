import request from './request'

export interface Storage {
  id: number
  node_name: string
  name: string
  type: string
  status: string
  total_gb: number
  used_gb: number
  available_gb: number
  content: string
  shared: boolean
  scanned_at: string
}

export function getStorageList(params?: { node?: string }) {
  return request.get<any, Storage[]>('/scanner/storage/', { params })
}
