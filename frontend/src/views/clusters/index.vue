<template>
  <div class="clusters-page">
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ t('clusters.title') }}</h2>
        <p class="page-subtitle">{{ t('clusters.subtitle') }}</p>
      </div>
      <el-button type="primary" size="large" @click="showCreate = true">{{ t('clusters.createNew') }}</el-button>
    </div>

    <!-- 加载中 -->
    <el-card v-if="loading" shadow="hover">
      <div style="text-align: center; padding: 60px">
        <el-icon class="is-loading" :size="32"><Loading /></el-icon>
        <p style="margin-top: 12px; color: var(--text-secondary)">{{ t('common.loading') }}</p>
      </div>
    </el-card>

    <!-- 空状态 -->
    <el-card v-else-if="clusters.length === 0" shadow="hover">
      <el-empty :description="t('clusters.emptyDesc')">
        <el-button type="primary" @click="showCreate = true">{{ t('clusters.createButton') }}</el-button>
      </el-empty>
    </el-card>

    <!-- 集群列表 -->
    <div v-else class="cluster-list">
      <el-card v-for="cluster in clusters" :key="cluster.id" shadow="hover" class="cluster-card">
        <div class="cluster-card-inner">
          <!-- 顶部：名称 + 状态 + 操作 -->
          <div class="cluster-header">
            <div class="cluster-info">
              <div class="cluster-icon">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M4 4h6v6H4zm10 0h6v6h-6zM4 14h6v6H4zm10 0h6v6h-6z"/></svg>
              </div>
              <div class="cluster-info-body">
                <div class="cluster-name-row">
                  <h3 class="cluster-name">{{ cluster.name }}</h3>
                  <el-tag :type="statusType(cluster.status)" size="small" effect="light">
                    {{ statusLabel(cluster.status) }}
                  </el-tag>
                </div>
                <p v-if="cluster.description" class="cluster-desc">{{ cluster.description }}</p>
                <div class="cluster-meta">
                  <span v-if="cluster.pve_version" class="meta-chip">
                    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>
                    {{ cluster.pve_version }}
                  </span>
                  <span class="meta-chip">
                    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4"/><path d="M8 2v4"/><path d="M3 10h18"/></svg>
                    {{ cluster.last_scanned_at ? formatTime(cluster.last_scanned_at) : t('clusters.notScanned') }}
                  </span>
                </div>
              </div>
            </div>
            <div class="cluster-actions">
              <el-button size="default" plain @click="viewDetail(cluster)">
                <el-icon><View /></el-icon>
                {{ t('common.detail') }}
              </el-button>
              <template v-if="cluster.is_active">
                <el-button size="default" plain type="warning" @click="handleToggleActive(cluster, false)">
                  <el-icon><VideoPause /></el-icon>
                  {{ t('clusters.stop') }}
                </el-button>
              </template>
              <template v-else>
                <el-button size="default" plain type="success" @click="handleToggleActive(cluster, true)">
                  <el-icon><CircleCheck /></el-icon>
                  {{ t('clusters.restore') }}
                </el-button>
                <el-button size="default" plain type="danger" @click="confirmDelete(cluster)">
                  <el-icon><Delete /></el-icon>
                  {{ t('clusters.delete') }}
                </el-button>
              </template>
            </div>
          </div>
          <!-- 统计网格 -->
          <div class="cluster-stats">
            <div class="stat-item" :title="t('clusters.nodesCount')">
              <div class="stat-icon stat-icon-node">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8"/><path d="M12 17v4"/></svg>
              </div>
              <div class="stat-body">
                <span class="stat-value">{{ cluster.total_nodes }}</span>
                <span class="stat-label">{{ t('common.nodes') }}</span>
              </div>
            </div>
            <div class="stat-item" :title="t('clusters.vmsCount')">
              <div class="stat-icon stat-icon-vm">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="4" width="16" height="12" rx="1"/><path d="M9 16v4"/><path d="M15 16v4"/><path d="M7 20h10"/></svg>
              </div>
              <div class="stat-body">
                <span class="stat-value">{{ cluster.total_vms }}</span>
                <span class="stat-label">{{ t('common.vms') }}</span>
              </div>
            </div>
            <div class="stat-item" :title="t('clusters.containersCount')">
              <div class="stat-icon stat-icon-lxc">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 9v11a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V9"/><path d="M22 5H2v3h20V5z"/><path d="M8 14h8"/><path d="M8 18h5"/></svg>
              </div>
              <div class="stat-body">
                <span class="stat-value">{{ cluster.total_lxc }}</span>
                <span class="stat-label">{{ t('common.containers') }}</span>
              </div>
            </div>
            <div class="stat-item" :title="t('clusters.storageCount')">
              <div class="stat-icon stat-icon-storage">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v4c0 1.66 4.03 3 9 3s9-1.34 9-3V5"/><path d="M3 11v4c0 1.66 4.03 3 9 3s9-1.34 9-3v-4"/><path d="M3 17v4c0 1.66 4.03 3 9 3s9-1.34 9-3v-4"/></svg>
              </div>
              <div class="stat-body">
                <span class="stat-value">{{ cluster.total_storage }}</span>
                <span class="stat-label">{{ t('common.storage') }}</span>
              </div>
            </div>
            <div class="stat-item" :title="t('clusters.agentsCount')">
              <div class="stat-icon stat-icon-agent">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="10" r="3"/><path d="M7 20.6V19a3 3 0 0 1 3-3h4a3 3 0 0 1 3 3v1.6"/></svg>
              </div>
              <div class="stat-body">
                <span class="stat-value" :class="{ 'text-success': cluster.online_agents > 0 }">
                  {{ cluster.online_agents }}/{{ cluster.agent_count }}
                </span>
                <span class="stat-label">Agent</span>
              </div>
            </div>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 新建集群弹窗 -->
    <el-dialog v-model="showCreate" :title="t('clusters.createTitle')" width="560px" :close-on-click-modal="false">
      <el-form ref="createFormRef" :model="createForm" :rules="createRules" label-width="120px">
        <el-form-item :label="t('clusters.nameLabel')" prop="name">
          <el-input v-model="createForm.name" :placeholder="t('clusters.clusterNamePlaceholder')" maxlength="128" />
        </el-form-item>
        <el-form-item :label="t('clusters.description')" prop="description">
          <el-input v-model="createForm.description" type="textarea" :rows="2" :placeholder="t('clusters.descPlaceholder')" />
        </el-form-item>
        <el-divider content-position="left">{{ t('clusters.pveConnectionInfo') }}</el-divider>
        <el-form-item :label="t('clusters.apiEndpointLabel')" prop="pve_endpoint">
          <el-input v-model="createForm.pve_endpoint" :placeholder="t('clusters.apiEndpointPlaceholder')" />
        </el-form-item>
        <el-form-item label="PVE API Token" prop="pve_token">
          <el-input v-model="createForm.pve_token" :placeholder="t('clusters.pveTokenPlaceholder')" show-password />
        </el-form-item>
        <p class="form-hint">{{ t('clusters.apiTokenTip') }}</p>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreate">{{ t('clusters.create') }}</el-button>
      </template>
    </el-dialog>

    <!-- 集群详情弹窗 -->
    <el-dialog v-model="showDetail" :title="detail?.name || t('clusters.basicInfo')" width="800px">
      <template v-if="detail">
        <el-tabs v-model="detailTab">
          <!-- 基本信息 Tab -->
          <el-tab-pane :label="t('clusters.basicInfo')" name="info">
            <div class="detail-section">
              <div class="detail-grid">
                <div class="detail-item">
                  <span class="detail-label">{{ t('common.status') }}</span>
                  <el-tag :type="statusType(detail.status)" size="small">{{ statusLabel(detail.status) }}</el-tag>
                </div>
                <div class="detail-item">
                  <span class="detail-label">{{ t('clusters.pveVersion') }}</span>
                  <span>{{ detail.pve_version || t('common.unknown') }}</span>
                </div>
                <div class="detail-item">
                  <span class="detail-label">{{ t('clusters.lastScan') }}</span>
                  <span>{{ detail.last_scanned_at ? formatTime(detail.last_scanned_at) : t('clusters.notScanned') }}</span>
                </div>
                <div class="detail-item">
                  <span class="detail-label">{{ t('common.nodes') }}</span>
                  <span>{{ detail.total_nodes }} {{ t('common.unitTai') }}</span>
                </div>
                <div class="detail-item">
                  <span class="detail-label">{{ t('common.vms') }}</span>
                  <span>{{ detail.total_vms }} {{ t('common.unitTai') }}</span>
                </div>
                <div class="detail-item">
                  <span class="detail-label">{{ t('common.containers') }}</span>
                  <span>{{ detail.total_lxc }} {{ t('common.unitTai') }}</span>
                </div>
                <div class="detail-item" v-if="detail.total_storage">
                  <span class="detail-label">{{ t('common.storage') }}</span>
                  <span>{{ detail.total_storage }} {{ t('common.unitGe') }}</span>
                </div>
                <div class="detail-item" v-if="detail.description">
                  <span class="detail-label">{{ t('clusters.description') }}</span>
                  <span>{{ detail.description }}</span>
                </div>
              </div>
            </div>

            <div class="detail-section">
              <el-collapse>
                <el-collapse-item>
                  <template #title>
                    <div class="install-title-row">
                      <h4>{{ t('clusters.installCommand') }}</h4>
                      <el-button size="small" @click.stop="copyCommand(detail.install_command)">
                        <el-icon><CopyDocument /></el-icon> {{ t('clusters.copy') }}
                      </el-button>
                    </div>
                  </template>
                  <div class="install-cmd-box">
                    <code>{{ detail.install_command }}</code>
                  </div>
                  <p class="install-hint">{{ t('clusters.installTip') }}</p>
                </el-collapse-item>
              </el-collapse>
            </div>
          </el-tab-pane>

          <!-- Agent 列表 Tab -->
          <el-tab-pane :label="t('clusters.agents')" name="agents">
            <div class="detail-section">
              <el-table v-if="detail.agents.length > 0" :data="detail.agents" stripe>
                <el-table-column prop="hostname" :label="t('clusters.hostname')" width="120" />
                <el-table-column prop="agent_id" label="Agent ID" width="160">
                  <template #default="{ row }">
                    <code style="font-size: 12px">{{ row.agent_id.slice(0, 12) }}...</code>
                  </template>
                </el-table-column>
                <el-table-column :label="t('common.status')" width="80">
                  <template #default="{ row }">
                    <el-tag :type="agentStatusType(row.status)" size="small">{{ agentStatusLabel(row.status) }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column :label="t('common.version')" width="110">
                  <template #default="{ row }">
                    <span style="margin-right: 4px">{{ row.version }}</span>
                    <span
                      v-if="latestAgentVersion && compareVersions(row.version, latestAgentVersion) < 0"
                      class="version-tag version-outdated"
                    >{{ t('clusters.updateAvailable') }}</span>
                    <el-icon
                      v-else-if="latestAgentVersion"
                      class="version-check"
                    ><CircleCheckFilled /></el-icon>
                  </template>
                </el-table-column>
                <el-table-column prop="total_scans" :label="t('clusters.scanCount')" width="90" />
                <el-table-column :label="t('clusters.lastHeartbeat')" min-width="140">
                  <template #default="{ row }">
                    {{ row.last_heartbeat_at ? formatTime(row.last_heartbeat_at) : t('clusters.never') }}
                  </template>
                </el-table-column>
              </el-table>
              <el-empty v-else :description="t('clusters.noAgent')" :image-size="60" />
            </div>
          </el-tab-pane>
        </el-tabs>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'

const { t } = useI18n()
import type { FormInstance } from 'element-plus'
import { Loading, View, Delete, CopyDocument, VideoPause, CircleCheck, CircleCheckFilled } from '@element-plus/icons-vue'
import { getClusters, getCluster, createCluster, updateCluster, deleteCluster, getLatestAgentVersion } from '@/api/clusters'
import type { Cluster, ClusterDetail } from '@/api/clusters'

const loading = ref(true)
const clusters = ref<Cluster[]>([])
const showCreate = ref(false)
const creating = ref(false)
const showDetail = ref(false)
const detail = ref<ClusterDetail | null>(null)
const createFormRef = ref<FormInstance>()
const latestAgentVersion = ref('')
const detailTab = ref('info')

function compareVersions(a: string, b: string): number {
  const pa = a.split('.').map(Number)
  const pb = b.split('.').map(Number)
  for (let i = 0; i < Math.max(pa.length, pb.length); i++) {
    const na = pa[i] || 0
    const nb = pb[i] || 0
    if (na !== nb) return na - nb
  }
  return 0
}

async function fetchLatestAgentVersion() {
  try {
    const res = await getLatestAgentVersion()
    latestAgentVersion.value = res.latest_version
  } catch {
    // non-critical, silently ignore
  }
}

const createForm = ref({ name: '', description: '', pve_endpoint: '', pve_token: '' })
const createRules = {
  name: [{ required: true, message: t('clusters.nameRequired'), trigger: 'blur' }],
  pve_endpoint: [{ required: true, message: t('clusters.apiRequired'), trigger: 'blur' }],
  pve_token: [{ required: true, message: t('clusters.tokenRequired'), trigger: 'blur' }],
}

async function loadClusters() {
  loading.value = true
  try {
    const res = await getClusters()
    clusters.value = res.results || []
  } catch {
    // error handled by interceptor
  } finally {
    loading.value = false
  }
}

async function handleCreate() {
  const valid = await createFormRef.value?.validate().catch(() => false)
  if (!valid) return
  creating.value = true
  try {
    await createCluster(createForm.value)
    ElMessage.success(t('clusters.createSuccess'))
    showCreate.value = false
    createForm.value = { name: '', description: '', pve_endpoint: '', pve_token: '' }
    await loadClusters()
  } catch {
    // error handled by interceptor
  } finally {
    creating.value = false
  }
}

async function viewDetail(cluster: Cluster) {
  try {
    detail.value = await getCluster(cluster.id)
    showDetail.value = true
    detailTab.value = 'info'
  } catch {
    // error handled by interceptor
  }
}

async function handleToggleActive(cluster: Cluster, activate: boolean) {
  const label = activate ? t('clusters.confirmRestore') : t('clusters.confirmStop')
  try {
    await ElMessageBox.confirm(
      `${t('clusters.confirmAction', { action: label, name: cluster.name })}${activate ? t('clusters.confirmRestoreHint') : t('clusters.confirmStopHint')}`,
      t('clusters.confirmActionTitle', { action: label }),
      { type: activate ? 'success' : 'warning', confirmButtonText: label, cancelButtonText: t('common.cancel') },
    )
    await updateCluster(cluster.id, { is_active: activate })
    ElMessage.success(t('clusters.actionSuccess', { action: label }))
    await loadClusters()
  } catch {
    // user cancelled or error
  }
}

async function confirmDelete(cluster: Cluster) {
  try {
    await ElMessageBox.confirm(
      t('clusters.confirmDelete', { name: cluster.name }),
      t('clusters.confirmDeleteTitle'),
      { type: 'warning', confirmButtonText: t('clusters.delete'), cancelButtonText: t('common.cancel') },
    )
    // 二次确认
    await ElMessageBox.confirm(
      t('clusters.deleteConfirm', { name: cluster.name }),
      t('clusters.deleteConfirmTitle'),
      {
        type: 'error',
        confirmButtonText: t('clusters.confirmDeleteButton'),
        cancelButtonText: t('common.cancel'),
        inputValue: '',
        inputPlaceholder: `${t('common.name')} ${cluster.name}`,
        inputValidator: (v: string) => v === cluster.name || t('clusters.inputMismatch'),
        inputErrorMessage: t('clusters.nameMismatch'),
      },
    )
    await deleteCluster(cluster.id)
    ElMessage.success(t('clusters.deleted'))
    await loadClusters()
  } catch {
    // user cancelled or error
  }
}

function copyCommand(cmd: string) {
  const ta = document.createElement('textarea')
  ta.value = cmd
  ta.style.cssText = 'position:fixed;left:-9999px;top:-9999px'
  document.body.appendChild(ta)
  ta.focus()
  ta.select()
  try {
    document.execCommand('copy')
    ElMessage.success(t('common.copySuccess'))
  } catch {
    ElMessage.error(t('common.copyFailed'))
  } finally {
    document.body.removeChild(ta)
  }
}

function formatTime(iso: string) {
  const d = new Date(iso)
  const now = new Date()
  const diff = (now.getTime() - d.getTime()) / 1000
  if (diff < 60) return t('common.justNow')
  if (diff < 3600) return `${Math.floor(diff / 60)} ${t('common.minutesAgo')}`
  if (diff < 86400) return `${Math.floor(diff / 3600)} ${t('common.hoursAgo')}`
  return d.toLocaleDateString('zh-CN')
}

function statusType(s: string) {
  return s === 'active' ? 'success' : s === 'error' ? 'danger' : 'warning'
}
function statusLabel(s: string) {
  return { active: t('clusters.active'), pending: t('clusters.pending'), error: t('clusters.error'), archived: t('clusters.archived') }[s] || s
}
function agentStatusType(s: string) {
  return s === 'online' ? 'success' : s === 'error' ? 'danger' : 'info'
}
function agentStatusLabel(s: string) {
  return { online: t('clusters.agentOnline'), offline: t('clusters.agentOffline'), error: t('clusters.error'), paused: t('clusters.agentPaused') }[s] || s
}

onMounted(() => {
  loadClusters()
  fetchLatestAgentVersion()
})
</script>

<style scoped>
.clusters-page { max-width: 1400px; margin: 0 auto; }
.page-header {
  display: flex; align-items: center; justify-content: space-between; margin-bottom: 28px;
}
.page-title { font-size: 24px; font-weight: 700; color: var(--text-primary, #303133); margin: 0; }
.page-subtitle { font-size: 14px; color: var(--text-secondary, #909399); margin: 4px 0 0; }

.cluster-list { display: flex; flex-direction: column; gap: 16px; }
.cluster-card {
  border-radius: 12px;
  overflow: hidden;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  border: 1px solid var(--border-light, #ebeef5);
}
.cluster-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 12px 32px rgba(0,0,0,0.1);
}

.cluster-card-inner { padding: 8px 0; }

/* ── 顶部：图标 + 名称 + 操作 ── */
.cluster-header {
  display: flex; align-items: center; justify-content: space-between; gap: 16px;
}
.cluster-info { display: flex; align-items: center; gap: 14px; flex: 1; min-width: 0; }
.cluster-icon {
  flex-shrink: 0; width: 44px; height: 44px; border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
}
.cluster-icon svg { stroke: #fff; }
.cluster-name-row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.cluster-name {
  font-size: 18px; font-weight: 600; margin: 0;
  color: var(--text-primary, #303133);
}
.cluster-info-body { min-width: 0; }
.cluster-desc {
  color: var(--text-secondary, #909399); margin: 3px 0 6px; font-size: 13px;
  line-height: 1.5; word-break: break-word;
}
.cluster-meta {
  display: flex; gap: 8px; align-items: center; flex-wrap: wrap;
}
.meta-chip {
  display: inline-flex; align-items: center; gap: 4px;
  font-size: 11px; color: var(--text-secondary, #909399);
  background: var(--el-fill-color-light, #f5f7fa);
  padding: 2px 8px; border-radius: 5px;
}
.cluster-actions { display: flex; gap: 4px; flex-shrink: 0; }

/* ── 统计行 ── */
.cluster-stats {
  display: flex; gap: 0; padding: 16px 0 0; margin-top: 14px;
  border-top: 1px solid var(--border-light, #ebeef5);
}
.stat-item {
  display: flex; align-items: center; gap: 10px;
  padding: 0 28px 0 0; flex: 1; position: relative;
}
.stat-item + .stat-item { padding-left: 28px; }
.stat-item + .stat-item::before {
  content: ''; position: absolute; left: 0; top: 50%; transform: translateY(-50%);
  width: 1px; height: 30px; background: var(--border-light, #ebeef5);
}
.stat-icon {
  width: 36px; height: 36px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.stat-icon-node { background: linear-gradient(135deg, #409eff22, #409eff44); color: #409eff; }
.stat-icon-vm { background: linear-gradient(135deg, #67c23a22, #67c23a44); color: #67c23a; }
.stat-icon-lxc { background: linear-gradient(135deg, #e6a23c22, #e6a23c44); color: #e6a23c; }
.stat-icon-storage { background: linear-gradient(135deg, #90939922, #90939944); color: #909399; }
.stat-icon-agent { background: linear-gradient(135deg, #409eff22, #409eff44); color: #409eff; }

.stat-body { display: flex; flex-direction: column; gap: 2px; }
.stat-value { font-size: 20px; font-weight: 700; color: var(--text-primary, #303133); line-height: 1.2; }
.stat-label { font-size: 12px; color: var(--text-secondary, #909399); white-space: nowrap; }
.text-success { color: #67c23a; }

/* ── 详情弹窗 ── */
.detail-section { margin-bottom: 24px; }
.detail-section h4 { font-size: 15px; font-weight: 600; margin: 0 0 12px; color: var(--text-primary, #303133); }
.detail-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px 16px; }
.detail-item { display: flex; flex-direction: column; gap: 4px; }
.detail-label { font-size: 12px; color: var(--text-secondary, #909399); }

/* Agent 版本标签 */
.version-check { color: #67c23a; font-size: 16px; vertical-align: middle; }
.version-tag { font-size: 12px; padding: 1px 6px; border-radius: 4px; vertical-align: middle; }
.version-outdated { color: #e6a23c; background: #faecd8; }

.install-cmd-box {
  position: relative; background: #1e1e1e; border-radius: 8px; padding: 14px 16px;
  overflow-x: auto;
}
.install-cmd-box code {
  font-family: 'SF Mono', 'Fira Code', monospace; font-size: 13px;
  color: #d4d4d4; white-space: pre-wrap; word-break: break-all;
}
.install-title-row { display: flex; align-items: center; justify-content: space-between; }
.install-title-row h4 { margin: 0; font-size: 15px; font-weight: 600; color: var(--text-primary, #303133); }
.install-title-row .el-icon { margin-right: 4px; }
.install-title-row .el-button { margin-right: 4px; }
.install-hint { font-size: 12px; color: var(--text-secondary, #909399); margin-top: 8px; }
.form-hint { font-size: 12px; color: var(--text-secondary, #909399); margin: -8px 0 0 120px; }

/* 版本标签 */
:deep(.el-collapse-item__header) {
  height: 32px;
  line-height: 32px;
  font-size: 13px;
}
:deep(.el-collapse-item__wrap) {
  margin-bottom: 0;
}

/* ── Footer ── */
:deep(.el-card__body) { padding: 20px 24px; }
</style>
