<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">节点管理</h2>
        <p class="page-desc">管理和监控 PVE 集群节点状态</p>
      </div>
      <div class="header-actions">
        <el-select v-model="clusterFilter" placeholder="选择集群" clearable style="width: 180px" @change="loadData">
          <el-option v-for="c in clusterList" :key="c.id" :label="c.name" :value="c.id" />
        </el-select>
        <div class="header-stats" v-if="nodes.length">
          <el-tag type="success" effect="plain">在线 {{ onlineCount }}</el-tag>
          <el-tag type="info" effect="plain">总计 {{ nodes.length }}</el-tag>
        </div>
      </div>
    </div>
    <el-card shadow="hover" class="table-card">
      <div v-if="loading" class="loading-box">
        <el-icon class="is-loading" :size="20"><Loading /></el-icon>
        <span>加载中...</span>
      </div>
      <el-table v-else :data="nodes" style="width: 100%" stripe>
        <el-table-column prop="node_name" label="节点名称" min-width="130" fixed>
          <template #default="{ row }">
            <span class="node-name">{{ row.node_name }}</span>
            <div class="sub-text">{{ row.cluster_name }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 'online' ? 'success' : 'danger'" size="small" disable-transitions>
              {{ row.status === 'online' ? '在线' : '离线' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="CPU" min-width="150">
          <template #default="{ row }">
            <div class="usage-cell">
              <el-progress :percentage="cpuPercent(row)" :stroke-width="8" :color="cpuColor(cpuPercent(row))" :show-text="false" />
              <span class="usage-text">{{ cpuPercent(row) }}% · {{ row.cpu_cores || '?' }}核</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="内存" min-width="180">
          <template #default="{ row }">
            <div class="usage-cell">
              <el-progress :percentage="Math.round(row.memory_usage_pct || 0)" :stroke-width="8" color="#409eff" :show-text="false" />
              <span class="usage-text">{{ fmtMB(row.memory_used_mb) }}/{{ fmtMB(row.memory_total_mb) }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="磁盘" min-width="130">
          <template #default="{ row }">
            <span>{{ row.rootfs_used_gb || 0 }}GB / {{ row.rootfs_total_gb || 0 }}GB</span>
          </template>
        </el-table-column>
        <el-table-column label="I/O延迟" width="90" align="center">
          <template #default="{ row }">
            <span :class="{ 'text-warn': (row.disk_io_delay_ms || 0) > 50 }">{{ (row.disk_io_delay_ms || 0).toFixed(1) }}ms</span>
          </template>
        </el-table-column>
        <el-table-column prop="ip_address" label="IP 地址" min-width="140">
          <template #default="{ row }">{{ row.ip_address || '未知' }}</template>
        </el-table-column>
        <el-table-column prop="pve_version" label="PVE 版本" min-width="140" />
        <el-table-column label="运行时长" min-width="100">
          <template #default="{ row }">{{ fmtUptime(row.uptime_seconds) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="80" align="center" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="showDetail(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && !nodes.length" description="暂无节点数据，请先部署 Agent 采集数据" />
    </el-card>

    <!-- 节点详情弹窗 -->
    <el-dialog v-model="detailVisible" :title="detailData?.node?.node_name || '节点详情'" width="820px" destroy-on-close top="5vh">
      <div v-if="detailLoading" class="loading-box">
        <el-icon class="is-loading" :size="20"><Loading /></el-icon>
        <span>加载中...</span>
      </div>
      <div v-else-if="detailData" class="detail-content">
        <!-- 基本信息 -->
        <div class="detail-section">
          <h4>基本信息</h4>
          <div class="detail-kv">
            <div class="kv-row"><span class="kv-label">节点名称</span><span class="kv-val">{{ detailData.node.node_name }}</span></div>
            <div class="kv-row"><span class="kv-label">集群</span><span class="kv-val">{{ detailData.node.cluster_name }}</span></div>
            <div class="kv-row"><span class="kv-label">状态</span><span class="kv-val"><el-tag :type="detailData.node.status === 'online' ? 'success' : 'danger'" size="small">{{ detailData.node.status === 'online' ? '在线' : '离线' }}</el-tag></span></div>
            <div class="kv-row"><span class="kv-label">IP 地址</span><span class="kv-val mono">{{ detailData.node.ip_address || '-' }}</span></div>
            <div class="kv-row" v-if="detailData.node.mac_address"><span class="kv-label">MAC</span><span class="kv-val mono">{{ detailData.node.mac_address }}</span></div>
            <div class="kv-row"><span class="kv-label">PVE 版本</span><span class="kv-val mono">{{ detailData.node.pve_version || '-' }}</span></div>
            <div class="kv-row"><span class="kv-label">内核版本</span><span class="kv-val mono">{{ detailData.node.kernel_version || '-' }}</span></div>
            <div class="kv-row"><span class="kv-label">运行时长</span><span class="kv-val">{{ fmtUptime(detailData.node.uptime_seconds) }}</span></div>
            <div class="kv-row"><span class="kv-label">角色</span><span class="kv-val">
              <el-tag v-if="detailData.node.is_ceph_node" type="success" size="small" effect="plain">Ceph</el-tag>
              <el-tag v-if="detailData.node.is_ha_node" type="warning" size="small" effect="plain" style="margin-left:4px">HA</el-tag>
              <span v-if="!detailData.node.is_ceph_node && !detailData.node.is_ha_node">-</span>
            </span></div>
            <div class="kv-row"><span class="kv-label">扫描时间</span><span class="kv-val mono">{{ fmtTime(detailData.node.scanned_at) }}</span></div>
          </div>
        </div>
        <!-- 硬件信息 -->
        <div class="detail-section">
          <h4>硬件</h4>
          <div class="detail-kv">
            <div class="kv-row"><span class="kv-label">CPU 型号</span><span class="kv-val">{{ detailData.node.cpu_model || '-' }}</span></div>
            <div class="kv-row"><span class="kv-label">CPU</span><span class="kv-val">{{ detailData.node.cpu_load?.toFixed(1) || 0 }}% · {{ detailData.node.cpu_cores }}核 × {{ detailData.node.cpu_sockets || 1 }}插槽</span></div>
            <div class="kv-row"><span class="kv-label">内存</span><span class="kv-val">{{ fmtMB(detailData.node.memory_used_mb) }} / {{ fmtMB(detailData.node.memory_total_mb) }} ({{ detailData.node.memory_usage_pct?.toFixed(1) || 0 }}%)</span></div>
            <div class="kv-row"><span class="kv-label">可用内存</span><span class="kv-val">{{ fmtMB(detailData.node.memory_free_mb) }}</span></div>
            <div class="kv-row"><span class="kv-label">Swap</span><span class="kv-val">{{ fmtMB(detailData.node.swap_used_mb) }} / {{ fmtMB(detailData.node.swap_total_mb) }}</span></div>
            <div class="kv-row"><span class="kv-label">根分区</span><span class="kv-val">{{ detailData.node.rootfs_used_gb }}GB / {{ detailData.node.rootfs_total_gb }}GB (可用 {{ detailData.node.rootfs_avail_gb }}GB)</span></div>
            <div class="kv-row"><span class="kv-label">I/O 延迟</span><span class="kv-val" :class="{ 'text-warn': (detailData.node.disk_io_delay_ms || 0) > 50 }">{{ (detailData.node.disk_io_delay_ms || 0).toFixed(1) }}ms</span></div>
          </div>
        </div>
        <!-- 网络接口 -->
        <div class="detail-section" v-if="detailData.networks?.length">
          <h4>网络接口</h4>
          <div class="device-list">
            <div v-for="net in detailData.networks" :key="net.name" class="device-chip">
              <span class="chip-tag">{{ net.name }}</span>
              <span class="chip-body">{{ net.type }}</span>
              <el-tag :type="net.active ? 'success' : 'info'" size="small" effect="plain">{{ net.active ? '启用' : '禁用' }}</el-tag>
              <span v-if="net.address" class="chip-sub mono">{{ net.address }}</span>
              <span v-if="net.gateway" class="chip-sub">GW {{ net.gateway }}</span>
              <span v-if="net.speed_mbps" class="chip-sub">{{ net.speed_mbps }}Mbps</span>
            </div>
          </div>
        </div>
        <!-- 存储 -->
        <div class="detail-section" v-if="detailData.storages?.length">
          <h4>存储</h4>
          <div class="device-list">
            <div v-for="s in detailData.storages" :key="s.name" class="device-chip">
              <span class="chip-tag">{{ s.name }}</span>
              <span class="chip-body">{{ s.type }}</span>
              <el-tag :type="s.status === 'available' ? 'success' : 'danger'" size="small" effect="plain">{{ s.status === 'available' ? '可用' : '不可用' }}</el-tag>
              <span v-if="s.total_gb" class="chip-sub">{{ s.used_gb || 0 }}GB / {{ s.total_gb }}GB</span>
              <span v-if="s.content_types" class="chip-sub mono">{{ s.content_types }}</span>
              <el-tag v-if="s.shared" type="info" size="small" effect="plain">共享</el-tag>
            </div>
          </div>
        </div>
        <!-- 虚拟机 -->
        <div class="detail-section" v-if="detailData.vms?.length">
          <el-collapse v-model="vmCollapse">
            <el-collapse-item title="" name="vm">
              <template #title>
                <h4 class="collapse-title">虚拟机 ({{ detailData.vms.length }})</h4>
              </template>
              <div class="resource-list">
                <div v-for="vm in detailData.vms" :key="vm.vmid" class="resource-item">
                  <div class="resource-header">
                    <code class="mono">{{ vm.vmid }}</code>
                    <span class="resource-name">{{ vm.name }}</span>
                    <el-tag :type="vm.status === 'running' ? 'success' : 'danger'" size="small">{{ vm.status === 'running' ? '运行' : '停止' }}</el-tag>
                  </div>
                  <div class="resource-detail">
                    <span>CPU {{ vm.cpu_usage?.toFixed(1) || 0 }}% · {{ vm.cpu_cores }}核</span>
                    <span>{{ fmtMB(vm.memory_used_mb) }} / {{ fmtMB(vm.memory_mb) }}</span>
                    <span>{{ vm.disk_gb }}GB</span>
                  </div>
                </div>
              </div>
            </el-collapse-item>
          </el-collapse>
        </div>
        <!-- 容器 -->
        <div class="detail-section" v-if="detailData.containers?.length">
          <el-collapse v-model="ctCollapse">
            <el-collapse-item title="" name="ct">
              <template #title>
                <h4 class="collapse-title">容器 ({{ detailData.containers.length }})</h4>
              </template>
              <div class="resource-list">
                <div v-for="ct in detailData.containers" :key="ct.vmid" class="resource-item">
                  <div class="resource-header">
                    <code class="mono">{{ ct.vmid }}</code>
                    <span class="resource-name">{{ ct.name }}</span>
                    <el-tag v-if="ct.has_template" type="warning" size="small" effect="plain">模板</el-tag>
                    <el-tag v-else :type="ct.status === 'running' ? 'success' : 'danger'" size="small">{{ ct.status === 'running' ? '运行' : '停止' }}</el-tag>
                  </div>
                  <div class="resource-detail">
                    <span>CPU {{ ct.cpu_usage?.toFixed(1) || 0 }}% · {{ ct.cpu_cores }}核</span>
                    <span>{{ fmtMB(ct.memory_used_mb) }} / {{ fmtMB(ct.memory_mb) }}</span>
                    <span>{{ ct.disk_gb }}GB</span>
                  </div>
                </div>
              </div>
            </el-collapse-item>
          </el-collapse>
        </div>
      </div>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Loading } from '@element-plus/icons-vue'
import { getNodes, getNodeDetail } from '@/api/nodes'
import type { NodeInfo, NodeDetail } from '@/api/nodes'
import { getClusters, type Cluster } from '@/api/clusters'

const loading = ref(true)
const nodes = ref<NodeInfo[]>([])
const onlineCount = computed(() => nodes.value.filter(n => n.status === 'online').length)
const clusterFilter = ref<number | ''>('')
const clusterList = ref<Cluster[]>([])

const detailVisible = ref(false)
const detailLoading = ref(false)
const detailData = ref<NodeDetail | null>(null)
const vmCollapse = ref<string[]>([])
const ctCollapse = ref<string[]>([])

async function loadData() {
  loading.value = true
  try {
    const params: Record<string, any> = {}
    if (clusterFilter.value !== '') params.cluster_id = clusterFilter.value
    nodes.value = await getNodes(params)
  } catch {} finally { loading.value = false }
}

onMounted(async () => {
  try {
    const res = await getClusters()
    clusterList.value = res.results
    if (clusterList.value.length) {
      clusterFilter.value = clusterList.value[0].id
    }
  } catch {} finally {
    loadData()
  }
})

async function showDetail(row: NodeInfo) {
  detailVisible.value = true
  detailLoading.value = true
  detailData.value = null
  try { detailData.value = await getNodeDetail(row.id) } catch {} finally { detailLoading.value = false }
}

function cpuPercent(row: NodeInfo) { return Math.round(row.cpu_load || 0) }
function cpuColor(p: number) { return p > 85 ? '#f56c6c' : p >= 70 ? '#e6a23c' : '#67c23a' }
function fmtMB(mb: number) { return mb >= 1024 ? `${(mb / 1024).toFixed(1)}GB` : `${mb || 0}MB` }
function fmtTime(iso: string) {
  if (!iso) return '-'
  return new Date(iso).toLocaleString('zh-CN')
}
function fmtUptime(s: number) {
  if (!s) return '-'
  const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600)
  return d > 0 ? `${d}天${h}时` : `${h}时${Math.floor((s % 3600) / 60)}分`
}
</script>

<style scoped>
.page-container { max-width: 1400px; margin: 0 auto; }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 28px; }
.page-title { font-size: 24px; font-weight: 700; color: var(--text-heading); margin: 0; }
.page-desc { font-size: 14px; color: var(--text-muted); margin: 4px 0 0; }
.header-actions { display: flex; gap: 8px; align-items: center; }
.header-stats { display: flex; gap: 8px; }
.table-card { border-radius: 16px; }
.loading-box { display: flex; align-items: center; justify-content: center; gap: 8px; padding: 40px; color: var(--text-secondary); }
.node-name { font-weight: 600; color: var(--text-primary); }
.sub-text { font-size: 12px; color: var(--text-muted); }
.usage-cell { display: flex; flex-direction: column; gap: 4px; }
.usage-text { font-size: 12px; color: var(--text-muted); }
.text-warn { color: #e6a23c; font-weight: 600; }

/* 详情弹窗 */
.detail-content { max-height: 70vh; overflow-y: auto; }
.detail-section { margin-bottom: 16px; }
.detail-section:last-child { margin-bottom: 0; }
.detail-section h4 { font-size: 13px; font-weight: 600; color: var(--text-secondary); margin: 0 0 8px; padding-bottom: 6px; border-bottom: 1px solid var(--border-color); text-transform: uppercase; letter-spacing: 0.5px; }
.detail-kv { display: grid; grid-template-columns: 1fr 1fr; gap: 2px 20px; }
.kv-row { display: flex; align-items: center; padding: 5px 0; border-bottom: 1px dashed var(--border-color); }
.kv-label { font-size: 13px; color: var(--text-muted); min-width: 80px; flex-shrink: 0; }
.kv-val { font-size: 13px; color: var(--text-primary); }
.mono { font-family: 'SF Mono', 'Menlo', monospace; font-size: 12px; }
.device-list { display: flex; flex-direction: column; gap: 4px; }
.device-chip { display: flex; align-items: center; gap: 8px; padding: 6px 10px; background: var(--bg-secondary); border-radius: 8px; }
.chip-tag { font-size: 12px; font-weight: 600; color: var(--color-primary); background: rgba(64, 158, 255, 0.1); padding: 1px 6px; border-radius: 4px; white-space: nowrap; }
.chip-body { font-size: 13px; font-weight: 500; color: var(--text-primary); }
.chip-sub { font-size: 12px; color: var(--text-muted); }
.resource-list { display: flex; flex-direction: column; gap: 6px; }
.resource-item { padding: 8px 10px; background: var(--bg-secondary); border-radius: 8px; }
.resource-header { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.resource-name { font-weight: 600; font-size: 13px; color: var(--text-primary); }
.resource-detail { display: flex; gap: 16px; font-size: 12px; color: var(--text-muted); }
/* 折叠面板样式 */
.collapse-title { margin: 0; font-size: 13px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px; }
:deep(.el-collapse) { border: none; }
:deep(.el-collapse-item__header) { background: transparent; border: none; height: 32px; line-height: 32px; margin-bottom: 8px; }
:deep(.el-collapse-item__wrap) { background: transparent; border: none; }
:deep(.el-collapse-item__content) { padding-bottom: 0; }
:deep(.el-collapse-item__arrow) { margin-right: 8px; }

:deep(.el-table) { background: var(--el-card-bg-color); --el-table-bg-color: var(--el-card-bg-color); --el-table-tr-bg-color: var(--el-card-bg-color); --el-table-header-bg-color: var(--el-card-bg-color); --el-table-border-color: var(--border-color); --el-table-text-color: var(--text-primary); --el-table-header-text-color: var(--text-secondary); }
:deep(.el-table::before) { display: none; }
:deep(.el-table th.el-table__cell) { background-color: var(--el-card-bg-color); }
:deep(.el-table--enable-row-hover .el-table__body tr:hover > td) { background-color: rgba(64, 158, 255, 0.05); }
:deep(.el-tag--success) { --el-tag-bg-color: rgba(103, 194, 58, 0.15); --el-tag-text-color: #67c23a; --el-tag-border-color: transparent; }
:deep(.el-tag--danger) { --el-tag-bg-color: rgba(245, 108, 108, 0.15); --el-tag-text-color: #f56c6c; --el-tag-border-color: transparent; }
/* 固定列强制不透明背景 */
:deep(.el-table__fixed td),
:deep(.el-table__fixed-right td),
:deep(.el-table .el-table-fixed-column--left),
:deep(.el-table .el-table-fixed-column--right) {
  background-color: var(--el-card-bg-color) !important;
}
:deep(.el-table__fixed th),
:deep(.el-table__fixed-right th) {
  background-color: var(--el-card-bg-color) !important;
}
</style>
