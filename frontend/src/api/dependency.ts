import request from './request'

export interface DependencyNode {
  id: string
  type: 'cluster' | 'node' | 'vm' | 'container' | 'storage' | 'network' | 'ceph' | 'ha' | 'sdn_zone' | 'sdn_vnet' | 'sdn_subnet'
  name: string
  [key: string]: any
}

export interface DependencyEdge {
  source: string
  target: string
  type: string
}

export interface DependencyGraph {
  nodes: DependencyNode[]
  edges: DependencyEdge[]
}

export function getDependencyGraph(params?: { cluster_id?: number }) {
  return request.get<any, DependencyGraph>('/scanner/dependency/', { params })
}
