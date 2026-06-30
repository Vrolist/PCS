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
