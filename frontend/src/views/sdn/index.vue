<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ t('advanced.sdn.title') }}</h2>
        <p class="page-desc">{{ t('advanced.sdn.subtitle') }}</p>
      </div>
    </div>

    <div class="stats-row" v-if="!sdnUnsupported">
      <div class="el-card is-never-shadow stat-card">
        <div class="el-card__body" style="">
          <div class="stat-label">{{ t('advanced.sdn.zones') }}</div>
          <div class="stat-value">{{ zones.length }}</div>
        </div>
      </div>
      <div class="el-card is-never-shadow stat-card">
        <div class="el-card__body" style="">
          <div class="stat-label">{{ t('advanced.sdn.vnets') }}</div>
          <div class="stat-value">{{ vnets.length }}</div>
        </div>
      </div>
      <div class="el-card is-never-shadow stat-card">
        <div class="el-card__body" style="">
          <div class="stat-label">{{ t('advanced.sdn.subnets') }}</div>
          <div class="stat-value">{{ subnets.length }}</div>
        </div>
      </div>
    </div>

    <!-- PVE 7 不支持 SDN -->
    <el-card v-if="sdnUnsupported" shadow="hover" class="unsupported-card">
      <el-empty description="">
        <template #image>
          <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" stroke-width="1.5">
            <circle cx="12" cy="12" r="10"/><path d="M12 8v4m0 4h.01"/>
          </svg>
        </template>
        <template #description>
          <p style="font-size: 16px; font-weight: 600; color: var(--text-heading); margin: 0 0 8px">
            PVE {{ pveMajor }} 不支持 SDN 虚拟网络
          </p>
          <p style="font-size: 13px; color: var(--text-muted); margin: 0">
            SDN 功能需要 Proxmox VE 8.0 及以上版本，当前集群版本为 PVE {{ pveMajor }}。
          </p>
        </template>
      </el-empty>
    </el-card>

    <el-card v-else shadow="hover" class="table-card">
      <el-tabs v-model="activeTab">
        <el-tab-pane :label="t('advanced.sdn.zones')" name="zones">
          <el-table :data="zones" stripe style="width: 100%" v-loading="loading" empty-text="暂无 SDN 区域数据">
            <el-table-column prop="zone" :label="t('advanced.sdn.zoneName')" min-width="160" />
            <el-table-column prop="zone_type" :label="t('advanced.sdn.zoneType')" min-width="120" align="center">
              <template #default="{ row }">
                <el-tag size="small" effect="plain">{{ row.zone_type }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="nodes" :label="t('advanced.sdn.nodes')" min-width="200" />
            <el-table-column prop="cluster_name" :label="t('advanced.sdn.cluster')" min-width="160" />
            <el-table-column prop="scanned_at" :label="t('advanced.sdn.scannedAt')" min-width="160">
              <template #default="{ row }">{{ formatTime(row.scanned_at) }}</template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane :label="t('advanced.sdn.vnets')" name="vnets">
          <el-table :data="vnets" stripe style="width: 100%" v-loading="loading" empty-text="暂无 SDN 虚拟网络数据">
            <el-table-column prop="vnet" :label="t('advanced.sdn.vnetName')" min-width="160" />
            <el-table-column prop="vnet_type" :label="t('advanced.sdn.vnetType')" min-width="100" align="center">
              <template #default="{ row }">
                <el-tag size="small" effect="plain">{{ row.vnet_type }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="vlan" :label="t('advanced.sdn.vlan')" min-width="80" align="center">
              <template #default="{ row }">
                <span v-if="row.vlan != null">{{ row.vlan }}</span>
                <span v-else class="text-muted">-</span>
              </template>
            </el-table-column>
            <el-table-column prop="zone" :label="t('advanced.sdn.zoneName')" min-width="140" />
            <el-table-column prop="cluster_name" :label="t('advanced.sdn.cluster')" min-width="160" />
            <el-table-column prop="scanned_at" :label="t('advanced.sdn.scannedAt')" min-width="160">
              <template #default="{ row }">{{ formatTime(row.scanned_at) }}</template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane :label="t('advanced.sdn.subnets')" name="subnets">
          <el-table :data="subnets" stripe style="width: 100%" v-loading="loading" empty-text="暂无 SDN 子网数据">
            <el-table-column prop="subnet" :label="t('advanced.sdn.subnetName')" min-width="140" />
            <el-table-column prop="vnet" :label="t('advanced.sdn.vnetName')" min-width="140" />
            <el-table-column prop="gateway" :label="t('advanced.sdn.gateway')" min-width="140" />
            <el-table-column prop="dns_server" :label="t('advanced.sdn.dnsServer')" min-width="160" />
            <el-table-column prop="dns_zone_prefix" :label="t('advanced.sdn.dnsZonePrefix')" min-width="140" />
            <el-table-column prop="cluster_name" :label="t('advanced.sdn.cluster')" min-width="160" />
            <el-table-column prop="scanned_at" :label="t('advanced.sdn.scannedAt')" min-width="160">
              <template #default="{ row }">{{ formatTime(row.scanned_at) }}</template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useClusterStore } from '@/stores/cluster'
import { getSDNZones, getSDNVNets, getSDNSubnets, type SDNZone, type SDNVNet, type SDNSubnet } from '@/api/sdn'

const { t } = useI18n()
const clusterStore = useClusterStore()

const loading = ref(false)
const activeTab = ref('zones')
const zones = ref<SDNZone[]>([])
const vnets = ref<SDNVNet[]>([])
const subnets = ref<SDNSubnet[]>([])

/** 解析 PVE 主版本号，如 "pve-manager/8.2.4" → 8 */
const pveMajor = computed(() => {
  const ver = clusterStore.currentCluster?.pve_version || ''
  const m = ver.match(/pve-manager\/(\d+)/)
  return m ? parseInt(m[1], 10) : 0
})

/** PVE 7 不支持 SDN */
const sdnUnsupported = computed(() => pveMajor.value > 0 && pveMajor.value < 8)

function formatTime(iso: string) {
  if (!iso) return '-'
  const d = new Date(iso)
  return `${d.getFullYear()}/${String(d.getMonth() + 1).padStart(2, '0')}/${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}`
}

async function fetchData() {
  if (!clusterStore.currentClusterId) return
  loading.value = true
  try {
    const params = { cluster_id: clusterStore.currentClusterId }
    const [z, v, s] = await Promise.all([
      getSDNZones(params),
      getSDNVNets(params),
      getSDNSubnets(params),
    ])
    zones.value = z
    vnets.value = v
    subnets.value = s
  } catch { /* ignore */ } finally {
    loading.value = false
  }
}

onMounted(async () => {
  if (!clusterStore.clusterList.length) await clusterStore.fetchClusters()
  fetchData()
})

watch(() => clusterStore.currentClusterId, () => fetchData())
</script>

<style scoped>
.page-container { max-width: 1400px; margin: 0 auto; }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.page-title { font-size: 24px; font-weight: 700; color: var(--text-heading); margin: 0; }
.page-desc { font-size: 14px; color: var(--text-muted); margin: 4px 0 0; }
.stats-row { display: flex; gap: 16px; margin-bottom: 16px; }
.stat-card { flex: 1; }
.stat-card .el-card__body { padding: 20px 24px; display: flex; flex-direction: column; gap: 4px; }
.stat-label { font-size: 13px; color: var(--text-muted); }
.stat-value { font-size: 28px; font-weight: 700; color: var(--text-heading); }
.table-card { margin-top: 0; }
.unsupported-card { margin-top: 0; }
.unsupported-card .el-card__body { padding: 80px 20px; }
.text-muted { color: var(--text-muted); }
</style>
