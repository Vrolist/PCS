import request from './request'

export interface NetworkInterface {
  id: number
  node_name: string
  cluster_name: string
  name: string
  type: string
  address: string
  gateway: string
  mac_address: string
  speed: number
  status: string
  bridge_ports: string
  bond_mode: string
  bond_slaves: string
  vlan_id: number | null
  mtu: number | null
  scanned_at: string
}

export function getNetworkList(params?: { node?: string; type?: string; cluster_id?: number }) {
  return request.get<any, NetworkInterface[]>('/scanner/networks/', { params })
}
