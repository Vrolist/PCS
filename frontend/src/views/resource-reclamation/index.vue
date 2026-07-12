<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">资源回收建议</h2>
        <p class="page-desc">
          检测僵尸 VM、未使用磁盘等可回收资源
          <el-tooltip placement="right" :width="320">
            <template #content>
              <div class="tooltip-content">
                <p><strong>僵尸 VM/容器：</strong>状态为 stopped 且运行时长为 0</p>
                <p><strong>旧快照：</strong>创建时间超过 30 天的快照</p>
                <p><strong>低使用率存储：</strong>存储使用率低于 30%</p>
                <p><strong>空闲资源：</strong>运行中但 CPU 和内存使用均为 0</p>
              </div>
            </template>
            <el-icon class="help-icon"><QuestionFilled /></el-icon>
          </el-tooltip>
        </p>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stat-cards">
      <div class="stat-card">
        <div class="stat-icon zombie-icon">
          <el-icon :size="24"><Warning /></el-icon>
        </div>
        <div class="stat-body">
          <div class="stat-value">{{ summary.zombie_vms_count + summary.zombie_containers_count }}</div>
          <div class="stat-label">僵尸资源</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon snapshot-icon">
          <el-icon :size="24"><Clock /></el-icon>
        </div>
        <div class="stat-body">
          <div class="stat-value">{{ summary.old_snapshots_count }}</div>
          <div class="stat-label">旧快照</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon storage-icon">
          <el-icon :size="24"><Coin /></el-icon>
        </div>
        <div class="stat-body">
          <div class="stat-value">{{ summary.low_usage_storages_count }}</div>
          <div class="stat-label">低使用率存储</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon space-icon">
          <el-icon :size="24"><FolderOpened /></el-icon>
        </div>
        <div class="stat-body">
          <div class="stat-value">{{ summary.reclaimable_space_gb }} GB</div>
          <div class="stat-label">可回收空间</div>
          <div class="stat-sub" v-if="summary.total_storage_gb > 0">
            占总存储 {{ Math.round(summary.reclaimable_space_gb / summary.total_storage_gb * 100) }}%
          </div>
        </div>
      </div>
    </div>

    <!-- 资源回收内容 -->
    <el-card shadow="hover" class="table-card">
      <el-tabs v-model="activeTab" class="resource-tabs">
        <el-tab-pane name="zombie_vms">
          <template #label>
            <span class="tab-label">
              僵尸 VM
              <el-badge :value="zombie_vms.length" :max="99" class="tab-badge" />
            </span>
          </template>
          <el-empty v-if="zombie_vms.length === 0" description="暂无僵尸 VM" />
          <el-table v-else :data="zombie_vms" stripe style="width: 100%">
            <el-table-column prop="vmid" label="VM ID" width="100" />
            <el-table-column prop="name" label="名称" min-width="120" />
            <el-table-column prop="node_name" label="节点" width="100" />
            <el-table-column prop="cluster_name" label="集群" width="120" />
            <el-table-column prop="cpu_cores" label="CPU" width="80" />
            <el-table-column label="内存" width="100">
              <template #default="{ row }">
                {{ row.memory_mb ? `${row.memory_mb} MB` : '-' }}
              </template>
            </el-table-column>
            <el-table-column label="磁盘" width="100">
              <template #default="{ row }">
                {{ row.disk_gb ? `${row.disk_gb} GB` : '-' }}
              </template>
            </el-table-column>
            <el-table-column label="停机时长" width="120">
              <template #default="{ row }">
                <span :class="{ 'text-danger': row.stopped_days > 90, 'text-warning': row.stopped_days > 30 }">
                  {{ row.stopped_days }} 天
                </span>
              </template>
            </el-table-column>
            <el-table-column label="风险等级" width="100">
              <template #default="{ row }">
                <el-tag :type="getRiskType(row.risk_level)" size="small">
                  {{ getRiskLabel(row.risk_level) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="回收建议" min-width="200">
              <template #default="{ row }">
                <span class="suggestion-text">{{ row.suggestion }}</span>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
        <el-tab-pane name="zombie_containers">
          <template #label>
            <span class="tab-label">
              僵尸容器
              <el-badge :value="zombie_containers.length" :max="99" class="tab-badge" />
            </span>
          </template>
          <el-empty v-if="zombie_containers.length === 0" description="暂无僵尸容器" />
          <el-table v-else :data="zombie_containers" stripe style="width: 100%">
            <el-table-column prop="vmid" label="容器 ID" width="100" />
            <el-table-column prop="name" label="名称" min-width="120" />
            <el-table-column prop="node_name" label="节点" width="100" />
            <el-table-column prop="cluster_name" label="集群" width="120" />
            <el-table-column prop="cpu_cores" label="CPU" width="80" />
            <el-table-column label="内存" width="100">
              <template #default="{ row }">
                {{ row.memory_mb ? `${row.memory_mb} MB` : '-' }}
              </template>
            </el-table-column>
            <el-table-column label="磁盘" width="100">
              <template #default="{ row }">
                {{ row.disk_gb ? `${row.disk_gb} GB` : '-' }}
              </template>
            </el-table-column>
            <el-table-column label="停机时长" width="120">
              <template #default="{ row }">
                <span :class="{ 'text-danger': row.stopped_days > 90, 'text-warning': row.stopped_days > 30 }">
                  {{ row.stopped_days }} 天
                </span>
              </template>
            </el-table-column>
            <el-table-column label="风险等级" width="100">
              <template #default="{ row }">
                <el-tag :type="getRiskType(row.risk_level)" size="small">
                  {{ getRiskLabel(row.risk_level) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="回收建议" min-width="200">
              <template #default="{ row }">
                <span class="suggestion-text">{{ row.suggestion }}</span>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
        <el-tab-pane name="old_snapshots">
          <template #label>
            <span class="tab-label">
              旧快照
              <el-badge :value="old_snapshots.length" :max="99" class="tab-badge" />
            </span>
          </template>
          <el-empty v-if="old_snapshots.length === 0" description="暂无旧快照" />
          <el-table v-else :data="old_snapshots" stripe style="width: 100%">
            <el-table-column prop="snapid" label="快照 ID" width="120" />
            <el-table-column prop="name" label="名称" min-width="120" />
            <el-table-column prop="vm_name" label="虚拟机" min-width="120" />
            <el-table-column prop="vm_vmid" label="VM ID" width="100" />
            <el-table-column prop="node_name" label="节点" width="100" />
            <el-table-column prop="cluster_name" label="集群" width="120" />
            <el-table-column label="快照时间" width="180">
              <template #default="{ row }">
                {{ row.snap_time ? formatDate(row.snap_time) : '-' }}
              </template>
            </el-table-column>
            <el-table-column label="大小" width="100">
              <template #default="{ row }">
                {{ row.size_gb ? `${row.size_gb} GB` : '-' }}
              </template>
            </el-table-column>
            <el-table-column label="快照年龄" width="120">
              <template #default="{ row }">
                <span :class="{ 'text-danger': row.snap_age_days > 180, 'text-warning': row.snap_age_days > 90 }">
                  {{ row.snap_age_days }} 天
                </span>
              </template>
            </el-table-column>
            <el-table-column label="风险等级" width="100">
              <template #default="{ row }">
                <el-tag :type="getRiskType(row.risk_level)" size="small">
                  {{ getRiskLabel(row.risk_level) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="回收建议" min-width="200">
              <template #default="{ row }">
                <span class="suggestion-text">{{ row.suggestion }}</span>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
        <el-tab-pane name="low_usage_storages">
          <template #label>
            <span class="tab-label">
              低使用率存储
              <el-badge :value="low_usage_storages.length" :max="99" class="tab-badge" />
            </span>
          </template>
          <el-empty v-if="low_usage_storages.length === 0" description="暂无低使用率存储" />
          <el-table v-else :data="low_usage_storages" stripe style="width: 100%">
            <el-table-column prop="storage_name" label="存储名称" min-width="120" />
            <el-table-column prop="type" label="类型" width="100" />
            <el-table-column prop="node_name" label="节点" width="100" />
            <el-table-column prop="cluster_name" label="集群" width="120" />
            <el-table-column label="总容量" width="100">
              <template #default="{ row }">
                {{ row.total_gb ? `${row.total_gb} GB` : '-' }}
              </template>
            </el-table-column>
            <el-table-column label="已用" width="100">
              <template #default="{ row }">
                {{ row.used_gb ? `${row.used_gb} GB` : '-' }}
              </template>
            </el-table-column>
            <el-table-column label="可用" width="100">
              <template #default="{ row }">
                {{ row.avail_gb ? `${row.avail_gb} GB` : '-' }}
              </template>
            </el-table-column>
            <el-table-column label="使用率" width="120">
              <template #default="{ row }">
                <el-progress :percentage="Math.round((row.used_fraction || 0) * 100)" :color="getProgressColor(row.used_fraction)" :stroke-width="10" />
              </template>
            </el-table-column>
            <el-table-column label="风险等级" width="100">
              <template #default="{ row }">
                <el-tag :type="getRiskType(row.risk_level)" size="small">
                  {{ getRiskLabel(row.risk_level) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="回收建议" min-width="200">
              <template #default="{ row }">
                <span class="suggestion-text">{{ row.suggestion }}</span>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
        <el-tab-pane name="idle_resources">
          <template #label>
            <span class="tab-label">
              空闲资源
              <el-badge :value="idle_resources.length" :max="99" class="tab-badge" />
            </span>
          </template>
          <el-empty v-if="idle_resources.length === 0" description="暂无空闲资源" />
          <el-table v-else :data="idle_resources" stripe style="width: 100%">
            <el-table-column prop="type" label="类型" width="100">
              <template #default="{ row }">
                <el-tag :type="row.type === 'vm' ? 'primary' : 'success'" size="small">
                  {{ row.type === 'vm' ? '虚拟机' : '容器' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="vmid" label="ID" width="100" />
            <el-table-column prop="name" label="名称" min-width="120" />
            <el-table-column prop="node_name" label="节点" width="100" />
            <el-table-column prop="cluster_name" label="集群" width="120" />
            <el-table-column prop="cpu_cores" label="CPU" width="80" />
            <el-table-column label="内存" width="100">
              <template #default="{ row }">
                {{ row.memory_mb ? `${row.memory_mb} MB` : '-' }}
              </template>
            </el-table-column>
            <el-table-column label="磁盘" width="100">
              <template #default="{ row }">
                {{ row.disk_gb ? `${row.disk_gb} GB` : '-' }}
              </template>
            </el-table-column>
            <el-table-column label="风险等级" width="100">
              <template #default="{ row }">
                <el-tag :type="getRiskType(row.risk_level)" size="small">
                  {{ getRiskLabel(row.risk_level) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="回收建议" min-width="200">
              <template #default="{ row }">
                <span class="suggestion-text">{{ row.suggestion }}</span>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useClusterStore } from '@/stores/cluster'
import { getResourceReclamation } from '@/api/resource-reclamation'
import type { ZombieResource, OldSnapshot, LowUsageStorage, IdleResource } from '@/api/resource-reclamation'
import { Warning, Clock, Coin, FolderOpened, QuestionFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const clusterStore = useClusterStore()
const activeTab = ref('zombie_vms')
const loading = ref(false)

const summary = ref({
  zombie_vms_count: 0,
  zombie_containers_count: 0,
  old_snapshots_count: 0,
  low_usage_storages_count: 0,
  idle_resources_count: 0,
  reclaimable_space_gb: 0,
  total_storage_gb: 0,
})

const zombie_vms = ref<ZombieResource[]>([])
const zombie_containers = ref<ZombieResource[]>([])
const old_snapshots = ref<OldSnapshot[]>([])
const low_usage_storages = ref<LowUsageStorage[]>([])
const idle_resources = ref<IdleResource[]>([])

const fetchData = async () => {
  loading.value = true
  try {
    const params = clusterStore.currentClusterId ? { cluster_id: clusterStore.currentClusterId } : undefined
    const data = await getResourceReclamation(params)
    
    summary.value = data.summary
    zombie_vms.value = data.zombie_vms
    zombie_containers.value = data.zombie_containers
    old_snapshots.value = data.old_snapshots
    low_usage_storages.value = data.low_usage_storages
    idle_resources.value = data.idle_resources
  } catch (error) {
    console.error('获取资源回收数据失败:', error)
    ElMessage.error('获取资源回收数据失败')
  } finally {
    loading.value = false
  }
}

// 监听全局集群选择器变化
watch(() => clusterStore.currentClusterId, () => {
  fetchData()
})

const formatDate = (dateStr: string) => {
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}

const getProgressColor = (fraction: number | null) => {
  if (!fraction) return '#67c23a'
  const percentage = fraction * 100
  if (percentage < 20) return '#67c23a'
  if (percentage < 50) return '#e6a23c'
  return '#f56c6c'
}

const getRiskType = (level: string) => {
  switch (level) {
    case 'high': return 'danger'
    case 'medium': return 'warning'
    case 'low': return 'success'
    default: return 'info'
  }
}

const getRiskLabel = (level: string) => {
  switch (level) {
    case 'high': return '高风险'
    case 'medium': return '中风险'
    case 'low': return '低风险'
    default: return '未知'
  }
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.page-container {
  max-width: 1400px;
  margin: 0 auto;
}
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}
.page-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-heading);
  margin: 0;
}
.page-desc {
  font-size: 14px;
  color: var(--text-muted);
  margin: 4px 0 0;
  display: flex;
  align-items: center;
  gap: 6px;
}
.help-icon {
  cursor: pointer;
  color: var(--text-muted);
  font-size: 16px;
}
.help-icon:hover {
  color: var(--el-color-primary);
}
.tooltip-content p {
  margin: 4px 0;
  line-height: 1.6;
}

/* === Stat Cards (standalone row, like dashboard StatCards.vue) === */
.stat-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}
@media (max-width: 1200px) { .stat-cards { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 640px) { .stat-cards { grid-template-columns: 1fr; } }

.stat-card {
  background: #fff;
  border: 1px solid var(--border-color);
  border-radius: 14px;
  padding: 20px 24px;
  display: flex;
  align-items: center;
  gap: 16px;
  transition: transform 0.25s ease, box-shadow 0.25s ease;
  cursor: default;
}
.dark .stat-card {
  background: var(--bg-card);
  border-color: var(--border-color);
}
.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--card-hover-shadow);
}

.stat-icon {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.zombie-icon { background: rgba(245, 108, 108, 0.1); color: #f56c6c; }
.snapshot-icon { background: rgba(230, 162, 60, 0.1); color: #e6a23c; }
.storage-icon { background: rgba(103, 194, 58, 0.1); color: #67c23a; }
.space-icon { background: rgba(64, 158, 255, 0.1); color: #409eff; }

.stat-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.stat-value {
  font-size: 26px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.2;
}
.stat-label {
  font-size: 14px;
  color: var(--text-secondary);
}
.stat-sub {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 1px;
}

/* === Table Card (tabs inside el-card, like HA/nodes pages) === */
.table-card {
  border-radius: 16px;
}
.table-card :deep(.el-card__body) {
  padding: 0;
}

.resource-tabs {
  padding: 0;
}
.resource-tabs :deep(.el-tabs__header) {
  margin: 0;
  padding: 16px 24px 0;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  border-radius: 16px 16px 0 0;
}
.resource-tabs :deep(.el-tabs__content) {
  padding: 20px 24px;
}

.tab-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.tab-badge :deep(.el-badge__content) {
  background-color: var(--primary-color, #409eff);
}

.text-danger {
  color: var(--danger-color, #f56c6c);
  font-weight: 600;
}
.text-warning {
  color: var(--warning-color, #e6a23c);
  font-weight: 600;
}
.suggestion-text {
  font-size: 13px;
  color: var(--text-muted);
}
</style>
