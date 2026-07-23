import request from './request'

export interface ClusterLogItem {
  id: number
  cluster_id: number
  cluster_name: string
  entry_id: number
  log_level: string
  tag: string
  message: string
  log_time: string | null
  scanned_at: string
}

export function getClusterLogs(params?: {
  cluster_id?: number
  level?: string
  tag?: string
  search?: string
  page?: number
  page_size?: number
}) {
  return request.get<any, { count: number; results: ClusterLogItem[] }>('/scanner/cluster-log/', { params })
}
