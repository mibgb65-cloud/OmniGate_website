<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ChatDotRound, DataAnalysis, Key, Link, Monitor, User, UserFilled } from '@element-plus/icons-vue'

import { logout } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'
import AdminHeader from '@/layouts/components/Header.vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const isCollapse = ref(false)

const navItems = [
  {
    path: '/dashboard',
    title: '控制台概览',
    icon: DataAnalysis,
  },
  {
    path: '/google/accounts',
    title: 'Google 账号池',
    icon: Monitor,
  },
  {
    path: '/github/accounts',
    title: 'GitHub 账号池',
    icon: Link,
  },
  {
    path: '/chatgpt/accounts',
    title: 'ChatGPT 账号池',
    icon: ChatDotRound,
  },
  {
    path: '/tools/2fa',
    title: '2FA 工具',
    icon: Key,
  },
  {
    path: '/profile',
    title: '个人中心',
    icon: UserFilled,
  },
  {
    path: '/users',
    title: '用户管理',
    icon: User,
  },
]

function getGoogleSnapshotEmail(accountId) {
  if (!accountId) {
    return ''
  }
  try {
    const raw = sessionStorage.getItem(`og-google-account-snapshot-${accountId}`)
    if (!raw) {
      return ''
    }
    const snapshot = JSON.parse(raw)
    return typeof snapshot?.email === 'string' ? snapshot.email.trim() : ''
  } catch {
    return ''
  }
}

const breadcrumbs = computed(() => {
  const items = route.matched
    .filter((item) => item.meta?.title)
    .map((item) => ({
      path: item.path,
      title: item.meta.title,
    }))

  if (route.path.startsWith('/google/accounts/') && route.params.id) {
    const emailFromQuery = typeof route.query.email === 'string' ? route.query.email.trim() : ''
    const emailFromSnapshot = getGoogleSnapshotEmail(String(route.params.id))
    const detailLabel = emailFromQuery || emailFromSnapshot || String(route.params.id)
    items.push({
      path: route.fullPath,
      title: detailLabel,
    })
  }
  return items
})
const activeMenuPath = computed(() => {
  const currentPath = route.path
  if (currentPath.startsWith('/users')) return '/users'
  if (currentPath.startsWith('/google/accounts')) return '/google/accounts'
  if (currentPath.startsWith('/github/accounts')) return '/github/accounts'
  if (currentPath.startsWith('/chatgpt/accounts')) return '/chatgpt/accounts'
  if (currentPath.startsWith('/tools/2fa')) return '/tools/2fa'
  if (currentPath.startsWith('/profile')) return '/profile'
  if (currentPath.startsWith('/dashboard')) return '/dashboard'
  return currentPath
})

function toggleCollapse() {
  isCollapse.value = !isCollapse.value
}

async function handleLogout() {
  try {
    await logout({ refreshToken: authStore.refreshToken }).catch(() => undefined)
  } finally {
    authStore.clearAuth()
    await router.replace('/login')
    ElMessage.success('已安全退出登录')
  }
}
</script>

<template>
  <el-container class="admin-shell">
    <el-aside :width="isCollapse ? '84px' : '258px'" class="admin-aside">
      <div class="brand" @click="router.push('/dashboard')">
        <div class="brand-mark">OG</div>
        <transition name="fade">
          <div v-show="!isCollapse" class="brand-copy">
            <h1>OmniGate</h1>
            <p>Admin Control</p>
          </div>
        </transition>
      </div>

      <el-menu
        :default-active="activeMenuPath"
        :collapse="isCollapse"
        :collapse-transition="false"
        router
        class="admin-menu"
      >
        <el-menu-item v-for="item in navItems" :key="item.path" :index="item.path">
          <el-icon><component :is="item.icon" /></el-icon>
          <template #title>{{ item.title }}</template>
        </el-menu-item>
      </el-menu>

      <div class="aside-footer" v-if="!isCollapse">
        <div class="footer-card">
          <p>System Status</p>
          <div class="status-indicator">
            <span class="dot"></span>
            Operational
          </div>
        </div>
      </div>
    </el-aside>

    <el-container class="main-shell">
      <AdminHeader
        :is-collapse="isCollapse"
        :breadcrumbs="breadcrumbs"
        :username="authStore.username"
        :role="authStore.role"
        @toggle-collapse="toggleCollapse"
        @logout="handleLogout"
      />

      <el-main class="page-main">
        <router-view v-slot="{ Component }">
          <transition name="fade-transform" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.admin-shell {
  height: 100vh;
  background-color: #f4f6f8;
  padding: 12px;
  gap: 12px;
}

.admin-aside {
  background: #172028;
  border-radius: 16px;
  display: flex;
  flex-direction: column;
  transition: width 0.3s ease;
  overflow: hidden;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}

.brand {
  padding: 24px 20px;
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.brand:hover {
  background: rgba(255, 255, 255, 0.03);
}

.brand .brand-mark {
  width: 40px;
  height: 40px;
  background: linear-gradient(135deg, #1f2d39 0%, #12a173 100%);
  border-radius: 10px;
  display: grid;
  place-items: center;
  color: #ffffff;
  font-weight: 700;
  font-size: 1.2rem;
  box-shadow: 0 6px 16px rgba(8, 15, 20, 0.3);
}

.brand .brand-copy h1 {
  margin: 0;
  color: #ffffff;
  font-size: 1.08rem;
  font-weight: 700;
}

.brand .brand-copy p {
  margin: 2px 0 0;
  color: rgba(255, 255, 255, 0.56);
  font-size: 0.75rem;
  letter-spacing: 0.02em;
}

.admin-menu {
  border-right: none;
  background: transparent;
  flex: 1;
}

:deep(.admin-menu .el-menu-item) {
  color: rgba(255, 255, 255, 0.65);
  margin: 4px 12px;
  border-radius: 10px;
  height: 50px;
  transition: all 0.3s ease;
}

:deep(.admin-menu .el-menu-item:hover) {
  background: rgba(255, 255, 255, 0.06);
  color: #ffffff;
}

:deep(.admin-menu .el-menu-item.is-active) {
  background: rgba(18, 161, 115, 0.16);
  color: #39be95;
  font-weight: 700;
}

:deep(.admin-menu .el-menu-item.is-active .el-icon) {
  color: #39be95;
}

:deep(.admin-menu .el-menu-item .el-icon) {
  font-size: 1.12rem;
}

:deep(.admin-menu.el-menu--collapse) {
  width: 100%;
}

:deep(.admin-menu.el-menu--collapse .el-menu-item) {
  width: calc(100% - 20px);
  margin: 4px auto;
  padding: 0 !important;
  justify-content: center;
}

:deep(.admin-menu.el-menu--collapse .el-menu-item .el-icon) {
  margin-right: 0;
}

.aside-footer {
  padding: 20px;
}

.aside-footer .footer-card {
  border-radius: 12px;
  padding: 12px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.04);
}

.aside-footer .footer-card p {
  margin: 0 0 6px;
  color: rgba(255, 255, 255, 0.45);
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.aside-footer .footer-card .status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #ffffff;
  font-size: 0.84rem;
  font-weight: 600;
}

.aside-footer .footer-card .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #12a173;
  box-shadow: 0 0 12px #12a173;
}

.main-shell {
  background: #ffffff;
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.page-main {
  padding: 24px;
  background: #f4f6f8;
  overflow-y: auto;
}

.fade-transform-enter-active,
.fade-transform-leave-active {
  transition: all 0.3s ease;
}

.fade-transform-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.fade-transform-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

@media (max-width: 992px) {
  .admin-shell {
    padding: 0;
    gap: 0;
  }

  .admin-aside {
    border-radius: 0;
  }

  .main-shell {
    border-radius: 0;
  }

  .page-main {
    padding: 16px;
  }
}
</style>
