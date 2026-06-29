import request from './request'

export interface NetworkInterface {
  id: number
  node_name: string
  name: string
  type: string
  address: string
  mac_address: string
  speed: number
  status: string
  scanned_at: string
}

export function getNetworkList(params?: { node?: string; type?: string }) {
  return request.get<any, NetworkInterface[]>('/scanner/networks/', { params })
}
