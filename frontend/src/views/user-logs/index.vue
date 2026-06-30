<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">操作日志</h2>
        <p class="page-desc">查看用户操作记录</p>
      </div>
      <div class="page-actions">
        <el-select v-model="actionFilter" placeholder="操作类型" clearable size="default" style="width: 140px" @change="loadLogs(1)">
          <el-option v-for="a in actionOptions" :key="a.value" :label="a.label" :value="a.value" />
        </el-select>
      </div>
    </div>

    <el-card shadow="hover">
      <el-empty v-if="!loading && logs.length === 0" description="暂无操作日志" />

      <el-table v-else :data="logs" stripe style="width: 100%" v-loading="loading">
        <el-table-column prop="created_at" label="操作时间" width="170">
          <template #default="{ row }">
            <span class="mono">{{ formatTime(row.created_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="action_display" label="操作类型" width="100">
          <template #default="{ row }">
            <el-tag :type="tagType(row.action)" size="small">{{ row.action_display }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="resource_type" label="资源类型" width="100" />
        <el-table-column prop="resource_id" label="资源 ID" width="100" />
        <el-table-column prop="detail" label="操作详情" min-width="240" show-overflow-tooltip />
        <el-table-column prop="ip_address" label="IP 地址" width="150" />
      </el-table>

      <div v-if="total > pageSize" class="pagination-wrap">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          layout="prev, pager, next"
          @current-change="loadLogs"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getUserLogs } from '@/api/auth'
import type { UserLog } from '@/api/auth'

const loading = ref(false)
const logs = ref<UserLog[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = 20
const actionFilter = ref('')

const actionOptions = [
  { value: '', label: '全部' },
  { value: 'login', label: '登录' },
  { value: 'register', label: '注册' },
  { value: 'create', label: '创建' },
  { value: 'update', label: '更新' },
  { value: 'delete', label: '删除' },
  { value: 'change_password', label: '修改密码' },
  { value: 'reset_password', label: '重置密码' },
]

function tagType(action: string) {
  const map: Record<string, string> = {
    login: 'success',
    register: 'primary',
    create: 'success',
    update: 'warning',
    delete: 'danger',
    change_password: 'info',
    reset_password: 'info',
  }
  return map[action] || ''
}

function formatTime(t: string) {
  if (!t) return '-'
  return t.slice(0, 19).replace('T', ' ')
}

async function loadLogs(page = 1) {
  currentPage.value = page
  loading.value = true
  try {
    const data = await getUserLogs({
      page,
      page_size: pageSize,
      action: actionFilter.value || undefined,
    })
    logs.value = data.results
    total.value = data.count
  } catch {
    // handled by interceptor
  } finally {
    loading.value = false
  }
}

onMounted(() => loadLogs())
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
.page-actions {
  display: flex;
  gap: 12px;
}
.mono {
  font-family: 'SF Mono', 'Fira Code', 'Cascadia Code', monospace;
  font-size: 13px;
}
.pagination-wrap {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}
</style>
