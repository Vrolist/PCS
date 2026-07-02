<template>
  <div class="settings-page">
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ t('settings.title') }}</h2>
        <p class="page-desc">{{ t('settings.subtitle') }}</p>
      </div>
    </div>

    <div class="settings-layout">
      <!-- 左侧：用户卡片 -->
      <div class="settings-left">
        <el-card shadow="hover" class="profile-card">
          <div class="profile-header">
            <el-avatar :size="80" icon="UserFilled" class="profile-avatar" />
            <h3 class="profile-name">{{ userData.username || '-' }}</h3>
            <el-tag v-if="userData.is_superuser" type="danger" size="small" class="role-badge">{{ t('settings.admin') }}</el-tag>
            <el-tag v-else type="info" size="small" class="role-badge">{{ t('settings.normalUser') }}</el-tag>
          </div>
          <el-divider />
          <div class="profile-detail">
            <div class="profile-row">
              <span class="profile-label">{{ t('settings.email') }}</span>
              <span class="profile-val">{{ userData.email || '-' }}</span>
            </div>
            <div class="profile-row">
              <span class="profile-label">{{ t('settings.phone') }}</span>
              <span class="profile-val">{{ userData.phone || '-' }}</span>
            </div>
            <div class="profile-row">
              <span class="profile-label">{{ t('settings.company') }}</span>
              <span class="profile-val">{{ userData.company || '-' }}</span>
            </div>
            <div class="profile-row">
              <span class="profile-label">{{ t('settings.registerTime') }}</span>
              <span class="profile-val">{{ userData.date_joined?.slice(0, 10) || '-' }}</span>
            </div>
            <div class="profile-row">
              <span class="profile-label">{{ t('settings.userId') }}</span>
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
            <span class="form-title">{{ t('settings.editProfile') }}</span>
          </template>
          <el-form
            ref="profileFormRef"
            :model="profileForm"
            :rules="profileRules"
            label-position="top"
            class="settings-form"
          >
            <el-form-item :label="t('settings.usernameLabel')">
              <el-input v-model="userData.username" disabled :placeholder="t('settings.usernameDisabled')" />
              <div class="form-tip">{{ t('settings.usernameDisabled') }}</div>
            </el-form-item>
            <el-form-item :label="t('settings.emailLabel')">
              <el-input v-model="userData.email" disabled :placeholder="t('settings.emailDisabled')" />
              <div class="form-tip">{{ t('settings.emailDisabled') }}</div>
            </el-form-item>
            <el-form-item :label="t('settings.phoneLabel')" prop="phone">
              <el-input v-model="profileForm.phone" :placeholder="t('settings.phonePlaceholder')" maxlength="20" />
            </el-form-item>
            <el-form-item :label="t('settings.companyLabel')" prop="company">
              <el-input v-model="profileForm.company" :placeholder="t('settings.companyPlaceholder')" maxlength="128" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="saving" @click="handleSaveProfile">
                {{ t('settings.saveChanges') }}
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <!-- 安全设置 -->
        <el-card shadow="hover" class="form-card">
          <template #header>
            <span class="form-title">{{ t('settings.securitySettings') }}</span>
          </template>
          <div class="security-section">
            <div class="security-row">
              <div class="security-info">
                <span class="security-label">{{ t('settings.loginPassword') }}</span>
                <span class="security-desc">{{ t('settings.loginPasswordDesc') }}</span>
              </div>
              <el-button @click="$router.push('/dashboard/change-password')">
                {{ t('settings.changePassword') }}
              </el-button>
            </div>
            <el-divider />
            <div class="security-row">
              <div class="security-info">
                <span class="security-label">{{ t('settings.adminBackend') }}</span>
                <span class="security-desc">{{ t('settings.adminBackendDesc') }}</span>
              </div>
              <el-button v-if="userData.is_superuser" type="warning" @click="handleAdminSession">
                {{ t('settings.adminBackend') }}
              </el-button>
              <el-tag v-else type="info" size="small">{{ t('settings.adminOnly') }}</el-tag>
            </div>
          </div>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import { updateUserInfo, createAdminSession } from '@/api/auth'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'

const { t } = useI18n()
const authStore = useAuthStore()
const userData: any = reactive({})
const profileFormRef = ref<FormInstance>()
const saving = ref(false)

const profileForm = reactive({
  phone: '',
  company: '',
})

const profileRules: FormRules = {
  phone: [{ max: 20, message: () => t('settings.phoneMax'), trigger: 'blur' }],
  company: [{ max: 128, message: () => t('settings.companyMax'), trigger: 'blur' }],
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
    ElMessage.success(t('settings.updateSuccess'))
  } catch (e: any) {
    const msg = e?.response?.data?.detail || e?.response?.data?.[0] || t('settings.updateFailed')
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
    ElMessage.error(t('settings.sessionFailed'))
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
