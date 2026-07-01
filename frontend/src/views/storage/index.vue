<template>
  <div class="page-container">
    <div class="page-header">
      <h2>存储管理</h2>
    </div>

    <div class="filter-bar">
      <el-select v-model="clusterFilter" placeholder="选择集群" clearable style="width: 180px" @change="fetchData">
        <el-option v-for="c in clusterList" :key="c.id" :label="c.name" :value="c.id" />
      </el-select>
      <el-select v-model="filterNode" placeholder="全部节点" clearable style="width: 160px">
        <el-option v-for="n in nodes" :key="n" :label="n" :value="n" />
      </el-select>
    </div>

    <el-card shadow="never">
      <el-table :data="filteredList" v-loading="loading" stripe border size="small">
        <el-table-column prop="name" label="存储名称" min-width="140" fixed />
        <el-table-column prop="type" label="类型" width="120">
          <template #default="{ row }">
            <el-tag size="small">{{ row.type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'danger'" size="small">
              {{ row.status === 'active' ? '正常' : row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="node_name" label="节点" width="120" />
        <el-table-column label="已用 / 总量" min-width="160">
          <template #default="{ row }">
            <span>{{ formatGB(row.used_gb) }} / {{ formatGB(row.total_gb) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="使用率" width="160">
          <template #default="{ row }">
            <div v-if="row.total_gb > 0">
              <el-progress :percentage="getPercent(row.used_gb, row.total_gb)" :stroke-height="8"
                :color="getProgressColor(getPercent(row.used_gb, row.total_gb))" />
            </div>
            <span v-else>--</span>
          </template>
        </el-table-column>
        <el-table-column prop="shared" label="共享" width="80" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.shared" type="success" size="small">是</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { getStorageList, type Storage } from '@/api/storage'
import { getClusters, type Cluster } from '@/api/clusters'

const loading = ref(false)
const storageList = ref<Storage[]>([])
const filterNode = ref('')
const clusterFilter = ref<number | ''>('')
const clusterList = ref<Cluster[]>([])

const nodes = computed(() => {
  const set = new Set(storageList.value.map(s => s.node_name))
  return Array.from(set).sort()
})

const filteredList = computed(() => {
  if (!filterNode.value) return storageList.value
  return storageList.value.filter(s => s.node_name === filterNode.value)
})

async function fetchData() {
  loading.value = true
  try {
    const params: Record<string, any> = {}
    if (clusterFilter.value !== '') params.cluster_id = clusterFilter.value
    storageList.value = await getStorageList(params)
  } finally {
    loading.value = false
  }
}

function formatGB(val: number): string {
  if (!val) return '0GB'
  return val >= 1024 ? `${(val / 1024).toFixed(1)}TB` : `${Math.round(val)}GB`
}

function getPercent(used: number, total: number): number {
  return Math.min(Math.round((used / total) * 100), 100)
}

function getProgressColor(percent: number): string {
  if (percent >= 90) return '#f56c6c'
  if (percent >= 70) return '#e6a23c'
  return '#67c23a'
}

onMounted(async () => {
  try {
    const res = await getClusters()
    clusterList.value = res.results
    if (clusterList.value.length) {
      clusterFilter.value = clusterList.value[0].id
    }
  } catch {} finally {
    fetchData()
  }
})
</script>

<style scoped>
.page-container { padding: 20px; }
.page-header { margin-bottom: 8px; }
.page-header h2 { margin: 0; font-size: 20px; font-weight: 600; }
.filter-bar { margin-bottom: 16px; display: flex; gap: 12px; }
</style>
