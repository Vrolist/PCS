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

    <!-- 集群卡片网格 -->
    <div v-else class="cluster-grid">
      <div v-for="cluster in clusters" :key="cluster.id" class="cc" @click="viewDetail(cluster)">
        <!-- 顶部：状态指示 + 名称 + 菜单 -->
        <div class="cc-head">
          <div class="cc-status-dot" :class="'cc-dot--' + cluster.status"></div>
          <h3 class="cc-name">{{ cluster.name }}</h3>
          <el-dropdown trigger="click" :teleported="true" @command="(cmd: string) => handleCardCommand(cmd, cluster)" @click.stop>
            <button class="cc-menu" @click.stop>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="5" r="2"/><circle cx="12" cy="12" r="2"/><circle cx="12" cy="19" r="2"/></svg>
            </button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="detail"><el-icon><View /></el-icon>{{ t('common.detail') }}</el-dropdown-item>
                <template v-if="cluster.is_active">
                  <el-dropdown-item command="stop" divided><el-icon><VideoPause /></el-icon>{{ t('clusters.stop') }}</el-dropdown-item>
                </template>
                <template v-else>
                  <el-dropdown-item command="restore" divided><el-icon><CircleCheck /></el-icon>{{ t('clusters.restore') }}</el-dropdown-item>
                  <el-dropdown-item command="delete"><el-icon><Delete /></el-icon>{{ t('clusters.delete') }}</el-dropdown-item>
                </template>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>

        <!-- 核心指标：一行 4 个 -->
        <div class="cc-metrics">
          <div class="cc-metric">
            <span class="cc-metric-val">{{ cluster.total_nodes }}</span>
            <span class="cc-metric-lbl">节点</span>
          </div>
          <div class="cc-metric">
            <span class="cc-metric-val">{{ cluster.total_vms + cluster.total_lxc }}</span>
            <span class="cc-metric-lbl">实例</span>
          </div>
          <div class="cc-metric">
            <span class="cc-metric-val">{{ cluster.total_storage }}</span>
            <span class="cc-metric-lbl">存储</span>
          </div>
          <div class="cc-metric">
            <span class="cc-metric-val" :class="{ 'cc-g': cluster.online_agents > 0 }">{{ cluster.online_agents }}<span class="cc-metric-of">/{{ cluster.agent_count }}</span></span>
            <span class="cc-metric-lbl">Agent</span>
          </div>
        </div>

        <!-- 底部 -->
        <div class="cc-foot">
          <span class="cc-foot-tag" v-if="cluster.pve_version">PVE {{ cluster.pve_version }}</span>
          <span class="cc-foot-time">
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>
            {{ cluster.last_scanned_at ? formatTime(cluster.last_scanned_at) : t('clusters.notScanned') }}
          </span>
          <span v-if="cluster.sync_enabled" class="cc-foot-sync">同步</span>
        </div>
      </div>
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

          <!-- 数据同步 Tab -->
          <el-tab-pane label="数据同步" name="sync">
            <div class="detail-section">
              <div class="sync-config">
                <div class="sync-header">
                  <div class="sync-status-row">
                    <span class="sync-label">同步状态</span>
                    <el-tag :type="detail.sync_enabled ? 'success' : 'info'" size="small" effect="light">
                      {{ detail.sync_enabled ? '已启用' : '未启用' }}
                    </el-tag>
                    <span v-if="detail.last_synced_at" class="sync-time">
                      最近同步: {{ formatTime(detail.last_synced_at) }}
                    </span>
                  </div>
                  <el-switch
                    v-model="syncForm.sync_enabled"
                    active-text="启用"
                    inactive-text="关闭"
                    @change="handleSyncToggle"
                  />
                </div>

                <el-divider />

                <el-form label-width="120px" :disabled="!syncForm.sync_enabled">
                  <el-form-item label="PCSS 平台地址">
                    <el-input
                      v-model="syncForm.sync_url"
                      placeholder="如 https://pcss.example.com:8099"
                      @change="handleSyncFieldChange"
                    />
                    <div class="form-tip">PCSS 云平台的访问地址，需包含协议和端口</div>
                  </el-form-item>
                  <el-form-item label="同步 ID">
                    <el-input
                      v-model="syncForm.sync_id"
                      placeholder="PCSS 分配的集群同步标识"
                      @change="handleSyncFieldChange"
                    />
                    <div class="form-tip">在 PCSS 创建集群时生成的同步 ID</div>
                  </el-form-item>
                  <el-form-item label="同步 Token">
                    <el-input
                      v-model="syncForm.sync_token"
                      placeholder="PCSS 分配的同步认证令牌"
                      show-password
                      @change="handleSyncFieldChange"
                    />
                    <div class="form-tip">在 PCSS 创建集群时生成的同步 Token</div>
                  </el-form-item>
                </el-form>

                <div class="sync-actions" v-if="syncForm.sync_enabled">
                  <el-button type="primary" :loading="syncing" @click="handleManualSync(false)">
                    <el-icon><Upload /></el-icon>
                    立即同步
                  </el-button>
                  <el-button :loading="syncing" @click="handleManualSync(true)">
                    <el-icon><RefreshRight /></el-icon>
                    全量同步
                  </el-button>
                </div>

                <div class="sync-tip" v-if="syncForm.sync_enabled">
                  <el-icon><InfoFilled /></el-icon>
                  <span>启用同步后，每次 Agent 扫描完成会自动将数据推送到 PCSS。全量同步会推送所有历史数据。</span>
                </div>
              </div>
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
import { Loading, View, Delete, CopyDocument, VideoPause, CircleCheck, CircleCheckFilled, Upload, RefreshRight, InfoFilled } from '@element-plus/icons-vue'
import { getClusters, getCluster, createCluster, updateCluster, deleteCluster, getLatestAgentVersion, triggerSync } from '@/api/clusters'
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

// 同步相关状态
const syncing = ref(false)
const syncForm = ref({ sync_enabled: false, sync_url: '', sync_id: '', sync_token: '' })

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
    // 填充同步表单
    syncForm.value = {
      sync_enabled: detail.value.sync_enabled,
      sync_url: detail.value.sync_url || '',
      sync_id: detail.value.sync_id || '',
      sync_token: detail.value.sync_token || '',
    }
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

function handleCardCommand(cmd: string, cluster: Cluster) {
  if (cmd === 'detail') viewDetail(cluster)
  else if (cmd === 'stop') handleToggleActive(cluster, false)
  else if (cmd === 'restore') handleToggleActive(cluster, true)
  else if (cmd === 'delete') confirmDelete(cluster)
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

async function handleSyncToggle(val: boolean) {
  if (!detail.value) return
  // 如果启用同步但没有填写 URL，提示用户
  if (val && !syncForm.value.sync_url) {
    ElMessage.warning('请先填写 PCSS 平台地址')
    syncForm.value.sync_enabled = false
    return
  }
  try {
    await updateCluster(detail.value.id, {
      sync_enabled: val,
      sync_url: syncForm.value.sync_url,
      sync_id: syncForm.value.sync_id,
      sync_token: syncForm.value.sync_token,
    } as any)
    detail.value.sync_enabled = val
    ElMessage.success(val ? '同步已启用' : '同步已关闭')
    await loadClusters()
  } catch {
    syncForm.value.sync_enabled = !val
  }
}

async function handleSyncFieldChange() {
  if (!detail.value || !syncForm.value.sync_enabled) return
  try {
    await updateCluster(detail.value.id, {
      sync_url: syncForm.value.sync_url,
      sync_id: syncForm.value.sync_id,
      sync_token: syncForm.value.sync_token,
    } as any)
    ElMessage.success('同步配置已保存')
  } catch {
    // error handled by interceptor
  }
}

async function handleManualSync(forceFull: boolean) {
  if (!detail.value) return
  if (!syncForm.value.sync_url || !syncForm.value.sync_id || !syncForm.value.sync_token) {
    ElMessage.warning('请先完整填写同步配置（URL、同步 ID、同步 Token）')
    return
  }
  syncing.value = true
  try {
    const res = await triggerSync(detail.value.id, forceFull)
    ElMessage.success(res.message || '同步成功')
    // 刷新详情
    detail.value = await getCluster(detail.value.id)
    syncForm.value.sync_enabled = detail.value.sync_enabled
    await loadClusters()
  } catch {
    // error handled by interceptor
  } finally {
    syncing.value = false
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

/* ── 卡片网格 ── */
.cluster-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

/* ── 卡片 ── */
.cc {
  background: var(--el-bg-color, #fff);
  border: 1px solid var(--border-light, #e4e7ed);
  border-radius: 12px;
  cursor: pointer;
  display: flex; flex-direction: column;
  transition: all 0.25s ease;
  overflow: hidden;
}
.cc:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px -8px rgba(0,0,0,0.12);
  border-color: #c0c4cc;
}

/* ── 头部 ── */
.cc-head {
  display: flex; align-items: center; gap: 10px;
  padding: 18px 18px 0;
}
.cc-status-dot {
  width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0;
}
.cc-dot--active  { background: #67c23a; box-shadow: 0 0 0 3px #67c23a20; }
.cc-dot--error   { background: #f56c6c; box-shadow: 0 0 0 3px #f56c6c20; }
.cc-dot--pending { background: #e6a23c; box-shadow: 0 0 0 3px #e6a23c20; }
.cc-dot--archived { background: #909399; }

.cc-name {
  flex: 1; min-width: 0; margin: 0;
  font-size: 15px; font-weight: 600;
  color: var(--text-primary, #303133);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.cc-menu {
  flex-shrink: 0; width: 28px; height: 28px; border-radius: 6px;
  border: none; background: transparent; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  color: var(--text-placeholder, #c0c4cc);
  transition: all 0.15s;
}
.cc-menu:hover { background: var(--el-fill-color-light, #f5f7fa); color: var(--text-secondary, #909399); }

/* ── 指标行 ── */
.cc-metrics {
  display: flex; gap: 0; padding: 18px 18px 0;
}
.cc-metric {
  flex: 1; text-align: center;
}
.cc-metric + .cc-metric { border-left: 1px solid var(--border-light, #ebeef5); }
.cc-metric-val {
  display: block; font-size: 20px; font-weight: 700; line-height: 1;
  color: var(--text-primary, #303133);
  font-variant-numeric: tabular-nums;
}
.cc-metric-of { font-size: 13px; font-weight: 400; color: var(--text-secondary, #909399); }
.cc-metric-lbl {
  display: block; margin-top: 4px;
  font-size: 11px; color: var(--text-secondary, #909399);
}
.cc-g { color: #67c23a; }

/* ── 底部 ── */
.cc-foot {
  display: flex; align-items: center; gap: 8px;
  padding: 14px 18px 16px; margin-top: 14px;
  border-top: 1px solid var(--border-light, #ebeef5);
}
.cc-foot-tag {
  font-size: 10px; font-weight: 500;
  color: var(--text-secondary, #909399);
  background: var(--el-fill-color-light, #f5f7fa);
  padding: 2px 8px; border-radius: 4px;
}
.cc-foot-time {
  flex: 1;
  display: inline-flex; align-items: center; gap: 4px;
  font-size: 11px; color: var(--text-placeholder, #c0c4cc);
}
.cc-foot-time svg { opacity: 0.5; }
.cc-foot-sync {
  font-size: 10px; font-weight: 500;
  color: #67c23a; background: #67c23a10;
  padding: 2px 8px; border-radius: 4px;
}

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

/* ── 同步配置 ── */
.meta-chip-sync { color: #67c23a; background: #67c23a15; }
.sync-config { max-width: 600px; }
.sync-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 0;
}
.sync-status-row {
  display: flex; align-items: center; gap: 10px;
}
.sync-label { font-size: 14px; font-weight: 600; color: var(--text-primary, #303133); }
.sync-time { font-size: 12px; color: var(--text-secondary, #909399); }
.sync-actions {
  display: flex; gap: 12px; margin: 20px 0 16px;
}
.sync-tip {
  display: flex; align-items: flex-start; gap: 8px;
  font-size: 12px; color: var(--text-secondary, #909399);
  background: var(--el-fill-color-light, #f5f7fa);
  padding: 10px 14px; border-radius: 8px; line-height: 1.6;
}
.sync-tip .el-icon { margin-top: 2px; flex-shrink: 0; }
.form-tip {
  font-size: 12px; color: var(--text-secondary, #909399); margin-top: 4px; line-height: 1.4;
}

/* ── Footer ── */
:deep(.el-card__body) { padding: 20px 24px; }
</style>
