<template>
  <div class="settings-page">
    <div class="page-header">
      <div>
        <h2 class="page-title">用户信息</h2>
        <p class="page-desc">管理您的个人资料与账户信息</p>
      </div>
    </div>

    <div class="settings-layout">
      <!-- 左侧：用户卡片 -->
      <div class="settings-left">
        <el-card shadow="hover" class="profile-card">
          <div class="profile-header">
            <el-avatar :size="80" icon="UserFilled" class="profile-avatar" />
            <h3 class="profile-name">{{ userData.username || '-' }}</h3>
            <el-tag v-if="userData.is_superuser" type="danger" size="small" class="role-badge">管理员</el-tag>
            <el-tag v-else type="info" size="small" class="role-badge">普通用户</el-tag>
          </div>
          <el-divider />
          <div class="profile-detail">
            <div class="profile-row">
              <span class="profile-label">邮箱</span>
              <span class="profile-val">{{ userData.email || '-' }}</span>
            </div>
            <div class="profile-row">
              <span class="profile-label">手机</span>
              <span class="profile-val">{{ userData.phone || '-' }}</span>
            </div>
            <div class="profile-row">
              <span class="profile-label">公司</span>
              <span class="profile-val">{{ userData.company || '-' }}</span>
            </div>
            <div class="profile-row">
              <span class="profile-label">注册时间</span>
              <span class="profile-val">{{ userData.date_joined?.slice(0, 10) || '-' }}</span>
            </div>
            <div class="profile-row">
              <span class="profile-label">用户 ID</span>
              <span class="profile-val mono">{{ userData.id }}</span>
            </div>
          </div>
        </el-card>
      </div>

      <!-- 右侧：编辑区 -->
      <div class="settings-right">
        <!-- 编辑资料 -->
        <el-card shadow="hover" class="form-card">
          <template #header>
            <span class="form-title">编辑资料</span>
          </template>
          <el-form
            ref="profileFormRef"
            :model="profileForm"
            :rules="profileRules"
            label-position="top"
            class="settings-form"
          >
            <el-form-item label="用户名">
              <el-input v-model="userData.username" disabled placeholder="用户名不可修改" />
              <div class="form-tip">用户名不可修改</div>
            </el-form-item>
            <el-form-item label="邮箱">
              <el-input v-model="userData.email" disabled placeholder="邮箱不可修改" />
              <div class="form-tip">邮箱不可修改</div>
            </el-form-item>
            <el-form-item label="手机号" prop="phone">
              <el-input v-model="profileForm.phone" placeholder="请输入手机号" maxlength="20" />
            </el-form-item>
            <el-form-item label="公司" prop="company">
              <el-input v-model="profileForm.company" placeholder="请输入公司名称" maxlength="128" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="saving" @click="handleSaveProfile">
                保存修改
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <!-- 安全设置 -->
        <el-card shadow="hover" class="form-card">
          <template #header>
            <span class="form-title">安全设置</span>
          </template>
          <div class="security-section">
            <div class="security-row">
              <div class="security-info">
                <span class="security-label">登录密码</span>
                <span class="security-desc">定期更换密码可以提高账户安全性</span>
              </div>
              <el-button @click="$router.push('/dashboard/change-password')">
                修改密码
              </el-button>
            </div>
            <el-divider />
            <div class="security-row">
              <div class="security-info">
                <span class="security-label">后台管理</span>
                <span class="security-desc">进入 Django Admin 管理后台</span>
              </div>
              <el-button v-if="userData.is_superuser" type="warning" @click="handleAdminSession">
                管理后台
              </el-button>
              <el-tag v-else type="info" size="small">仅管理员可用</el-tag>
            </div>
          </div>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { updateUserInfo, createAdminSession } from '@/api/auth'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'

const authStore = useAuthStore()
const userData: any = reactive({})
const profileFormRef = ref<FormInstance>()
const saving = ref(false)

const profileForm = reactive({
  phone: '',
  company: '',
})

const profileRules: FormRules = {
  phone: [{ max: 20, message: '手机号不超过 20 个字符', trigger: 'blur' }],
  company: [{ max: 128, message: '公司名称不超过 128 个字符', trigger: 'blur' }],
}

onMounted(async () => {
  if (!authStore.user) {
    await authStore.fetchUser()
  }
  if (authStore.user) {
    Object.assign(userData, authStore.user)
    profileForm.phone = authStore.user.phone || ''
    profileForm.company = authStore.user.company || ''
  }
})

async function handleSaveProfile() {
  const valid = await profileFormRef.value?.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    const updated = await updateUserInfo({
      phone: profileForm.phone,
      company: profileForm.company,
    })
    Object.assign(userData, updated)
    authStore.setUser(updated)
    ElMessage.success('资料更新成功')
  } catch (e: any) {
    const msg = e?.response?.data?.detail || e?.response?.data?.[0] || '更新失败'
    ElMessage.error(msg)
  } finally {
    saving.value = false
  }
}

async function handleAdminSession() {
  try {
    await createAdminSession()
    window.open('/admin/', '_blank')
  } catch {
    ElMessage.error('创建会话失败')
  }
}
</script>

<style scoped>
.settings-page {
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

.settings-layout {
  display: grid;
  grid-template-columns: 340px 1fr;
  gap: 28px;
  align-items: start;
}
@media (max-width: 900px) {
  .settings-layout { grid-template-columns: 1fr; }
}

/* 左侧用户卡片 */
.profile-card {
  border-radius: 12px;
}
.profile-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 16px 0 0;
  text-align: center;
}
.profile-avatar {
  background: linear-gradient(135deg, #409eff, #8b5cf6);
  margin-bottom: 12px;
}
.profile-name {
  font-size: 20px;
  font-weight: 600;
  margin: 0 0 8px;
  color: var(--text-heading);
}
.role-badge {
  margin-bottom: 4px;
}
.profile-detail {
  padding: 0 4px;
}
.profile-row {
  display: flex;
  justify-content: space-between;
  padding: 10px 0;
  font-size: 13px;
}
.profile-row + .profile-row {
  border-top: 1px solid var(--border-color);
}
.profile-label {
  color: var(--text-muted);
}
.profile-val {
  color: var(--text-secondary);
  font-weight: 500;
}

/* 右侧表单 */
.form-card {
  border-radius: 12px;
}
.form-card + .form-card {
  margin-top: 20px;
}
.form-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-heading);
}
.settings-form {
  max-width: 480px;
  padding: 8px 0;
}
.form-tip {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 4px;
}

/* 安全设置 */
.security-section {
  padding: 4px 0;
}
.security-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.security-label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 4px;
}
.security-desc {
  font-size: 12px;
  color: var(--text-muted);
}

.mono {
  font-family: 'SF Mono', 'Fira Code', 'Cascadia Code', monospace;
}
</style>
