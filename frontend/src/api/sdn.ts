import request from './request'

export interface SDNZone {
  id: number
  zone: string
  zone_type: string
  nodes: string
  cluster_name: string
  scanned_at: string
}

export interface SDNVNet {
  id: number
  vnet: string
  vnet_type: string
  vlan: number | null
  zone_name: string
  zone: string
  cluster_name: string
  scanned_at: string
}

export interface SDNSubnet {
  id: number
  subnet: string
  vnet_name: string
  vnet: string
  gateway: string
  dns_server: string
  dns_zone_prefix: string
  cluster_name: string
  scanned_at: string
}

export function getSDNZones(params?: { cluster_id?: number }) {
  return request.get<any, SDNZone[]>('/scanner/sdn/zones/', { params })
}

export function getSDNVNets(params?: { cluster_id?: number }) {
  return request.get<any, SDNVNet[]>('/scanner/sdn/vnets/', { params })
}

export function getSDNSubnets(params?: { cluster_id?: number }) {
  return request.get<any, SDNSubnet[]>('/scanner/sdn/subnets/', { params })
}
