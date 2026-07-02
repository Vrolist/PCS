import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/Home.vue'),
    meta: { title: '首页', noAuth: true },
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/auth/Login.vue'),
    meta: { title: '登录', noAuth: true },
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/auth/Register.vue'),
    meta: { title: '注册', noAuth: true },
  },
  {
    path: '/forgot-password',
    name: 'ForgotPassword',
    component: () => import('@/views/auth/ForgotPassword.vue'),
    meta: { title: '找回密码', noAuth: true },
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
        meta: { title: '控制台', icon: 'Monitor' },
      },
      {
        path: 'change-password',
        name: 'ChangePassword',
        component: () => import('@/views/dashboard/ChangePassword.vue'),
        meta: { title: '修改密码', icon: 'Key' },
      },
      {
        path: 'clusters',
        name: 'Clusters',
        component: () => import('@/views/clusters/index.vue'),
        meta: { title: '集群管理', icon: 'Connection' },
      },
      {
        path: 'nodes',
        name: 'Nodes',
        component: () => import('@/views/nodes/index.vue'),
        meta: { title: '节点管理', icon: 'Cpu' },
      },
      {
        path: 'vms',
        name: 'VMs',
        component: () => import('@/views/vms/index.vue'),
        meta: { title: '虚拟机', icon: 'Cpu' },
      },
      {
        path: 'containers',
        name: 'Containers',
        component: () => import('@/views/containers/index.vue'),
        meta: { title: '容器', icon: 'Box' },
      },
      {
        path: 'storage',
        name: 'Storage',
        component: () => import('@/views/storage/index.vue'),
        meta: { title: '存储管理', icon: 'Coin' },
      },
      {
        path: 'networks',
        name: 'Networks',
        component: () => import('@/views/networks/index.vue'),
        meta: { title: '网络接口', icon: 'Connection' },
      },
      {
        path: 'network-topology',
        name: 'NetworkTopology',
        component: () => import('@/views/network-topology/index.vue'),
        meta: { title: '网络拓扑', icon: 'Share' },
      },
      {
        path: 'ceph',
        name: 'Ceph',
        component: () => import('@/views/ceph/index.vue'),
        meta: { title: 'Ceph 存储', icon: 'Box' },
      },
      {
        path: 'ha',
        name: 'HA',
        component: () => import('@/views/ha/index.vue'),
        meta: { title: 'HA 高可用', icon: 'Connection' },
      },
      {
        path: 'sdn',
        name: 'SDN',
        component: () => import('@/views/sdn/index.vue'),
        meta: { title: 'SDN', icon: 'Share' },
      },
      {
        path: 'firewall',
        name: 'Firewall',
        component: () => import('@/views/firewall/index.vue'),
        meta: { title: 'Firewall', icon: 'Lock' },
      },
      {
        path: 'backup',
        name: 'Backup',
        component: () => import('@/views/backup/index.vue'),
        meta: { title: 'Backup', icon: 'FolderOpened' },
      },
      {
        path: 'replication',
        name: 'Replication',
        component: () => import('@/views/replication/index.vue'),
        meta: { title: 'Replication', icon: 'CopyDocument' },
      },
      {
        path: 'snapshots',
        name: 'Snapshots',
        component: () => import('@/views/snapshots/index.vue'),
        meta: { title: 'Snapshots', icon: 'Camera' },
      },
      {
        path: 'alerts',
        name: 'Alerts',
        component: () => import('@/views/alerts/index.vue'),
        meta: { title: '告警中心', icon: 'Bell' },
      },
      {
        path: 'services',
        name: 'Services',
        component: () => import('@/views/services/index.vue'),
        meta: { title: '运维服务', icon: 'Service' },
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('@/views/settings/index.vue'),
        meta: { title: '用户信息', icon: 'User' },
      },
      {
        path: 'user-logs',
        name: 'UserLogs',
        component: () => import('@/views/user-logs/index.vue'),
        meta: { title: '操作日志', icon: 'Document' },
      },
      {
        path: 'user-notifications',
        name: 'UserNotifications',
        component: () => import('@/views/user-notifications/index.vue'),
        meta: { title: '通知设置', icon: 'Bell' },
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
