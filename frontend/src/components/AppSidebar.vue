<template>
  <el-menu
    :default-active="route.path"
    :collapse="appStore.sidebarCollapsed"
    router
    class="sidebar-menu"
    :class="{ 'is-dark': themeStore.theme === 'dark' }"
  >
    <div class="sidebar-logo" :class="{ collapsed: appStore.sidebarCollapsed }" @click="$router.push('/')" style="cursor: pointer">
      <div class="logo-icon-box">
        <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <rect x="2" y="2" width="20" height="20" rx="2" ry="2"></rect>
          <line x1="6" y1="8" x2="18" y2="8"></line>
          <line x1="6" y1="12" x2="18" y2="12"></line>
          <line x1="6" y1="16" x2="18" y2="16"></line>
          <circle cx="6" cy="6" r="1" fill="currentColor" stroke="none"></circle>
        </svg>
      </div>
      <transition name="fade">
        <div v-if="!appStore.sidebarCollapsed" class="logo-text-group">
          <span class="logo-main">PCS</span>
          <span class="logo-sub"><span class="accent">P</span>ve<span class="accent">C</span>luster<span class="accent">S</span>can</span>
        </div>
      </transition>
    </div>

    <!-- 控制管理 -->
    <div class="menu-section">
      <span v-if="!appStore.sidebarCollapsed" class="menu-label">{{ t('nav.controlManagement') }}</span>
    </div>

    <el-menu-item index="/dashboard" class="sidebar-item">
      <div class="item-icon-wrap">
        <el-icon><Monitor /></el-icon>
      </div>
      <template #title><span>{{ t('nav.dashboard') }}</span></template>
    </el-menu-item>

    <el-menu-item index="/dashboard/clusters" class="sidebar-item">
      <div class="item-icon-wrap">
        <el-icon><Connection /></el-icon>
      </div>
      <template #title><span>{{ t('nav.clusters') }}</span></template>
    </el-menu-item>

    <el-menu-item index="/dashboard/llm-settings" class="sidebar-item">
      <div class="item-icon-wrap">
        <el-icon><ChatDotRound /></el-icon>
      </div>
      <template #title><span>{{ t('nav.llmSettings') }}</span></template>
    </el-menu-item>

    <!-- 选择集群 -->
    <div class="menu-section">
      <span v-if="!appStore.sidebarCollapsed" class="menu-label">{{ t('nav.selectCluster') }}</span>
    </div>

    <div v-if="!appStore.sidebarCollapsed" class="cluster-selector" ref="clusterSelectorRef">
      <div class="cluster-trigger" @click="clusterDropdownOpen = !clusterDropdownOpen">
        <span class="cluster-dot" :class="{ online: clusterStore.currentCluster }"></span>
        <span class="cluster-name">{{ clusterStore.currentCluster?.name || t('nav.selectCluster') }}</span>
        <span v-if="pveMajor" class="pve-version-badge">PVE {{ pveMajor }}</span>
        <el-icon class="cluster-caret" :class="{ open: clusterDropdownOpen }"><ArrowDown /></el-icon>
      </div>
      <transition name="dropdown">
        <div v-if="clusterDropdownOpen" class="cluster-dropdown">
          <div
            v-for="c in clusterStore.clusterList"
            :key="c.id"
            class="cluster-option"
            :class="{ selected: c.id === clusterStore.currentClusterId }"
            @click="selectCluster(c.id)"
          >
            <span class="cluster-dot online"></span>
            <div class="cluster-option-info">
              <span class="cluster-option-name">{{ c.name }}</span>
              <span class="cluster-option-meta">{{ c.total_nodes || 0 }} {{ t('common.nodes') }} · {{ c.total_vms || 0 }} VM</span>
            </div>
            <el-icon v-if="c.id === clusterStore.currentClusterId" class="cluster-check"><Check /></el-icon>
          </div>
          <div v-if="!clusterStore.clusterList.length" class="cluster-option empty">
            <span class="cluster-option-name" style="color: var(--text-muted)">{{ t('nav.noCluster') }}</span>
          </div>
        </div>
      </transition>
    </div>

    <!-- 折叠态：tooltip 显示当前集群名 -->
    <el-tooltip v-else :content="clusterStore.currentCluster?.name || t('nav.selectCluster')" placement="right">
      <div class="cluster-switcher-collapsed">
        <el-icon @click="appStore.sidebarCollapsed = false"><Connection /></el-icon>
      </div>
    </el-tooltip>

    <!-- 基本信息 -->
    <div v-if="!appStore.sidebarCollapsed" class="menu-section collapsible" @click="toggleSection('basic')">
      <span class="menu-label">{{ t('nav.basicInfo') }}</span>
      <el-icon class="section-arrow" :class="{ expanded: expandedSections.basic }"><ArrowRight /></el-icon>
    </div>
    <div v-else class="menu-section">
      <span class="menu-label" style="font-size:0"></span>
    </div>
    <template v-if="expandedSections.basic || appStore.sidebarCollapsed">
      <el-menu-item index="/dashboard/nodes" class="sidebar-item">
        <div class="item-icon-wrap"><el-icon><Cpu /></el-icon></div>
        <template #title><span>{{ t('nav.nodeManagement') }}</span></template>
      </el-menu-item>
      <el-menu-item index="/dashboard/vms" class="sidebar-item">
        <div class="item-icon-wrap"><el-icon><Cpu /></el-icon></div>
        <template #title><span>{{ t('nav.virtualMachines') }}</span></template>
      </el-menu-item>
      <el-menu-item index="/dashboard/containers" class="sidebar-item">
        <div class="item-icon-wrap"><el-icon><Box /></el-icon></div>
        <template #title><span>{{ t('nav.containers') }}</span></template>
      </el-menu-item>
      <el-menu-item index="/dashboard/storage" class="sidebar-item">
        <div class="item-icon-wrap"><el-icon><Coin /></el-icon></div>
        <template #title><span>{{ t('nav.storageManagement') }}</span></template>
      </el-menu-item>
      <el-menu-item index="/dashboard/networks" class="sidebar-item">
        <div class="item-icon-wrap"><el-icon><Connection /></el-icon></div>
        <template #title><span>{{ t('nav.networkInterfaces') }}</span></template>
      </el-menu-item>
      <el-menu-item index="/dashboard/agents" class="sidebar-item">
        <div class="item-icon-wrap"><el-icon><User /></el-icon></div>
        <template #title><span>{{ t('nav.agentManagement') }}</span></template>
      </el-menu-item>
    </template>

    <!-- 进阶信息 -->
    <div v-if="!appStore.sidebarCollapsed" class="menu-section collapsible" @click="toggleSection('advanced')">
      <span class="menu-label">{{ t('nav.advancedInfo') }}</span>
      <el-icon class="section-arrow" :class="{ expanded: expandedSections.advanced }"><ArrowRight /></el-icon>
    </div>
    <div v-else class="menu-section">
      <span class="menu-label" style="font-size:0"></span>
    </div>
    <template v-if="expandedSections.advanced || appStore.sidebarCollapsed">
      <el-menu-item index="/dashboard/network-topology" class="sidebar-item">
        <div class="item-icon-wrap"><el-icon><Share /></el-icon></div>
        <template #title><span>{{ t('nav.networkTopology') }}</span></template>
      </el-menu-item>
      <el-menu-item index="/dashboard/ceph" class="sidebar-item">
        <div class="item-icon-wrap"><el-icon><Box /></el-icon></div>
        <template #title><span>{{ t('nav.cephStorage') }}</span></template>
      </el-menu-item>
      <el-menu-item index="/dashboard/ha" class="sidebar-item">
        <div class="item-icon-wrap"><el-icon><Connection /></el-icon></div>
        <template #title><span>{{ t('nav.haManagement') }}</span></template>
      </el-menu-item>
      <el-menu-item index="/dashboard/sdn" class="sidebar-item">
        <div class="item-icon-wrap"><el-icon><Share /></el-icon></div>
        <template #title><span>{{ t('nav.softwareDefinedNetwork') }}</span></template>
      </el-menu-item>
      <el-menu-item index="/dashboard/firewall" class="sidebar-item">
        <div class="item-icon-wrap"><el-icon><Lock /></el-icon></div>
        <template #title><span>{{ t('nav.firewall') }}</span></template>
      </el-menu-item>
      <el-menu-item index="/dashboard/backup" class="sidebar-item">
        <div class="item-icon-wrap"><el-icon><FolderOpened /></el-icon></div>
        <template #title><span>{{ t('nav.backupManagement') }}</span></template>
      </el-menu-item>
      <el-menu-item index="/dashboard/replication" class="sidebar-item">
        <div class="item-icon-wrap"><el-icon><CopyDocument /></el-icon></div>
        <template #title><span>{{ t('nav.dataReplication') }}</span></template>
      </el-menu-item>
      <el-menu-item index="/dashboard/snapshots" class="sidebar-item">
        <div class="item-icon-wrap"><el-icon><Camera /></el-icon></div>
        <template #title><span>{{ t('nav.snapshotManagement') }}</span></template>
      </el-menu-item>
      <el-menu-item index="/dashboard/cluster-tasks" class="sidebar-item">
        <div class="item-icon-wrap"><el-icon><Tickets /></el-icon></div>
        <template #title><span>{{ t('nav.clusterTasks') }}</span></template>
      </el-menu-item>
      <el-menu-item index="/dashboard/cluster-log" class="sidebar-item">
        <div class="item-icon-wrap"><el-icon><Document /></el-icon></div>
        <template #title><span>{{ t('nav.clusterLog') }}</span></template>
      </el-menu-item>
    </template>

    <!-- 运维检测 -->
    <div v-if="!appStore.sidebarCollapsed" class="menu-section collapsible" @click="toggleSection('ops')">
      <span class="menu-label">{{ t('nav.opsDetection') }}</span>
      <el-icon class="section-arrow" :class="{ expanded: expandedSections.ops }"><ArrowRight /></el-icon>
    </div>
    <div v-else class="menu-section">
      <span class="menu-label" style="font-size:0"></span>
    </div>
    <template v-if="expandedSections.ops || appStore.sidebarCollapsed">
      <el-menu-item index="/dashboard/alerts" class="sidebar-item">
        <div class="item-icon-wrap"><el-icon><Bell /></el-icon></div>
        <template #title><span>{{ t('nav.alertCenter') }}</span></template>
      </el-menu-item>
      <el-menu-item index="/dashboard/services" class="sidebar-item">
        <div class="item-icon-wrap"><el-icon><Service /></el-icon></div>
        <template #title><span>{{ t('nav.opsService') }}</span></template>
      </el-menu-item>
    </template>

    <!-- 智能分析 -->
    <div v-if="!appStore.sidebarCollapsed" class="menu-section collapsible" @click="toggleSection('smart')">
      <span class="menu-label">{{ t('nav.smartAnalysis') }}</span>
      <el-icon class="section-arrow" :class="{ expanded: expandedSections.smart }"><ArrowRight /></el-icon>
    </div>
    <div v-else class="menu-section">
      <span class="menu-label" style="font-size:0"></span>
    </div>
    <template v-if="expandedSections.smart || appStore.sidebarCollapsed">
      <el-menu-item index="/dashboard/capacity-planning" class="sidebar-item">
        <div class="item-icon-wrap"><el-icon><DataAnalysis /></el-icon></div>
        <template #title><span>{{ t('nav.capacityPlanning') }}</span></template>
      </el-menu-item>
      <el-menu-item index="/dashboard/change-tracking" class="sidebar-item">
        <div class="item-icon-wrap"><el-icon><Switch /></el-icon></div>
        <template #title><span>{{ t('nav.changeTracking') }}</span></template>
      </el-menu-item>
      <el-menu-item index="/dashboard/resource-reclamation" class="sidebar-item">
        <div class="item-icon-wrap"><el-icon><Delete /></el-icon></div>
        <template #title><span>{{ t('nav.resourceReclamation') }}</span></template>
      </el-menu-item>
      <el-menu-item index="/dashboard/performance-correlation" class="sidebar-item">
        <div class="item-icon-wrap"><el-icon><Histogram /></el-icon></div>
        <template #title><span>{{ t('nav.performanceCorrelation') }}</span></template>
      </el-menu-item>
      <el-menu-item index="/dashboard/dependency-mapping" class="sidebar-item">
        <div class="item-icon-wrap"><el-icon><Share /></el-icon></div>
        <template #title><span>{{ t('nav.dependencyMapping') }}</span></template>
      </el-menu-item>
    </template>

    <!-- 报告中心 -->
    <div v-if="!appStore.sidebarCollapsed" class="menu-section collapsible" @click="toggleSection('report')">
      <span class="menu-label">{{ t('nav.reportCenter') }}</span>
      <el-icon class="section-arrow" :class="{ expanded: expandedSections.report }"><ArrowRight /></el-icon>
    </div>
    <div v-else class="menu-section">
      <span class="menu-label" style="font-size:0"></span>
    </div>
    <template v-if="expandedSections.report || appStore.sidebarCollapsed">
      <el-menu-item index="/dashboard/compliance-report" class="sidebar-item">
        <div class="item-icon-wrap"><el-icon><Files /></el-icon></div>
        <template #title><span>{{ t('nav.complianceReport') }}</span></template>
      </el-menu-item>
      <el-menu-item index="/dashboard/health-report" class="sidebar-item">
        <div class="item-icon-wrap"><el-icon><Document /></el-icon></div>
        <template #title><span>{{ t('nav.healthReport') }}</span></template>
      </el-menu-item>
      <el-menu-item index="/dashboard/dr-score" class="sidebar-item">
        <div class="item-icon-wrap"><el-icon><Trophy /></el-icon></div>
        <template #title><span>{{ t('nav.drScore') }}</span></template>
      </el-menu-item>
    </template>

    <!-- 用户信息 -->
    <div v-if="!appStore.sidebarCollapsed" class="menu-section collapsible" @click="toggleSection('user')">
      <span class="menu-label">{{ t('nav.userInfo') }}</span>
      <el-icon class="section-arrow" :class="{ expanded: expandedSections.user }"><ArrowRight /></el-icon>
    </div>
    <div v-else class="menu-section">
      <span class="menu-label" style="font-size:0"></span>
    </div>
    <template v-if="expandedSections.user || appStore.sidebarCollapsed">
      <el-menu-item index="/dashboard/settings" class="sidebar-item">
        <div class="item-icon-wrap"><el-icon><User /></el-icon></div>
        <template #title><span>{{ t('nav.userInfo') }}</span></template>
      </el-menu-item>
      <el-menu-item index="/dashboard/user-logs" class="sidebar-item">
        <div class="item-icon-wrap"><el-icon><Document /></el-icon></div>
        <template #title><span>{{ t('nav.operationLogs') }}</span></template>
      </el-menu-item>
      <el-menu-item index="/dashboard/cluster-logs" class="sidebar-item">
        <div class="item-icon-wrap"><el-icon><Document /></el-icon></div>
        <template #title><span>{{ t('nav.clusterOperationLogs') }}</span></template>
      </el-menu-item>
      <el-menu-item index="/dashboard/user-notifications" class="sidebar-item">
        <div class="item-icon-wrap"><el-icon><Bell /></el-icon></div>
        <template #title><span>{{ t('nav.notificationSettings') }}</span></template>
      </el-menu-item>
    </template>

    <!-- 管理员功能（仅超级管理员可见） -->
    <template v-if="isSuperUser">
      <div v-if="!appStore.sidebarCollapsed" class="menu-section collapsible" @click="toggleSection('admin')">
        <span class="menu-label">{{ t('nav.adminFunctions') }}</span>
        <el-icon class="section-arrow" :class="{ expanded: expandedSections.admin }"><ArrowRight /></el-icon>
      </div>
      <div v-else class="menu-section">
        <span class="menu-label" style="font-size:0"></span>
      </div>
      <template v-if="expandedSections.admin || appStore.sidebarCollapsed">
        <el-menu-item index="/dashboard/admin/users" class="sidebar-item">
          <div class="item-icon-wrap"><el-icon><User /></el-icon></div>
          <template #title><span>{{ t('nav.adminUsers') }}</span></template>
        </el-menu-item>
      </template>
    </template>
  </el-menu>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAppStore } from '@/stores/app'
import { useThemeStore } from '@/stores/theme'
import { useClusterStore } from '@/stores/cluster'
import { useAuthStore } from '@/stores/auth'
import { Monitor, Connection, Cpu, Box, Bell, Service, User, Document, Coin, Share, Lock, FolderOpened, CopyDocument, Camera, ArrowRight, ArrowDown, Check, DataAnalysis, Switch, Delete, Trophy, Histogram, Files, Tickets, ChatDotRound } from '@element-plus/icons-vue'

const route = useRoute()
const { t } = useI18n()
const appStore = useAppStore()
const themeStore = useThemeStore()
const clusterStore = useClusterStore()
const authStore = useAuthStore()

const isSuperUser = computed(() => authStore.user?.is_superuser || false)

// 集群选择器
const clusterDropdownOpen = ref(false)
const clusterSelectorRef = ref<HTMLElement>()

// 从 pve_version（如 "8.2.4"）提取大版本号（如 "8"）
const pveMajor = computed(() => {
  const v = clusterStore.currentCluster?.pve_version
  if (!v) return ''
  const m = v.match(/(\d+)/)
  return m ? m[1] : ''
})

function selectCluster(id: number) {
  clusterStore.setCluster(id)
  clusterDropdownOpen.value = false
}

function handleClickOutside(e: MouseEvent) {
  if (clusterSelectorRef.value && !clusterSelectorRef.value.contains(e.target as Node)) {
    clusterDropdownOpen.value = false
  }
}

// 菜单分组路由映射
const sectionRoutes: Record<string, string[]> = {
  basic: ['/dashboard/nodes', '/dashboard/vms', '/dashboard/containers', '/dashboard/storage', '/dashboard/networks', '/dashboard/agents'],
  advanced: ['/dashboard/network-topology', '/dashboard/ceph', '/dashboard/ha', '/dashboard/sdn', '/dashboard/firewall', '/dashboard/backup', '/dashboard/replication', '/dashboard/snapshots'],
  ops: ['/dashboard/alerts', '/dashboard/services'],
  smart: ['/dashboard/capacity-planning', '/dashboard/change-tracking', '/dashboard/resource-reclamation', '/dashboard/performance-correlation', '/dashboard/dependency-mapping'],
  report: ['/dashboard/compliance-report', '/dashboard/health-report', '/dashboard/dr-score'],
  user: ['/dashboard/settings', '/dashboard/user-logs', '/dashboard/cluster-logs', '/dashboard/user-notifications'],
  admin: ['/dashboard/admin/users'],
}

function getInitialSections(): Record<string, boolean> {
  const saved = localStorage.getItem('sidebar_sections')
  if (saved) {
    try { return JSON.parse(saved) } catch {}
  }
  return { basic: true, advanced: true, ops: true, smart: true, report: true, user: true }
}

const expandedSections = reactive<Record<string, boolean>>(getInitialSections())

function toggleSection(key: string) {
  expandedSections[key] = !expandedSections[key]
  localStorage.setItem('sidebar_sections', JSON.stringify(expandedSections))
}

// 当前路由所在分组自动展开
function autoExpandActiveSection() {
  for (const [key, paths] of Object.entries(sectionRoutes)) {
    if (paths.some(p => route.path.startsWith(p))) {
      if (!expandedSections[key]) {
        expandedSections[key] = true
        localStorage.setItem('sidebar_sections', JSON.stringify(expandedSections))
      }
      break
    }
  }
}

watch(() => route.path, autoExpandActiveSection, { immediate: true })

onMounted(() => {
  if (!clusterStore.clusterList.length) {
    clusterStore.fetchClusters()
  }
  document.addEventListener('click', handleClickOutside)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<style scoped>
.sidebar-menu {
  height: 100vh;
  border-right: none;
  overflow-y: auto;
  overflow-x: hidden;
  width: 100%;
}
.sidebar-menu::-webkit-scrollbar {
  width: 0;
}
.sidebar-logo {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px 20px 16px;
  margin-bottom: 8px;
  min-height: 68px;
}
.sidebar-logo.collapsed {
  justify-content: center;
  padding: 20px 0 16px;
}
.logo-icon-box {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  background: linear-gradient(135deg, #409eff, #8b5cf6);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.3);
}
.logo-text-group {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  white-space: nowrap;
}
.logo-main {
  font-size: 18px;
  font-weight: 700;
  line-height: 1.2;
}
.logo-sub {
  font-size: 10px;
  letter-spacing: 0.5px;
}
.accent {
  color: #409eff;
  font-weight: 600;
}
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.2s;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}
.menu-section {
  padding: 16px 20px 6px;
}
.menu-section.collapsible {
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  padding: 12px 20px 6px;
  border-radius: 0;
  transition: background 0.15s;
  user-select: none;
}
.menu-section.collapsible:hover {
  background: rgba(64, 158, 255, 0.06);
}
.section-arrow {
  font-size: 12px;
  transition: transform 0.2s ease;
  flex-shrink: 0;
}
.section-arrow.expanded {
  transform: rotate(90deg);
}
.menu-label {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 1.5px;
  font-weight: 600;
}
.sidebar-item {
  margin: 2px 12px;
  border-radius: 10px;
  height: 42px;
  line-height: 42px;
  padding-left: 12px !important;
  transition: all 0.2s ease;
}
.sidebar-item .el-icon {
  font-size: 18px;
  margin: 0;
}
.sidebar-item:hover {
  background: rgba(64, 158, 255, 0.1) !important;
}
.sidebar-item.is-active {
  background: linear-gradient(135deg, rgba(64, 158, 255, 0.2), rgba(139, 92, 246, 0.15)) !important;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.15);
}
.sidebar-item.is-active .item-icon-wrap {
  background: linear-gradient(135deg, #409eff, #8b5cf6);
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.4);
  color: #fff;
}
.item-icon-wrap {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 10px;
  flex-shrink: 0;
  transition: all 0.2s ease;
}

/* 集群选择器 */
.cluster-selector {
  position: relative;
  padding: 0 12px 8px;
}
.cluster-trigger {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid var(--border-color);
  background: var(--bg-primary);
}
.cluster-trigger:hover {
  border-color: rgba(64, 158, 255, 0.3);
  background: rgba(64, 158, 255, 0.04);
}
.cluster-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #c0c4cc;
  flex-shrink: 0;
  transition: background 0.2s;
}
.cluster-dot.online {
  background: #67c23a;
  box-shadow: 0 0 6px rgba(103, 194, 58, 0.4);
}
.cluster-name {
  flex: 1;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pve-version-badge {
  font-size: 10px;
  font-weight: 700;
  color: #409eff;
  background: rgba(64, 158, 255, 0.12);
  padding: 1px 6px;
  border-radius: 4px;
  flex-shrink: 0;
  letter-spacing: 0.3px;
}
.cluster-caret {
  font-size: 12px;
  color: var(--text-muted);
  transition: transform 0.2s ease;
  flex-shrink: 0;
}
.cluster-caret.open {
  transform: rotate(180deg);
}
.cluster-dropdown {
  position: absolute;
  left: 12px;
  right: 12px;
  top: calc(100% + 4px);
  border-radius: 12px;
  padding: 6px;
  z-index: 100;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12), 0 2px 8px rgba(0, 0, 0, 0.06);
  border: 1px solid var(--border-color);
  background: var(--bg-primary);
}
.cluster-option {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s ease;
}
.cluster-option:hover {
  background: rgba(64, 158, 255, 0.08);
}
.cluster-option.selected {
  background: rgba(64, 158, 255, 0.1);
}
.cluster-option.empty {
  cursor: default;
  justify-content: center;
}
.cluster-option.empty:hover {
  background: transparent;
}
.cluster-option-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.cluster-option-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.cluster-option-meta {
  font-size: 11px;
  color: var(--text-muted);
}
.cluster-check {
  font-size: 14px;
  color: #409eff;
  flex-shrink: 0;
}

/* dropdown 动画 */
.dropdown-enter-active, .dropdown-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.dropdown-enter-from, .dropdown-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

.cluster-switcher-collapsed {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 36px;
  margin: 0 6px 4px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}
.cluster-switcher-collapsed:hover {
  background: rgba(64, 158, 255, 0.1);
}
.cluster-switcher-collapsed .el-icon {
  font-size: 18px;
}

/* 压缩模式：图标居中 */
.sidebar-menu.el-menu--collapse .sidebar-item {
  margin: 2px 6px;
  padding: 0 !important;
  display: flex !important;
  align-items: center;
  justify-content: center;
  line-height: normal;
}
.sidebar-menu.el-menu--collapse .sidebar-item :deep(.el-menu-tooltip__trigger) {
  display: flex !important;
  align-items: center;
  justify-content: center;
  padding: 0 !important;
  margin: 0 !important;
  flex: none;
  line-height: normal;
}
.sidebar-menu.el-menu--collapse .sidebar-item .item-icon-wrap {
  margin: 0 !important;
  flex: none;
}

/* ===== 亮色主题（默认） ===== */
.sidebar-menu {
  --el-menu-bg-color: transparent;
  --el-menu-text-color: #4e5159;
  --el-menu-hover-bg-color: rgba(64, 158, 255, 0.08);
  --el-menu-hover-text-color: #409eff;
  --el-menu-active-color: #409eff;
  background: var(--bg-secondary) !important;
}
.sidebar-logo {
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
}
.logo-main {
  color: #1d1e24;
}
.logo-sub {
  color: rgba(0, 0, 0, 0.35);
}
.section-arrow {
  color: rgba(0, 0, 0, 0.25);
}
.menu-label {
  color: rgba(0, 0, 0, 0.3);
}
.sidebar-item:hover {
  background: rgba(64, 158, 255, 0.08) !important;
}
.sidebar-item.is-active {
  color: #409eff !important;
}
.sidebar-item.is-active .item-icon-wrap {
  background: linear-gradient(135deg, #409eff, #8b5cf6);
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.4);
  color: #fff;
}
.item-icon-wrap {
  background: rgba(0, 0, 0, 0.05);
  color: #606266;
}

/* ===== 暗色主题 ===== */
.sidebar-menu.is-dark {
  --el-menu-bg-color: transparent;
  --el-menu-text-color: rgba(255, 255, 255, 0.6);
  --el-menu-hover-bg-color: rgba(64, 158, 255, 0.1);
  --el-menu-hover-text-color: rgba(255, 255, 255, 0.85);
  --el-menu-active-color: #fff;
  background: var(--bg-secondary) !important;
}
.sidebar-menu.is-dark .sidebar-logo {
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}
.sidebar-menu.is-dark .logo-main {
  color: #fff;
}
.sidebar-menu.is-dark .logo-sub {
  color: rgba(255, 255, 255, 0.4);
}
.sidebar-menu.is-dark .menu-label {
  color: rgba(255, 255, 255, 0.25);
}
.sidebar-menu.is-dark .menu-section.collapsible:hover {
  background: rgba(64, 158, 255, 0.08);
}
.sidebar-menu.is-dark .section-arrow {
  color: rgba(255, 255, 255, 0.35);
}
.sidebar-menu.is-dark .cluster-trigger {
  border-color: rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.03);
}
.sidebar-menu.is-dark .cluster-trigger:hover {
  border-color: rgba(64, 158, 255, 0.3);
  background: rgba(64, 158, 255, 0.06);
}
.sidebar-menu.is-dark .pve-version-badge {
  color: #6db3ff;
  background: rgba(64, 158, 255, 0.18);
}
.sidebar-menu.is-dark .cluster-dropdown {
  border-color: rgba(255, 255, 255, 0.1);
  background: var(--bg-primary);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3), 0 2px 8px rgba(0, 0, 0, 0.2);
}
.sidebar-menu.is-dark .cluster-option:hover {
  background: rgba(64, 158, 255, 0.12);
}
.sidebar-menu.is-dark .cluster-option.selected {
  background: rgba(64, 158, 255, 0.15);
}
.sidebar-menu.is-dark .sidebar-item:hover {
  background: rgba(64, 158, 255, 0.1) !important;
}
.sidebar-menu.is-dark .sidebar-item.is-active {
  color: #fff !important;
}
.sidebar-menu.is-dark .sidebar-item.is-active .item-icon-wrap {
  background: linear-gradient(135deg, #409eff, #8b5cf6);
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.4);
  color: #fff;
}
.sidebar-menu.is-dark .item-icon-wrap {
  background: rgba(255, 255, 255, 0.06);
  color: rgba(255, 255, 255, 0.6);
}
</style>
