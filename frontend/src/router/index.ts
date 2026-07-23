import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/Home.vue'),
    meta: { title: '首页', titleKey: 'nav.home', noAuth: true },
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/auth/Login.vue'),
    meta: { title: '登录', titleKey: 'nav.login', noAuth: true },
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/auth/Register.vue'),
    meta: { title: '注册', titleKey: 'nav.register', noAuth: true },
  },
  {
    path: '/forgot-password',
    name: 'ForgotPassword',
    component: () => import('@/views/auth/ForgotPassword.vue'),
    meta: { title: '找回密码', titleKey: 'nav.forgotPassword', noAuth: true },
  },
  {
    path: '/',
    redirect: '/dashboard',
  },
  {
    path: '/dashboard',
    component: () => import('@/layouts/MainLayout.vue'),
    children: [
      {
        path: '',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/index.vue'),
        meta: { title: '控制台', titleKey: 'nav.dashboard', icon: 'Monitor' },
      },
      {
        path: 'change-password',
        name: 'ChangePassword',
        component: () => import('@/views/dashboard/ChangePassword.vue'),
        meta: { title: '修改密码', titleKey: 'nav.changePassword', icon: 'Key' },
      },
      {
        path: 'clusters',
        name: 'Clusters',
        component: () => import('@/views/clusters/index.vue'),
        meta: { title: '集群管理', titleKey: 'nav.clusters', icon: 'Connection' },
      },
      {
        path: 'agents',
        name: 'Agents',
        component: () => import('@/views/agents/index.vue'),
        meta: { title: 'Agent 管理', titleKey: 'nav.agentManagement', icon: 'User' },
      },
      {
        path: 'nodes',
        name: 'Nodes',
        component: () => import('@/views/nodes/index.vue'),
        meta: { title: '节点管理', titleKey: 'nav.nodeManagement', icon: 'Cpu' },
      },
      {
        path: 'vms',
        name: 'VMs',
        component: () => import('@/views/vms/index.vue'),
        meta: { title: '虚拟机', titleKey: 'nav.virtualMachines', icon: 'Cpu' },
      },
      {
        path: 'containers',
        name: 'Containers',
        component: () => import('@/views/containers/index.vue'),
        meta: { title: '容器', titleKey: 'nav.containers', icon: 'Box' },
      },
      {
        path: 'storage',
        name: 'Storage',
        component: () => import('@/views/storage/index.vue'),
        meta: { title: '存储管理', titleKey: 'nav.storageManagement', icon: 'Coin' },
      },
      {
        path: 'networks',
        name: 'Networks',
        component: () => import('@/views/networks/index.vue'),
        meta: { title: '网络接口', titleKey: 'nav.networkInterfaces', icon: 'Connection' },
      },
      {
        path: 'network-topology',
        name: 'NetworkTopology',
        component: () => import('@/views/network-topology/index.vue'),
        meta: { title: '网络拓扑', titleKey: 'nav.networkTopology', icon: 'Share' },
      },
      {
        path: 'ceph',
        name: 'Ceph',
        component: () => import('@/views/ceph/index.vue'),
        meta: { title: 'Ceph 存储', titleKey: 'nav.cephStorage', icon: 'Box' },
      },
      {
        path: 'ha',
        name: 'HA',
        component: () => import('@/views/ha/index.vue'),
        meta: { title: '高可用管理', titleKey: 'nav.haManagement', icon: 'Connection' },
      },
      {
        path: 'sdn',
        name: 'SDN',
        component: () => import('@/views/sdn/index.vue'),
        meta: { title: '软件定义网络', titleKey: 'nav.softwareDefinedNetwork', icon: 'Share' },
      },
      {
        path: 'firewall',
        name: 'Firewall',
        component: () => import('@/views/firewall/index.vue'),
        meta: { title: '防火墙', titleKey: 'nav.firewall', icon: 'Lock' },
      },
      {
        path: 'backup',
        name: 'Backup',
        component: () => import('@/views/backup/index.vue'),
        meta: { title: '备份管理', titleKey: 'nav.backupManagement', icon: 'FolderOpened' },
      },
      {
        path: 'replication',
        name: 'Replication',
        component: () => import('@/views/replication/index.vue'),
        meta: { title: '数据复制', titleKey: 'nav.dataReplication', icon: 'CopyDocument' },
      },
      {
        path: 'snapshots',
        name: 'Snapshots',
        component: () => import('@/views/snapshots/index.vue'),
        meta: { title: '快照管理', titleKey: 'nav.snapshotManagement', icon: 'Camera' },
      },
      {
        path: 'cluster-tasks',
        name: 'ClusterTasks',
        component: () => import('@/views/cluster-tasks/index.vue'),
        meta: { title: '集群任务', titleKey: 'nav.clusterTasks', icon: 'Tickets' },
      },
      {
        path: 'cluster-log',
        name: 'ClusterLog',
        component: () => import('@/views/cluster-log/index.vue'),
        meta: { title: '集群日志', titleKey: 'nav.clusterLog', icon: 'Document' },
      },
      // 智能分析
      {
        path: 'capacity-planning',
        name: 'CapacityPlanning',
        component: () => import('@/views/capacity-planning/index.vue'),
        meta: { title: '容量规划', titleKey: 'nav.capacityPlanning', icon: 'DataAnalysis' },
      },
      {
        path: 'change-tracking',
        name: 'ChangeTracking',
        component: () => import('@/views/change-tracking/index.vue'),
        meta: { title: '变更追踪', titleKey: 'nav.changeTracking', icon: 'Switch' },
      },
      {
        path: 'resource-reclamation',
        name: 'ResourceReclamation',
        component: () => import('@/views/resource-reclamation/index.vue'),
        meta: { title: '资源回收', titleKey: 'nav.resourceReclamation', icon: 'Delete' },
      },
      {
        path: 'dr-score',
        name: 'DRScore',
        component: () => import('@/views/dr-score/index.vue'),
        meta: { title: '灾备评分', titleKey: 'nav.drScore', icon: 'Trophy' },
      },
      {
        path: 'performance-correlation',
        name: 'PerformanceCorrelation',
        component: () => import('@/views/performance-correlation/index.vue'),
        meta: { title: '性能关联', titleKey: 'nav.performanceCorrelation', icon: 'Histogram' },
      },
      {
        path: 'dependency-mapping',
        name: 'DependencyMapping',
        component: () => import('@/views/dependency-mapping/index.vue'),
        meta: { title: '依赖链路', titleKey: 'nav.dependencyMapping', icon: 'Share' },
      },
      // 报告中心
      {
        path: 'compliance-report',
        name: 'ComplianceReport',
        component: () => import('@/views/compliance-report/index.vue'),
        meta: { title: '合规审计报告', titleKey: 'nav.complianceReport', icon: 'Files' },
      },
      {
        path: 'health-report',
        name: 'HealthReport',
        component: () => import('@/views/health-report/index.vue'),
        meta: { title: '定期健康报告', titleKey: 'nav.healthReport', icon: 'Document' },
      },
      // 运维检测
      {
        path: 'alerts',
        name: 'Alerts',
        component: () => import('@/views/alerts/index.vue'),
        meta: { title: '告警中心', titleKey: 'nav.alertCenter', icon: 'Bell' },
      },
      {
        path: 'services',
        name: 'Services',
        component: () => import('@/views/services/index.vue'),
        meta: { title: '运维服务', titleKey: 'nav.opsService', icon: 'Service' },
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('@/views/settings/index.vue'),
        meta: { title: '用户信息', titleKey: 'nav.userInfo', icon: 'User' },
      },
      {
        path: 'user-logs',
        name: 'UserLogs',
        component: () => import('@/views/user-logs/index.vue'),
        meta: { title: '操作日志', titleKey: 'nav.operationLogs', icon: 'Document' },
      },
      {
        path: 'cluster-logs',
        name: 'ClusterLogs',
        component: () => import('@/views/cluster-logs/index.vue'),
        meta: { title: '集群操作记录', titleKey: 'nav.clusterOperationLogs', icon: 'Document' },
      },
      {
        path: 'user-notifications',
        name: 'UserNotifications',
        component: () => import('@/views/user-notifications/index.vue'),
        meta: { title: '通知设置', titleKey: 'nav.notificationSettings', icon: 'Bell' },
      },
      // 管理员专用
      {
        path: 'admin/users',
        name: 'AdminUsers',
        component: () => import('@/views/admin/users/index.vue'),
        meta: { title: '用户管理', titleKey: 'nav.adminUsers', icon: 'User', adminOnly: true },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 路由守卫
router.beforeEach((to, _from, next) => {
  const token = localStorage.getItem('token')
  if (!to.meta.noAuth && !token) {
    next('/login')
  } else {
    next()
  }
})

export default router
