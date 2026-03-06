import { createRouter, createWebHistory } from 'vue-router'

import pinia from '@/stores'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { guestOnly: true, title: '登录' },
  },
  {
    path: '/',
    component: () => import('@/layouts/AdminLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        redirect: '/dashboard',
      },
      {
        path: '/dashboard',
        name: 'dashboard',
        component: () => import('@/views/Dashboard.vue'),
        meta: { requiresAuth: true, title: '控制台概览' },
      },
      {
        path: '/users',
        name: 'users',
        component: () => import('@/views/users/UserManagementView.vue'),
        meta: { requiresAuth: true, title: '用户管理' },
      },
      {
        path: '/google/accounts',
        name: 'google-accounts',
        component: () => import('@/views/google/GoogleAccountList.vue'),
        meta: { requiresAuth: true, title: 'Google 账号池' },
      },
      {
        path: '/google/accounts/:id',
        name: 'google-account-detail',
        component: () => import('@/views/google/GoogleAccountDetail.vue'),
        meta: { requiresAuth: true, title: 'Google 账号详情' },
      },
      {
        path: '/github/accounts',
        name: 'github-accounts',
        component: () => import('@/views/github/GithubAccountList.vue'),
        meta: { requiresAuth: true, title: 'GitHub 账号池' },
      },
      {
        path: '/github/accounts/:id',
        name: 'github-account-detail',
        component: () => import('@/views/github/GithubAccountDetail.vue'),
        meta: { requiresAuth: true, title: 'GitHub 账号详情' },
      },
      {
        path: '/chatgpt/accounts',
        name: 'chatgpt-accounts',
        component: () => import('@/views/chatgpt/ChatgptAccountList.vue'),
        meta: { requiresAuth: true, title: 'ChatGPT 账号池' },
      },
      {
        path: '/chatgpt/accounts/:id',
        name: 'chatgpt-account-detail',
        component: () => import('@/views/chatgpt/ChatgptAccountDetail.vue'),
        meta: { requiresAuth: true, title: 'ChatGPT 账号详情' },
      },
      {
        path: '/tools/2fa',
        name: 'two-factor-tool',
        component: () => import('@/views/tools/TwoFactorToolView.vue'),
        meta: { requiresAuth: true, title: '2FA 工具' },
      },
      {
        path: '/profile',
        name: 'profile',
        component: () => import('@/views/profile/ProfileView.vue'),
        meta: { requiresAuth: true, title: '个人中心' },
      },
    ],
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@/views/NotFoundView.vue'),
    meta: { title: '404' },
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
  scrollBehavior() {
    return { top: 0, left: 0 }
  },
})

router.beforeEach((to) => {
  const authStore = useAuthStore(pinia)

  if (to.meta.requiresAuth && !authStore.hasAccessToken) {
    return {
      path: '/login',
      query: { redirect: to.fullPath },
    }
  }

  if (to.meta.guestOnly && authStore.hasAccessToken) {
    const redirect = typeof to.query.redirect === 'string' ? to.query.redirect : '/dashboard'
    return redirect
  }

  return true
})

router.afterEach((to) => {
  const pageTitle = to.meta?.title ? `${to.meta.title} · OmniGate` : 'OmniGate Admin'
  document.title = pageTitle
})

export default router
