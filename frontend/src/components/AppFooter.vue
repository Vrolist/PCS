<template>
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
            <router-link to="/features">{{ t('nav.monitorData') }}</router-link>
            <router-link to="/ai-assistant">{{ t('nav.aiAssistant') }}</router-link>
            <router-link to="/privacy">{{ t('footer.privacy') }}</router-link>
          </div>
          <div class="footer-col">
            <h4>{{ t('footer.contact') }}</h4>
            <a :href="`mailto:${contactEmail}`">{{ contactEmail }}</a>
          </div>
        </div>
      </div>
      <div class="footer-bottom">
        <p>&copy; {{ year }} {{ t('footer.brand') }} · pve-cluster-scan. {{ t('footer.allRights') }}</p>
      </div>
    </div>
  </footer>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const contactEmail = '1121031509@qq.com'
const year = new Date().getFullYear()
</script>

<style scoped>
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
}
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
.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
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
.logo-wrapper {
  display: flex;
  flex-direction: column;
  line-height: 1.15;
}
.logo-main {
  font-size: 20px;
  font-weight: 800;
  letter-spacing: 1px;
  color: #e0e0f0;
}
.logo-sub {
  font-size: 11px;
  color: #8080a0;
  letter-spacing: 0.3px;
}
.accent-l {
  font-size: 14px;
  font-weight: 700;
  color: #60b0ff;
}
.footer-desc {
  font-size: 14px;
  color: #707090;
}
.footer-brand .logo {
  margin-bottom: 12px;
}
.footer-links {
  display: flex;
  gap: 48px;
}
.footer-col {
  min-width: 180px;
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
@media (max-width: 640px) {
  .footer-top {
    flex-direction: column;
    gap: 32px;
  }
}
</style>
