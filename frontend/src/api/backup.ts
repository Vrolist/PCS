import request from './request'

export interface BackupStorage {
  id: number
  cluster_id: number
  cluster_name: string
  node_name: string
  storage_name: string
  storage_type: string
  path: string
  content_types: string
  active: boolean
  shared: boolean
  total_gb: number
  used_gb: number
  avail_gb: number
  used_fraction: number
  scanned_at: string
}

export interface BackupJob {
  id: number
  cluster_id: number
  cluster_name: string
  job_id: string
  vmid: number | null
  resource_type: string
  node_name: string
  storage_name: string
  mode: string
  schedule: string
  retention: string
  enabled: boolean
  compress: string
  notes: string
  last_run: string | null
  last_status: string
  next_run: string | null
  scanned_at: string
}

export interface BackupHistoryItem {
  id: number
  cluster_id: number
  cluster_name: string
  task_id: string
  vmid: number | null
  resource_type: string
  node_name: string
  storage_name: string
  mode: string
  status: string
  started_at: string | null
  finished_at: string | null
  duration_seconds: number | null
  size_bytes: number | null
  filename: string
  error_message: string
  scanned_at: string
}

export interface BackupStats {
  total_storages: number
  total_storages_gb: number
  used_storages_gb: number
  total_jobs: number
  enabled_jobs: number
  total_backups: number
  success_backups: number
  failed_backups: number
  success_rate: number
  total_backup_size_gb: number
}

export function getBackupStorages(params?: { cluster_id?: number }) {
  return request.get<any, BackupStorage[]>('/scanner/backup/storages/', { params })
}

export function getBackupJobs(params?: { cluster_id?: number; status?: string }) {
  return request.get<any, BackupJob[]>('/scanner/backup/jobs/', { params })
}

export function getBackupHistory(params?: {
  cluster_id?: number
  status?: string
  vmid?: number
  search?: string
  page?: number
  page_size?: number
}) {
  return request.get<any, { count: number; results: BackupHistoryItem[] }>('/scanner/backup/history/', { params })
}

export function getBackupStats(params?: { cluster_id?: number }) {
  return request.get<any, BackupStats>('/scanner/backup/stats/', { params })
}
