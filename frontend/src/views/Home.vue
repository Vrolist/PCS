<template>
  <div class="home-page">
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
        <div class="gradient-orb orb-3"></div>
        <div class="grid-pattern"></div>
      </div>
      <div class="container hero-content">
        <div class="hero-text">
          <div class="badge">{{ t('home.badge') }}</div>
          <h1 class="hero-title">
            <span class="title-line">{{ t('home.heroTitle1') }}</span>
            <span class="title-line accent">{{ t('home.heroTitle2') }}</span>
          </h1>
          <p class="hero-subtitle">
            {{ t('home.heroDesc') }}
          </p>
          <div class="hero-actions">
            <router-link to="/dashboard">
              <el-button type="primary" size="large" round class="cta-btn">
                {{ t('home.getStarted') }}
                <el-icon class="btn-arrow"><ArrowRight /></el-icon>
              </el-button>
            </router-link>
            <router-link to="/login">
              <el-button size="large" round plain class="login-btn">{{ t('home.hasAccount') }}</el-button>
            </router-link>
          </div>
          <div class="hero-stats">
            <div class="stat-item"><span class="stat-num">{{ t('home.zeroConfig') }}</span><span class="stat-label">{{ t('home.deployAgent') }}</span></div>
            <div class="stat-dot"></div>
            <div class="stat-item"><span class="stat-num">{{ t('home.fullyAuto') }}</span><span class="stat-label">{{ t('home.dataCollection') }}</span></div>
            <div class="stat-dot"></div>
            <div class="stat-item"><span class="stat-num">{{ t('home.intelligent') }}</span><span class="stat-label">{{ t('home.alertDetection') }}</span></div>
          </div>
        </div>
        <div class="hero-visual">
          <div
            class="visual-card"
            ref="visualCardRef"
            @mousemove="handleTilt"
            @mouseleave="handleTiltLeave"
            :style="tiltStyle"
          >
            <div class="vc-header">
              <div class="vc-dots"><span></span><span></span><span></span></div>
              <span class="vc-title">pve-cluster</span>
            </div>
            <div class="vc-body">
              <div class="vc-row" v-for="(w, i) in barWidths" :key="i">
                <div class="vc-dot" :class="i === 1 ? 'warn' : i === 3 ? 'ok' : ''"></div>
                <div class="vc-bar" :style="{ width: w + '%' }"></div>
                <span class="vc-label">{{ ['pve-1', 'pve-2', 'pve-3', 'pve-4'][i] }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Features -->
    <section class="features" id="features">
      <div class="container">
        <div class="section-header">
          <span class="section-tag">{{ t('home.coreFeatures') }}</span>
          <h2 class="section-title">{{ t('home.whyChoose') }}</h2>
          <p class="section-desc">{{ t('home.whyChooseDesc') }}</p>
        </div>
        <div class="feature-grid">
          <div v-for="(f, i) in features" :key="f.title" class="feature-card" :style="{ '--i': i }">
            <div class="feature-icon" :style="{ background: f.bg, color: f.color }">
              <el-icon :size="24"><component :is="f.icon" /></el-icon>
            </div>
            <h3>{{ f.title }}</h3>
            <p>{{ f.desc }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- Remote Ops Service -->
    <section class="remote-service">
      <div class="container">
        <div class="section-header">
          <span class="section-tag">{{ t('home.service') }}</span>
          <h2 class="section-title">{{ t('home.remoteOps') }}</h2>
          <p class="section-desc">{{ t('home.remoteOpsDesc') }}</p>
        </div>
        <div class="service-cards">
          <div class="service-card">
            <div class="service-icon"><el-icon :size="28"><Monitor /></el-icon></div>
            <h3>{{ t('home.monitoring247') }}</h3>
            <p>{{ t('home.monitoring247Desc') }}</p>
          </div>
          <div class="service-card">
            <div class="service-icon"><el-icon :size="28"><WarningFilled /></el-icon></div>
            <h3>{{ t('home.emergencyResponse') }}</h3>
            <p>{{ t('home.emergencyResponseDesc') }}</p>
          </div>
          <div class="service-card">
            <div class="service-icon"><el-icon :size="28"><Connection /></el-icon></div>
            <h3>{{ t('home.securityPatch') }}</h3>
            <p>{{ t('home.securityPatchDesc') }}</p>
          </div>
          <div class="service-card">
            <div class="service-icon"><el-icon :size="28"><TrendCharts /></el-icon></div>
            <h3>{{ t('home.healthReport') }}</h3>
            <p>{{ t('home.healthReportDesc') }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- How it works -->
    <section class="how-it-works">
      <div class="container">
        <div class="section-header">
          <span class="section-tag">{{ t('home.workflow') }}</span>
          <h2 class="section-title">{{ t('home.fourSteps') }}</h2>
          <p class="section-desc">{{ t('home.fourStepsDesc') }}</p>
        </div>
        <div class="steps">
          <div v-for="(step, i) in steps" :key="i" class="step-card">
            <div class="step-badge">0{{ i + 1 }}</div>
            <div class="step-content">
              <h3>{{ step.title }}</h3>
              <p>{{ step.desc }}</p>
            </div>
            <div v-if="i < steps.length - 1" class="step-connector"></div>
          </div>
        </div>
      </div>
    </section>

    <!-- CTA -->
    <section class="cta-section">
      <div class="container cta-container">
        <div class="cta-card">
          <h2>{{ t('home.ctaTitle') }}</h2>
          <p>{{ t('home.ctaDesc') }}</p>
          <router-link to="/dashboard">
            <el-button type="primary" size="large" round class="cta-btn">
              {{ t('home.startNow') }}
              <el-icon class="btn-arrow"><ArrowRight /></el-icon>
            </el-button>
          </router-link>
        </div>
      </div>
    </section>

    <!-- Footer -->
    <footer class="footer">
      <div class="container">
        <div class="footer-top">
          <div class="footer-brand">
            <div class="logo">
              <div class="logo-icon-footer"><ServerIcon size="28" /></div>
              <div class="logo-wrapper">
                <span class="logo-main">PCS</span>
                <span class="logo-sub"><span class="accent-l">P</span>ve<span class="accent-l">C</span>luster<span class="accent-l">S</span>can</span>
              </div>
            </div>
            <p class="footer-desc">{{ t('home.footerDesc') }}</p>
          </div>
          <div class="footer-links">
            <div class="footer-col">
              <h4>{{ t('home.product') }}</h4>
              <a href="#features">{{ t('home.features') }}</a>
              <a href="#">{{ t('home.pricing') }}</a>
            </div>
            <div class="footer-col">
              <h4>{{ t('home.support') }}</h4>
              <a href="#">{{ t('home.docs') }}</a>
              <a href="#">API</a>
            </div>
          </div>
        </div>
        <div class="footer-bottom">
          <p>&copy; 2026 pve-cluster-scan. All rights reserved.</p>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useThemeStore } from '@/stores/theme'
import { useAuthStore } from '@/stores/auth'

const { t } = useI18n()
const themeStore = useThemeStore()
const authStore = useAuthStore()
const scrolled = ref(false)

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

  // Parallax tilt for visual console card
const visualCardRef = ref<HTMLElement | null>(null)
const tiltX = ref(0)
const tiltY = ref(0)
const tiltTransition = ref(true)

function handleTilt(e: MouseEvent) {
  const card = visualCardRef.value
  if (!card) return
  const rect = card.getBoundingClientRect()
  const centerX = rect.left + rect.width / 2
  const centerY = rect.top + rect.height / 2
  const mouseX = e.clientX - centerX
  const mouseY = e.clientY - centerY
  const rangeX = rect.width / 2
  const rangeY = rect.height / 2
  const maxAngle = 10
  tiltX.value = -(mouseY / rangeY) * maxAngle
  tiltY.value = (mouseX / rangeX) * maxAngle
  tiltTransition.value = false
}

function handleTiltLeave() {
  tiltX.value = 0
  tiltY.value = 0
  tiltTransition.value = true
}

const tiltStyle = computed(() => ({
  transform: `rotateX(${tiltX.value}deg) rotateY(${tiltY.value}deg)`,
  transition: tiltTransition.value ? 'transform 0.5s ease' : 'transform 0.05s',
}))

// Periodic bar width animation
const barWidths = ref([55, 45, 60, 50])

function randomizeBars() {
  barWidths.value = barWidths.value.map(() => 40 + Math.round(Math.random() * 50))
}

let barTimer: ReturnType<typeof setInterval>
onMounted(() => {
  barTimer = setInterval(randomizeBars, 10000)
})
onUnmounted(() => {
  clearInterval(barTimer)
})

const features = computed(() => [
  {
    title: t('home.autoDiscovery'),
    desc: t('home.autoDiscoveryDesc'),
    icon: 'Search',
    color: '#409eff',
    bg: 'rgba(64,158,255,0.12)',
  },
  {
    title: t('home.realtimeMonitor'),
    desc: t('home.realtimeMonitorDesc'),
    icon: 'Monitor',
    color: '#67c23a',
    bg: 'rgba(103,194,58,0.12)',
  },
  {
    title: t('home.smartDetection'),
    desc: t('home.smartDetectionDesc'),
    icon: 'WarningFilled',
    color: '#e6a23c',
    bg: 'rgba(230,162,60,0.12)',
  },
  {
    title: t('home.multiAgent'),
    desc: t('home.multiAgentDesc'),
    icon: 'Connection',
    color: '#8b5cf6',
    bg: 'rgba(139,92,246,0.12)',
  },
  {
    title: t('home.trendAnalysis'),
    desc: t('home.trendAnalysisDesc'),
    icon: 'TrendCharts',
    color: '#f56c6c',
    bg: 'rgba(245,108,108,0.12)',
  },
  {
    title: t('home.cephIntegration'),
    desc: t('home.cephIntegrationDesc'),
    icon: 'DataAnalysis',
    color: '#409eff',
    bg: 'rgba(64,158,255,0.12)',
  },
])

const steps = computed(() => [
  {
    title: t('home.step1'),
    desc: t('home.step1Desc'),
  },
  {
    title: t('home.step2'),
    desc: t('home.step2Desc'),
  },
  {
    title: t('home.step3'),
    desc: t('home.step3Desc'),
  },
  {
    title: t('home.step4'),
    desc: t('home.step4Desc'),
  },
])
</script>

<style scoped>
.home-page {
  min-height: 100vh;
  background: var(--bg-primary);
  color: var(--text-primary);
  transition: background-color 0.3s, color 0.3s;
}

.container {
  max-width: 1100px;
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
  border-bottom-color: transparent;
  box-shadow: 0 1px 8px rgba(0, 0, 0, 0.06);
}
:root .navbar.nav-scrolled {
  border-bottom: 1px solid transparent;
  background-image: linear-gradient(var(--bg-navbar), var(--bg-navbar)), linear-gradient(90deg, #409eff, #8b5cf6, #409eff);
  background-origin: padding-box, border-box;
  background-clip: padding-box, border-box;
}
.dark .navbar.nav-scrolled {
  border-bottom-color: rgba(64, 158, 255, 0.12);
  box-shadow: 0 2px 20px rgba(0, 0, 0, 0.2);
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
.logo-text {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-heading);
}
.logo-accent {
  color: #409eff;
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
.logo-icon-footer {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: linear-gradient(135deg, #409eff, #337ecc);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
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
  min-height: 100vh;
  display: flex;
  align-items: center;
  overflow: hidden;
  padding: 120px 0 80px;
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
  animation-delay: 0s;
}
.orb-2 {
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, #8b5cf640 0%, transparent 70%);
  bottom: 10%;
  right: 10%;
  animation-delay: -7s;
}
.orb-3 {
  width: 300px;
  height: 300px;
  background: radial-gradient(circle, #67c23a30 0%, transparent 70%);
  top: 40%;
  left: 50%;
  animation-delay: -14s;
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
  display: flex;
  align-items: center;
  gap: 60px;
  width: 100%;
}

.hero-text {
  flex: 1;
  max-width: 580px;
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
  font-size: 52px;
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
  margin-bottom: 32px;
  max-width: 480px;
}

.hero-actions {
  display: flex;
  gap: 12px;
  margin-bottom: 40px;
}
.cta-btn {
  font-weight: 600;
  padding: 12px 28px !important;
  font-size: 16px !important;
}
.btn-arrow {
  margin-left: 4px;
  transition: transform 0.2s;
}
.cta-btn:hover .btn-arrow {
  transform: translateX(4px);
}
.login-btn {
  padding: 12px 24px !important;
  font-size: 16px !important;
}

.hero-stats {
  display: flex;
  align-items: center;
  gap: 20px;
}
.stat-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.stat-num {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-heading);
}
.stat-label {
  font-size: 13px;
  color: var(--text-muted);
}
.stat-dot {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--text-muted);
  opacity: 0.4;
}

/* Hero Visual */
.hero-visual {
  flex: 1;
  max-width: 420px;
  perspective: 800px;
}
.visual-card {
  background: rgba(255, 255, 255, 0.10);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.20);
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 30px 80px rgba(0, 0, 0, 0.10);
  transform: rotateY(-8deg) rotateX(4deg);
  transition: transform 0.4s;
}
.visual-card:hover {
  box-shadow: 0 30px 80px rgba(0, 0, 0, 0.15);
}
.dark .visual-card {
  background: rgba(255, 255, 255, 0.04);
  border-color: rgba(255, 255, 255, 0.08);
}
:root .visual-card {
  background: rgba(255, 255, 255, 0.75);
  border-color: rgba(200, 210, 230, 0.40);
  box-shadow: 0 30px 60px rgba(0, 0, 0, 0.08);
}
.vc-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 18px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}
.vc-dots {
  display: flex;
  gap: 6px;
}
.vc-dots span {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
}
.vc-dots span:first-child { background: #f56c6c; }
.vc-dots span:nth-child(2) { background: #e6a23c; }
.vc-dots span:last-child { background: #67c23a; }
.vc-title {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.6);
  font-weight: 500;
  letter-spacing: 0.5px;
}
.dark .vc-title {
  color: rgba(255, 255, 255, 0.5);
}
.vc-body {
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.vc-row {
  display: flex;
  align-items: center;
  gap: 10px;
}
.vc-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #67c23a;
  flex-shrink: 0;
}
.vc-dot.warn { background: #e6a23c; }
.vc-dot.ok { background: #67c23a; }
.vc-bar {
  height: 6px;
  border-radius: 3px;
  background: linear-gradient(90deg, #409eff, #8b5cf6);
  opacity: 0.6;
  transition: width 0.3s;
}
.dark .vc-bar {
  opacity: 0.8;
}
:root .vc-bar {
  opacity: 0.85;
  background: linear-gradient(90deg, #409eff, #6d69d0);
}
.vc-label {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.85);
  font-weight: 600;
  flex-shrink: 0;
  letter-spacing: 0.3px;
}
:root .vc-label {
  color: #3a3d4a;
}
:root .vc-title {
  color: #4e5159;
}

/* ============ Features ============ */
.features {
  padding: 100px 0;
  position: relative;
}
.features::before {
  content: '';
  position: absolute;
  top: -60px;
  left: 0;
  right: 0;
  height: 60px;
  background: linear-gradient(180deg, transparent, var(--bg-primary));
  pointer-events: none;
  z-index: 1;
}
.features::after {
  content: '';
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 15% 30%, rgba(64, 158, 255, 0.04) 0%, transparent 40%),
    radial-gradient(circle at 85% 70%, rgba(139, 92, 246, 0.04) 0%, transparent 40%);
  pointer-events: none;
  z-index: 0;
}

.section-header {
  text-align: center;
  margin-bottom: 56px;
  position: relative;
  z-index: 1;
}
.section-tag {
  display: inline-flex;
  padding: 4px 14px;
  border-radius: 16px;
  font-size: 13px;
  font-weight: 500;
  background: rgba(64, 158, 255, 0.1);
  color: #409eff;
  border: 1px solid rgba(64, 158, 255, 0.15);
  margin-bottom: 16px;
}
.section-title {
  font-size: 34px;
  font-weight: 800;
  color: var(--text-heading);
  margin-bottom: 12px;
  letter-spacing: -0.5px;
}
.section-desc {
  font-size: 16px;
  color: var(--text-muted);
}

.feature-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
  position: relative;
  z-index: 1;
}

.feature-card {
  background: var(--bg-card);
  border-radius: 16px;
  padding: 32px 28px;
  border: 1px solid var(--border-color);
  transition: all 0.35s cubic-bezier(0.25, 0.46, 0.45, 0.94);
  animation: fadeUp 0.6s both;
  animation-delay: calc(var(--i) * 0.08s);
}
@keyframes fadeUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}
.feature-card:hover {
  transform: translateY(-6px);
  box-shadow: var(--card-hover-shadow);
  border-color: rgba(64, 158, 255, 0.3);
}

.feature-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 20px;
  font-size: 24px;
}
.feature-card h3 {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-heading);
  margin-bottom: 10px;
}
.feature-card p {
  font-size: 14px;
  line-height: 1.7;
  color: var(--text-secondary);
}

/* ============ Remote Ops Service ============ */
.remote-service {
  padding: 100px 0;
  background: var(--bg-secondary);
  transition: background 0.3s;
  position: relative;
}
.remote-service::before {
  content: '';
  position: absolute;
  top: -60px;
  left: 0;
  right: 0;
  height: 60px;
  background: linear-gradient(180deg, transparent, var(--bg-secondary));
  pointer-events: none;
  z-index: 1;
}
.service-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24px;
  margin-top: 48px;
  position: relative;
  z-index: 1;
}
.service-card {
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  padding: 32px 24px;
  text-align: center;
  transition: all 0.3s;
}
.service-card:hover {
  transform: translateY(-4px);
  border-color: #409eff;
  box-shadow: 0 12px 32px rgba(64, 158, 255, 0.12);
}
.service-icon {
  width: 56px;
  height: 56px;
  border-radius: 14px;
  background: linear-gradient(135deg, rgba(64,158,255,0.12), rgba(139,92,246,0.12));
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 16px;
  color: #409eff;
}
.service-card h3 {
  font-size: 17px;
  font-weight: 600;
  color: var(--text-heading);
  margin-bottom: 8px;
}
.service-card p {
  font-size: 14px;
  color: var(--text-muted);
  line-height: 1.7;
  margin: 0;
}
@media (max-width: 992px) {
  .service-cards { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 600px) {
  .service-cards { grid-template-columns: 1fr; }
}

/* ============ How it works ============ */
.how-it-works {
  padding: 100px 0;
  position: relative;
}
.how-it-works::before {
  content: '';
  position: absolute;
  top: -60px;
  left: 0;
  right: 0;
  height: 60px;
  background: linear-gradient(180deg, transparent, var(--bg-primary));
  pointer-events: none;
  z-index: 1;
}
.dark .how-it-works {
  background: transparent;
}
:root .how-it-works {
  background: transparent;
}

.steps {
  display: flex;
  flex-direction: column;
  gap: 20px;
  max-width: 720px;
  margin: 0 auto;
  position: relative;
  z-index: 1;
}

.step-card {
  display: flex;
  align-items: flex-start;
  gap: 24px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  padding: 28px 32px;
  transition: all 0.35s cubic-bezier(0.25, 0.46, 0.45, 0.94);
  position: relative;
}
.step-card:hover {
  border-color: #409eff;
  box-shadow: 0 8px 28px rgba(64, 158, 255, 0.12);
  transform: translateX(4px);
}

.step-badge {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border-radius: 12px;
  flex-shrink: 0;
  font-size: 16px;
  font-weight: 700;
  color: #fff;
  background: linear-gradient(135deg, #409eff, #7c5cfc);
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.25);
  position: relative;
  z-index: 1;
}
.step-card:nth-child(2) .step-badge {
  background: linear-gradient(135deg, #67c23a, #36a86b);
  box-shadow: 0 4px 12px rgba(103, 194, 58, 0.25);
}
.step-card:nth-child(3) .step-badge {
  background: linear-gradient(135deg, #e6a23c, #d4842f);
  box-shadow: 0 4px 12px rgba(230, 162, 60, 0.25);
}
.step-card:nth-child(4) .step-badge {
  background: linear-gradient(135deg, #8b5cf6, #6366f1);
  box-shadow: 0 4px 12px rgba(139, 92, 246, 0.25);
}
:root .step-badge {
  box-shadow: 0 4px 14px rgba(64, 158, 255, 0.18);
}
:root .step-card:nth-child(2) .step-badge {
  box-shadow: 0 4px 14px rgba(103, 194, 58, 0.18);
}
:root .step-card:nth-child(3) .step-badge {
  box-shadow: 0 4px 14px rgba(230, 162, 60, 0.18);
}
:root .step-card:nth-child(4) .step-badge {
  box-shadow: 0 4px 14px rgba(139, 92, 246, 0.18);
}

.step-content {
  flex: 1;
  padding-top: 4px;
}
.step-content h3 {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-heading);
  margin-bottom: 6px;
}
.step-content p {
  font-size: 14px;
  line-height: 1.7;
  color: var(--text-secondary);
  margin: 0;
}

.step-connector {
  position: absolute;
  bottom: -20px;
  left: 40px;
  width: 2px;
  height: 20px;
  background: linear-gradient(180deg, #409eff, transparent);
  opacity: 0.4;
}
.step-card:last-child .step-connector {
  display: none;
}

/* ============ CTA ============ */
.cta-section {
  padding: 80px 0;
  position: relative;
  background: var(--bg-secondary);
  transition: background 0.3s;
}
.cta-section::before {
  content: '';
  position: absolute;
  top: -60px;
  left: 0;
  right: 0;
  height: 60px;
  background: linear-gradient(180deg, transparent, var(--bg-secondary));
  pointer-events: none;
  z-index: 1;
}
.cta-container {
  position: relative;
}
.cta-card {
  text-align: center;
  background: linear-gradient(135deg, #1a3a6b, #2a1a5e);
  border-radius: 20px;
  padding: 64px 40px;
  color: #fff;
}
.cta-card h2 {
  font-size: 28px;
  font-weight: 700;
  margin-bottom: 12px;
}
.cta-card p {
  font-size: 16px;
  color: rgba(255, 255, 255, 0.7);
  margin-bottom: 32px;
}

/* ============ Footer ============ */
.footer {
  padding: 60px 0 32px;
  background: var(--footer-bg);
  color: #909399;
  transition: background 0.3s;
}
.footer-top {
  display: flex;
  justify-content: space-between;
  margin-bottom: 40px;
}
.footer-brand .logo {
  margin-bottom: 12px;
}
.footer-brand .logo-main {
  color: #e0e0f0;
}
.footer-brand .logo-sub {
  color: #8080a0;
}
.footer-brand .accent-l {
  color: #60b0ff;
}
.footer-desc {
  font-size: 14px;
  color: #707090;
}
.footer-links {
  display: flex;
  gap: 48px;
}
.footer-col h4 {
  font-size: 14px;
  font-weight: 600;
  color: #c0c0d0;
  margin-bottom: 12px;
}
.footer-col a {
  display: block;
  font-size: 14px;
  color: #707090;
  text-decoration: none;
  margin-bottom: 8px;
  transition: color 0.2s;
}
.footer-col a:hover {
  color: #409eff;
}
.footer-bottom {
  padding-top: 24px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  text-align: center;
  font-size: 13px;
}

/* ============ Responsive ============ */
@media (max-width: 900px) {
  .hero-content {
    flex-direction: column;
  }
  .hero-visual { display: none; }
  .title-line { font-size: 36px; }
  .feature-grid { grid-template-columns: 1fr 1fr; }
}
@media (max-width: 640px) {
  .feature-grid { grid-template-columns: 1fr; }
  .hero-stats { flex-wrap: wrap; }
  .footer-top { flex-direction: column; gap: 32px; }
}
</style>
