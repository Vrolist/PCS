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

export interface NodeDetailInfo extends NodeInfo {
  memory_free_mb: number
  swap_total_mb: number
  swap_used_mb: number
  diskstat: Array<Record<string, any>>
  mac_address: string
}

export interface NodeStorage {
  name: string
  type: string
  status: string
  active: boolean
  total_gb: number
  used_gb: number
  avail_gb: number
  content_types: string
  shared: boolean
}

export interface NodeNetwork {
  name: string
  type: string
  active: boolean
  method: string
  address: string
  gateway: string
  speed_mbps: number
}

export interface NodeVM {
  vmid: number
  name: string
  status: string
  cpu_cores: number
  cpu_usage: number
  memory_mb: number
  memory_used_mb: number
  disk_gb: number
  uptime_seconds: number
}

export interface NodeContainer {
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
  has_template: boolean
}

export interface NodeDetail {
  node: NodeDetailInfo
  storages: NodeStorage[]
  networks: NodeNetwork[]
  vms: NodeVM[]
  containers: NodeContainer[]
}

export function getNodes() {
  return request.get<any, NodeInfo[]>('/scanner/nodes/')
}

export function getNodeDetail(id: number) {
  return request.get<any, NodeDetail>(`/scanner/nodes/${id}/detail/`)
}
