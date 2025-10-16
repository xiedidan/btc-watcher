import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/Login.vue'),
      meta: { requiresAuth: false }
    },
    {
      path: '/',
      component: () => import('@/layouts/MainLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          name: 'dashboard',
          component: () => import('@/views/Dashboard.vue'),
          meta: { title: '仪表盘' }
        },
        {
          path: 'strategies',
          name: 'strategies',
          component: () => import('@/views/Strategies.vue'),
          meta: { title: '策略管理' }
        },
        {
          path: 'drafts',
          name: 'drafts',
          component: () => import('@/views/Drafts.vue'),
          meta: { title: '草稿管理' }
        },
        {
          path: 'signals',
          name: 'signals',
          component: () => import('@/views/Signals.vue'),
          meta: { title: '信号列表' }
        },
        {
          path: 'proxies',
          name: 'proxies',
          component: () => import('@/views/Proxies.vue'),
          meta: { title: '代理管理' }
        },
        {
          path: 'monitoring',
          name: 'monitoring',
          component: () => import('@/views/Monitoring.vue'),
          meta: { title: '系统监控' }
        },
        {
          path: 'settings',
          name: 'settings',
          component: () => import('@/views/Settings.vue'),
          meta: { title: '系统设置' }
        }
      ]
    }
  ]
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const userStore = useUserStore()
  const requiresAuth = to.matched.some(record => record.meta.requiresAuth)

  if (requiresAuth && !userStore.isAuthenticated) {
    next({ name: 'login', query: { redirect: to.fullPath } })
  } else if (to.name === 'login' && userStore.isAuthenticated) {
    next({ name: 'dashboard' })
  } else {
    next()
  }
})

export default router
