import request from './request'

export interface ContainerInfo {
  id: number
  node_id: number
  node_name: string
  cluster_id: number
  cluster_name: string
  vmid: number
  name: string
  status: string
  cpu_cores: number
  cpu_usage: number
  memory_mb: number
  memory_used_mb: number
  swap_mb: number
  swap_used_mb: number
  disk_gb: number
  uptime_seconds: number
  tags: string
  scanned_at: string
}

export function getContainers(params?: { cluster_id?: number; node_id?: number; status?: string; search?: string }) {
  return request.get<any, ContainerInfo[]>('/scanner/containers/', { params })
}
