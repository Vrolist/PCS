import request from './request'

export interface NodeInfo {
  id: number
  cluster_id: number
  cluster_name: string
  node_name: string
  status: string
  cpu_model: string
  cpu_cores: number
  cpu_sockets: number
  cpu_load: number
  memory_total_mb: number
  memory_used_mb: number
  memory_usage_pct: number
  rootfs_total_gb: number
  rootfs_used_gb: number
  rootfs_avail_gb: number
  disk_io_delay_ms: number
  ip_address: string
  pve_version: string
  kernel_version: string
  uptime_seconds: number
  is_ceph_node: boolean
  is_ha_node: boolean
  scanned_at: string
}

export function getNodes() {
  return request.get<any, NodeInfo[]>('/scanner/nodes/')
}
