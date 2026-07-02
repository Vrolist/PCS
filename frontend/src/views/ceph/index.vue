<template>
  <div class="page-container">
    <div class="page-header">
      <h2>Ceph 存储</h2>
    </div>



    <div v-if="loading" class="empty-state">加载中...</div>
    <div v-else-if="!cephData" class="empty-state">暂无 Ceph 数据</div>
    <div v-else>
      <div class="stats-row">
        <el-card shadow="never" class="stat-card">
          <div class="stat-label">健康状态</div>
          <div class="stat-value">
            <el-tag :type="cephData.health === 'HEALTH_OK' ? 'success' : 'danger'" size="large">
              {{ cephData.health }}
            </el-tag>
          </div>
        </el-card>
        <el-card shadow="never" class="stat-card">
          <div class="stat-label">OSD 数量</div>
          <div class="stat-value">{{ cephData.total_osds }}</div>
        </el-card>
        <el-card shadow="never" class="stat-card">
          <div class="stat-label">PG 总数</div>
          <div class="stat-value">{{ cephData.total_pgs }}</div>
        </el-card>
        <el-card shadow="never" class="stat-card">
          <div class="stat-label">容量</div>
          <div class="stat-value">{{ formatGB(cephData.bytes_used_gb) }} / {{ formatGB(cephData.bytes_total_gb) }}</div>
        </el-card>
      </div>

      <el-card shadow="never" style="margin-top: 16px;">
        <template #header>详情</template>
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="集群名称">{{ cephData.cluster_name || '--' }}</el-descriptions-item>
          <el-descriptions-item label="版本">{{ cephData.version || '--' }}</el-descriptions-item>
          <el-descriptions-item label="运行时长">{{ cephData.uptime || '--' }}</el-descriptions-item>
        </el-descriptions>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { getCephStatus, type CephStatus } from '@/api/ceph'
import { useClusterStore } from '@/stores/cluster'

const clusterStore = useClusterStore()

const loading = ref(false)
const cephData = ref<CephStatus | null>(null)

async function fetchData() {
  loading.value = true
  try {
    const params: Record<string, any> = {}
    if (clusterStore.currentClusterId) params.cluster_id = clusterStore.currentClusterId
    cephData.value = await getCephStatus(params)
  } finally {
    loading.value = false
  }
}

function formatGB(val: number): string {
  if (!val) return '0GB'
  return val >= 1024 ? `${(val / 1024).toFixed(1)}TB` : `${Math.round(val)}GB`
}

onMounted(async () => {
  if (!clusterStore.clusterList.length) await clusterStore.fetchClusters()
  fetchData()
})

watch(() => clusterStore.currentClusterId, () => { fetchData() })
</script>

<style scoped>
.page-container { padding: 20px; }
.page-header { margin-bottom: 8px; }
.page-header h2 { margin: 0; font-size: 20px; font-weight: 600; }
.filter-bar { margin-bottom: 16px; display: flex; gap: 12px; }
.empty-state { text-align: center; color: var(--text-secondary); padding: 60px 0; }
.stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
.stat-card { text-align: center; }
.stat-label { font-size: 13px; color: var(--text-secondary); margin-bottom: 8px; }
.stat-value { font-size: 20px; font-weight: 600; }
</style>
