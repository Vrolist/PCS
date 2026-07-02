import request from './request'

export interface SnapshotInfo {
  id: number
  snapid: string
  name: string
  description: string
  snap_time: string | null
  parent: string
  ram: boolean
  vmstate: boolean
  snap_type: string
  size_mb: number | null
  vm_id: number
  vm_vmid: number
  vm_name: string
  vm_status: string
  node_name: string
  cluster_id: number
  cluster_name: string
  scanned_at: string
}

export function getSnapshots(params?: {
  cluster_id?: number
  node_id?: number
  vmid?: number
  search?: string
}) {
  return request.get<any, SnapshotInfo[]>('/scanner/snapshots/', { params })
}
