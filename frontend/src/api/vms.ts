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
  cpu_sockets: number
  cpu_usage: number
  memory_mb: number
  memory_used_mb: number
  balloon_min_mb: number
  balloon_max_mb: number
  disk_gb: number
  max_disk_gb: number
  disk_read_iops: number
  disk_write_iops: number
  net_in_bps: number
  net_out_bps: number
  uptime_seconds: number
  os_type: string
  snapshot_count: number
  has_template: boolean
  tags: string
  description: string
  scanned_at: string
}

export interface VMConfig {
  cpu_type: string
  cpu_cores: number
  cpu_sockets: number
  memory_mb: number
  balloon_min_mb: number
  os_type: string
  boot_order: string
  scsi_disks: Array<{ slot: string; storage: string; raw: string }>
  ide_disks: Array<{ slot: string; storage: string; media: string; raw: string }>
  net_devices: Array<Record<string, string>>
  agent_enabled: boolean
  ha_enabled: boolean
  ha_group: string
  description: string
  tags: string
}

export interface VMDetail {
  vm: VMInfo
  config: VMConfig | null
}

export function getVMs(params?: { cluster_id?: number; node_id?: number; status?: string; search?: string }) {
  return request.get<any, VMInfo[]>('/scanner/vms/', { params })
}

export function getVMDetail(id: number) {
  return request.get<any, VMDetail>(`/scanner/vms/${id}/detail/`)
}
