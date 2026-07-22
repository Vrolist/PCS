import request from './request'

export interface HAResource {
  id: number
  sid: string
  resource_type: string
  vmid: number
  node_name: string
  cluster_name: string
  state: string
  ha_group: string
  ha_status: string
  crm_state: string
  max_restarts: number
  max_shutdown: number
  scanned_at: string
}

export function getHAResources(params?: { cluster_id?: number }) {
  return request.get<any, HAResource[]>('/scanner/ha/', { params })
}

export interface HACoverage {
  total_resources: number
  total_vms: number
  total_lxc: number
  ha_protected: number
  ha_vms: number
  ha_lxc: number
  coverage_pct: number
  unprotected_count: number
  crm_abnormal: number
}

export function getHACoverage(params?: { cluster_id?: number }) {
  return request.get<any, HACoverage>('/scanner/ha/coverage/', { params })
}
