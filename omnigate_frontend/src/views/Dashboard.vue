<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Calendar, Collection, Cpu, Monitor, Plus, Right, User, UserFilled } from '@element-plus/icons-vue'

import { pageGoogleAccounts } from '@/api/google'
import { pageGithubAccounts } from '@/api/github'
import { pageChatgptAccounts } from '@/api/chatgpt'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const router = useRouter()

const greeting = computed(() => {
  const hour = new Date().getHours()
  if (hour < 6) return '凌晨好'
  if (hour < 9) return '早安'
  if (hour < 12) return '上午好'
  if (hour < 14) return '中午好'
  if (hour < 18) return '下午好'
  return '晚上好'
})

const roleLabel = computed(() => {
  const roleMap = {
    ADMIN: '超级管理员',
    OPERATOR: '运营管理员',
    VIEWER: '只读观察者',
  }
  return roleMap[authStore.role] || authStore.role || '管理员'
})

const currentDate = computed(() =>
  new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    weekday: 'long',
  }).format(new Date()),
)

const loadingStats = ref(false)
const lastSyncTime = ref('尚未同步')

const stats = ref([
  {
    label: '系统总用户',
    value: '1,284',
    trend: '接口同步中',
    icon: UserFilled,
    tone: 'emerald',
  },
  {
    label: 'Google 账号池',
    value: '520',
    trend: '接口同步中',
    icon: Monitor,
    tone: 'slate',
  },
  {
    label: 'GitHub 账号池',
    value: '312',
    trend: '接口同步中',
    icon: Collection,
    tone: 'sage',
  },
  {
    label: 'ChatGPT 账号池',
    value: '168',
    trend: '接口同步中',
    icon: Cpu,
    tone: 'amber',
  },
])

const quickActions = [
  {
    title: '导入 Google 账号',
    description: '批量导入账号并同步状态',
    icon: Plus,
    path: '/google/accounts',
  },
  {
    title: '维护 GitHub 池',
    description: '统一管理账号状态与代理',
    icon: Collection,
    path: '/github/accounts',
  },
  {
    title: '进入 ChatGPT 模块',
    description: '管理账号池与批量状态操作',
    icon: Cpu,
    path: '/chatgpt/accounts',
  },
  {
    title: '个人中心',
    description: '查看当前用户资料与安全状态',
    icon: User,
    path: '/profile',
  },
]

const activities = ref([
  {
    time: '2026-03-03 14:20',
    content: '导入 50 个 Google 账号，并完成第一轮同步检查。',
  },
  {
    time: '2026-03-03 10:00',
    content: '系统安全巡检完成，核心服务状态全部正常。',
  },
  {
    time: '2026-03-02 18:45',
    content: '更新 GitHub 令牌配置，刷新历史失效凭据。',
  },
  {
    time: '2026-03-01 11:30',
    content: '新增管理员 mimanchi 并绑定默认权限组。',
  },
])

function formatNumber(value) {
  return Number(value || 0).toLocaleString('zh-CN')
}

async function fetchOverviewStats() {
  loadingStats.value = true
  try {
    const [googleData, githubData, chatgptData] = await Promise.all([
      pageGoogleAccounts({ current: 1, size: 1 }),
      pageGithubAccounts({ current: 1, size: 1 }),
      pageChatgptAccounts({ current: 1, size: 1 }),
    ])

    const googleTotal = Number(googleData?.total || 0)
    const githubTotal = Number(githubData?.total || 0)
    const chatgptTotal = Number(chatgptData?.total || 0)
    const mergedTotal = googleTotal + githubTotal + chatgptTotal

    stats.value = [
      {
        label: '系统总用户',
        value: formatNumber(mergedTotal),
        trend: '由账号池总量聚合',
        icon: UserFilled,
        tone: 'emerald',
      },
      {
        label: 'Google 账号池',
        value: formatNumber(googleTotal),
        trend: '实时同步',
        icon: Monitor,
        tone: 'slate',
      },
      {
        label: 'GitHub 账号池',
        value: formatNumber(githubTotal),
        trend: '实时同步',
        icon: Collection,
        tone: 'sage',
      },
      {
        label: 'ChatGPT 账号池',
        value: formatNumber(chatgptTotal),
        trend: '实时同步',
        icon: Cpu,
        tone: 'amber',
      },
    ]

    const now = new Date()
    lastSyncTime.value = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(
      now.getDate(),
    ).padStart(2, '0')} ${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`

    activities.value = [
      {
        time: lastSyncTime.value,
        content: `已完成首页概览数据刷新，Google ${formatNumber(googleTotal)} / GitHub ${formatNumber(githubTotal)} / ChatGPT ${formatNumber(chatgptTotal)}。`,
      },
      ...activities.value.slice(0, 3),
    ]
  } catch {
    ElMessage.warning('概览数据刷新失败，已回退为默认占位数据')
  } finally {
    loadingStats.value = false
  }
}

function handleQuickAction(path) {
  if (!path) return
  router.push(path)
}

onMounted(fetchOverviewStats)
</script>

<template>
  <div class="dashboard-view">
    <section class="welcome-card">
      <div class="welcome-content">
        <div class="greeting-chip">
          <el-icon><Calendar /></el-icon>
          <span>{{ greeting }}，{{ authStore.username || '管理员' }}</span>
        </div>

        <h1>欢迎回到 OmniGate 智能资产控制台</h1>
        <p>当前权限：<strong>{{ roleLabel }}</strong>。你可以继续管理账号池、同步状态与系统配置。</p>

        <div class="welcome-meta">
          <span class="meta-item">{{ currentDate }}</span>
          <span class="meta-item">最近同步：{{ lastSyncTime }}</span>
        </div>
      </div>

      <div class="welcome-accent">
        <div class="accent-ring" />
        <div class="accent-pill">权限等级 {{ authStore.role || 'ADMIN' }}</div>
      </div>
    </section>

    <section class="stats-grid" v-loading="loadingStats">
      <article v-for="item in stats" :key="item.label" class="stat-card">
        <div class="stat-top">
          <div class="stat-icon" :class="`tone-${item.tone}`">
            <el-icon><component :is="item.icon" /></el-icon>
          </div>
          <span class="stat-label">{{ item.label }}</span>
        </div>
        <strong class="stat-value">{{ item.value }}</strong>
        <span class="stat-trend">{{ item.trend }}</span>
      </article>
    </section>

    <section class="dashboard-body">
      <article class="panel-card action-panel">
        <header class="panel-header">
          <h3>业务快捷入口</h3>
          <el-button text @click="fetchOverviewStats">刷新概览 <el-icon><Right /></el-icon></el-button>
        </header>

        <div class="quick-action-grid">
          <button
            v-for="item in quickActions"
            :key="item.title"
            type="button"
            class="quick-action-item"
            @click="handleQuickAction(item.path)"
          >
            <span class="action-icon"><el-icon><component :is="item.icon" /></el-icon></span>
            <span class="action-copy">
              <strong>{{ item.title }}</strong>
              <em>{{ item.description }}</em>
            </span>
          </button>
        </div>
      </article>

      <article class="panel-card timeline-panel">
        <header class="panel-header">
          <h3>近期系统动态</h3>
        </header>

        <el-timeline>
          <el-timeline-item
            v-for="(item, index) in activities"
            :key="index"
            :timestamp="item.time"
            type="success"
            hollow
          >
            {{ item.content }}
          </el-timeline-item>
        </el-timeline>
      </article>
    </section>
  </div>
</template>

<style scoped>
.dashboard-view {
  display: grid;
  gap: 20px;
}

.welcome-card {
  background:
    radial-gradient(circle at 84% 18%, rgba(18, 161, 115, 0.3), transparent 34%),
    radial-gradient(circle at 4% 80%, rgba(255, 255, 255, 0.08), transparent 38%),
    linear-gradient(135deg, #14202a 0%, #1e2d39 52%, #233744 100%);
  color: #f5faf8;
  border-radius: 16px;
  padding: 30px;
  min-height: 220px;
  display: flex;
  justify-content: space-between;
  gap: 20px;
  box-shadow: 0 14px 32px rgba(12, 23, 32, 0.2);
}

.welcome-content {
  max-width: 760px;
}

.greeting-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border-radius: 999px;
  padding: 6px 14px;
  margin-bottom: 16px;
  color: #8af5ce;
  border: 1px solid rgba(138, 245, 206, 0.28);
  background: rgba(138, 245, 206, 0.1);
}

.welcome-content h1 {
  margin: 0 0 10px;
  font-family: 'Space Grotesk', 'Manrope', sans-serif;
  font-size: clamp(1.4rem, 3.2vw, 2rem);
  line-height: 1.24;
}

.welcome-content p {
  margin: 0;
  font-size: 0.98rem;
  color: rgba(243, 251, 248, 0.86);
  line-height: 1.6;
}

.welcome-content p strong {
  color: #8af5ce;
  font-weight: 700;
}

.welcome-meta {
  margin-top: 18px;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.meta-item {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 5px 12px;
  font-size: 0.78rem;
  color: rgba(243, 251, 248, 0.82);
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.06);
}

.welcome-accent {
  min-width: 180px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 14px;
}

.accent-ring {
  width: 112px;
  height: 112px;
  border-radius: 50%;
  border: 10px solid rgba(138, 245, 206, 0.16);
  outline: 1px solid rgba(138, 245, 206, 0.32);
  box-shadow: inset 0 0 24px rgba(138, 245, 206, 0.24);
}

.accent-pill {
  border-radius: 999px;
  padding: 7px 14px;
  color: #dffef2;
  font-weight: 600;
  font-size: 0.8rem;
  letter-spacing: 0.02em;
  background: rgba(18, 161, 115, 0.18);
  border: 1px solid rgba(138, 245, 206, 0.24);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.stat-card {
  background: #ffffff;
  border-radius: 12px;
  padding: 20px;
  border: 1px solid rgba(23, 37, 48, 0.08);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
  transition: all 0.3s ease;
}

.stat-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 12px 24px rgba(15, 27, 36, 0.11);
}

.stat-top {
  display: flex;
  align-items: center;
  gap: 12px;
}

.stat-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  font-size: 1.25rem;
}

.stat-icon.tone-emerald {
  color: #0f8d65;
  background: rgba(18, 161, 115, 0.13);
}

.stat-icon.tone-slate {
  color: #314455;
  background: rgba(49, 68, 85, 0.14);
}

.stat-icon.tone-sage {
  color: #5f7d6a;
  background: rgba(95, 125, 106, 0.14);
}

.stat-icon.tone-amber {
  color: #9d7340;
  background: rgba(157, 115, 64, 0.15);
}

.stat-label {
  color: var(--og-slate-600);
  font-size: 0.88rem;
}

.stat-value {
  display: block;
  margin-top: 14px;
  color: var(--og-slate-900);
  font-family: 'Space Grotesk', 'Manrope', sans-serif;
  font-size: 1.62rem;
  line-height: 1.1;
}

.stat-trend {
  margin-top: 6px;
  display: block;
  color: var(--og-slate-500);
  font-size: 0.79rem;
}

.dashboard-body {
  display: grid;
  grid-template-columns: 1.2fr 0.8fr;
  gap: 16px;
}

.panel-card {
  background: #ffffff;
  border-radius: 12px;
  padding: 22px;
  border: 1px solid rgba(23, 37, 48, 0.08);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.panel-header h3 {
  margin: 0;
  color: var(--og-slate-900);
  font-size: 1.04rem;
}

.quick-action-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.quick-action-item {
  display: flex;
  align-items: center;
  gap: 12px;
  text-align: left;
  width: 100%;
  border: 1px solid rgba(29, 47, 61, 0.08);
  background: #f7faf9;
  border-radius: 12px;
  padding: 14px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.quick-action-item:hover {
  background: #ffffff;
  border-color: rgba(18, 161, 115, 0.38);
  box-shadow: 0 8px 18px rgba(16, 31, 41, 0.09);
  transform: translateY(-2px);
}

.action-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: grid;
  place-items: center;
  color: #0f8d65;
  background: rgba(18, 161, 115, 0.13);
  font-size: 1.1rem;
}

.action-copy {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.action-copy strong {
  font-size: 0.9rem;
  color: var(--og-slate-900);
}

.action-copy em {
  margin: 0;
  font-style: normal;
  color: var(--og-slate-500);
  font-size: 0.78rem;
}

:deep(.timeline-panel .el-timeline-item__timestamp) {
  color: var(--og-slate-500);
  font-size: 0.76rem;
  margin-bottom: 4px;
}

:deep(.timeline-panel .el-timeline-item__content) {
  color: var(--og-slate-700);
  line-height: 1.6;
}

@media (max-width: 1200px) {
  .stats-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .dashboard-body {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 900px) {
  .welcome-card {
    flex-direction: column;
    padding: 24px;
  }

  .welcome-accent {
    align-items: flex-start;
  }
}

@media (max-width: 640px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }

  .quick-action-grid {
    grid-template-columns: 1fr;
  }
}
</style>
