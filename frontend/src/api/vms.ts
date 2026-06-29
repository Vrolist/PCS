import request from './request'

export interface VMInfo {
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
  disk_gb: number
  max_disk_gb: number
  net_in_bps: number
  net_out_bps: number
  disk_read_iops: number
  disk_write_iops: number
  uptime_seconds: number
  os_type: string
  tags: string
  scanned_at: string
}

export function getVMs(params?: { cluster_id?: number; node_id?: number; status?: string; search?: string }) {
  return request.get<any, VMInfo[]>('/scanner/vms/', { params })
}
