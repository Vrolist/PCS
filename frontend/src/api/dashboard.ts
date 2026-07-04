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

export function getDashboardAlerts(limit = 10, clusterId?: number) {
  const params: Record<string, any> = { limit }
  if (clusterId) params.cluster_id = clusterId
  return request.get<any, DashboardAlert[]>('/dashboard/alerts/', { params })
}

export function getDashboardTrends(days = 7, clusterId?: number) {
  const params: Record<string, any> = { days }
  if (clusterId) params.cluster_id = clusterId
  return request.get<any, DashboardTrends>('/dashboard/trends/', { params })
}

export function getDashboardNodes(clusterId?: number) {
  const params: Record<string, any> = {}
  if (clusterId) params.cluster_id = clusterId
  return request.get<any, DashboardNode[]>('/dashboard/nodes/', { params })
}

export interface PredictionDimension {
  current: number | null
  current_pct: number | null
  current_used_gb?: number | null
  total_gb?: number
  total_mb?: number
  trend: 'rising' | 'declining' | 'stable' | 'unknown'
  slope_per_day: number | null
  slope_gb_per_day?: number | null
  days_until_full: number | null
  predicted_full_date: string | null
  data_points: number
  history_days: number
  chart: {
    dates: string[]
    values: number[]
    predicted_dates: string[]
    predicted_values: number[]
  }
}

export interface Predictions {
  cpu: PredictionDimension
  memory: PredictionDimension
  storage: PredictionDimension
  rootfs: PredictionDimension
}

export function getPredictions(clusterId?: number, days = 30) {
  const params: Record<string, any> = { days }
  if (clusterId) params.cluster_id = clusterId
  return request.get<any, Predictions>('/dashboard/predictions/', { params })
}

// === 健康报告 ===
export interface HealthReportIssue {
  type: string
  severity: 'critical' | 'warning' | 'info'
  resource: string
  detail: string
}

export interface HealthReportScore {
  score: number
  weight: number
}

export interface HealthReportData {
  overall_score: number
  scores: {
    node: HealthReportScore
    resource: HealthReportScore
    alert: HealthReportScore
    backup: HealthReportScore
    completeness: HealthReportScore
  }
  issues: HealthReportIssue[]
  trends: {
    dates: string[]
    cpu: number[]
    memory: number[]
  }
  assets: {
    total_nodes: number
    online_nodes: number
    total_vms: number
    running_vms: number
    total_lxc: number
    running_lxc: number
    total_storage_gb: number
    used_storage_gb: number
  }
  summary: {
    days: number
    actual_days: number
    data_adequacy: 'sufficient' | 'moderate' | 'limited' | 'insufficient'
    scan_count: number
    node_count: number
    avg_cpu: number
    avg_mem: number
    total_alerts: number
    unresolved_alerts: number
    backup_total: number
    backup_enabled: number
    storage_issue_count: number
    period_start: string
    period_end: string
  }
}

export function getHealthReport(clusterId?: number, days = 0) {
  const params: Record<string, any> = { days }
  if (clusterId) params.cluster_id = clusterId
  return request.get<any, HealthReportData>('/dashboard/health-report/', { params })
}
