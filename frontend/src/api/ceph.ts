import request from './request'

export interface CephStatus {
  id: number
  cluster_name: string
  health: string
  total_osds: number
  up_osds: number
  in_osds: number
  total_pgs: number
  bytes_used_gb: number
  bytes_total_gb: number
  version: string
  uptime: string
  scanned_at: string
}

export function getCephStatus(params?: { cluster_id?: number }) {
  return request.get<any, CephStatus>('/scanner/ceph/', { params })
}
