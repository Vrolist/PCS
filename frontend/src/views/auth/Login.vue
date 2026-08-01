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
    <div class="top-actions">
      <LangSwitcher />
      <button class="theme-btn" @click="themeStore.toggle">
        <el-icon :size="18"><Sunny v-if="themeStore.theme === 'dark'" /><Moon v-else /></el-icon>
      </button>
    </div>

    <div class="auth-container">
      <!-- Left: Brand -->
      <div class="auth-brand">
        <div class="brand-card">
          <div class="brand-logo">
            <div class="logo-icon"><ServerIcon :size="22" /></div>
            <div class="brand-logo-text">
              <span class="logo-main">PCS</span>
              <span class="logo-sub"><span class="accent-l">P</span>ve<span class="accent-l">C</span>luster<span class="accent-l">S</span>can</span>
            </div>
          </div>
          <h2 class="brand-title">{{ t('login.welcomeBack') }}</h2>
          <p class="brand-desc">{{ t('login.welcomeDesc') }}</p>
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
          <h2 class="form-title">{{ t('login.loginTitle') }}</h2>
          <p class="form-subtitle">{{ t('login.loginSubtitle') }}</p>

          <el-form
            ref="formRef"
            :model="form"
            :rules="rules"
            label-width="0"
            size="large"
            class="auth-form"
            @keyup.enter="handleLogin"
          >
            <el-form-item prop="username">
              <el-input
                v-model="form.username"
                :placeholder="t('login.usernamePlaceholder')"
                :prefix-icon="User"
              />
            </el-form-item>

            <el-form-item prop="password">
              <el-input
                v-model="form.password"
                type="password"
                :placeholder="t('login.passwordPlaceholder')"
                :prefix-icon="Lock"
                show-password
              />
            </el-form-item>

            <div class="form-options">
              <router-link to="/forgot-password" class="forgot-link">{{ t('login.forgotPassword') }}</router-link>
            </div>

            <el-form-item>
              <el-button
                type="primary"
                :loading="loading"
                @click="handleLogin"
                class="submit-btn"
                round
              >
                {{ loading ? t('login.loggingIn') : t('login.login') }}
              </el-button>
            </el-form-item>
          </el-form>

          <div class="form-footer">
            <span>{{ t('login.noAccount') }}</span>
            <router-link to="/register" class="form-link">{{ t('login.registerNow') }}</router-link>
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
import { User, Lock } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore } from '@/stores/theme'
import LangSwitcher from '@/components/LangSwitcher.vue'
import { login } from '@/api/auth'

const { t } = useI18n()

const router = useRouter()
const authStore = useAuthStore()
const themeStore = useThemeStore()
const loading = ref(false)
const formRef = ref()

const form = reactive({
  username: '',
  password: '',
})

const rules = {
  username: [{ required: true, message: t('login.usernameRequired'), trigger: 'blur' }],
  password: [{ required: true, message: t('login.passwordRequired'), trigger: 'blur' }],
}

const brandItems = [
  { icon: 'Search', label: t('login.autoDiscoveryLabel') },
  { icon: 'Monitor', label: t('login.realtimeMonitorLabel') },
  { icon: 'WarningFilled', label: t('login.smartAlertLabel') },
  { icon: 'Connection', label: t('login.multiAgentLabel') },
]

async function handleLogin() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    const res: any = await login(form)
    authStore.setToken(res.access)
    if (res.refresh) authStore.setRefreshToken(res.refresh)
    ElMessage.success(t('login.loginSuccess'))
    router.push('/dashboard')
  } catch (err: any) {
    const detail = err?.response?.data
    if (typeof detail === 'string') {
      ElMessage.error(detail)
    } else if (detail?.__all__) {
      ElMessage.error(Array.isArray(detail.__all__) ? detail.__all__[0] : detail.__all__)
    } else if (detail?.non_field_errors) {
      ElMessage.error(detail.non_field_errors[0])
    } else {
      ElMessage.error(t('login.loginFailed'))
    }
  } finally {
    loading.value = false
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

/* Background */
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

/* Top buttons */
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

.top-actions {
  position: fixed;
  top: 24px;
  right: 24px;
  z-index: 10;
  display: flex;
  align-items: center;
  gap: 8px;
}
.theme-btn {
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

/* Layout */
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

/* Left Brand Panel */
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

/* Right Form Panel */
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

.form-options {
  display: flex;
  justify-content: flex-end;
  margin: -12px 0 20px;
}
.forgot-link {
  font-size: 13px;
  color: var(--text-muted);
  text-decoration: none;
  transition: color 0.2s;
}
.forgot-link:hover {
  color: #409eff;
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

/* Responsive */
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
