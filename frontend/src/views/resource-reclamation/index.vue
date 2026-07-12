<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">资源回收建议</h2>
        <p class="page-desc">检测僵尸 VM、未使用磁盘等可回收资源</p>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stat-cards">
      <el-card shadow="hover" class="stat-card">
        <div class="stat-content">
          <div class="stat-icon zombie-icon">
            <el-icon><Warning /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ summary.zombie_vms_count + summary.zombie_containers_count }}</div>
            <div class="stat-label">僵尸资源</div>
          </div>
        </div>
      </el-card>
      
      <el-card shadow="hover" class="stat-card">
        <div class="stat-content">
          <div class="stat-icon snapshot-icon">
            <el-icon><Clock /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ summary.old_snapshots_count }}</div>
            <div class="stat-label">旧快照</div>
          </div>
        </div>
      </el-card>
      
      <el-card shadow="hover" class="stat-card">
        <div class="stat-content">
          <div class="stat-icon storage-icon">
            <el-icon><Coin /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ summary.low_usage_storages_count }}</div>
            <div class="stat-label">低使用率存储</div>
          </div>
        </div>
      </el-card>
      
      <el-card shadow="hover" class="stat-card">
        <div class="stat-content">
          <div class="stat-icon space-icon">
            <el-icon><FolderOpened /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ summary.reclaimable_space_gb }} GB</div>
            <div class="stat-label">可回收空间</div>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 资源回收内容 -->
    <el-tabs v-model="activeTab" class="resource-tabs">
      <el-tab-pane label="僵尸 VM" name="zombie_vms">
        <el-table :data="zombie_vms" stripe style="width: 100%">
          <el-table-column prop="vmid" label="VM ID" width="100" />
          <el-table-column prop="name" label="名称" />
          <el-table-column prop="node_name" label="节点" />
          <el-table-column prop="cluster_name" label="集群" />
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
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="row.status === 'stopped' ? 'danger' : 'success'" size="small">
                {{ row.status }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
      
      <el-tab-pane label="僵尸容器" name="zombie_containers">
        <el-table :data="zombie_containers" stripe style="width: 100%">
          <el-table-column prop="vmid" label="容器 ID" width="100" />
          <el-table-column prop="name" label="名称" />
          <el-table-column prop="node_name" label="节点" />
          <el-table-column prop="cluster_name" label="集群" />
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
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="row.status === 'stopped' ? 'danger' : 'success'" size="small">
                {{ row.status }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
      
      <el-tab-pane label="旧快照" name="old_snapshots">
        <el-table :data="old_snapshots" stripe style="width: 100%">
          <el-table-column prop="snapid" label="快照 ID" width="120" />
          <el-table-column prop="name" label="名称" />
          <el-table-column prop="vm_name" label="虚拟机" />
          <el-table-column prop="vm_vmid" label="VM ID" width="100" />
          <el-table-column prop="node_name" label="节点" />
          <el-table-column prop="cluster_name" label="集群" />
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
        </el-table>
      </el-tab-pane>
      
      <el-tab-pane label="低使用率存储" name="low_usage_storages">
        <el-table :data="low_usage_storages" stripe style="width: 100%">
          <el-table-column prop="storage_name" label="存储名称" />
          <el-table-column prop="type" label="类型" width="100" />
          <el-table-column prop="node_name" label="节点" />
          <el-table-column prop="cluster_name" label="集群" />
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
              <el-progress
                :percentage="Math.round((row.used_fraction || 0) * 100)"
                :color="getProgressColor(row.used_fraction)"
                :stroke-width="10"
              />
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
      
      <el-tab-pane label="空闲资源" name="idle_resources">
        <el-table :data="idle_resources" stripe style="width: 100%">
          <el-table-column prop="type" label="类型" width="100">
            <template #default="{ row }">
              <el-tag :type="row.type === 'vm' ? 'primary' : 'success'" size="small">
                {{ row.type === 'vm' ? '虚拟机' : '容器' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="vmid" label="ID" width="100" />
          <el-table-column prop="name" label="名称" />
          <el-table-column prop="node_name" label="节点" />
          <el-table-column prop="cluster_name" label="集群" />
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
        </el-table>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useClusterStore } from '@/stores/cluster'
import { getResourceReclamation } from '@/api/resource-reclamation'
import type { ResourceReclamationData, ZombieResource, OldSnapshot, LowUsageStorage, IdleResource } from '@/api/resource-reclamation'
import { Warning, Clock, Coin, FolderOpened } from '@element-plus/icons-vue'
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
  margin-bottom: 28px;
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
}
.stat-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 28px;
}
.stat-card {
  border-radius: 12px;
}
.stat-content {
  display: flex;
  align-items: center;
  gap: 16px;
}
.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}
.zombie-icon {
  background: rgba(245, 108, 108, 0.1);
  color: #f56c6c;
}
.snapshot-icon {
  background: rgba(230, 162, 60, 0.1);
  color: #e6a23c;
}
.storage-icon {
  background: rgba(103, 194, 58, 0.1);
  color: #67c23a;
}
.space-icon {
  background: rgba(64, 158, 255, 0.1);
  color: #409eff;
}
.stat-info {
  flex: 1;
}
.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-heading);
  line-height: 1.2;
}
.stat-label {
  font-size: 14px;
  color: var(--text-muted);
  margin-top: 4px;
}
.resource-tabs {
  margin-top: 20px;
}
</style>
