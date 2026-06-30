import request from './request'

export interface DashboardStats {
  total_clusters: number
  total_nodes: number
  online_nodes: number
  total_vms: number
  total_containers: number
  active_alerts: number
}

export interface DashboardAlert {
  id: number
  title: string
  severity: 'critical' | 'warning' | 'info'
  category: string
  affected_resource: string
  detail: string
  created_at: string
  cluster_name: string
}

export interface DashboardTrends {
  dates: string[]
  cpu_avg: number[]
  memory_avg: number[]
}

export interface DashboardNode {
  name: string
  status: string
  cpu_load: number
  memory_total_mb: number
  memory_used_mb: number
  memory_usage_pct: number
  rootfs_total_gb: number
  rootfs_used_gb: number
  pve_version: string
  ip_address: string
  cluster_name: string
  disk_io_delay_ms: number
  last_scan: string
}

export function getDashboardStats() {
  return request.get<any, DashboardStats>('/dashboard/stats/')
}

export function getDashboardAlerts(limit = 10) {
  return request.get<any, DashboardAlert[]>('/dashboard/alerts/', { params: { limit } })
}

export function getDashboardTrends(days = 7) {
  return request.get<any, DashboardTrends>('/dashboard/trends/', { params: { days } })
}

export function getDashboardNodes() {
  return request.get<any, DashboardNode[]>('/dashboard/nodes/')
}
