import request from './request'

export interface ReplicationJob {
  id: number
  cluster_id: number
  cluster_name: string
  job_id: string
  vmid: number | null
  resource_type: string
  source_node: string
  target_node: string
  schedule: string
  rate_limit: number | null
  comment: string
  enabled: boolean
  state: string
  last_sync: string | null
  last_try: string | null
  last_duration: number | null
  error_message: string
  sync_count: number
  scanned_at: string
}

export function getReplicationJobs(params?: { cluster_id?: number; status?: string; search?: string }) {
  return request.get<any, ReplicationJob[]>('/scanner/replication/', { params })
}
