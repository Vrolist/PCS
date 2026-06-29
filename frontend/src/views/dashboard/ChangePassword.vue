<template>
  <div class="change-pw-page">
    <div class="change-pw-layout">
      <!-- 左侧：用户信息 -->
      <div class="cp-left">
        <el-card shadow="hover" class="user-card">
          <div class="user-info-content">
            <el-avatar :size="72" icon="UserFilled" class="user-avatar" />
            <h3 class="user-name">{{ authStore.user?.username || '-' }}</h3>
            <div class="user-detail">
              <div class="detail-row">
                <span class="detail-label">邮箱</span>
                <span class="detail-value">{{ authStore.user?.email || '-' }}</span>
              </div>
              <div class="detail-row">
                <span class="detail-label">加入时间</span>
                <span class="detail-value">{{ authStore.user?.date_joined?.slice(0, 10) || '-' }}</span>
              </div>
            </div>
          </div>
        </el-card>
      </div>

      <!-- 右侧：修改密码 -->
      <div class="cp-right">
        <el-card shadow="hover" class="form-card">
          <template #header>
            <span class="form-title">修改密码</span>
          </template>
          <el-form
            ref="formRef"
            :model="form"
            :rules="rules"
            label-position="top"
            class="pw-form"
            @keyup.enter="handleSubmit"
          >
            <el-form-item label="新密码" prop="new_password">
              <el-input
                v-model="form.new_password"
                type="password"
                placeholder="请输入新密码"
                show-password
              />
            </el-form-item>
            <el-form-item label="确认新密码" prop="new_password2">
              <el-input
                v-model="form.new_password2"
                type="password"
                placeholder="请再次输入新密码"
                show-password
              />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="submitting" @click="handleSubmit">
                确认修改
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </div>
    </div>

    <!-- 成功弹窗 -->
    <el-dialog
      v-model="successDialog"
      title="修改成功"
      :show-close="false"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      width="400px"
      class="success-dialog"
    >
      <div class="success-body">
        <el-icon :size="48" color="#67c23a"><SuccessFilled /></el-icon>
        <p class="success-msg">密码修改成功，已自动退出登录</p>
        <p class="success-hint">请使用新密码重新登录</p>
      </div>
      <template #footer>
        <el-button type="primary" @click="doLogout" :loading="logouting">
          确定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { changePassword } from '@/api/auth'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { SuccessFilled } from '@element-plus/icons-vue'

const router = useRouter()
const authStore = useAuthStore()

const formRef = ref<FormInstance>()
const submitting = ref(false)
const successDialog = ref(false)
const logouting = ref(false)

const form = reactive({
  new_password: '',
  new_password2: '',
})

const validatePass2 = (_rule: any, value: string, callback: any) => {
  if (value !== form.new_password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const rules: FormRules = {
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 位', trigger: 'blur' },
  ],
  new_password2: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    { validator: validatePass2, trigger: 'blur' },
  ],
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    await changePassword({
      new_password: form.new_password,
      new_password2: form.new_password2,
    })
    successDialog.value = true
  } catch (e: any) {
    const msg = e?.response?.data?.detail || e?.response?.data?.[0] || '修改失败'
    ElMessage.error(msg)
  } finally {
    submitting.value = false
  }
}

function doLogout() {
  logouting.value = true
  authStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.change-pw-page {
  max-width: 1400px;
  margin: 0 auto;
}
.change-pw-layout {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 28px;
  align-items: start;
}

/* 左侧用户信息 */
.user-card {
  border-radius: 12px;
}
.user-info-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 24px 0 8px;
  text-align: center;
}
.user-avatar {
  background: linear-gradient(135deg, #409eff, #8b5cf6);
  margin-bottom: 16px;
}
.user-name {
  font-size: 20px;
  font-weight: 600;
  margin: 0 0 20px;
  color: var(--text-heading);
}
.user-detail {
  width: 100%;
  text-align: left;
}
.detail-row {
  display: flex;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px solid var(--border-color);
  font-size: 13px;
}
.detail-row:last-child {
  border-bottom: none;
}
.detail-label {
  color: var(--text-muted);
}
.detail-value {
  color: var(--text-secondary);
  font-weight: 500;
}

/* 右侧表单 */
.form-card {
  border-radius: 12px;
}
.form-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-heading);
}
.pw-form {
  max-width: 420px;
  padding: 8px 0;
}

/* 成功弹窗 */
.success-body {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 16px 0;
  gap: 12px;
}
.success-msg {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-heading);
  margin: 0;
}
.success-hint {
  font-size: 14px;
  color: var(--text-muted);
  margin: 0;
}

@media (max-width: 900px) {
  .change-pw-layout {
    grid-template-columns: 1fr;
  }
}
</style>
