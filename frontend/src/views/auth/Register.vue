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
      <span>返回首页</span>
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
            <div class="logo-icon"><ServerIcon :size="22" /></div>
            <div class="brand-logo-text">
              <span class="logo-main">PCS</span>
              <span class="logo-sub"><span class="accent-l">P</span>ve<span class="accent-l">C</span>luster<span class="accent-l">S</span>can</span>
            </div>
          </div>
          <h2 class="brand-title">开始免费使用</h2>
          <p class="brand-desc">注册即享完整的 PVE 集群监控能力，无需信用卡。</p>
          <div class="brand-benefits">
            <div class="benefit-row">
              <el-icon :size="18" color="#67c23a"><CircleCheckFilled /></el-icon>
              <div>
                <strong>多集群管理</strong>
                <p>同时管理多个 PVE 集群</p>
              </div>
            </div>
            <div class="benefit-row">
              <el-icon :size="18" color="#67c23a"><CircleCheckFilled /></el-icon>
              <div>
                <strong>实时告警</strong>
                <p>秒级检测异常并通知</p>
              </div>
            </div>
            <div class="benefit-row">
              <el-icon :size="18" color="#67c23a"><CircleCheckFilled /></el-icon>
              <div>
                <strong>历史趋势</strong>
                <p>数据归档，趋势可回溯</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Right: Form -->
      <div class="auth-form-panel">
        <div class="form-card">
          <h2 class="form-title">创建账号</h2>
          <p class="form-subtitle">填写以下信息完成注册</p>

          <el-form
            ref="formRef"
            :model="form"
            :rules="rules"
            label-width="0"
            size="large"
            class="auth-form"
            @keyup.enter="handleRegister"
          >
            <el-form-item prop="username">
              <el-input
                v-model="form.username"
                placeholder="用户名"
                :prefix-icon="User"
              />
            </el-form-item>

            <el-form-item prop="email">
              <el-input
                v-model="form.email"
                placeholder="邮箱"
                :prefix-icon="Message"
              />
            </el-form-item>

            <el-form-item prop="password">
              <el-input
                v-model="form.password"
                type="password"
                placeholder="密码"
                :prefix-icon="Lock"
                show-password
              />
            </el-form-item>

            <el-form-item prop="confirmPassword">
              <el-input
                v-model="form.confirmPassword"
                type="password"
                placeholder="确认密码"
                :prefix-icon="Lock"
                show-password
              />
            </el-form-item>

            <el-form-item>
              <el-button
                type="primary"
                :loading="loading"
                @click="handleRegister"
                class="submit-btn"
                round
              >
                {{ loading ? '注册中...' : '创建账号' }}
              </el-button>
            </el-form-item>
          </el-form>

          <div class="form-footer">
            <span>已有账号？</span>
            <router-link to="/login" class="form-link">立即登录</router-link>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock, Message, CircleCheckFilled } from '@element-plus/icons-vue'
import { useThemeStore } from '@/stores/theme'
import { register } from '@/api/auth'

const router = useRouter()
const themeStore = useThemeStore()
const loading = ref(false)
const formRef = ref()

const form = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: '',
})

const validateConfirm = (_rule: any, value: string, callback: any) => {
  if (value !== form.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 2, max: 32, message: '用户名长度 2-32 位', trigger: 'blur' },
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 位', trigger: 'blur' },
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    { validator: validateConfirm, trigger: 'blur' },
  ],
}

async function handleRegister() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    await register({
      username: form.username,
      email: form.email,
      password: form.password,
      password2: form.confirmPassword,
    })
    ElMessage.success('注册成功，请登录')
    router.push('/login')
  } catch {
    // error handled by request interceptor
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

/* Layout */
.auth-container {
  position: relative;
  z-index: 1;
  display: flex;
  width: 900px;
  max-width: 94vw;
  min-height: 600px;
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
.brand-benefits {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.benefit-row {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}
.benefit-row strong {
  display: block;
  font-size: 15px;
  color: #fff;
  margin-bottom: 2px;
}
.benefit-row p {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.6);
  margin: 0;
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
  margin-bottom: 28px;
}

.auth-form .el-form-item {
  margin-bottom: 18px;
}

.submit-btn {
  width: 100%;
  height: 44px;
  font-size: 16px;
  font-weight: 600;
}

.form-footer {
  text-align: center;
  margin-top: 20px;
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
