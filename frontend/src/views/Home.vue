<template>
  <div class="home-page">
    <!-- Navbar -->
    <header class="navbar" :class="{ 'nav-scrolled': scrolled }">
      <div class="container nav-container">
        <router-link to="/" class="logo">
          <div class="logo-icon"><ServerIcon /></div>
          <span class="logo-text">PVE<span class="logo-accent">Scan</span></span>
        </router-link>
        <nav class="nav-actions">
          <button class="theme-btn" @click="themeStore.toggle" :title="themeStore.theme === 'dark' ? '切换到亮色' : '切换到暗色'">
            <el-icon :size="20"><Sunny v-if="themeStore.theme === 'dark'" /><Moon v-else /></el-icon>
          </button>
          <router-link to="/login">
            <el-button :type="themeStore.theme === 'dark' ? 'primary' : ''" plain round size="default">登录</el-button>
          </router-link>
          <router-link to="/dashboard">
            <el-button type="primary" round size="default">控制台</el-button>
          </router-link>
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
          <div class="badge">Proxmox VE 运维利器</div>
          <h1 class="hero-title">
            <span class="title-line">集群监控，</span>
            <span class="title-line accent">如此简单。</span>
          </h1>
          <p class="hero-subtitle">
            一键部署 Agent，自动发现 PVE 集群全量资源。实时监控、智能告警、
            历史趋势，让基础设施运维从被动响应走向主动管理。
          </p>
          <div class="hero-actions">
            <router-link to="/dashboard">
              <el-button type="primary" size="large" round class="cta-btn">
                免费开始使用
                <el-icon class="btn-arrow"><ArrowRight /></el-icon>
              </el-button>
            </router-link>
            <router-link to="/login">
              <el-button size="large" round plain class="login-btn">已有账号</el-button>
            </router-link>
          </div>
          <div class="hero-stats">
            <div class="stat-item"><span class="stat-num">零配置</span><span class="stat-label">部署 Agent</span></div>
            <div class="stat-dot"></div>
            <div class="stat-item"><span class="stat-num">全自动</span><span class="stat-label">数据采集</span></div>
            <div class="stat-dot"></div>
            <div class="stat-item"><span class="stat-num">智能化</span><span class="stat-label">告警检测</span></div>
          </div>
        </div>
        <div class="hero-visual">
          <div class="visual-card">
            <div class="vc-header">
              <div class="vc-dots"><span></span><span></span><span></span></div>
              <span class="vc-title">pve-cluster</span>
            </div>
            <div class="vc-body">
              <div class="vc-row" v-for="i in 4" :key="i">
                <div class="vc-dot" :class="i === 2 ? 'warn' : i === 4 ? 'ok' : ''"></div>
                <div class="vc-bar" :style="{ width: (40 + Math.random() * 50) + '%' }"></div>
                <span class="vc-label">{{ ['pve-1', 'pve-2', 'pve-3', 'pve-4'][i - 1] }}</span>
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
          <span class="section-tag">核心能力</span>
          <h2 class="section-title">为什么选择 PVE&nbsp;Scan？</h2>
          <p class="section-desc">从发现到诊断，覆盖 PVE 运维全场景的工具链</p>
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

    <!-- How it works -->
    <section class="how-it-works">
      <div class="container">
        <div class="section-header">
          <span class="section-tag">工作流程</span>
          <h2 class="section-title">三步完成接入</h2>
          <p class="section-desc">从零到全面监控，只需三个步骤</p>
        </div>
        <div class="steps">
          <div v-for="(step, i) in steps" :key="i" class="step-card">
            <div class="step-number">0{{ i + 1 }}</div>
            <div class="step-content">
              <h3>{{ step.title }}</h3>
              <p>{{ step.desc }}</p>
            </div>
            <div v-if="i < steps.length - 1" class="step-connector">
              <el-icon color="#409eff"><ArrowRight /></el-icon>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- CTA -->
    <section class="cta-section">
      <div class="container cta-container">
        <div class="cta-card">
          <h2>准备好简化你的 PVE 运维了吗？</h2>
          <p>注册即可开始使用，无需任何前置条件</p>
          <router-link to="/dashboard">
            <el-button type="primary" size="large" round class="cta-btn">
              立即开始
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
              <div class="logo-icon"><ServerIcon /></div>
              <span class="logo-text">PVE<span class="logo-accent">Scan</span></span>
            </div>
            <p class="footer-desc">开源 PVE 集群监控平台</p>
          </div>
          <div class="footer-links">
            <div class="footer-col">
              <h4>产品</h4>
              <a href="#features">功能特性</a>
              <a href="#">价格</a>
            </div>
            <div class="footer-col">
              <h4>支持</h4>
              <a href="#">文档</a>
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
import { ref, onMounted, onUnmounted } from 'vue'
import { useThemeStore } from '@/stores/theme'

const themeStore = useThemeStore()
const scrolled = ref(false)

function onScroll() {
  scrolled.value = window.scrollY > 20
}
onMounted(() => window.addEventListener('scroll', onScroll))
onUnmounted(() => window.removeEventListener('scroll', onScroll))

const features = [
  {
    title: '自动发现',
    desc: 'Agent 部署后自动发现集群全部节点、VM、LXC 容器与存储，无需手动配置。',
    icon: 'Search',
    color: '#409eff',
    bg: 'rgba(64,158,255,0.12)',
  },
  {
    title: '实时监控',
    desc: 'CPU、内存、磁盘、网络 IO 秒级采集，支持自定义间隔，数据所见即所得。',
    icon: 'Monitor',
    color: '#67c23a',
    bg: 'rgba(103,194,58,0.12)',
  },
  {
    title: '智能检测',
    desc: '规则引擎自动扫描资源过载、节点离线、磁盘不足等异常，及时发现隐患。',
    icon: 'WarningFilled',
    color: '#e6a23c',
    bg: 'rgba(230,162,60,0.12)',
  },
  {
    title: '多 Agent',
    desc: '支持一个集群部署多个 Agent 实例，避免单点故障，数据更可靠。',
    icon: 'Connection',
    color: '#8b5cf6',
    bg: 'rgba(139,92,246,0.12)',
  },
  {
    title: '趋势分析',
    desc: '自动归档扫描快照，历史数据可回溯，便于容量规划与性能分析。',
    icon: 'TrendCharts',
    color: '#f56c6c',
    bg: 'rgba(245,108,108,0.12)',
  },
  {
    title: 'Ceph 集成',
    desc: '深度集成 Ceph 健康检测，OSD 状态、存储池用量一目了然。',
    icon: 'DataAnalysis',
    color: '#409eff',
    bg: 'rgba(64,158,255,0.12)',
  },
]

const steps = [
  {
    title: '创建集群',
    desc: '在平台创建一个 PVE 集群，获得专属的 Agent 接入 Token。',
  },
  {
    title: '部署 Agent',
    desc: '在可访问 PVE API 的服务器上执行一条命令，Agent 自动完成注册与首次扫描。',
  },
  {
    title: '全面监控',
    desc: '平台自动展示集群拓扑、资源用量和检测结果，一切尽在掌握。',
  },
]
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
  backdrop-filter: blur(16px) saturate(180%);
  -webkit-backdrop-filter: blur(16px) saturate(180%);
  border-bottom: 1px solid transparent;
  transition: all 0.3s;
}
.navbar.nav-scrolled {
  border-bottom-color: var(--border-color);
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
.logo-text {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-heading);
}
.logo-accent {
  color: #409eff;
}

.nav-actions {
  display: flex;
  align-items: center;
  gap: 8px;
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
  background: rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 30px 80px rgba(0, 0, 0, 0.1);
  transform: rotateY(-8deg) rotateX(4deg);
  transition: transform 0.4s;
}
.visual-card:hover {
  transform: rotateY(-4deg) rotateX(2deg);
}
.dark .visual-card {
  background: rgba(255, 255, 255, 0.04);
  border-color: rgba(255, 255, 255, 0.08);
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
.vc-label {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.7);
  font-weight: 500;
  flex-shrink: 0;
}

/* ============ Features ============ */
.features {
  padding: 100px 0;
}

.section-header {
  text-align: center;
  margin-bottom: 56px;
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

/* ============ How it works ============ */
.how-it-works {
  padding: 100px 0;
  background: var(--bg-secondary);
}

.steps {
  display: flex;
  flex-direction: column;
  gap: 24px;
  max-width: 680px;
  margin: 0 auto;
}

.step-card {
  display: flex;
  align-items: flex-start;
  gap: 24px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  padding: 28px 32px;
  transition: all 0.3s;
  position: relative;
}
.step-card:hover {
  border-color: rgba(64, 158, 255, 0.3);
  box-shadow: var(--card-hover-shadow);
}

.step-number {
  font-size: 32px;
  font-weight: 800;
  color: rgba(64, 158, 255, 0.15);
  line-height: 1;
  flex-shrink: 0;
  font-feature-settings: 'tnum';
}
.dark .step-number {
  color: rgba(64, 158, 255, 0.25);
}

.step-content {
  flex: 1;
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
}

.step-connector {
  position: absolute;
  bottom: -28px;
  left: 56px;
  transform: translateX(-50%);
  color: #409eff;
  opacity: 0.5;
  font-size: 18px;
}

/* ============ CTA ============ */
.cta-section {
  padding: 80px 0;
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
.footer-brand .logo-text {
  color: #e0e0f0;
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
