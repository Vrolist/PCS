<template>
  <div class="privacy-page">
    <!-- Navbar -->
    <header class="navbar" :class="{ 'nav-scrolled': scrolled }">
      <div class="container nav-container">
        <router-link to="/" class="logo">
          <div class="logo-icon"><ServerIcon /></div>
          <div class="logo-wrapper">
            <span class="logo-main">PCS</span>
            <span class="logo-sub"><span class="accent-l">P</span>ve<span class="accent-l">C</span>luster<span class="accent-l">S</span>can</span>
          </div>
        </router-link>
        <nav class="nav-links">
          <router-link to="/" class="nav-link">{{ t('nav.home') }}</router-link>
          <router-link to="/features" class="nav-link">{{ t('nav.monitorData') }}</router-link>
          <router-link to="/ai-assistant" class="nav-link">{{ t('nav.aiAssistant') }}</router-link>
        </nav>
        <nav class="nav-actions">
          <button class="theme-btn" @click="themeStore.toggle" :title="themeStore.theme === 'dark' ? t('header.switchToLight') : t('header.switchToDark')">
            <el-icon :size="20"><Sunny v-if="themeStore.theme === 'dark'" /><Moon v-else /></el-icon>
          </button>
          <template v-if="authStore.isLoggedIn">
            <span class="nav-user">{{ authStore.user?.username }}</span>
            <router-link to="/dashboard">
              <el-button type="primary" round size="default">{{ t('nav.dashboard') }}</el-button>
            </router-link>
          </template>
          <template v-else>
            <router-link to="/login">
              <el-button :type="themeStore.theme === 'dark' ? 'primary' : ''" plain round size="default">{{ t('login.login') }}</el-button>
            </router-link>
            <router-link to="/register">
              <el-button type="primary" round size="default">{{ t('home.register') }}</el-button>
            </router-link>
          </template>
        </nav>
      </div>
    </header>

    <!-- Hero -->
    <section class="hero">
      <div class="hero-bg">
        <div class="gradient-orb orb-1"></div>
        <div class="gradient-orb orb-2"></div>
        <div class="grid-pattern"></div>
      </div>
      <div class="container hero-content">
        <div class="badge">{{ t('privacy.badge') }}</div>
        <h1 class="hero-title">
          <span class="title-line accent">{{ t('privacy.title') }}</span>
        </h1>
        <p class="hero-subtitle">{{ t('privacy.subtitle') }}</p>
        <div class="hero-meta">
          <span class="updated">{{ t('privacy.lastUpdated') }}</span>
        </div>
      </div>
    </section>

    <!-- Content -->
    <section class="content-section">
      <div class="container">
        <div class="intro-card">
          <p>{{ t('privacy.intro') }}</p>
        </div>

        <div class="policy-card" v-for="(s, i) in sections" :key="s.title">
          <div class="pc-index">0{{ i + 1 }}</div>
          <div class="pc-body">
            <h2>{{ t(s.title) }}</h2>
            <p class="pc-desc">{{ t(s.desc) }}</p>
          </div>
        </div>

        <div class="contact-card">
          <div class="contact-icon"><el-icon :size="28"><Message /></el-icon></div>
          <div class="contact-body">
            <h2>{{ t('privacy.contact.title') }}</h2>
            <p>{{ t('privacy.contact.desc') }}</p>
            <a class="contact-email" :href="`mailto:${contactEmail}`">
              <el-icon :size="16"><Message /></el-icon>
              {{ t('privacy.contact.emailLabel') }}：{{ contactEmail }}
            </a>
          </div>
        </div>
      </div>
    </section>

    <!-- Footer -->
    <AppFooter />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useThemeStore } from '@/stores/theme'
import { useAuthStore } from '@/stores/auth'
import AppFooter from '@/components/AppFooter.vue'

const { t } = useI18n()
const themeStore = useThemeStore()
const authStore = useAuthStore()
const scrolled = ref(false)

const contactEmail = '1121031509@qq.com'

const sections = [
  { title: 'privacy.collect.title', desc: 'privacy.collect.desc' },
  { title: 'privacy.use.title', desc: 'privacy.use.desc' },
  { title: 'privacy.security.title', desc: 'privacy.security.desc' },
  { title: 'privacy.rights.title', desc: 'privacy.rights.desc' },
]

function onScroll() {
  scrolled.value = window.scrollY > 20
}
onMounted(() => {
  window.addEventListener('scroll', onScroll)
  if (authStore.isLoggedIn) {
    authStore.fetchUser()
  }
})
onUnmounted(() => window.removeEventListener('scroll', onScroll))
</script>

<style scoped>
.privacy-page {
  min-height: 100vh;
  background: var(--bg-primary);
  color: var(--text-primary);
  transition: background-color 0.3s, color 0.3s;
}

.container {
  max-width: 900px;
  margin: 0 auto;
  padding: 0 24px;
}

/* ============ Navbar ============ */
.navbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 100;
  background: var(--bg-navbar);
  backdrop-filter: blur(20px) saturate(200%);
  -webkit-backdrop-filter: blur(20px) saturate(200%);
  border-bottom: 1px solid transparent;
  transition: all 0.4s;
}
.navbar.nav-scrolled {
  box-shadow: 0 1px 8px rgba(0, 0, 0, 0.06);
}
.nav-container {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 64px;
}
.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
}
.logo-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: linear-gradient(135deg, #409eff, #337ecc);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 20px;
}
.logo-wrapper {
  display: flex;
  flex-direction: column;
  line-height: 1.15;
}
.logo-main {
  font-size: 20px;
  font-weight: 800;
  letter-spacing: 1px;
  color: var(--text-heading);
}
.logo-sub {
  font-size: 11px;
  color: var(--text-muted);
  letter-spacing: 0.3px;
}
.accent-l {
  font-size: 14px;
  font-weight: 700;
  color: #409eff;
}
.nav-links {
  display: flex;
  align-items: center;
  gap: 4px;
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
}
.nav-link {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-secondary);
  text-decoration: none;
  padding: 6px 14px;
  border-radius: 8px;
  transition: all 0.2s;
}
.nav-link:hover {
  color: var(--color-primary);
  background: rgba(64, 158, 255, 0.08);
}
.nav-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.nav-user {
  font-size: 14px;
  color: var(--text-secondary);
  font-weight: 500;
  margin-right: 4px;
}
.theme-btn {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  border: 1px solid var(--border-color);
  background: var(--bg-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  transition: all 0.2s;
  font-size: 18px;
}
.theme-btn:hover {
  border-color: #409eff;
  color: #409eff;
}

/* ============ Hero ============ */
.hero {
  position: relative;
  min-height: 55vh;
  display: flex;
  align-items: center;
  overflow: hidden;
  padding: 120px 0 80px;
  text-align: center;
}
.hero-bg {
  position: absolute;
  inset: 0;
  z-index: 0;
  background: linear-gradient(160deg, var(--hero-bg-start) 0%, var(--hero-bg-mid) 50%, var(--hero-bg-end) 100%);
  transition: background 0.5s;
}
.gradient-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.4;
  animation: orbFloat 20s ease-in-out infinite;
}
.orb-1 {
  width: 500px;
  height: 500px;
  background: radial-gradient(circle, #409eff40 0%, transparent 70%);
  top: -10%;
  left: -5%;
}
.orb-2 {
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, #8b5cf640 0%, transparent 70%);
  bottom: 10%;
  right: 10%;
  animation-delay: -7s;
}
@keyframes orbFloat {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(30px, -40px) scale(1.1); }
  66% { transform: translate(-20px, 20px) scale(0.9); }
}
.grid-pattern {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(var(--border-color) 1px, transparent 1px),
    linear-gradient(90deg, var(--border-color) 1px, transparent 1px);
  background-size: 60px 60px;
  opacity: 0.15;
  mask-image: radial-gradient(ellipse at 50% 60%, black 30%, transparent 70%);
  -webkit-mask-image: radial-gradient(ellipse at 50% 60%, black 30%, transparent 70%);
}
.hero-content {
  position: relative;
  z-index: 1;
}
.badge {
  display: inline-flex;
  padding: 6px 16px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 500;
  background: rgba(64, 158, 255, 0.1);
  color: #409eff;
  border: 1px solid rgba(64, 158, 255, 0.2);
  margin-bottom: 24px;
  letter-spacing: 0.3px;
}
.hero-title {
  margin-bottom: 20px;
}
.title-line {
  display: block;
  font-size: 44px;
  font-weight: 800;
  line-height: 1.15;
  color: var(--text-heading);
  letter-spacing: -1px;
}
.title-line.accent {
  background: linear-gradient(135deg, #409eff, #8b5cf6);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.hero-subtitle {
  font-size: 17px;
  line-height: 1.8;
  color: var(--text-secondary);
  margin: 0 auto 20px;
  max-width: 560px;
}
.hero-meta {
  display: flex;
  justify-content: center;
}
.updated {
  font-size: 13px;
  color: var(--text-muted);
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  padding: 6px 16px;
  border-radius: 20px;
}

/* ============ Content ============ */
.content-section {
  padding: 40px 0 100px;
  position: relative;
}
.intro-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-left: 4px solid #409eff;
  border-radius: 12px;
  padding: 24px 28px;
  margin-bottom: 28px;
}
.intro-card p {
  font-size: 15px;
  line-height: 1.9;
  color: var(--text-secondary);
  margin: 0;
}
.policy-card {
  display: flex;
  gap: 20px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  padding: 28px 28px;
  margin-bottom: 20px;
  transition: all 0.3s;
}
.policy-card:hover {
  border-color: rgba(64, 158, 255, 0.3);
  box-shadow: 0 8px 24px rgba(64, 158, 255, 0.08);
  transform: translateY(-2px);
}
.pc-index {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border-radius: 14px;
  flex-shrink: 0;
  font-size: 17px;
  font-weight: 700;
  color: #fff;
  background: linear-gradient(135deg, #409eff, #7c5cfc);
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.25);
}
.pc-body {
  flex: 1;
}
.pc-body h2 {
  font-size: 19px;
  font-weight: 700;
  color: var(--text-heading);
  margin: 0 0 12px;
}
.pc-desc {
  font-size: 14px;
  line-height: 2;
  color: var(--text-secondary);
  margin: 0;
  white-space: pre-line;
}
.contact-card {
  display: flex;
  gap: 20px;
  align-items: flex-start;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  padding: 28px 28px;
  margin-top: 32px;
}
.contact-icon {
  width: 52px;
  height: 52px;
  border-radius: 14px;
  background: linear-gradient(135deg, rgba(64, 158, 255, 0.12), rgba(139, 92, 246, 0.12));
  display: flex;
  align-items: center;
  justify-content: center;
  color: #409eff;
  flex-shrink: 0;
}
.contact-body h2 {
  font-size: 19px;
  font-weight: 700;
  color: var(--text-heading);
  margin: 0 0 8px;
}
.contact-body p {
  font-size: 14px;
  line-height: 1.8;
  color: var(--text-secondary);
  margin: 0 0 12px;
}
.contact-email {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: #409eff;
  text-decoration: none;
  padding: 8px 16px;
  border-radius: 10px;
  background: rgba(64, 158, 255, 0.1);
  border: 1px solid rgba(64, 158, 255, 0.2);
  transition: all 0.2s;
}
.contact-email:hover {
  background: rgba(64, 158, 255, 0.18);
  border-color: #409eff;
}

/* ============ Responsive ============ */
@media (max-width: 900px) {
  .nav-links { display: none; }
  .title-line { font-size: 34px; }
}
@media (max-width: 640px) {
  .policy-card { flex-direction: column; }
  .contact-card { flex-direction: column; }
}
</style>
