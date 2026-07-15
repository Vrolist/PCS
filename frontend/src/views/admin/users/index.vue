<template>
  <div class="admin-page">
    <!-- 页头 -->
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ t('adminUsers.title') }}</h2>
        <p class="page-desc">{{ t('adminUsers.subtitle') }}</p>
      </div>
      <el-button type="primary" @click="openCreateDialog">
        <el-icon><Plus /></el-icon>新增用户
      </el-button>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-grid">
      <div class="stat-item">
        <div class="stat-icon total"><el-icon><User /></el-icon></div>
        <div class="stat-body">
          <span class="stat-val">{{ users.length }}</span>
          <span class="stat-lbl">{{ t('adminUsers.totalUsers') }}</span>
        </div>
      </div>
      <div class="stat-item">
        <div class="stat-icon normal"><el-icon><CircleCheck /></el-icon></div>
        <div class="stat-body">
          <span class="stat-val">{{ activeCount }}</span>
          <span class="stat-lbl">{{ t('adminUsers.activeUsers') }}</span>
        </div>
      </div>
      <div class="stat-item">
        <div class="stat-icon banned"><el-icon><CircleClose /></el-icon></div>
        <div class="stat-body">
          <span class="stat-val">{{ disabledCount }}</span>
          <span class="stat-lbl">{{ t('adminUsers.disabledUsers') }}</span>
        </div>
      </div>
      <div class="stat-item">
        <div class="stat-icon reg"><el-icon><Switch /></el-icon></div>
        <div class="stat-body">
          <el-switch
            v-model="registrationEnabled"
            :active-text="t('adminUsers.open')"
            :inactive-text="t('adminUsers.closed')"
            inline-prompt
            @change="toggleRegistration"
          />
          <span class="stat-lbl">{{ t('adminUsers.registration') }}</span>
        </div>
      </div>
    </div>

    <!-- 搜索栏 -->
    <div class="toolbar">
      <el-input
        v-model="searchText"
        :placeholder="t('adminUsers.searchPlaceholder')"
        clearable
        class="search-box"
      >
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <el-select v-model="statusFilter" :placeholder="t('adminUsers.statusFilter')" clearable class="status-select">
        <el-option label="全部" value="" />
        <el-option label="正常" value="active" />
        <el-option label="已禁用" value="disabled" />
      </el-select>
    </div>

    <!-- 用户表格 -->
    <el-card shadow="never" class="table-wrap">
      <el-empty v-if="!loading && filteredUsers.length === 0" :description="t('adminUsers.noData')" />

      <el-table v-else :data="paginatedUsers" stripe v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="60" align="center" />

        <el-table-column prop="username" :label="t('adminUsers.username')" min-width="150">
          <template #default="{ row }">
            <div class="user-info-cell">
              <el-avatar :size="30" class="user-avatar">{{ row.username?.charAt(0)?.toUpperCase() }}</el-avatar>
              <div class="user-meta">
                <span class="user-name">{{ row.username }}</span>
                <el-tag v-if="row.is_superuser" size="small" class="admin-badge">管理员</el-tag>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="email" :label="t('adminUsers.email')" min-width="180">
          <template #default="{ row }"><span class="cell-muted">{{ row.email || '-' }}</span></template>
        </el-table-column>

        <el-table-column prop="phone" :label="t('adminUsers.phone')" width="120" />
        <el-table-column prop="company" :label="t('adminUsers.company')" width="120" />

        <el-table-column :label="t('adminUsers.joinTime')" width="165">
          <template #default="{ row }"><span class="mono">{{ formatTime(row.date_joined) }}</span></template>
        </el-table-column>

        <el-table-column :label="t('adminUsers.status')" width="90" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.is_active" size="small" type="success">正常</el-tag>
            <el-tag v-else size="small" type="danger">已禁用</el-tag>
          </template>
        </el-table-column>

        <el-table-column :label="t('adminUsers.actions')" width="100" align="center" fixed="right">
          <template #default="{ row }">
            <el-dropdown trigger="click" @command="(cmd: string) => handleAction(cmd, row)">
              <el-button size="small" class="action-btn">
                <el-icon><MoreFilled /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="edit">
                    <el-icon><Edit /></el-icon>编辑资料
                  </el-dropdown-item>
                  <el-dropdown-item command="password">
                    <el-icon><Key /></el-icon>修改密码
                  </el-dropdown-item>
                  <el-dropdown-item
                    v-if="!row.is_superuser"
                    :command="row.is_active ? 'disable' : 'enable'"
                    :divided="true"
                  >
                    <el-icon><component :is="row.is_active ? 'Lock' : 'Unlock'" /></el-icon>
                    {{ row.is_active ? '禁用账户' : '启用账户' }}
                  </el-dropdown-item>
                  <el-dropdown-item
                    v-if="!row.is_superuser"
                    command="delete"
                    :divided="true"
                    class="danger-item"
                  >
                    <el-icon><Delete /></el-icon>删除用户
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
      </el-table>

      <div v-if="filteredUsers.length > pageSize" class="pagination-bar">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="filteredUsers.length"
          layout="prev, pager, next, total"
          background
          small
        />
      </div>
    </el-card>

    <!-- 编辑弹窗 -->
    <el-dialog v-model="editDialogVisible" title="编辑用户" width="480px" class="user-dialog">
      <el-form :model="editForm" label-width="80px">
        <el-form-item label="用户名"><el-input v-model="editForm.username" /></el-form-item>
        <el-form-item label="邮箱"><el-input v-model="editForm.email" /></el-form-item>
        <el-form-item label="手机"><el-input v-model="editForm.phone" /></el-form-item>
        <el-form-item label="公司"><el-input v-model="editForm.company" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitEdit">保存</el-button>
      </template>
    </el-dialog>

    <!-- 密码弹窗 -->
    <el-dialog v-model="passwordDialogVisible" title="修改密码" width="420px" class="user-dialog">
      <el-form :model="passwordForm" label-width="80px">
        <el-form-item label="新密码">
          <el-input v-model="passwordForm.new_password" type="password" show-password />
        </el-form-item>
        <el-form-item label="确认密码">
          <el-input v-model="passwordForm.new_password2" type="password" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="passwordDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitChangePassword">确认</el-button>
      </template>
    </el-dialog>

    <!-- 新增用户弹窗 -->
    <el-dialog v-model="createDialogVisible" title="新增用户" width="520px" class="user-dialog">
      <el-form :model="createForm" :rules="createRules" ref="createFormRef" label-width="80px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="createForm.username" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="createForm.email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="createForm.password" type="password" show-password placeholder="请输入密码" />
        </el-form-item>
        <el-form-item label="手机">
          <el-input v-model="createForm.phone" placeholder="选填" />
        </el-form-item>
        <el-form-item label="公司">
          <el-input v-model="createForm.company" placeholder="选填" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitCreateUser" :loading="createLoading">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { User, CircleCheck, CircleClose, Search, Edit, Key, Lock, Unlock, MoreFilled, Plus, Delete } from '@element-plus/icons-vue'
import { getAdminUsers, createAdminUser, updateAdminUser, deleteAdminUser, adminChangePassword, adminToggleUserActive, getRegistrationStatus, toggleRegistration as toggleRegApi } from '@/api/admin'
import type { AdminUser } from '@/api/admin'

const { t } = useI18n()

const loading = ref(false)
const users = ref<AdminUser[]>([])
const registrationEnabled = ref(true)
const searchText = ref('')
const statusFilter = ref('')
const currentPage = ref(1)
const pageSize = 10

const editDialogVisible = ref(false)
const editForm = ref<Partial<AdminUser>>({})
const editUserId = ref(0)

const passwordDialogVisible = ref(false)
const passwordForm = ref({ new_password: '', new_password2: '' })
const passwordUserId = ref(0)

const createDialogVisible = ref(false)
const createLoading = ref(false)
const createFormRef = ref<FormInstance>()
const createForm = ref({
  username: '',
  email: '',
  password: '123456',
  phone: '',
  company: '',
})
const createRules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' },
  ],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

const activeCount = computed(() => users.value.filter(u => u.is_active).length)
const disabledCount = computed(() => users.value.filter(u => !u.is_active).length)

const filteredUsers = computed(() => {
  let r = users.value
  const q = searchText.value.toLowerCase()
  if (q) r = r.filter(u => [u.username, u.email, u.phone, u.company].some(v => v?.toLowerCase().includes(q)))
  if (statusFilter.value === 'active') r = r.filter(u => u.is_active)
  else if (statusFilter.value === 'disabled') r = r.filter(u => !u.is_active)
  return r
})

const paginatedUsers = computed(() => {
  const s = (currentPage.value - 1) * pageSize
  return filteredUsers.value.slice(s, s + pageSize)
})

function formatTime(t: string) {
  return t ? t.slice(0, 19).replace('T', ' ') : '-'
}

function handleAction(cmd: string, row: AdminUser) {
  if (cmd === 'edit') handleEdit(row)
  else if (cmd === 'password') handleChangePassword(row)
  else if (cmd === 'disable' || cmd === 'enable') handleToggleActive(row)
  else if (cmd === 'delete') handleDeleteUser(row)
}

async function loadUsers() {
  loading.value = true
  try {
    const data = await getAdminUsers()
    users.value = data.results
  } finally {
    loading.value = false
  }
}

async function loadRegistrationStatus() {
  try {
    const data = await getRegistrationStatus()
    registrationEnabled.value = data.enabled
  } catch { /* ignore */ }
}

function handleEdit(user: AdminUser) {
  editUserId.value = user.id
  editForm.value = { username: user.username, email: user.email, phone: user.phone, company: user.company }
  editDialogVisible.value = true
}

async function submitEdit() {
  await updateAdminUser(editUserId.value, editForm.value)
  ElMessage.success('用户信息更新成功')
  editDialogVisible.value = false
  loadUsers()
}

function handleChangePassword(user: AdminUser) {
  passwordUserId.value = user.id
  passwordForm.value = { new_password: '', new_password2: '' }
  passwordDialogVisible.value = true
}

async function submitChangePassword() {
  if (passwordForm.value.new_password !== passwordForm.value.new_password2) {
    ElMessage.error('两次输入的密码不一致')
    return
  }
  await adminChangePassword(passwordUserId.value, passwordForm.value)
  ElMessage.success('密码修改成功')
  passwordDialogVisible.value = false
}

async function handleToggleActive(user: AdminUser) {
  const action = user.is_active ? '禁用' : '启用'
  await ElMessageBox.confirm(`确定要${action}用户「${user.username}」吗？`, '确认', { type: 'warning' })
  const result = await adminToggleUserActive(user.id)
  ElMessage.success(result.detail)
  await loadUsers()
}

async function handleDeleteUser(user: AdminUser) {
  await ElMessageBox.confirm(`确定要删除用户「${user.username}」吗？此操作不可恢复。`, '删除确认', {
    type: 'warning',
    confirmButtonText: '确定删除',
    cancelButtonText: '取消',
  })
  await deleteAdminUser(user.id)
  ElMessage.success('用户已删除')
  await loadUsers()
}

async function toggleRegistration() {
  const result = await toggleRegApi()
  registrationEnabled.value = result.enabled
  ElMessage.success(result.detail)
}

function openCreateDialog() {
  createForm.value = { username: '', email: '', password: '123456', phone: '', company: '' }
  createDialogVisible.value = true
}

async function submitCreateUser() {
  if (!createFormRef.value) return
  try {
    await createFormRef.value.validate()
  } catch {
    return
  }
  createLoading.value = true
  try {
    await createAdminUser(createForm.value)
    ElMessage.success('用户创建成功')
    createDialogVisible.value = false
    loadUsers()
  } catch (err: any) {
    const data = err.response?.data
    if (data) {
      // 提取字段级错误信息（如 {"username": ["该用户名已被使用"]}）
      const msgs: string[] = []
      for (const [field, errors] of Object.entries(data)) {
        if (Array.isArray(errors)) {
          msgs.push(errors.join('；'))
        } else if (typeof errors === 'string') {
          msgs.push(errors)
        }
      }
      if (msgs.length) {
        ElMessage.error(msgs.join('；'))
      }
    }
  } finally {
    createLoading.value = false
  }
}

onMounted(() => {
  loadUsers()
  loadRegistrationStatus()
})
</script>

<style scoped>
.admin-page {
  max-width: 1400px;
  margin: 0 auto;
}

/* ========== 页头 ========== */
.page-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  margin-bottom: 28px;
}
.page-title {
  font-size: 24px;
  font-weight: 700;
  margin: 0;
  color: var(--text-heading);
}
.page-desc {
  font-size: 14px;
  margin: 4px 0 0;
  color: var(--text-muted);
}
/* ========== 统计卡片 ========== */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}
.stat-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px 24px;
  background: #fff;
  border: 1px solid var(--border-color);
  border-radius: 12px;
  transition: transform .2s, box-shadow .2s;
}
.dark .stat-item {
  background: var(--bg-primary);
}
.stat-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(0,0,0,.08);
}
.stat-icon {
  width: 46px;
  height: 46px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  color: #fff;
  flex-shrink: 0;
}
.stat-icon.total   { background: linear-gradient(135deg,#667eea,#764ba2); }
.stat-icon.normal  { background: linear-gradient(135deg,#43e97b,#38f9d7); }
.stat-icon.banned  { background: linear-gradient(135deg,#f093fb,#f5576c); }
.stat-icon.reg     { background: linear-gradient(135deg,#4facfe,#00f2fe); }
.stat-body {
  display: flex;
  flex-direction: column;
}
.stat-val {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-heading);
  line-height: 1.2;
}
.stat-lbl {
  font-size: 13px;
  color: var(--text-muted);
  margin-top: 2px;
}

/* ========== 工具栏 ========== */
.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}
.search-box {
  max-width: 320px;
}
.search-box :deep(.el-input__wrapper) {
  border-radius: 8px;
}
.status-select {
  width: 120px;
}
.status-select :deep(.el-select__wrapper) {
  border-radius: 8px;
}

/* ========== 表格 ========== */
.table-wrap {
  border-radius: 12px;
  border: 1px solid var(--border-color);
  background: var(--bg-primary);
}
.table-wrap :deep(.el-card__body) {
  padding: 20px 0;
}
/* 状态圆点 */
.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}
.dot-on  { background: #43e97b; box-shadow: 0 0 6px rgba(67,233,123,.5); }
.dot-off { background: #f5576c; box-shadow: 0 0 6px rgba(245,87,108,.5); }

/* 用户信息行 */
.user-info-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}
.user-avatar {
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: #fff;
  font-weight: 600;
  flex-shrink: 0;
}
.user-meta {
  display: flex;
  align-items: center;
  gap: 6px;
}
.user-name {
  font-weight: 500;
  color: var(--text-primary);
}
.admin-badge {
  font-size: 11px;
}
.cell-muted {
  color: var(--text-secondary);
}
.mono {
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: 13px;
}

/* 操作按钮 */
.action-btn {
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 6px 10px;
  background: transparent;
}
.action-btn:hover {
  background: var(--bg-secondary);
}

/* 分页 */
.pagination-bar {
  display: flex;
  justify-content: center;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid var(--border-color);
}

/* 弹窗 */
.user-dialog :deep(.el-dialog__header) {
  border-bottom: 1px solid var(--border-color);
  margin-right: 0;
  padding-bottom: 16px;
}

/* 危险操作项 */
.danger-item {
  color: #f56c6c !important;
}
.danger-item:hover {
  background: rgba(245, 108, 108, 0.1) !important;
}

/* 响应式 */
@media (max-width: 1100px) {
  .stats-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 600px) {
  .stats-grid { grid-template-columns: 1fr; }
  .toolbar { flex-direction: column; align-items: stretch; }
  .search-box { max-width: 100%; }
}
</style>
