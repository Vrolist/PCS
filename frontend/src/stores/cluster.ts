import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getClusters, type Cluster } from '@/api/clusters'

const STORAGE_KEY = 'pcs_current_cluster_id'

export const useClusterStore = defineStore('cluster', () => {
  const clusterList = ref<Cluster[]>([])
  const currentClusterId = ref<number | null>(
    Number(localStorage.getItem(STORAGE_KEY)) || null
  )
  const loading = ref(false)

  const currentCluster = computed(() =>
    clusterList.value.find(c => c.id === currentClusterId.value) || null
  )

  /** 加载集群列表 */
  async function fetchClusters() {
    loading.value = true
    try {
      const res = await getClusters()
      clusterList.value = res.results || []
      // 如果当前选中的集群不在列表中，自动选第一个
      if (currentClusterId.value && !clusterList.value.find(c => c.id === currentClusterId.value)) {
        currentClusterId.value = clusterList.value.length ? clusterList.value[0].id : null
        saveToLocal()
      } else if (!currentClusterId.value && clusterList.value.length) {
        currentClusterId.value = clusterList.value[0].id
        saveToLocal()
      }
    } catch {
      // ignore
    } finally {
      loading.value = false
    }
  }

  /** 切换集群 */
  function setCluster(id: number | null) {
    currentClusterId.value = id
    saveToLocal()
  }

  function saveToLocal() {
    if (currentClusterId.value) {
      localStorage.setItem(STORAGE_KEY, String(currentClusterId.value))
    } else {
      localStorage.removeItem(STORAGE_KEY)
    }
  }

  return { clusterList, currentClusterId, currentCluster, loading, fetchClusters, setCluster }
})
