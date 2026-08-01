<template>
  <div class="ai-page">
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
          <router-link to="/ai-assistant" class="nav-link active">{{ t('nav.aiAssistant') }}</router-link>
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
        <div class="gradient-orb orb-3"></div>
        <div class="grid-pattern"></div>
      </div>
      <div class="container hero-content">
        <div class="hero-text">
          <div class="badge">{{ t('aiAssistant.badge') }}</div>
          <h1 class="hero-title">
            <span class="title-line">{{ t('aiAssistant.heroTitle1') }}</span>
            <span class="title-line accent">{{ t('aiAssistant.heroTitle2') }}</span>
          </h1>
          <p class="hero-subtitle">{{ t('aiAssistant.heroDesc') }}</p>
          <div class="hero-actions">
            <router-link to="/dashboard">
              <el-button type="primary" size="large" round class="cta-btn">
                {{ t('aiAssistant.tryNow') }}
                <el-icon class="btn-arrow"><ArrowRight /></el-icon>
              </el-button>
            </router-link>
            <router-link to="/features">
              <el-button size="large" round plain class="login-btn">{{ t('aiAssistant.viewData') }}</el-button>
            </router-link>
          </div>
          <div class="hero-stats">
            <div class="stat-item"><span class="stat-num">{{ t('aiAssistant.statStream') }}</span><span class="stat-label">{{ t('aiAssistant.statStreamLabel') }}</span></div>
            <div class="stat-dot"></div>
            <div class="stat-item"><span class="stat-num">{{ t('aiAssistant.statModel') }}</span><span class="stat-label">{{ t('aiAssistant.statModelLabel') }}</span></div>
            <div class="stat-dot"></div>
            <div class="stat-item"><span class="stat-num">{{ t('aiAssistant.statContext') }}</span><span class="stat-label">{{ t('aiAssistant.statContextLabel') }}</span></div>
          </div>
        </div>
        <div class="hero-visual">
          <div class="chat-card">
            <div class="cc-header">
              <div class="cc-dots"><span></span><span></span><span></span></div>
              <span class="cc-title">PCS AI Assistant</span>
              <span class="cc-live"><span class="live-dot"></span>{{ t('aiAssistant.live') }}</span>
            </div>
            <div class="cc-body">
              <div class="msg msg-user">{{ t('aiAssistant.demoQuestion') }}</div>
              <div class="msg msg-ai">
                <div class="ai-bubble">
                  <span class="token" v-for="(tk, i) in demoTokens" :key="i" :style="{ '--d': i * 0.08 }">{{ tk }}</span>
                  <span class="typing-cursor"></span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 核心能力 -->
    <section class="ability-section">
      <div class="container">
        <div class="section-header">
          <span class="section-tag">{{ t('aiAssistant.abilityTag') }}</span>
          <h2 class="section-title">{{ t('aiAssistant.abilityTitle') }}</h2>
          <p class="section-desc">{{ t('aiAssistant.abilityDesc') }}</p>
        </div>
        <div class="ability-grid">
          <div v-for="(a, i) in abilities" :key="i" class="ability-card" :style="{ '--i': i }">
            <div class="ab-icon" :style="{ background: a.bg, color: a.color }">
              <el-icon :size="28"><component :is="a.icon" /></el-icon>
            </div>
            <h3>{{ t(a.title) }}</h3>
            <p>{{ t(a.desc) }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- 使用场景 -->
    <section class="scene-section">
      <div class="container">
        <div class="section-header">
          <span class="section-tag">{{ t('aiAssistant.sceneTag') }}</span>
          <h2 class="section-title">{{ t('aiAssistant.sceneTitle') }}</h2>
          <p class="section-desc">{{ t('aiAssistant.sceneDesc') }}</p>
        </div>
        <div class="scene-list">
          <div v-for="(s, i) in scenes" :key="i" class="scene-card" :style="{ '--i': i }">
            <div class="sc-number">0{{ i + 1 }}</div>
            <div class="sc-body">
              <h4>{{ t(s.title) }}</h4>
              <p>{{ t(s.desc) }}</p>
              <div class="sc-example">
                <span class="sc-example-label">{{ t('aiAssistant.example') }}</span>
                <span class="sc-example-text">{{ t(s.example) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 技术流程 -->
    <section class="tech-section">
      <div class="container">
        <div class="section-header">
          <span class="section-tag">{{ t('aiAssistant.techTag') }}</span>
          <h2 class="section-title">{{ t('aiAssistant.techTitle') }}</h2>
          <p class="section-desc">{{ t('aiAssistant.techDesc') }}</p>
        </div>
        <div class="tech-flow">
          <div v-for="(step, i) in techSteps" :key="i" class="tech-step">
            <div class="ts-icon" :style="{ background: step.bg }">
              <el-icon :size="22"><component :is="step.icon" /></el-icon>
            </div>
            <div class="ts-content">
              <h4>{{ t(step.title) }}</h4>
              <p>{{ t(step.desc) }}</p>
            </div>
            <div class="ts-connector" v-if="i < techSteps.length - 1">
              <el-icon :size="18"><ArrowRight /></el-icon>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- CTA -->
    <section class="cta-section">
      <div class="container cta-container">
        <div class="cta-card">
          <h2>{{ t('aiAssistant.ctaTitle') }}</h2>
          <p>{{ t('aiAssistant.ctaDesc') }}</p>
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
import { ref, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useThemeStore } from '@/stores/theme'
import { useAuthStore } from '@/stores/auth'
import AppFooter from '@/components/AppFooter.vue'

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

const abilities = [
  { title: 'aiAssistant.ability.dataQA.title', desc: 'aiAssistant.ability.dataQA.desc', icon: 'ChatDotRound', color: '#409eff', bg: 'rgba(64,158,255,0.12)' },
  { title: 'aiAssistant.ability.stream.title', desc: 'aiAssistant.ability.stream.desc', icon: 'Connection', color: '#67c23a', bg: 'rgba(103,194,58,0.12)' },
  { title: 'aiAssistant.ability.context.title', desc: 'aiAssistant.ability.context.desc', icon: 'Files', color: '#e6a23c', bg: 'rgba(230,162,60,0.12)' },
  { title: 'aiAssistant.ability.model.title', desc: 'aiAssistant.ability.model.desc', icon: 'MagicStick', color: '#8b5cf6', bg: 'rgba(139,92,246,0.12)' },
]

const scenes = [
  { title: 'aiAssistant.scene.fault.title', desc: 'aiAssistant.scene.fault.desc', example: 'aiAssistant.scene.fault.example' },
  { title: 'aiAssistant.scene.capacity.title', desc: 'aiAssistant.scene.capacity.desc', example: 'aiAssistant.scene.capacity.example' },
  { title: 'aiAssistant.scene.report.title', desc: 'aiAssistant.scene.report.desc', example: 'aiAssistant.scene.report.example' },
  { title: 'aiAssistant.scene.change.title', desc: 'aiAssistant.scene.change.desc', example: 'aiAssistant.scene.change.example' },
]

const techSteps = [
  { title: 'aiAssistant.tech.question.title', desc: 'aiAssistant.tech.question.desc', icon: 'ChatDotRound', bg: 'linear-gradient(135deg,#409eff,#337ecc)' },
  { title: 'aiAssistant.tech.match.title', desc: 'aiAssistant.tech.match.desc', icon: 'Search', bg: 'linear-gradient(135deg,#67c23a,#36a86b)' },
  { title: 'aiAssistant.tech.inject.title', desc: 'aiAssistant.tech.inject.desc', icon: 'DataAnalysis', bg: 'linear-gradient(135deg,#e6a23c,#d4842f)' },
  { title: 'aiAssistant.tech.stream.title', desc: 'aiAssistant.tech.stream.desc', icon: 'MagicStick', bg: 'linear-gradient(135deg,#8b5cf6,#6366f1)' },
]

const demoAnswer = t('aiAssistant.demoAnswer')
const demoTokens = ref<string[]>([])

onMounted(() => {
  const chars = demoAnswer.split('')
  let idx = 0
  const timer = setInterval(() => {
    if (idx < chars.length) {
      demoTokens.value.push(chars[idx])
      idx++
    } else {
      clearInterval(timer)
    }
  }, 90)
  onUnmounted(() => clearInterval(timer))
})
</script>

<style scoped>
.ai-page {
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
  max-width: 560px;
}
.badge {
  display: inline-flex;
  padding: 6px 16px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 500;
  background: rgba(139, 92, 246, 0.12);
  color: #8b5cf6;
  border: 1px solid rgba(139, 92, 246, 0.25);
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
  background: linear-gradient(135deg, #8b5cf6, #409eff);
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

/* Hero Visual: chat card */
.hero-visual {
  flex: 1;
  max-width: 440px;
  perspective: 800px;
}
.chat-card {
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
.chat-card:hover {
  box-shadow: 0 30px 80px rgba(0, 0, 0, 0.15);
}
.dark .chat-card {
  background: rgba(255, 255, 255, 0.04);
  border-color: rgba(255, 255, 255, 0.08);
}
.cc-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 18px;
  border-bottom: 1px solid rgba(200, 210, 230, 0.4);
}
.dark .cc-header {
  border-bottom-color: rgba(255, 255, 255, 0.08);
}
.cc-dots {
  display: flex;
  gap: 6px;
}
.cc-dots span {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
}
.cc-dots span:first-child { background: #f56c6c; }
.cc-dots span:nth-child(2) { background: #e6a23c; }
.cc-dots span:last-child { background: #67c23a; }
.cc-title {
  font-size: 13px;
  color: #4e5159;
  font-weight: 600;
  letter-spacing: 0.5px;
  flex: 1;
}
.dark .cc-title {
  color: rgba(255, 255, 255, 0.7);
}
.cc-live {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  color: #67c23a;
  font-weight: 600;
}
.live-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #67c23a;
  animation: pulse 2s infinite;
}
.cc-body {
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 200px;
}
.msg {
  max-width: 85%;
}
.msg-user {
  align-self: flex-end;
  background: linear-gradient(135deg, #8b5cf6, #6366f1);
  color: #fff;
  border-radius: 14px 14px 4px 14px;
  padding: 10px 14px;
  font-size: 13px;
  line-height: 1.6;
}
.msg-ai {
  align-self: flex-start;
}
.ai-bubble {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 14px 14px 14px 4px;
  padding: 10px 14px;
  font-size: 13px;
  line-height: 1.8;
  color: var(--text-primary);
  display: flex;
  flex-wrap: wrap;
  gap: 1px;
}
.dark .ai-bubble {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(255, 255, 255, 0.08);
}
.token {
  animation: tokenIn 0.25s ease-out both;
  animation-delay: var(--d);
}
@keyframes tokenIn {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}
.typing-cursor {
  width: 2px;
  height: 14px;
  background: #8b5cf6;
  margin-left: 3px;
  align-self: center;
  animation: blink 0.8s infinite;
}
@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}
@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.2); }
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
  background: rgba(139, 92, 246, 0.12);
  color: #8b5cf6;
  border: 1px solid rgba(139, 92, 246, 0.2);
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

/* ============ Ability ============ */
.ability-section {
  padding: 100px 0;
  position: relative;
}
.ability-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24px;
  position: relative;
  z-index: 1;
}
.ability-card {
  background: var(--bg-card);
  border-radius: 18px;
  padding: 32px 26px;
  border: 1px solid var(--border-color);
  transition: all 0.35s cubic-bezier(0.25, 0.46, 0.45, 0.94);
  animation: fadeUp 0.6s both;
  animation-delay: calc(var(--i) * 0.1s);
}
.ability-card:hover {
  transform: translateY(-6px);
  box-shadow: var(--card-hover-shadow);
  border-color: rgba(139, 92, 246, 0.35);
}
.ab-icon {
  width: 56px;
  height: 56px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 18px;
}
.ability-card h3 {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-heading);
  margin: 0 0 10px;
}
.ability-card p {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.7;
  margin: 0;
}

/* ============ Scenes ============ */
.scene-section {
  padding: 100px 0;
  background: var(--bg-secondary);
  transition: background 0.3s;
  position: relative;
}
.scene-list {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 24px;
  position: relative;
  z-index: 1;
}
.scene-card {
  display: flex;
  gap: 20px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  padding: 28px 26px;
  transition: all 0.3s;
  animation: fadeUp 0.5s both;
  animation-delay: calc(var(--i) * 0.08s);
}
.scene-card:hover {
  transform: translateY(-4px);
  border-color: rgba(139, 92, 246, 0.35);
  box-shadow: 0 8px 24px rgba(139, 92, 246, 0.1);
}
.sc-number {
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
  background: linear-gradient(135deg, #8b5cf6, #6366f1);
  box-shadow: 0 4px 12px rgba(139, 92, 246, 0.25);
}
.sc-body h4 {
  font-size: 17px;
  font-weight: 600;
  color: var(--text-heading);
  margin: 0 0 8px;
}
.sc-body p {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.7;
  margin: 0 0 14px;
}
.sc-example {
  display: flex;
  flex-direction: column;
  gap: 6px;
  background: var(--bg-secondary);
  border: 1px dashed var(--border-color);
  border-radius: 10px;
  padding: 12px 14px;
}
.sc-example-label {
  font-size: 11px;
  font-weight: 600;
  color: #8b5cf6;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.sc-example-text {
  font-size: 13px;
  color: var(--text-muted);
  line-height: 1.6;
  font-style: italic;
}

/* ============ Tech flow ============ */
.tech-section {
  padding: 100px 0;
  position: relative;
}
.tech-flow {
  display: flex;
  flex-direction: column;
  gap: 0;
  max-width: 760px;
  margin: 0 auto;
  position: relative;
  z-index: 1;
}
.tech-step {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 20px 0;
  position: relative;
}
.ts-icon {
  width: 48px;
  height: 48px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  position: relative;
  z-index: 1;
}
.ts-content {
  flex: 1;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 14px;
  padding: 20px 24px;
  transition: all 0.3s;
}
.ts-content:hover {
  border-color: rgba(139, 92, 246, 0.35);
  box-shadow: 0 8px 24px rgba(139, 92, 246, 0.1);
}
.ts-content h4 {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-heading);
  margin: 0 0 6px;
}
.ts-content p {
  font-size: 13px;
  color: var(--text-muted);
  line-height: 1.7;
  margin: 0;
}
.ts-connector {
  position: absolute;
  left: 24px;
  top: 68px;
  transform: translateX(-50%);
  color: #8b5cf6;
  opacity: 0.4;
  z-index: 0;
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
  background: linear-gradient(135deg, #2a1a5e, #1a3a6b);
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
  .ability-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 900px) {
  .nav-links { display: none; }
  .hero-content { flex-direction: column; }
  .hero-visual { display: none; }
  .title-line { font-size: 36px; }
  .scene-list { grid-template-columns: 1fr; }
}
@media (max-width: 640px) {
  .ability-grid { grid-template-columns: 1fr; }
  .hero-stats { flex-wrap: wrap; }
}
</style>
