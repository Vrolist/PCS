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

    <!-- 主 Tab 区域 -->
    <el-card shadow="hover" class="table-card">
      <el-tabs v-model="mainTab" @tab-change="onMainTabChange">
        <el-tab-pane :label="t('advanced.firewall.clusterRules')" name="cluster" />
        <el-tab-pane :label="t('advanced.firewall.nodeRules')" name="node" />
        <el-tab-pane :label="t('advanced.firewall.vmCtRules')" name="vm_ct" />
        <el-tab-pane :label="t('advanced.firewall.securityGroups')" name="groups" />
        <el-tab-pane :label="t('advanced.firewall.ipsets')" name="ipsets" />
        <el-tab-pane :label="t('advanced.firewall.aliases')" name="aliases" />
        <el-tab-pane :label="t('advanced.firewall.options')" name="options" />
      </el-tabs>

      <!-- ==================== 规则内容（集群/节点/VM&CT 共用） ==================== -->
      <div v-if="isRuleTab">
        <!-- 方向子 Tab -->
        <el-tabs v-model="dirTab" type="card" class="dir-tabs" @tab-change="onDirTabChange">
          <el-tab-pane :label="t('advanced.firewall.dirAll')" name="all" />
          <el-tab-pane name="in">
            <template #label>
              <span class="dir-label dir-in">IN</span>
            </template>
          </el-tab-pane>
          <el-tab-pane name="out">
            <template #label>
              <span class="dir-label dir-out">OUT</span>
            </template>
          </el-tab-pane>
          <el-tab-pane name="forward">
            <template #label>
              <span class="dir-label dir-forward">FWD</span>
            </template>
          </el-tab-pane>
        </el-tabs>

        <!-- 端口矩阵热力图 -->
        <div v-if="portMatrixData.length > 0" class="port-matrix-section">
          <div class="port-matrix-header">
            <span class="port-matrix-title">{{ t('advanced.firewall.portMatrix') }}</span>
            <div class="port-matrix-legend">
              <span class="legend-item"><span class="legend-dot legend-accept"></span>ACCEPT</span>
              <span class="legend-item"><span class="legend-dot legend-drop"></span>DROP</span>
              <span class="legend-item"><span class="legend-dot legend-reject"></span>REJECT</span>
            </div>
          </div>
          <div class="port-matrix-wrap">
            <v-chart :option="portMatrixOption" autoresize class="port-matrix-chart" />
          </div>
        </div>

        <!-- 搜索栏 -->
        <div class="tab-toolbar">
          <el-input v-model="ruleSearch" :placeholder="t('advanced.firewall.searchPlaceholder')"
            clearable style="width: 300px">
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
        </div>

        <!-- 规则表格 -->
        <el-table :data="pagedRules" stripe style="width: 100%" v-loading="loading" :empty-text="t('advanced.firewall.noRules')">
          <el-table-column prop="pos" label="#" width="60" align="center" />
          <el-table-column v-if="dirTab === 'all'" prop="direction" :label="t('advanced.firewall.direction')" width="90" align="center">
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
              <span>{{ row.proto || 'any' }}</span>
            </template>
          </el-table-column>
          <el-table-column :label="t('advanced.firewall.port')" width="130">
            <template #default="{ row }">
              <span v-if="row.dport" class="port-tag">{{ row.dport }}</span>
              <span v-else class="text-muted">any</span>
              <span v-if="row.sport" class="text-muted sport-hint"> (src:{{ row.sport }})</span>
            </template>
          </el-table-column>
          <el-table-column prop="source" :label="t('advanced.firewall.source')" min-width="140">
            <template #default="{ row }">
              <span>{{ row.source || 'any' }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="dest" :label="t('advanced.firewall.dest')" min-width="140">
            <template #default="{ row }">
              <span>{{ row.dest || 'any' }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="macro" :label="t('advanced.firewall.macro')" width="100">
            <template #default="{ row }">
              <el-tag v-if="row.macro" size="small" effect="plain">{{ row.macro }}</el-tag>
              <span v-else class="text-muted">-</span>
            </template>
          </el-table-column>
          <el-table-column prop="enabled" :label="t('advanced.firewall.enabledLabel')" width="80" align="center">
            <template #default="{ row }">
              <el-tag size="small" :type="row.enabled ? 'success' : 'info'">{{ row.enabled ? 'ON' : 'OFF' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="comment" :label="t('advanced.firewall.comment')" min-width="160" show-overflow-tooltip />
        </el-table>

        <!-- 分页 -->
        <div v-if="filteredRules.length > pageSize" class="pagination-wrap">
          <el-pagination layout="total, prev, pager, next" :total="filteredRules.length"
            v-model:current-page="currentPage" :page-size="pageSize" />
        </div>
      </div>

      <!-- ==================== 安全组 ==================== -->
      <div v-if="mainTab === 'groups'">
        <el-empty v-if="!loading && securityGroups.length === 0" :description="t('advanced.firewall.noGroups')" />
        <div v-for="group in securityGroups" :key="group.name" class="group-block">
          <div class="group-header">
            <el-tag effect="dark" type="warning">{{ group.name }}</el-tag>
            <span class="group-cluster">{{ group.cluster_name }}</span>
          </div>
          <el-table :data="group.rules" stripe size="small" style="width: 100%">
            <el-table-column prop="pos" label="#" width="60" align="center" />
            <el-table-column prop="direction" :label="t('advanced.firewall.direction')" width="90" align="center">
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
            <el-table-column :label="t('advanced.firewall.port')" width="130">
              <template #default="{ row }">
                <span v-if="row.dport" class="port-tag">{{ row.dport }}</span>
                <span v-else class="text-muted">any</span>
              </template>
            </el-table-column>
            <el-table-column prop="source" :label="t('advanced.firewall.source')" min-width="130">
              <template #default="{ row }">{{ row.source || 'any' }}</template>
            </el-table-column>
            <el-table-column prop="dest" :label="t('advanced.firewall.dest')" min-width="130">
              <template #default="{ row }">{{ row.dest || 'any' }}</template>
            </el-table-column>
            <el-table-column prop="comment" :label="t('advanced.firewall.comment')" min-width="160" show-overflow-tooltip />
            <el-table-column prop="enabled" :label="t('advanced.firewall.enabledLabel')" width="80" align="center">
              <template #default="{ row }">
                <el-tag size="small" :type="row.enabled ? 'success' : 'info'">{{ row.enabled ? 'ON' : 'OFF' }}</el-tag>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>

      <!-- ==================== IPSet ==================== -->
      <div v-if="mainTab === 'ipsets'">
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
      </div>

      <!-- ==================== 别名 ==================== -->
      <div v-if="mainTab === 'aliases'">
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
      </div>

      <!-- ==================== 防火墙选项 ==================== -->
      <div v-if="mainTab === 'options'">
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
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useClusterStore } from '@/stores/cluster'
import { useThemeStore } from '@/stores/theme'
import { Search } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import VChart from 'vue-echarts'
import {
  getFirewallSummary, getFirewallRules, getFirewallIPSets,
  getFirewallAliases, getFirewallOptions, getFirewallSecurityGroups,
  type FirewallSummary, type FirewallRule, type FirewallIPSet,
  type FirewallAlias, type FirewallOptions, type SecurityGroup,
} from '@/api/firewall'

const { t } = useI18n()
const clusterStore = useClusterStore()
const themeStore = useThemeStore()

const loading = ref(false)
const mainTab = ref('cluster')
const dirTab = ref('all')

const summary = ref<FirewallSummary>({
  cluster_enabled: false, policy_in: 'ACCEPT', policy_out: 'ACCEPT', policy_forward: 'ACCEPT',
  total_rules: 0, total_security_groups: 0, total_ipsets: 0, total_aliases: 0,
  cluster_rules: 0, node_rules: 0, vm_rules: 0, ct_rules: 0, group_rules: 0, scanned_at: null,
})

// 所有规则（一次加载，客户端筛选）
const allRules = ref<FirewallRule[]>([])
const securityGroups = ref<SecurityGroup[]>([])
const ipsets = ref<FirewallIPSet[]>([])
const aliases = ref<FirewallAlias[]>([])
const optionsList = ref<FirewallOptions[]>([])

const ruleSearch = ref('')
const currentPage = ref(1)
const pageSize = 20

const isRuleTab = computed(() => ['cluster', 'node', 'vm_ct'].includes(mainTab.value))

// ========== 规则筛选 ==========

const scopeFilteredRules = computed(() => {
  const scope = mainTab.value
  return allRules.value.filter(r => {
    if (scope === 'cluster') return r.scope === 'cluster'
    if (scope === 'node') return r.scope === 'node'
    if (scope === 'vm_ct') return r.scope === 'vm' || r.scope === 'ct'
    return false
  })
})

const filteredRules = computed(() => {
  let rules = scopeFilteredRules.value
  // 方向筛选
  if (dirTab.value !== 'all') {
    rules = rules.filter(r => r.direction === dirTab.value)
  }
  // 搜索筛选
  const q = ruleSearch.value.toLowerCase().trim()
  if (q) {
    rules = rules.filter(r =>
      (r.source || '').toLowerCase().includes(q) ||
      (r.dest || '').toLowerCase().includes(q) ||
      (r.dport || '').toLowerCase().includes(q) ||
      (r.comment || '').toLowerCase().includes(q) ||
      (r.proto || '').toLowerCase().includes(q) ||
      (r.action || '').toLowerCase().includes(q)
    )
  }
  return rules
})

const pagedRules = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return filteredRules.value.slice(start, start + pageSize)
})

// 搜索时重置分页
watch(ruleSearch, () => { currentPage.value = 1 })
watch(dirTab, () => { currentPage.value = 1 })

// ========== 端口矩阵热力图 ==========

const portMatrixData = computed(() => {
  const rules = scopeFilteredRules.value
  if (rules.length === 0) return []
  return rules
})

const portMatrixOption = computed(() => {
  const rules = scopeFilteredRules.value
  if (rules.length === 0) return {}

  // 提取所有端口（去重排序）
  const portSet = new Set<string>()
  rules.forEach(r => {
    portSet.add(r.dport || 'any')
  })
  const ports = Array.from(portSet).sort((a, b) => {
    if (a === 'any') return 1
    if (b === 'any') return -1
    const na = parseInt(a), nb = parseInt(b)
    if (!isNaN(na) && !isNaN(nb)) return na - nb
    return a.localeCompare(b)
  })

  const dirs = ['in', 'out', 'forward']
  const dirLabels = ['IN', 'OUT', 'FWD']

  // 构建数据: [dirIndex, portIndex, actionValue]
  // actionValue: 0=ACCEPT, 1=DROP, 2=REJECT
  const actionMap: Record<string, number> = { 'ACCEPT': 0, 'DROP': 1, 'REJECT': 2 }
  const data: [number, number, number, string][] = [] // [x, y, value, action]

  ports.forEach((port, pi) => {
    dirs.forEach((dir, di) => {
      const matchRules = rules.filter(r => {
        return (r.dport || 'any') === port && r.direction === dir
      })
      if (matchRules.length > 0) {
        // 取第一条规则的动作
        const action = matchRules[0].action
        data.push([di, pi, actionMap[action] ?? 0, action])
      }
    })
  })

  const isDark = themeStore.isDark
  const textColor = isDark ? '#c0c4cc' : '#606266'

  return {
    tooltip: {
      formatter(params: any) {
        const [x, y, , action] = params.data
        return `${dirLabels[x]} · ${ports[y]}<br/><strong>${action}</strong>`
      }
    },
    grid: { left: 80, right: 20, top: 10, bottom: 30 },
    xAxis: {
      type: 'category',
      data: dirLabels,
      axisLine: { lineStyle: { color: isDark ? '#4c4d4f' : '#dcdfe6' } },
      axisLabel: { color: textColor, fontSize: 12, fontWeight: 600 },
      splitArea: { show: true, areaStyle: { color: ['transparent'] } }
    },
    yAxis: {
      type: 'category',
      data: ports,
      axisLine: { lineStyle: { color: isDark ? '#4c4d4f' : '#dcdfe6' } },
      axisLabel: { color: textColor, fontSize: 11, fontFamily: 'SF Mono, Monaco, Consolas, monospace' }
    },
    visualMap: {
      show: false,
      type: 'piecewise',
      pieces: [
        { value: 0, color: '#67c23a', label: 'ACCEPT' },
        { value: 1, color: '#f56c6c', label: 'DROP' },
        { value: 2, color: '#e6a23c', label: 'REJECT' },
      ],
      outOfRange: { color: isDark ? '#2a2b2d' : '#f5f7fa' }
    },
    series: [{
      type: 'heatmap',
      data: data.map(d => [d[0], d[1], d[2]]),
      label: {
        show: true,
        formatter(params: any) {
          return data[params.dataIndex]?.[3] || ''
        },
        fontSize: 10,
        color: '#fff',
        fontWeight: 600,
      },
      itemStyle: {
        borderColor: isDark ? '#1d1e1f' : '#fff',
        borderWidth: 2,
        borderRadius: 4,
      },
      emphasis: {
        itemStyle: { shadowBlur: 8, shadowColor: 'rgba(0,0,0,0.3)' }
      }
    }]
  }
})

// ========== 工具函数 ==========

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

// ========== 数据加载 ==========

async function fetchSummary() {
  try { summary.value = await getFirewallSummary(params()) } catch { /* ignore */ }
}

async function fetchAllRules() {
  try { allRules.value = await getFirewallRules(params()) } catch { /* ignore */ }
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

// 规则 Tab 切换时，重置方向为"全部"
function onMainTabChange(tab: string | number) {
  dirTab.value = 'all'
  ruleSearch.value = ''
  currentPage.value = 1
  loadTabData(tab as string)
}

function onDirTabChange() {
  currentPage.value = 1
}

async function loadTabData(tab: string) {
  loading.value = true
  try {
    if (['cluster', 'node', 'vm_ct'].includes(tab)) {
      await fetchAllRules()
    } else if (tab === 'groups') {
      await fetchGroups()
    } else if (tab === 'ipsets') {
      await fetchIPSets()
    } else if (tab === 'aliases') {
      await fetchAliases()
    } else if (tab === 'options') {
      await fetchOptions()
    }
  } finally {
    loading.value = false
  }
}

async function fetchAll() {
  loading.value = true
  try {
    await Promise.all([fetchSummary(), fetchAllRules()])
    await loadTabData(mainTab.value)
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

/* 方向子 Tab */
.dir-tabs { margin-bottom: 16px; }
.dir-tabs :deep(.el-tabs__header) { margin-bottom: 0; }
.dir-label { font-weight: 600; font-size: 12px; }
.dir-in { color: #409eff; }
.dir-out { color: #e6a23c; }
.dir-forward { color: #909399; }

/* 端口标签 */
.port-tag {
  display: inline-block;
  padding: 1px 8px;
  border-radius: 3px;
  background: var(--el-fill-color-light);
  font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
  font-size: 12px;
  color: var(--text-heading);
}
.sport-hint { font-size: 11px; margin-left: 2px; }

/* 端口矩阵热力图 */
.port-matrix-section {
  margin-bottom: 16px;
  padding: 16px;
  border-radius: 8px;
  background: var(--el-fill-color-blank);
  border: 1px solid var(--el-border-color-lighter);
}
.port-matrix-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.port-matrix-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-heading);
}
.port-matrix-legend { display: flex; gap: 16px; }
.legend-item { display: flex; align-items: center; gap: 4px; font-size: 12px; color: var(--text-muted); }
.legend-dot { width: 10px; height: 10px; border-radius: 2px; display: inline-block; }
.legend-accept { background: #67c23a; }
.legend-drop { background: #f56c6c; }
.legend-reject { background: #e6a23c; }
.port-matrix-wrap { width: 100%; }
.port-matrix-chart { width: 100%; height: 180px; min-height: 120px; }

/* 分页 */
.pagination-wrap { display: flex; justify-content: flex-end; margin-top: 16px; }
</style>
