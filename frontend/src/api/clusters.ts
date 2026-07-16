import request from './request'

export interface Cluster {
  id: number
  name: string
  description: string
  status: string
  pve_version: string
  total_nodes: number
  total_vms: number
  total_lxc: number
  total_storage: number
  agent_count: number
  online_agents: number
  sync_enabled: boolean
  last_synced_at: string | null
  is_active: boolean
  last_scanned_at: string | null
  created_at: string
}

export interface AgentBrief {
  id: number
  agent_id: string
  hostname: string
  status: string
  pve_api_endpoint: string
  version: string
  total_scans: number
  error_message: string
  last_heartbeat_at: string | null
  created_at: string
}

export interface ClusterDetail extends Cluster {
  agent_token: string
  cluster_id: string
  sync_url: string
  sync_id: string
  sync_token: string
  agents: AgentBrief[]
  install_command: string
  updated_at: string
}

export function getClusters() {
  return request.get<any, { count: number; results: Cluster[] }>('/clusters/')
}

export function getCluster(id: number) {
  return request.get<any, ClusterDetail>(`/clusters/${id}/`)
}

export function createCluster(data: { name: string; description?: string }) {
  return request.post<any, Cluster>('/clusters/', data)
}

export function updateCluster(id: number, data: Partial<Cluster>) {
  return request.patch<any, Cluster>(`/clusters/${id}/`, data)
}

export function deleteCluster(id: number) {
  return request.delete(`/clusters/${id}/`)
}

export interface AgentVersion {
  latest_version: string
  download_url: string
  changelog: string
}

export function getLatestAgentVersion() {
  return request.get<any, AgentVersion>('/agent/version/')
}

// Agent 事件
export interface AgentEvent {
  id: number
  agent_id: string
  agent_hostname: string
  cluster_id: number
  cluster_name: string
  event_type: string
  event_type_display: string
  version: string
  old_version: string
  detail: string
  ip_address: string | null
  created_at: string
}

export interface AgentEventParams {
  cluster_id?: number
  agent_id?: string
  event_type?: string
  page?: number
  page_size?: number
}

export function getAgentEvents(params?: AgentEventParams) {
  return request.get<any, { count: number; results: AgentEvent[] }>('/agent/events/', { params })
}

// Agent 实例
export interface AgentInstance {
  id: number
  agent_id: string
  hostname: string
  version: string
  status: string
  status_display: string
  cluster_id: number
  cluster_name: string
  ip_address: string | null
  platform: string
  total_scans: number
  failed_scans: number
  last_heartbeat_at: string | null
  last_scan_at: string | null
  started_at: string
}

export interface AgentInstanceParams {
  cluster_id?: number
  status?: string
  page?: number
  page_size?: number
}

export function getAgentInstances(params?: AgentInstanceParams) {
  return request.get<any, { count: number; results: AgentInstance[] }>('/agent/instances/', { params })
}

// 数据同步
export function triggerSync(clusterId: number, forceFull = false) {
  return request.post<any, { ok: boolean; message: string }>(`/clusters/${clusterId}/sync/`, { force_full: forceFull })
}
