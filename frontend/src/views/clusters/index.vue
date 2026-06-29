<template>
  <div class="clusters-page">
    <div class="page-header">
      <h2 class="page-title">集群管理</h2>
      <el-button type="primary" @click="showCreate = true">新建集群</el-button>
    </div>

    <!-- 加载中 -->
    <el-card v-if="loading" shadow="hover">
      <div style="text-align: center; padding: 40px">
        <el-icon class="is-loading" :size="24"><Loading /></el-icon>
        <p style="margin-top: 8px; color: var(--text-secondary)">加载中...</p>
      </div>
    </el-card>

    <!-- 空状态 -->
    <el-card v-else-if="clusters.length === 0" shadow="hover">
      <el-empty description="暂无集群，点击上方按钮创建">
        <el-button type="primary" @click="showCreate = true">新建集群</el-button>
      </el-empty>
    </el-card>

    <!-- 集群列表 -->
    <div v-else class="cluster-list">
      <el-card v-for="cluster in clusters" :key="cluster.id" shadow="hover" class="cluster-card">
        <div class="cluster-header">
          <div class="cluster-info">
            <h3 class="cluster-name">{{ cluster.name }}</h3>
            <el-tag :type="statusType(cluster.status)" size="small">{{ statusLabel(cluster.status) }}</el-tag>
          </div>
          <div class="cluster-actions">
            <el-button text @click="viewDetail(cluster)">
              <el-icon><View /></el-icon> 详情
            </el-button>
            <el-button text type="danger" @click="confirmDelete(cluster)">
              <el-icon><Delete /></el-icon> 删除
            </el-button>
          </div>
        </div>

        <p v-if="cluster.description" class="cluster-desc">{{ cluster.description }}</p>

        <div class="cluster-stats">
          <div class="stat-item">
            <span class="stat-value">{{ cluster.total_nodes }}</span>
            <span class="stat-label">节点</span>
          </div>
          <div class="stat-item">
            <span class="stat-value">{{ cluster.total_vms }}</span>
            <span class="stat-label">虚拟机</span>
          </div>
          <div class="stat-item">
            <span class="stat-value">{{ cluster.total_lxc }}</span>
            <span class="stat-label">容器</span>
          </div>
          <div class="stat-item">
            <span class="stat-value">{{ cluster.total_storage }}</span>
            <span class="stat-label">存储</span>
          </div>
          <div class="stat-item">
            <span class="stat-value" :class="{ 'text-success': cluster.online_agents > 0 }">
              {{ cluster.online_agents }}/{{ cluster.agent_count }}
            </span>
            <span class="stat-label">Agent</span>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 新建集群弹窗 -->
    <el-dialog v-model="showCreate" title="新建集群" width="480px" :close-on-click-modal="false">
      <el-form ref="createFormRef" :model="createForm" :rules="createRules" label-width="80px">
        <el-form-item label="集群名称" prop="name">
          <el-input v-model="createForm.name" placeholder="如：生产环境集群" maxlength="128" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="createForm.description" type="textarea" :rows="3" placeholder="可选描述" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreate">创建</el-button>
      </template>
    </el-dialog>

    <!-- 集群详情弹窗 -->
    <el-dialog v-model="showDetail" :title="detail?.name || '集群详情'" width="720px">
      <template v-if="detail">
        <div class="detail-section">
          <h4>基本信息</h4>
          <div class="detail-grid">
            <div class="detail-item">
              <span class="detail-label">状态</span>
              <el-tag :type="statusType(detail.status)" size="small">{{ statusLabel(detail.status) }}</el-tag>
            </div>
            <div class="detail-item">
              <span class="detail-label">PVE 版本</span>
              <span>{{ detail.pve_version || '未知' }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">最后扫描</span>
              <span>{{ detail.last_scanned_at ? formatTime(detail.last_scanned_at) : '未扫描' }}</span>
            </div>
          </div>
        </div>

        <div class="detail-section">
          <h4>一键安装命令</h4>
          <div class="install-cmd-box">
            <code>{{ detail.install_command }}</code>
            <el-button class="copy-btn" size="small" @click="copyCommand(detail.install_command)">
              <el-icon><CopyDocument /></el-icon> 复制
            </el-button>
          </div>
          <p class="install-hint">在 PVE 节点上执行此命令即可自动安装 Agent</p>
        </div>

        <div class="detail-section">
          <h4>Agent 列表 ({{ detail.agents.length }})</h4>
          <el-table v-if="detail.agents.length > 0" :data="detail.agents" size="small" stripe>
            <el-table-column prop="hostname" label="主机名" width="120" />
            <el-table-column prop="agent_id" label="Agent ID" width="160">
              <template #default="{ row }">
                <code style="font-size: 12px">{{ row.agent_id.slice(0, 12) }}...</code>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="agentStatusType(row.status)" size="small">{{ agentStatusLabel(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="version" label="版本" width="80" />
            <el-table-column prop="total_scans" label="扫描次数" width="90" />
            <el-table-column label="最后心跳" min-width="140">
              <template #default="{ row }">
                {{ row.last_heartbeat_at ? formatTime(row.last_heartbeat_at) : '从未' }}
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-else description="暂无 Agent，请执行上方安装命令" :image-size="60" />
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance } from 'element-plus'
import { Loading, View, Delete, CopyDocument } from '@element-plus/icons-vue'
import { getClusters, getCluster, createCluster, deleteCluster } from '@/api/clusters'
import type { Cluster, ClusterDetail } from '@/api/clusters'

const loading = ref(true)
const clusters = ref<Cluster[]>([])
const showCreate = ref(false)
const creating = ref(false)
const showDetail = ref(false)
const detail = ref<ClusterDetail | null>(null)
const createFormRef = ref<FormInstance>()

const createForm = ref({ name: '', description: '' })
const createRules = {
  name: [{ required: true, message: '请输入集群名称', trigger: 'blur' }],
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
    ElMessage.success('集群创建成功')
    showCreate.value = false
    createForm.value = { name: '', description: '' }
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
  } catch {
    // error handled by interceptor
  }
}

async function confirmDelete(cluster: Cluster) {
  try {
    await ElMessageBox.confirm(
      `确定删除集群「${cluster.name}」？此操作不可恢复。`,
      '确认删除',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
    await deleteCluster(cluster.id)
    ElMessage.success('已删除')
    await loadClusters()
  } catch {
    // user cancelled or error
  }
}

function copyCommand(cmd: string) {
  navigator.clipboard.writeText(cmd).then(() => {
    ElMessage.success('已复制到剪贴板')
  })
}

function formatTime(iso: string) {
  const d = new Date(iso)
  const now = new Date()
  const diff = (now.getTime() - d.getTime()) / 1000
  if (diff < 60) return '刚刚'
  if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`
  if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`
  return d.toLocaleDateString('zh-CN')
}

function statusType(s: string) {
  return s === 'active' ? 'success' : s === 'error' ? 'danger' : 'warning'
}
function statusLabel(s: string) {
  return { active: '活跃', pending: '待激活', error: '错误', archived: '已归档' }[s] || s
}
function agentStatusType(s: string) {
  return s === 'online' ? 'success' : s === 'error' ? 'danger' : 'info'
}
function agentStatusLabel(s: string) {
  return { online: '在线', offline: '离线', error: '错误', paused: '暂停' }[s] || s
}

onMounted(loadClusters)
</script>

<style scoped>
.clusters-page { max-width: 1400px; margin: 0 auto; }
.page-header {
  display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px;
}
.page-title { font-size: 22px; font-weight: 600; color: var(--text-primary, #303133); margin: 0; }

.cluster-list { display: flex; flex-direction: column; gap: 16px; }
.cluster-card { transition: transform 0.2s; }
.cluster-card:hover { transform: translateY(-2px); }

.cluster-header { display: flex; align-items: center; justify-content: space-between; }
.cluster-info { display: flex; align-items: center; gap: 12px; }
.cluster-name { font-size: 18px; font-weight: 600; margin: 0; color: var(--text-primary, #303133); }
.cluster-desc { color: var(--text-secondary, #909399); margin: 8px 0 16px; font-size: 14px; }
.cluster-actions { display: flex; gap: 4px; }

.cluster-stats {
  display: flex; gap: 32px; padding: 16px 0 0; border-top: 1px solid var(--border-light, #ebeef5);
}
.stat-item { text-align: center; }
.stat-value { display: block; font-size: 24px; font-weight: 600; color: var(--text-primary, #303133); }
.stat-label { font-size: 12px; color: var(--text-secondary, #909399); }
.text-success { color: #67c23a; }

.detail-section { margin-bottom: 24px; }
.detail-section h4 { font-size: 15px; font-weight: 600; margin: 0 0 12px; color: var(--text-primary, #303133); }
.detail-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.detail-item { display: flex; flex-direction: column; gap: 4px; }
.detail-label { font-size: 12px; color: var(--text-secondary, #909399); }

.install-cmd-box {
  position: relative; background: #1e1e1e; border-radius: 8px; padding: 14px 16px;
  overflow-x: auto;
}
.install-cmd-box code {
  font-family: 'SF Mono', 'Fira Code', monospace; font-size: 13px;
  color: #d4d4d4; white-space: pre-wrap; word-break: break-all;
}
.copy-btn { position: absolute; top: 8px; right: 8px; }
.install-hint { font-size: 12px; color: var(--text-secondary, #909399); margin-top: 8px; }
</style>
