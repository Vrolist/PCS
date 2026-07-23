import request from './request'

export interface ClusterTaskItem {
  id: number
  cluster_id: number
  cluster_name: string
  upid: string
  task_type: string
  status: string
  exit_status: string
  node_name: string
  user: string
  vmid: number | null
  start_time: string | null
  end_time: string | null
  duration_seconds: number | null
  scanned_at: string
}

export function getClusterTasks(params?: {
  cluster_id?: number
  task_type?: string
  status?: string
  search?: string
  page?: number
  page_size?: number
}) {
  return request.get<any, { count: number; results: ClusterTaskItem[] }>('/scanner/cluster-tasks/', { params })
}
