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
  ip_address: string
  cpu_cores: number
  cpu_usage: number
  memory_mb: number
  memory_used_mb: number
  swap_mb: number
  swap_used_mb: number
  disk_gb: number
  uptime_seconds: number
  tags: string
  has_template: boolean
  scanned_at: string
}

export interface LXCConfig {
  hostname: string
  cpu_cores: number
  memory_mb: number
  swap_mb: number
  os_type: string
  rootfs: { storage: string; raw: string }
  mount_points: Array<{ slot: string; raw: string }>
  net_devices: Array<Record<string, string>>
  ha_enabled: boolean
  ha_group: string
  description: string
  tags: string
  startup_order: string
}

export interface ContainerDetail {
  container: ContainerInfo
  config: LXCConfig | null
}

export function getContainers(params?: { cluster_id?: number; node_id?: number; status?: string; search?: string }) {
  return request.get<any, ContainerInfo[]>('/scanner/containers/', { params })
}

export function getContainerDetail(id: number) {
  return request.get<any, ContainerDetail>(`/scanner/containers/${id}/detail/`)
}
