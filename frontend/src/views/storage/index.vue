<template>
  <div class="page-container">
    <div class="page-header">
      <h2>{{ t('storagePage.title') }}</h2>
    </div>

    <div class="filter-bar">
      <el-select v-model="filterNode" :placeholder="t('storagePage.allNodes')" clearable style="width: 160px">
        <el-option v-for="n in nodes" :key="n" :label="n" :value="n" />
      </el-select>
    </div>

    <el-card shadow="never">
      <el-table :data="filteredList" v-loading="loading" stripe border size="small">
        <el-table-column prop="name" :label="t('storagePage.storageName')" min-width="140" fixed />
        <el-table-column prop="type" :label="t('common.type')" width="120">
          <template #default="{ row }">
            <el-tag size="small">{{ row.type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" :label="t('common.status')" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'danger'" size="small">
              {{ row.status === 'active' ? t('common.enabled') : row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="node_name" :label="t('common.nodes')" width="120" />
        <el-table-column :label="t('storagePage.usedTotal')" min-width="160">
          <template #default="{ row }">
            <span>{{ formatGB(row.used_gb) }} / {{ formatGB(row.total_gb) }}</span>
          </template>
        </el-table-column>
        <el-table-column :label="t('storagePage.usageRate')" width="160">
          <template #default="{ row }">
            <div v-if="row.total_gb > 0">
              <el-progress :percentage="getPercent(row.used_gb, row.total_gb)" :stroke-height="8"
                :color="getProgressColor(getPercent(row.used_gb, row.total_gb))" />
            </div>
            <span v-else>--</span>
          </template>
        </el-table-column>
        <el-table-column prop="shared" :label="t('storagePage.shared')" width="80" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.shared" type="success" size="small">{{ t('storagePage.yes') }}</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { getStorageList, type Storage } from '@/api/storage'
import { useClusterStore } from '@/stores/cluster'

const { t } = useI18n()
const clusterStore = useClusterStore()

const loading = ref(false)
const storageList = ref<Storage[]>([])
const filterNode = ref('')

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
    if (clusterStore.currentClusterId) params.cluster_id = clusterStore.currentClusterId
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
</style>
