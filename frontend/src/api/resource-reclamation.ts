import request from './request'

export interface ZombieResource {
  id: number
  vmid: number
  name: string
  node_name: string
  cluster_name: string
  cpu_cores: number | null
  memory_mb: number | null
  disk_gb: number | null
  status: string
  scanned_at: string
  stopped_days: number
  risk_level: 'low' | 'medium' | 'high'
  suggestion: string
}

export interface OldSnapshot {
  id: number
  snapid: string
  name: string
  vm_name: string
  vm_vmid: number
  node_name: string
  cluster_name: string
  snap_time: string | null
  size_mb: number | null
  size_gb: number
  snap_age_days: number
  risk_level: 'low' | 'medium' | 'high'
  suggestion: string
}

export interface LowUsageStorage {
  id: number
  storage_name: string
  type: string
  node_name: string
  cluster_name: string
  total_gb: number | null
  used_gb: number | null
  avail_gb: number | null
  used_fraction: number | null
  scanned_at: string
  risk_level: 'low' | 'medium' | 'high'
  suggestion: string
}

export interface IdleResource {
  id: number
  type: 'vm' | 'container'
  vmid: number
  name: string
  node_name: string
  cluster_name: string
  cpu_cores: number | null
  memory_mb: number | null
  disk_gb: number | null
  scanned_at: string
  risk_level: 'low' | 'medium' | 'high'
  suggestion: string
}

export interface ResourceReclamationData {
  summary: {
    zombie_vms_count: number
    zombie_containers_count: number
    old_snapshots_count: number
    low_usage_storages_count: number
    idle_resources_count: number
    reclaimable_space_gb: number
    total_storage_gb: number
  }
  zombie_vms: ZombieResource[]
  zombie_containers: ZombieResource[]
  old_snapshots: OldSnapshot[]
  low_usage_storages: LowUsageStorage[]
  idle_resources: IdleResource[]
}

export function getResourceReclamation(params?: { cluster_id?: number }) {
  return request.get<any, ResourceReclamationData>('/scanner/resource-reclamation/', { params })
}