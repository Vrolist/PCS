<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ t('advanced.firewall.title') }}</h2>
        <p class="page-desc">{{ t('advanced.firewall.subtitle') }}</p>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-row">
      <div class="el-card is-never-shadow stat-card">
        <div class="el-card__body">
          <div class="stat-label">{{ t('advanced.firewall.totalRules') }}</div>
          <div class="stat-value">{{ summary.total_rules }}</div>
        </div>
      </div>
      <div class="el-card is-never-shadow stat-card">
        <div class="el-card__body">
          <div class="stat-label">{{ t('advanced.firewall.securityGroups') }}</div>
          <div class="stat-value">{{ summary.total_security_groups }}</div>
        </div>
      </div>
      <div class="el-card is-never-shadow stat-card">
        <div class="el-card__body">
          <div class="stat-label">{{ t('advanced.firewall.ipsets') }}</div>
          <div class="stat-value">{{ summary.total_ipsets }}</div>
        </div>
      </div>
      <div class="el-card is-never-shadow stat-card">
        <div class="el-card__body">
          <div class="stat-label">{{ t('advanced.firewall.aliases') }}</div>
          <div class="stat-value">{{ summary.total_aliases }}</div>
        </div>
      </div>
    </div>

    <!-- 全局状态条 -->
    <div class="el-card is-never-shadow status-bar">
      <div class="el-card__body status-bar-body">
        <span class="status-item">
          <span class="status-dot" :class="summary.cluster_enabled ? 'dot-on' : 'dot-off'"></span>
          {{ summary.cluster_enabled ? t('advanced.firewall.enabled') : t('advanced.firewall.disabled') }}
        </span>
        <span class="status-item">
          {{ t('advanced.firewall.policyIn') }}: <el-tag size="small" :type="policyTagType(summary.policy_in)">{{ summary.policy_in }}</el-tag>
        </span>
        <span class="status-item">
          {{ t('advanced.firewall.policyOut') }}: <el-tag size="small" :type="policyTagType(summary.policy_out)">{{ summary.policy_out }}</el-tag>
        </span>
      </div>
    </div>

    <!-- Tabs -->
    <el-card shadow="hover" class="table-card">
      <el-tabs v-model="activeTab" @tab-change="onTabChange">
        <!-- 规则管理 -->
        <el-tab-pane :label="t('advanced.firewall.rules')" name="rules">
          <div class="tab-toolbar">
            <el-input v-model="ruleSearch" :placeholder="t('advanced.firewall.searchPlaceholder')"
              clearable style="width: 300px" @input="debounceFetchRules">
              <template #prefix><el-icon><Search /></el-icon></template>
            </el-input>
            <el-select v-model="ruleScopeFilter" clearable :placeholder="t('advanced.firewall.scope')" style="width: 140px" @change="fetchRules">
              <el-option label="cluster" value="cluster" />
              <el-option label="node" value="node" />
              <el-option label="vm" value="vm" />
              <el-option label="ct" value="ct" />
              <el-option label="group" value="group" />
            </el-select>
          </div>
          <el-table :data="rules" stripe style="width: 100%" v-loading="loading" :empty-text="t('advanced.firewall.noRules')">
            <el-table-column prop="pos" :label="t('advanced.firewall.rulePos')" width="70" align="center" />
            <el-table-column prop="direction" :label="t('advanced.firewall.direction')" width="80" align="center">
              <template #default="{ row }">
                <el-tag size="small" :type="dirTagType(row.direction)">{{ row.direction?.toUpperCase() }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="action" :label="t('advanced.firewall.action')" width="100" align="center">
              <template #default="{ row }">
                <el-tag size="small" :type="actionTagType(row.action)">{{ row.action }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="proto" :label="t('advanced.firewall.proto')" width="80" align="center">
              <template #default="{ row }">
                <span v-if="row.proto">{{ row.proto }}</span>
                <span v-else class="text-muted">any</span>
              </template>
            </el-table-column>
            <el-table-column prop="source" :label="t('advanced.firewall.source')" min-width="140">
              <template #default="{ row }">
                <span v-if="row.source">{{ row.source }}</span>
                <span v-else class="text-muted">any</span>
              </template>
            </el-table-column>
            <el-table-column prop="dest" :label="t('advanced.firewall.dest')" min-width="140">
              <template #default="{ row }">
                <span v-if="row.dest">{{ row.dest }}</span>
                <span v-else class="text-muted">any</span>
              </template>
            </el-table-column>
            <el-table-column prop="dport" :label="t('advanced.firewall.dport')" width="110">
              <template #default="{ row }">
                <span v-if="row.dport">{{ row.dport }}</span>
                <span v-else class="text-muted">-</span>
              </template>
            </el-table-column>
            <el-table-column prop="macro" :label="t('advanced.firewall.macro')" width="100">
              <template #default="{ row }">
                <el-tag v-if="row.macro" size="small" effect="plain">{{ row.macro }}</el-tag>
                <span v-else class="text-muted">-</span>
              </template>
            </el-table-column>
            <el-table-column prop="scope" :label="t('advanced.firewall.scope')" width="90" align="center">
              <template #default="{ row }">
                <el-tag size="small" effect="plain">{{ row.scope }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="enabled" :label="t('advanced.firewall.enabledLabel')" width="80" align="center">
              <template #default="{ row }">
                <el-tag size="small" :type="row.enabled ? 'success' : 'info'">{{ row.enabled ? 'ON' : 'OFF' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="comment" :label="t('advanced.firewall.comment')" min-width="160" show-overflow-tooltip />
          </el-table>
        </el-tab-pane>

        <!-- 安全组 -->
        <el-tab-pane :label="t('advanced.firewall.securityGroups')" name="groups">
          <el-empty v-if="!loading && securityGroups.length === 0" :description="t('advanced.firewall.noGroups')" />
          <div v-for="group in securityGroups" :key="group.name" class="group-block">
            <div class="group-header">
              <el-tag effect="dark" type="warning">{{ group.name }}</el-tag>
              <span class="group-cluster">{{ group.cluster_name }}</span>
            </div>
            <el-table :data="group.rules" stripe size="small" style="width: 100%">
              <el-table-column prop="pos" label="#" width="60" align="center" />
              <el-table-column prop="direction" :label="t('advanced.firewall.direction')" width="80" align="center">
                <template #default="{ row }">
                  <el-tag size="small" :type="dirTagType(row.direction)">{{ row.direction?.toUpperCase() }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="action" :label="t('advanced.firewall.action')" width="100" align="center">
                <template #default="{ row }">
                  <el-tag size="small" :type="actionTagType(row.action)">{{ row.action }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="proto" :label="t('advanced.firewall.proto')" width="80" align="center">
                <template #default="{ row }">{{ row.proto || 'any' }}</template>
              </el-table-column>
              <el-table-column prop="source" :label="t('advanced.firewall.source')" min-width="130">
                <template #default="{ row }">{{ row.source || 'any' }}</template>
              </el-table-column>
              <el-table-column prop="dport" :label="t('advanced.firewall.dport')" width="110">
                <template #default="{ row }">{{ row.dport || '-' }}</template>
              </el-table-column>
              <el-table-column prop="comment" :label="t('advanced.firewall.comment')" min-width="160" show-overflow-tooltip />
              <el-table-column prop="enabled" :label="t('advanced.firewall.enabledLabel')" width="80" align="center">
                <template #default="{ row }">
                  <el-tag size="small" :type="row.enabled ? 'success' : 'info'">{{ row.enabled ? 'ON' : 'OFF' }}</el-tag>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>

        <!-- IPSet -->
        <el-tab-pane :label="t('advanced.firewall.ipsets')" name="ipsets">
          <el-empty v-if="!loading && ipsets.length === 0" :description="t('advanced.firewall.noIPSets')" />
          <div v-for="ipset in ipsets" :key="ipset.id" class="group-block">
            <div class="group-header">
              <el-tag effect="dark" type="primary">{{ ipset.name }}</el-tag>
              <span class="group-cluster">{{ ipset.cluster_name }}</span>
              <span v-if="ipset.comment" class="group-comment">{{ ipset.comment }}</span>
              <el-tag size="small" type="info" style="margin-left: auto">{{ ipset.entry_count }} {{ t('advanced.firewall.entryCount') }}</el-tag>
            </div>
            <el-table :data="ipset.entries" stripe size="small" style="width: 100%">
              <el-table-column prop="cidr" :label="t('advanced.firewall.cidr')" min-width="200">
                <template #default="{ row }">
                  <code>{{ row.cidr }}</code>
                </template>
              </el-table-column>
              <el-table-column prop="comment" :label="t('advanced.firewall.comment')" min-width="200" show-overflow-tooltip />
              <el-table-column prop="nomatch" :label="t('advanced.firewall.nomatch')" width="100" align="center">
                <template #default="{ row }">
                  <el-tag v-if="row.nomatch" size="small" type="danger">nomatch</el-tag>
                  <span v-else class="text-muted">-</span>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>

        <!-- 别名 -->
        <el-tab-pane :label="t('advanced.firewall.aliases')" name="aliases">
          <el-table :data="aliases" stripe style="width: 100%" v-loading="loading" :empty-text="t('advanced.firewall.noAliases')">
            <el-table-column prop="name" :label="t('advanced.firewall.aliasName')" min-width="160">
              <template #default="{ row }">
                <el-tag effect="plain">{{ row.name }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="cidr" :label="t('advanced.firewall.cidr')" min-width="200">
              <template #default="{ row }"><code>{{ row.cidr }}</code></template>
            </el-table-column>
            <el-table-column prop="alias_type" :label="t('advanced.firewall.aliasType')" width="100" align="center">
              <template #default="{ row }">
                <el-tag size="small" effect="plain">{{ row.alias_type }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="comment" :label="t('advanced.firewall.comment')" min-width="200" show-overflow-tooltip />
            <el-table-column prop="cluster_name" :label="t('advanced.firewall.cluster')" min-width="140" />
            <el-table-column prop="scanned_at" :label="t('advanced.firewall.scannedAt')" width="170">
              <template #default="{ row }">{{ formatTime(row.scanned_at) }}</template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <!-- 防火墙选项 -->
        <el-tab-pane :label="t('advanced.firewall.options')" name="options">
          <el-table :data="optionsList" stripe style="width: 100%" v-loading="loading" empty-text="暂无防火墙选项数据">
            <el-table-column prop="scope" :label="t('advanced.firewall.scope')" width="100" align="center">
              <template #default="{ row }">
                <el-tag size="small" effect="plain">{{ row.scope }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="node_name" :label="t('advanced.firewall.node')" min-width="120">
              <template #default="{ row }">
                <span v-if="row.node_name">{{ row.node_name }}</span>
                <span v-else class="text-muted">-</span>
              </template>
            </el-table-column>
            <el-table-column prop="vmid" :label="t('advanced.firewall.vmid')" width="80" align="center">
              <template #default="{ row }">
                <span v-if="row.vmid != null">{{ row.vmid }}</span>
                <span v-else class="text-muted">-</span>
              </template>
            </el-table-column>
            <el-table-column prop="enabled" :label="t('advanced.firewall.enabledLabel')" width="90" align="center">
              <template #default="{ row }">
                <el-tag size="small" :type="row.enabled ? 'success' : 'info'">{{ row.enabled ? 'ON' : 'OFF' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="policy_in" :label="t('advanced.firewall.policyIn')" width="110" align="center">
              <template #default="{ row }">
                <el-tag size="small" :type="policyTagType(row.policy_in)">{{ row.policy_in }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="policy_out" :label="t('advanced.firewall.policyOut')" width="110" align="center">
              <template #default="{ row }">
                <el-tag size="small" :type="policyTagType(row.policy_out)">{{ row.policy_out }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="policy_forward" :label="t('advanced.firewall.policyForward')" width="120" align="center">
              <template #default="{ row }">
                <el-tag size="small" :type="policyTagType(row.policy_forward)">{{ row.policy_forward }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="macfilter" label="MAC Filter" width="100" align="center">
              <template #default="{ row }">
                <el-tag size="small" :type="row.macfilter ? 'success' : 'info'">{{ row.macfilter ? 'ON' : 'OFF' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="ipfilter" label="IP Filter" width="100" align="center">
              <template #default="{ row }">
                <el-tag size="small" :type="row.ipfilter ? 'success' : 'info'">{{ row.ipfilter ? 'ON' : 'OFF' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="cluster_name" :label="t('advanced.firewall.cluster')" min-width="140" />
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useClusterStore } from '@/stores/cluster'
import { Search } from '@element-plus/icons-vue'
import {
  getFirewallSummary, getFirewallRules, getFirewallIPSets,
  getFirewallAliases, getFirewallOptions, getFirewallSecurityGroups,
  type FirewallSummary, type FirewallRule, type FirewallIPSet,
  type FirewallAlias, type FirewallOptions, type SecurityGroup,
} from '@/api/firewall'

const { t } = useI18n()
const clusterStore = useClusterStore()

const loading = ref(false)
const activeTab = ref('rules')

const summary = ref<FirewallSummary>({
  cluster_enabled: false, policy_in: 'ACCEPT', policy_out: 'ACCEPT', policy_forward: 'ACCEPT',
  total_rules: 0, total_security_groups: 0, total_ipsets: 0, total_aliases: 0,
  cluster_rules: 0, node_rules: 0, vm_rules: 0, ct_rules: 0, group_rules: 0, scanned_at: null,
})
const rules = ref<FirewallRule[]>([])
const securityGroups = ref<SecurityGroup[]>([])
const ipsets = ref<FirewallIPSet[]>([])
const aliases = ref<FirewallAlias[]>([])
const optionsList = ref<FirewallOptions[]>([])

const ruleSearch = ref('')
const ruleScopeFilter = ref('')
let debounceTimer: ReturnType<typeof setTimeout> | null = null

function formatTime(iso: string) {
  if (!iso) return '-'
  const d = new Date(iso)
  return `${d.getFullYear()}/${String(d.getMonth() + 1).padStart(2, '0')}/${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}`
}

function policyTagType(policy: string) {
  if (policy === 'ACCEPT') return 'success'
  if (policy === 'DROP') return 'danger'
  if (policy === 'REJECT') return 'warning'
  return 'info'
}

function actionTagType(action: string) {
  if (action === 'ACCEPT') return 'success'
  if (action === 'DROP') return 'danger'
  if (action === 'REJECT') return 'warning'
  return 'info'
}

function dirTagType(dir: string) {
  if (dir === 'in') return 'primary'
  if (dir === 'out') return 'warning'
  if (dir === 'forward') return 'info'
  return 'info'
}

function params() {
  const p: Record<string, any> = {}
  if (clusterStore.currentClusterId) p.cluster_id = clusterStore.currentClusterId
  return p
}

async function fetchSummary() {
  try { summary.value = await getFirewallSummary(params()) } catch { /* ignore */ }
}

async function fetchRules() {
  try {
    const p: Record<string, any> = { ...params() }
    if (ruleScopeFilter.value) p.scope = ruleScopeFilter.value
    if (ruleSearch.value) p.search = ruleSearch.value
    rules.value = await getFirewallRules(p)
  } catch { /* ignore */ }
}

function debounceFetchRules() {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => fetchRules(), 300)
}

async function fetchGroups() {
  try { securityGroups.value = await getFirewallSecurityGroups(params()) } catch { /* ignore */ }
}

async function fetchIPSets() {
  try { ipsets.value = await getFirewallIPSets(params()) } catch { /* ignore */ }
}

async function fetchAliases() {
  try { aliases.value = await getFirewallAliases(params()) } catch { /* ignore */ }
}

async function fetchOptions() {
  try { optionsList.value = await getFirewallOptions(params()) } catch { /* ignore */ }
}

async function fetchAll() {
  loading.value = true
  try {
    await fetchSummary()
    await onTabChange(activeTab.value)
  } finally {
    loading.value = false
  }
}

async function onTabChange(tab: string | number) {
  loading.value = true
  try {
    if (tab === 'rules') await fetchRules()
    else if (tab === 'groups') await fetchGroups()
    else if (tab === 'ipsets') await fetchIPSets()
    else if (tab === 'aliases') await fetchAliases()
    else if (tab === 'options') await fetchOptions()
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  if (!clusterStore.clusterList.length) await clusterStore.fetchClusters()
  fetchAll()
})

watch(() => clusterStore.currentClusterId, () => fetchAll())
</script>

<style scoped>
.page-container { max-width: 1400px; margin: 0 auto; }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.page-title { font-size: 24px; font-weight: 700; color: var(--text-heading); margin: 0; }
.page-desc { font-size: 14px; color: var(--text-muted); margin: 4px 0 0; }
.stats-row { display: flex; gap: 16px; margin-bottom: 16px; }
.stat-card { flex: 1; }
.stat-card .el-card__body { padding: 20px 24px; display: flex; flex-direction: column; gap: 4px; }
.stat-label { font-size: 13px; color: var(--text-muted); }
.stat-value { font-size: 28px; font-weight: 700; color: var(--text-heading); }
.status-bar { margin-bottom: 16px; }
.status-bar-body { display: flex; gap: 24px; align-items: center; padding: 12px 24px; }
.status-item { display: flex; align-items: center; gap: 6px; font-size: 14px; color: var(--text-primary); }
.status-dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
.dot-on { background: #67c23a; box-shadow: 0 0 6px #67c23a80; }
.dot-off { background: #909399; }
.table-card { margin-top: 0; }
.tab-toolbar { display: flex; gap: 12px; margin-bottom: 16px; align-items: center; }
.text-muted { color: var(--text-muted); }
.group-block { margin-bottom: 24px; }
.group-header { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
.group-cluster { font-size: 13px; color: var(--text-muted); }
.group-comment { font-size: 13px; color: var(--text-muted); font-style: italic; }
code { font-family: 'SF Mono', 'Monaco', 'Consolas', monospace; font-size: 13px; }
</style>
