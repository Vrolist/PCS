<template>
  <div class="page-container">
    <div class="page-header">
      <h2>{{ t('networks.title') }}</h2>
    </div>

    <div class="filter-bar">
      <el-select v-model="filterNode" :placeholder="t('networks.allNodes')" clearable style="width: 160px">
        <el-option v-for="n in nodes" :key="n" :label="n" :value="n" />
      </el-select>
      <el-select v-model="filterType" :placeholder="t('networks.allTypes')" clearable style="width: 140px">
        <el-option v-for="t in types" :key="t" :label="t" :value="t" />
      </el-select>
    </div>

    <el-card shadow="never">
      <el-table :data="filteredList" v-loading="loading" stripe border size="small">
        <el-table-column prop="name" :label="t('networks.ifaceName')" min-width="130" fixed />
        <el-table-column prop="node_name" :label="t('networks.node')" width="100" />
        <el-table-column prop="type" :label="t('networks.type')" width="90">
          <template #default="{ row }">
            <el-tag size="small">{{ row.type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="address" :label="t('networks.ipAddr')" min-width="150">
          <template #default="{ row }">
            <span>{{ row.address || '--' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="bridge_ports" :label="t('networks.bridgePorts')" min-width="130">
          <template #default="{ row }">
            <span>{{ row.bridge_ports || '--' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="bond_mode" :label="t('networks.bondMode')" width="110">
          <template #default="{ row }">
            <span v-if="row.bond_mode">{{ row.bond_mode }}</span>
            <span v-else class="text-muted">--</span>
          </template>
        </el-table-column>
        <el-table-column prop="vlan_id" label="VLAN" width="70" align="center">
          <template #default="{ row }">
            <span v-if="row.vlan_id">{{ row.vlan_id }}</span>
            <span v-else class="text-muted">--</span>
          </template>
        </el-table-column>
        <el-table-column prop="mtu" label="MTU" width="70" align="center">
          <template #default="{ row }">
            <span v-if="row.mtu">{{ row.mtu }}</span>
            <span v-else class="text-muted">--</span>
          </template>
        </el-table-column>
        <el-table-column prop="speed" :label="t('networks.speed')" width="100">
          <template #default="{ row }">
            <span>{{ row.speed ? row.speed + ' Mbps' : '--' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" :label="t('networks.status')" width="70" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 'up' ? 'success' : 'danger'" size="small">
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { getNetworkList, type NetworkInterface } from '@/api/networks'
import { useClusterStore } from '@/stores/cluster'

const { t } = useI18n()
const clusterStore = useClusterStore()

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
    const params: Record<string, any> = {}
    if (clusterStore.currentClusterId) params.cluster_id = clusterStore.currentClusterId
    networkList.value = await getNetworkList(params)
  } finally {
    loading.value = false
  }
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
.text-muted { color: var(--text-secondary, #909399); }
</style>
