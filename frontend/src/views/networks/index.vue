<template>
  <div class="page-container">
    <div class="page-header">
      <h2>网络接口</h2>
    </div>

    <div class="filter-bar">
      <el-select v-model="filterNode" placeholder="全部节点" clearable style="width: 160px">
        <el-option v-for="n in nodes" :key="n" :label="n" :value="n" />
      </el-select>
      <el-select v-model="filterType" placeholder="全部类型" clearable style="width: 140px">
        <el-option v-for="t in types" :key="t" :label="t" :value="t" />
      </el-select>
    </div>

    <el-card shadow="never">
      <el-table :data="filteredList" v-loading="loading" stripe border size="small">
        <el-table-column prop="name" label="接口名称" min-width="140" fixed />
        <el-table-column prop="node_name" label="节点" width="120" />
        <el-table-column prop="type" label="类型" width="100">
          <template #default="{ row }">
            <el-tag size="small">{{ row.type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="address" label="IP 地址" min-width="160">
          <template #default="{ row }">
            <span>{{ row.address || '--' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="mac_address" label="MAC 地址" width="160">
          <template #default="{ row }">
            <span style="font-family: monospace; font-size: 12px;">{{ row.mac_address || '--' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="speed" label="速率" width="120">
          <template #default="{ row }">
            <span>{{ row.speed ? row.speed + ' Mbps' : '--' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 'up' ? 'success' : row.status === 'active' ? 'success' : 'danger'" size="small">
              {{ row.status || '--' }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { getNetworkList, type NetworkInterface } from '@/api/networks'

const loading = ref(false)
const networkList = ref<NetworkInterface[]>([])
const filterNode = ref('')
const filterType = ref('')

const nodes = computed(() => {
  const set = new Set(networkList.value.map(n => n.node_name))
  return Array.from(set).sort()
})

const types = computed(() => {
  const set = new Set(networkList.value.map(n => n.type))
  return Array.from(set).sort()
})

const filteredList = computed(() => {
  let list = networkList.value
  if (filterNode.value) list = list.filter(n => n.node_name === filterNode.value)
  if (filterType.value) list = list.filter(n => n.type === filterType.value)
  return list
})

async function fetchData() {
  loading.value = true
  try {
    networkList.value = await getNetworkList()
  } finally {
    loading.value = false
  }
}

onMounted(fetchData)
</script>

<style scoped>
.page-container { padding: 20px; }
.page-header { margin-bottom: 16px; }
.page-header h2 { margin: 0; font-size: 20px; font-weight: 600; }
.filter-bar { margin-bottom: 16px; display: flex; gap: 12px; }
</style>
