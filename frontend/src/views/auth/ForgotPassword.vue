<template>
  <div class="auth-page">
    <!-- Background -->
    <div class="auth-bg">
      <div class="bg-orb orb-1"></div>
      <div class="bg-orb orb-2"></div>
      <div class="bg-grid"></div>
    </div>

    <!-- Back to home -->
    <router-link to="/" class="back-link">
      <el-icon><ArrowLeft /></el-icon>
      <span>{{ t('common.backToHome') }}</span>
    </router-link>

    <!-- Theme toggle -->
    <button class="theme-btn" @click="themeStore.toggle">
      <el-icon :size="18"><Sunny v-if="themeStore.theme === 'dark'" /><Moon v-else /></el-icon>
    </button>

    <div class="auth-container">
      <!-- Left: Brand -->
      <div class="auth-brand">
        <div class="brand-card">
          <div class="brand-logo">
            <div class="logo-icon"><svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="2" width="20" height="20" rx="2"/><line x1="6" y1="8" x2="18" y2="8"/><line x1="6" y1="12" x2="18" y2="12"/><line x1="6" y1="16" x2="18" y2="16"/><circle cx="6" cy="6" r="1" fill="currentColor" stroke="none"/></svg></div>
            <div class="brand-logo-text">
              <span class="logo-main">PCS</span>
              <span class="logo-sub"><span class="accent-l">P</span>ve<span class="accent-l">C</span>luster<span class="accent-l">S</span>can</span>
            </div>
          </div>
          <h2 class="brand-title">{{ t('forgotPassword.resetPassword') }}</h2>
          <p class="brand-desc">{{ t('forgotPassword.resetDesc') }}</p>
          <div class="brand-features">
            <div v-for="item in brandItems" :key="item.label" class="brand-feature">
              <el-icon :size="16" color="#409eff"><component :is="item.icon" /></el-icon>
              <span>{{ item.label }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Right: Form -->
      <div class="auth-form-panel">
        <div class="form-card">
          <!-- Step 1: Email -->
          <template v-if="step === 1">
            <h2 class="form-title">{{ t('forgotPassword.findPassword') }}</h2>
            <p class="form-subtitle">{{ t('forgotPassword.findPasswordSubtitle') }}</p>

            <el-form
              ref="formRef1"
              :model="form1"
              :rules="rules1"
              label-width="0"
              size="large"
              class="auth-form"
              @keyup.enter="handleSendCode"
            >
              <el-form-item prop="email">
                <el-input
                  v-model="form1.email"
                  :placeholder="t('forgotPassword.emailPlaceholder')"
                  :prefix-icon="Message"
                />
              </el-form-item>

              <el-form-item>
                <el-button
                  type="primary"
                  :loading="sending"
                  @click="handleSendCode"
                  class="submit-btn"
                  round
                >
                  {{ sending ? t('forgotPassword.sending') : t('forgotPassword.sendCode') }}
                </el-button>
              </el-form-item>
            </el-form>
          </template>

          <!-- Step 2: Reset -->
          <template v-else>
            <h2 class="form-title">{{ t('forgotPassword.setNewPassword') }}</h2>
            <p class="form-subtitle">{{ t('forgotPassword.codeSentTo') }} {{ form1.email }}</p>

            <el-form
              ref="formRef2"
              :model="form2"
              :rules="rules2"
              label-width="0"
              size="large"
              class="auth-form"
              @keyup.enter="handleReset"
            >
              <el-form-item prop="code">
                <el-input
                  v-model="form2.code"
                  :placeholder="t('forgotPassword.codePlaceholder')"
                  :prefix-icon="Key"
                />
              </el-form-item>

              <el-form-item prop="newPassword">
                <el-input
                  v-model="form2.newPassword"
                  type="password"
                  :placeholder="t('forgotPassword.newPasswordPlaceholder')"
                  :prefix-icon="Lock"
                  show-password
                />
              </el-form-item>

              <el-form-item prop="confirmPassword">
                <el-input
                  v-model="form2.confirmPassword"
                  type="password"
                  :placeholder="t('forgotPassword.confirmNewPasswordPlaceholder')"
                  :prefix-icon="Lock"
                  show-password
                />
              </el-form-item>

              <el-form-item>
                <el-button
                  type="primary"
                  :loading="resetting"
                  @click="handleReset"
                  class="submit-btn"
                  round
                >
                  {{ resetting ? t('forgotPassword.resetting') : t('forgotPassword.resetButton') }}
                </el-button>
              </el-form-item>
            </el-form>

            <div class="form-footer">
              <span>{{ t('forgotPassword.noCode') }}</span>
              <a href="javascript:void(0)" class="form-link" @click="step = 1">{{ t('forgotPassword.resend') }}</a>
            </div>
          </template>

          <div class="form-footer" :style="step === 2 ? 'display:none' : ''">
            <span>{{ t('forgotPassword.rememberPassword') }}</span>
            <router-link to="/login" class="form-link">{{ t('forgotPassword.backToLogin') }}</router-link>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { Message, Key, Lock } from '@element-plus/icons-vue'
import { useThemeStore } from '@/stores/theme'
import { passwordReset, passwordResetConfirm } from '@/api/auth'

const { t } = useI18n()

const router = useRouter()
const themeStore = useThemeStore()
const sending = ref(false)
const resetting = ref(false)
const formRef1 = ref()
const formRef2 = ref()
const step = ref(1)

const form1 = reactive({ email: '' })
const form2 = reactive({
  code: '',
  newPassword: '',
  confirmPassword: '',
})

const rules1 = {
  email: [
    { required: true, message: t('forgotPassword.emailRequired'), trigger: 'blur' },
    { type: 'email', message: t('forgotPassword.emailInvalid'), trigger: 'blur' },
  ],
}

const validateConfirm = (_rule: any, value: string, callback: any) => {
  if (value !== form2.newPassword) {
    callback(new Error(t('forgotPassword.passwordMismatch')))
  } else {
    callback()
  }
}

const rules2 = {
  code: [
    { required: true, message: t('forgotPassword.codeRequired'), trigger: 'blur' },
  ],
  newPassword: [
    { required: true, message: t('forgotPassword.newPasswordRequired'), trigger: 'blur' },
    { min: 6, message: t('forgotPassword.passwordMinLength'), trigger: 'blur' },
  ],
  confirmPassword: [
    { required: true, message: t('forgotPassword.confirmNewPasswordRequired'), trigger: 'blur' },
    { validator: validateConfirm, trigger: 'blur' },
  ],
}

const brandItems = [
  { icon: 'Search', label: t('login.autoDiscoveryLabel') },
  { icon: 'Monitor', label: t('login.realtimeMonitorLabel') },
  { icon: 'WarningFilled', label: t('login.smartAlertLabel') },
  { icon: 'Connection', label: t('login.multiAgentLabel') },
]

async function handleSendCode() {
  const valid = await formRef1.value.validate().catch(() => false)
  if (!valid) return

  sending.value = true
  try {
    await passwordReset({ email: form1.email })
    ElMessage.success(t('forgotPassword.codeSent'))
    step.value = 2
  } catch {
    // handled by interceptor
  } finally {
    sending.value = false
  }
}

async function handleReset() {
  const valid = await formRef2.value.validate().catch(() => false)
  if (!valid) return

  resetting.value = true
  try {
    await passwordResetConfirm({
      code: form2.code,
      new_password: form2.newPassword,
      new_password2: form2.confirmPassword,
    })
    ElMessage.success(t('forgotPassword.resetSuccess'))
    router.push('/login')
  } catch {
    // handled by interceptor
  } finally {
    resetting.value = false
  }
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-primary);
  position: relative;
  overflow: hidden;
}
.auth-bg {
  position: absolute;
  inset: 0;
  z-index: 0;
  background: linear-gradient(160deg, var(--hero-bg-start) 0%, var(--hero-bg-mid) 50%, var(--hero-bg-end) 100%);
}
.bg-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.3;
}
.orb-1 {
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, #409eff 0%, transparent 70%);
  top: -15%;
  right: -5%;
}
.orb-2 {
  width: 350px;
  height: 350px;
  background: radial-gradient(circle, #8b5cf6 0%, transparent 70%);
  bottom: -10%;
  left: 30%;
}
.bg-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(var(--border-color) 1px, transparent 1px),
    linear-gradient(90deg, var(--border-color) 1px, transparent 1px);
  background-size: 60px 60px;
  opacity: 0.08;
}
.back-link {
  position: fixed;
  top: 24px;
  left: 24px;
  z-index: 10;
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 14px;
  padding: 8px 16px;
  border-radius: 8px;
  background: var(--bg-navbar);
  backdrop-filter: blur(12px);
  border: 1px solid var(--border-color);
  transition: all 0.2s;
}
.back-link:hover {
  color: #409eff;
  border-color: #409eff;
}
.theme-btn {
  position: fixed;
  top: 24px;
  right: 24px;
  z-index: 10;
  width: 38px;
  height: 38px;
  border-radius: 8px;
  border: 1px solid var(--border-color);
  background: var(--bg-navbar);
  backdrop-filter: blur(12px);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  transition: all 0.2s;
}
.theme-btn:hover {
  border-color: #409eff;
  color: #409eff;
}
.auth-container {
  position: relative;
  z-index: 1;
  display: flex;
  width: 900px;
  max-width: 94vw;
  min-height: 560px;
  border-radius: 20px;
  overflow: hidden;
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.12);
}
.auth-brand {
  flex: 1;
  background: linear-gradient(135deg, #1a3a6b, #2a1a5e);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px;
}
.brand-card {
  color: #fff;
}
.brand-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 32px;
}
.logo-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: linear-gradient(135deg, #409eff, #337ecc);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
}
.brand-logo-text {
  display: flex;
  flex-direction: column;
  line-height: 1.15;
}
.brand-logo-text .logo-main {
  font-size: 22px;
  font-weight: 800;
  letter-spacing: 1px;
  color: #fff;
}
.brand-logo-text .logo-sub {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.55);
  letter-spacing: 0.3px;
}
.brand-logo-text .accent-l {
  font-size: 15px;
  font-weight: 700;
  color: #60b0ff;
}
.brand-title {
  font-size: 28px;
  font-weight: 700;
  margin-bottom: 12px;
}
.brand-desc {
  font-size: 15px;
  color: rgba(255, 255, 255, 0.65);
  line-height: 1.7;
  margin-bottom: 32px;
}
.brand-features {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.brand-feature {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.8);
}
.auth-form-panel {
  flex: 1;
  background: var(--bg-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px;
  transition: background 0.3s;
}
.form-card {
  width: 100%;
  max-width: 360px;
}
.form-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-heading);
  margin-bottom: 8px;
}
.form-subtitle {
  font-size: 14px;
  color: var(--text-muted);
  margin-bottom: 32px;
}
.auth-form .el-form-item {
  margin-bottom: 20px;
}
.submit-btn {
  width: 100%;
  height: 44px;
  font-size: 16px;
  font-weight: 600;
}
.form-footer {
  text-align: center;
  margin-top: 24px;
  font-size: 14px;
  color: var(--text-muted);
}
.form-link {
  color: #409eff;
  text-decoration: none;
  font-weight: 500;
  margin-left: 4px;
}
.form-link:hover {
  text-decoration: underline;
}
@media (max-width: 768px) {
  .auth-container {
    flex-direction: column;
    min-height: auto;
  }
  .auth-brand {
    display: none;
  }
  .auth-form-panel {
    padding: 32px 24px;
  }
}
</style>
