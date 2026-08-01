<template>
  <div class="features-page">
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
          <router-link to="/features" class="nav-link active">{{ t('nav.monitorData') }}</router-link>
          <router-link to="/ai-assistant" class="nav-link">{{ t('nav.aiAssistant') }}</router-link>
        </nav>
        <nav class="nav-actions">
          <LangSwitcher />
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
        <div class="hero-text">
          <div class="badge">{{ t('features.badge') }}</div>
          <h1 class="hero-title">
            <span class="title-line">{{ t('features.heroTitle1') }}</span>
            <span class="title-line accent">{{ t('features.heroTitle2') }}</span>
          </h1>
          <p class="hero-subtitle">{{ t('features.heroDesc') }}</p>
          <div class="hero-actions">
            <router-link to="/dashboard">
              <el-button type="primary" size="large" round class="cta-btn">
                {{ t('home.getStarted') }}
                <el-icon class="btn-arrow"><ArrowRight /></el-icon>
              </el-button>
            </router-link>
            <router-link to="/ai-assistant">
              <el-button size="large" round plain class="login-btn">{{ t('features.learnAI') }}</el-button>
            </router-link>
          </div>
          <div class="hero-stats">
            <div class="stat-item"><span class="stat-num">{{ t('features.statNodes') }}</span><span class="stat-label">{{ t('features.statNodesLabel') }}</span></div>
            <div class="stat-dot"></div>
            <div class="stat-item"><span class="stat-num">{{ t('features.statLayers') }}</span><span class="stat-label">{{ t('features.statLayersLabel') }}</span></div>
            <div class="stat-dot"></div>
            <div class="stat-item"><span class="stat-num">{{ t('features.statFields') }}</span><span class="stat-label">{{ t('features.statFieldsLabel') }}</span></div>
          </div>
        </div>
        <div class="hero-visual">
          <div class="flow-card">
            <div class="fc-header">
              <div class="fc-dots"><span></span><span></span><span></span></div>
              <span class="fc-title">{{ t('features.flowTitle') }}</span>
            </div>
            <div class="fc-body">
              <div class="flow-item" v-for="(item, i) in dataFlowItems" :key="i" :style="{ '--delay': i * 0.18 }">
                <div class="flow-icon" :style="{ background: item.bg }">
                  <el-icon :size="18"><component :is="item.icon" /></el-icon>
                </div>
                <div class="flow-label">{{ t(item.label) }}</div>
                <div class="flow-arrow" v-if="i < dataFlowItems.length - 1"><el-icon :size="14"><ArrowRight /></el-icon></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 四大核心监控能力 -->
    <section class="capability-section">
      <div class="container">
        <div class="section-header">
          <span class="section-tag">{{ t('features.capabilityTag') }}</span>
          <h2 class="section-title">{{ t('features.capabilityTitle') }}</h2>
          <p class="section-desc">{{ t('features.capabilityDesc') }}</p>
        </div>
        <div class="capability-grid">
          <div v-for="(feature, i) in largeFeatures" :key="i" class="capability-card" :style="{ '--i': i }">
            <div class="cc-icon" :style="{ background: feature.bg, color: feature.color }">
              <el-icon :size="30"><component :is="feature.icon" /></el-icon>
            </div>
            <h3>{{ t(feature.title) }}</h3>
            <p class="cc-desc">{{ t(feature.desc) }}</p>
            <div class="cc-details">
              <div class="cc-detail" v-for="(detail, j) in feature.details" :key="j">
                <span class="detail-dot" :style="{ background: detail.color }"></span>
                <span>{{ t(detail.text) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 全量数据类型 -->
    <section class="data-section">
      <div class="container">
        <div class="section-header">
          <span class="section-tag">{{ t('features.dataTypes.tag') }}</span>
          <h2 class="section-title">{{ t('features.dataTypes.title') }}</h2>
          <p class="section-desc">{{ t('features.dataTypes.desc') }}</p>
        </div>
        <div class="data-grid">
          <div v-for="(type, i) in dataTypes" :key="type.title" class="data-card" :style="{ '--i': i }">
            <div class="dt-icon" :style="{ background: type.bg }">
              <el-icon :size="26"><component :is="type.icon" /></el-icon>
            </div>
            <h4>{{ t(type.title) }}</h4>
            <p>{{ t(type.desc) }}</p>
            <div class="dt-fields">
              <span class="dt-field" v-for="(field, j) in type.fields" :key="j">{{ field }}</span>
            </div>
            <div class="dt-indicator">
              <span class="dt-pulse"></span>
              <span>{{ t('features.dataTypes.live') }}</span>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 特性补充 -->
    <section class="extra-section">
      <div class="container">
        <div class="section-header">
          <span class="section-tag">{{ t('features.extraTag') }}</span>
          <h2 class="section-title">{{ t('features.extraTitle') }}</h2>
          <p class="section-desc">{{ t('features.extraDesc') }}</p>
        </div>
        <div class="extra-grid">
          <div v-for="(feature, i) in smallFeatures" :key="feature.title" class="extra-card" :style="{ '--i': i }">
            <div class="ex-icon" :style="{ background: feature.bg, color: feature.color }">
              <el-icon :size="22"><component :is="feature.icon" /></el-icon>
            </div>
            <h4>{{ t(feature.title) }}</h4>
            <p>{{ t(feature.desc) }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- 数据流 / 接入流程 -->
    <section class="flow-section">
      <div class="container">
        <div class="section-header">
          <span class="section-tag">{{ t('features.workflowTag') }}</span>
          <h2 class="section-title">{{ t('features.workflowTitle') }}</h2>
          <p class="section-desc">{{ t('features.workflowDesc') }}</p>
        </div>
        <div class="steps">
          <div v-for="(step, i) in workflowSteps" :key="i" class="step-card">
            <div class="step-badge">0{{ i + 1 }}</div>
            <div class="step-content">
              <h3>{{ t(step.title) }}</h3>
              <p>{{ t(step.desc) }}</p>
            </div>
            <div v-if="i < workflowSteps.length - 1" class="step-connector"></div>
          </div>
        </div>
      </div>
    </section>

    <!-- CTA -->
    <section class="cta-section">
      <div class="container cta-container">
        <div class="cta-card">
          <h2>{{ t('features.ctaTitle') }}</h2>
          <p>{{ t('features.ctaDesc') }}</p>
          <router-link to="/register">
            <el-button type="primary" size="large" round class="cta-btn">
              {{ t('home.startNow') }}
              <el-icon class="btn-arrow"><ArrowRight /></el-icon>
            </el-button>
          </router-link>
        </div>
      </div>
    </section>

    <!-- Footer -->
    <AppFooter />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useThemeStore } from '@/stores/theme'
import { useAuthStore } from '@/stores/auth'
import AppFooter from '@/components/AppFooter.vue'
import LangSwitcher from '@/components/LangSwitcher.vue'

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

const dataFlowItems = [
  { label: 'features.flow.agent', icon: 'Connection', bg: 'linear-gradient(135deg,#409eff,#337ecc)' },
  { label: 'features.flow.collect', icon: 'Monitor', bg: 'linear-gradient(135deg,#67c23a,#36a86b)' },
  { label: 'features.flow.clean', icon: 'DataAnalysis', bg: 'linear-gradient(135deg,#e6a23c,#d4842f)' },
  { label: 'features.flow.upload', icon: 'Upload', bg: 'linear-gradient(135deg,#f56c6c,#d03050)' },
  { label: 'features.flow.store', icon: 'Coin', bg: 'linear-gradient(135deg,#8b5cf6,#6366f1)' },
]

const largeFeatures = [
  {
    title: 'features.hardware.title',
    desc: 'features.hardware.desc',
    icon: 'Monitor',
    color: '#409eff',
    bg: 'rgba(64,158,255,0.12)',
    details: [
      { text: 'features.hardware.nodeInfo', color: '#409eff' },
      { text: 'features.hardware.resource', color: '#67c23a' },
      { text: 'features.hardware.ioDelay', color: '#e6a23c' },
    ],
  },
  {
    title: 'features.virtual.title',
    desc: 'features.virtual.desc',
    icon: 'Cpu',
    color: '#67c23a',
    bg: 'rgba(103,194,58,0.12)',
    details: [
      { text: 'features.virtual.vms', color: '#67c23a' },
      { text: 'features.virtual.lxc', color: '#409eff' },
      { text: 'features.virtual.config', color: '#e6a23c' },
    ],
  },
  {
    title: 'features.storage.title',
    desc: 'features.storage.desc',
    icon: 'Coin',
    color: '#e6a23c',
    bg: 'rgba(230,162,60,0.12)',
    details: [
      { text: 'features.storage.ceph', color: '#e6a23c' },
      { text: 'features.storage.local', color: '#409eff' },
      { text: 'features.storage.shared', color: '#67c23a' },
    ],
  },
  {
    title: 'features.network.title',
    desc: 'features.network.desc',
    icon: 'Share',
    color: '#f56c6c',
    bg: 'rgba(245,108,108,0.12)',
    details: [
      { text: 'features.network.interface', color: '#f56c6c' },
      { text: 'features.network.sdn', color: '#8b5cf6' },
      { text: 'features.network.topology', color: '#409eff' },
    ],
  },
]

const smallFeatures = [
  { title: 'features.extra.ha.title', desc: 'features.extra.ha.desc', icon: 'Connection', color: '#f56c6c', bg: 'rgba(245,108,108,0.12)' },
  { title: 'features.extra.sdn.title', desc: 'features.extra.sdn.desc', icon: 'Share', color: '#8b5cf6', bg: 'rgba(139,92,246,0.12)' },
  { title: 'features.extra.alert.title', desc: 'features.extra.alert.desc', icon: 'Bell', color: '#e6a23c', bg: 'rgba(230,162,60,0.12)' },
  { title: 'features.extra.report.title', desc: 'features.extra.report.desc', icon: 'Files', color: '#409eff', bg: 'rgba(64,158,255,0.12)' },
  { title: 'features.extra.backup.title', desc: 'features.extra.backup.desc', icon: 'FolderOpened', color: '#67c23a', bg: 'rgba(103,194,58,0.12)' },
  { title: 'features.extra.trend.title', desc: 'features.extra.trend.desc', icon: 'TrendCharts', color: '#f56c6c', bg: 'rgba(245,108,108,0.12)' },
]

const dataTypes = [
  {
    title: 'features.dataTypes.node',
    desc: 'features.dataTypes.nodeDesc',
    icon: 'Monitor',
    bg: 'linear-gradient(135deg,#409eff,#337ecc)',
    fields: ['node_name', 'cpu_load', 'memory_used_mb', 'disk_io_delay_ms'],
  },
  {
    title: 'features.dataTypes.vm',
    desc: 'features.dataTypes.vmDesc',
    icon: 'Cpu',
    bg: 'linear-gradient(135deg,#67c23a,#36a86b)',
    fields: ['vmid', 'cpu_cores', 'memory_total_mb', 'disk_read_iops'],
  },
  {
    title: 'features.dataTypes.lxc',
    desc: 'features.dataTypes.lxcDesc',
    icon: 'Box',
    bg: 'linear-gradient(135deg,#e6a23c,#d4842f)',
    fields: ['vmid', 'cpu_limit', 'memory_limit_mb', 'disk_write_iops'],
  },
  {
    title: 'features.dataTypes.storage',
    desc: 'features.dataTypes.storageDesc',
    icon: 'Coin',
    bg: 'linear-gradient(135deg,#8b5cf6,#6366f1)',
    fields: ['storage', 'total_gb', 'used_gb', 'shared'],
  },
  {
    title: 'features.dataTypes.network',
    desc: 'features.dataTypes.networkDesc',
    icon: 'Connection',
    bg: 'linear-gradient(135deg,#409eff,#8b5cf6)',
    fields: ['iface', 'address', 'gateway', 'speed_mbps'],
  },
  {
    title: 'features.dataTypes.ceph',
    desc: 'features.dataTypes.cephDesc',
    icon: 'DataAnalysis',
    bg: 'linear-gradient(135deg,#f56c6c,#409eff)',
    fields: ['health', 'osd_nr', 'pg_bytes', 'max_avail_gb'],
  },
  {
    title: 'features.dataTypes.ha',
    desc: 'features.dataTypes.haDesc',
    icon: 'Connection',
    bg: 'linear-gradient(135deg,#e6a23c,#409eff)',
    fields: ['sid', 'resource_type', 'status', 'ha_group'],
  },
  {
    title: 'features.dataTypes.sdn',
    desc: 'features.dataTypes.sdnDesc',
    icon: 'Share',
    bg: 'linear-gradient(135deg,#409eff,#67c23a)',
    fields: ['zone', 'vnet', 'subnet', 'vlan'],
  },
]

const workflowSteps = computed(() => [
  { title: t('home.step1'), desc: t('home.step1Desc') },
  { title: t('home.step2'), desc: t('home.step2Desc') },
  { title: t('features.workflow.step3'), desc: t('features.workflow.step3Desc') },
  { title: t('features.workflow.step4'), desc: t('features.workflow.step4Desc') },
])
</script>

<style scoped>
.features-page {
  min-height: 100vh;
  background: var(--bg-primary);
  color: var(--text-primary);
  transition: background-color 0.3s, color 0.3s;
}

.container {
  max-width: 1200px;
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
.nav-link.active {
  color: var(--color-primary);
  background: rgba(64, 158, 255, 0.1);
  font-weight: 600;
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
  display: flex;
  align-items: center;
  gap: 60px;
  width: 100%;
}
.hero-text {
  flex: 1;
  max-width: 560px;
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

/* Hero Visual: data flow card */
.hero-visual {
  flex: 1;
  max-width: 420px;
  perspective: 800px;
}
.flow-card {
  background: rgba(255, 255, 255, 0.75);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(200, 210, 230, 0.4);
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 30px 60px rgba(0, 0, 0, 0.08);
  transform: rotateY(-8deg) rotateX(4deg);
  transition: transform 0.4s;
}
.flow-card:hover {
  box-shadow: 0 30px 80px rgba(0, 0, 0, 0.15);
}
.dark .flow-card {
  background: rgba(255, 255, 255, 0.04);
  border-color: rgba(255, 255, 255, 0.08);
}
.fc-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 18px;
  border-bottom: 1px solid rgba(200, 210, 230, 0.4);
}
.dark .fc-header {
  border-bottom-color: rgba(255, 255, 255, 0.08);
}
.fc-dots {
  display: flex;
  gap: 6px;
}
.fc-dots span {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
}
.fc-dots span:first-child { background: #f56c6c; }
.fc-dots span:nth-child(2) { background: #e6a23c; }
.fc-dots span:last-child { background: #67c23a; }
.fc-title {
  font-size: 13px;
  color: #4e5159;
  font-weight: 500;
  letter-spacing: 0.5px;
}
.dark .fc-title {
  color: rgba(255, 255, 255, 0.5);
}
.fc-body {
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.flow-item {
  display: flex;
  align-items: center;
  gap: 12px;
  animation: flowIn 0.5s ease-out both;
  animation-delay: var(--delay);
}
@keyframes flowIn {
  from { opacity: 0; transform: translateX(-20px); }
  to { opacity: 1; transform: translateX(0); }
}
.flow-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}
.flow-label {
  font-size: 14px;
  color: #3a3d4a;
  font-weight: 600;
  flex: 1;
}
.dark .flow-label {
  color: rgba(255, 255, 255, 0.85);
}
.flow-arrow {
  color: var(--text-muted);
  opacity: 0.5;
}

/* ============ Section header ============ */
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
  max-width: 640px;
  margin: 0 auto;
  line-height: 1.7;
}

/* ============ Capability ============ */
.capability-section {
  padding: 100px 0;
  position: relative;
}
.capability-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 28px;
  position: relative;
  z-index: 1;
}
.capability-card {
  background: var(--bg-card);
  border-radius: 20px;
  padding: 36px 32px;
  border: 1px solid var(--border-color);
  transition: all 0.35s cubic-bezier(0.25, 0.46, 0.45, 0.94);
  animation: fadeUp 0.6s both;
  animation-delay: calc(var(--i) * 0.1s);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04);
}
.capability-card:hover {
  transform: translateY(-6px);
  box-shadow: var(--card-hover-shadow);
  border-color: rgba(64, 158, 255, 0.3);
}
.cc-icon {
  width: 64px;
  height: 64px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 20px;
}
.cc-icon :deep(.el-icon) {
  color: inherit;
}
.capability-card h3 {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-heading);
  margin: 0 0 12px;
}
.cc-desc {
  font-size: 14px;
  color: var(--text-secondary);
  line-height: 1.8;
  margin: 0 0 20px;
}
.cc-details {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.cc-detail {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  color: var(--text-muted);
}
.detail-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

/* ============ Data types ============ */
.data-section {
  padding: 100px 0;
  background: var(--bg-secondary);
  transition: background 0.3s;
  position: relative;
}
.data-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  position: relative;
  z-index: 1;
}
.data-card {
  background: var(--bg-card);
  border-radius: 16px;
  border: 1px solid var(--border-color);
  padding: 26px 22px;
  transition: all 0.3s;
  animation: fadeUp 0.5s both;
  animation-delay: calc(var(--i) * 0.06s);
  display: flex;
  flex-direction: column;
}
.data-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.08);
  border-color: rgba(64, 158, 255, 0.2);
}
.dt-icon {
  width: 52px;
  height: 52px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  margin-bottom: 16px;
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.15);
}
.data-card h4 {
  font-size: 17px;
  font-weight: 700;
  color: var(--text-heading);
  margin: 0 0 8px;
}
.data-card p {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.7;
  margin: 0 0 14px;
  flex: 1;
}
.dt-fields {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 14px;
}
.dt-field {
  font-size: 11px;
  font-family: 'SF Mono', 'Menlo', monospace;
  background: var(--bg-secondary);
  padding: 3px 8px;
  border-radius: 6px;
  color: var(--text-muted);
  border: 1px solid var(--border-color);
}
.dt-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #67c23a;
  font-weight: 500;
}
.dt-pulse {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #67c23a;
  animation: pulse 2s infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.2); }
}

/* ============ Extra features ============ */
.extra-section {
  padding: 100px 0;
  position: relative;
}
.extra-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
  position: relative;
  z-index: 1;
}
.extra-card {
  background: var(--bg-card);
  border-radius: 16px;
  padding: 28px 26px;
  border: 1px solid var(--border-color);
  transition: all 0.3s;
  animation: fadeUp 0.5s both;
  animation-delay: calc(var(--i) * 0.08s);
}
.extra-card:hover {
  transform: translateY(-4px);
  border-color: #409eff;
  box-shadow: 0 8px 24px rgba(64, 158, 255, 0.08);
}
.ex-icon {
  width: 46px;
  height: 46px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
}
.extra-card h4 {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-heading);
  margin: 0 0 8px;
}
.extra-card p {
  font-size: 13px;
  color: var(--text-muted);
  line-height: 1.7;
  margin: 0;
}

/* ============ Workflow steps ============ */
.flow-section {
  padding: 100px 0;
  position: relative;
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

@keyframes fadeUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

/* ============ Responsive ============ */
@media (max-width: 1100px) {
  .data-grid { grid-template-columns: repeat(2, 1fr); }
  .extra-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 900px) {
  .nav-links { display: none; }
  .hero-content { flex-direction: column; }
  .hero-visual { display: none; }
  .title-line { font-size: 36px; }
  .capability-grid { grid-template-columns: 1fr; }
}
@media (max-width: 640px) {
  .data-grid { grid-template-columns: 1fr; }
  .extra-grid { grid-template-columns: 1fr; }
  .hero-stats { flex-wrap: wrap; }
}
</style>
