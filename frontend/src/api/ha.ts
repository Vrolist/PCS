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

export function getHAResources() {
  return request.get<any, HAResource[]>('/scanner/ha/')
}
