import request from './request'

export interface FirewallSummary {
  cluster_enabled: boolean
  policy_in: string
  policy_out: string
  policy_forward: string
  total_rules: number
  total_security_groups: number
  total_ipsets: number
  total_aliases: number
  cluster_rules: number
  node_rules: number
  vm_rules: number
  ct_rules: number
  group_rules: number
  scanned_at: string | null
}

export interface FirewallRule {
  id: number
  cluster_id: number
  cluster_name: string
  scope: string
  group_name: string
  node_name: string
  vmid: number | null
  pos: number
  action: string
  direction: string
  proto: string
  source: string
  dest: string
  dport: string
  sport: string
  comment: string
  enabled: boolean
  log: string
  iface: string
  macro: string
  scanned_at: string
}

export interface IPSetEntry {
  id: number
  cidr: string
  comment: string
  nomatch: boolean
}

export interface FirewallIPSet {
  id: number
  cluster_id: number
  cluster_name: string
  scope: string
  name: string
  comment: string
  entry_count: number
  entries: IPSetEntry[]
  scanned_at: string
}

export interface FirewallAlias {
  id: number
  cluster_id: number
  cluster_name: string
  scope: string
  name: string
  cidr: string
  alias_type: string
  comment: string
  scanned_at: string
}

export interface FirewallOptions {
  id: number
  cluster_id: number
  cluster_name: string
  scope: string
  node_name: string
  vmid: number | null
  enabled: boolean
  policy_in: string
  policy_out: string
  policy_forward: string
  log_level_in: string
  log_level_out: string
  dhcp: boolean
  ipfilter: boolean
  ndp: boolean
  macfilter: boolean
  scanned_at: string
}

export interface SecurityGroup {
  name: string
  cluster_id: number
  cluster_name: string
  rules: {
    id: number
    pos: number
    action: string
    direction: string
    proto: string
    source: string
    dest: string
    dport: string
    sport: string
    comment: string
    enabled: boolean
    log: string
    macro: string
  }[]
  scanned_at: string
}

export function getFirewallSummary(params?: { cluster_id?: number }) {
  return request.get<any, FirewallSummary>('/scanner/firewall/summary/', { params })
}

export function getFirewallRules(params?: {
  cluster_id?: number
  scope?: string
  group?: string
  search?: string
}) {
  return request.get<any, FirewallRule[]>('/scanner/firewall/rules/', { params })
}

export function getFirewallIPSets(params?: { cluster_id?: number }) {
  return request.get<any, FirewallIPSet[]>('/scanner/firewall/ipsets/', { params })
}

export function getFirewallAliases(params?: { cluster_id?: number }) {
  return request.get<any, FirewallAlias[]>('/scanner/firewall/aliases/', { params })
}

export function getFirewallOptions(params?: { cluster_id?: number }) {
  return request.get<any, FirewallOptions[]>('/scanner/firewall/options/', { params })
}

export function getFirewallSecurityGroups(params?: { cluster_id?: number }) {
  return request.get<any, SecurityGroup[]>('/scanner/firewall/security-groups/', { params })
}
