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
const overviewCounts = ref({
  google: 0,
  github: 0,
  chatgpt: 0,
})

const stats = ref([
  {
    label: '总资产',
    value: '0',
    trend: '等待同步',
    icon: UserFilled,
    tone: 'neutral',
  },
  {
    label: 'Google',
    value: '0',
    trend: '等待同步',
    icon: Monitor,
    tone: 'slate',
  },
  {
    label: 'GitHub',
    value: '0',
    trend: '等待同步',
    icon: Collection,
    tone: 'sage',
  },
  {
    label: 'ChatGPT',
    value: '0',
    trend: '等待同步',
    icon: Cpu,
    tone: 'amber',
  },
])

const quickActions = [
  {
    title: '导入 Google 账号',
    description: '导入后继续处理同步和家庭组。',
    icon: Plus,
    path: '/google/accounts',
  },
  {
    title: '维护 GitHub 池',
    description: '进入 token、star 和代理维护。',
    icon: Collection,
    path: '/github/accounts',
  },
  {
    title: '进入 ChatGPT 模块',
    description: '查看注册任务与账号巡检。',
    icon: Cpu,
    path: '/chatgpt/accounts',
  },
  {
    title: '个人中心',
    description: '检查当前身份和安全信息。',
    icon: User,
    path: '/profile',
  },
]

const activities = ref([
  {
    time: '2026-03-03 14:20',
    content: '导入 50 个 Google 账号并完成首轮同步检查。',
  },
  {
    time: '2026-03-03 10:00',
    content: '系统安全巡检完成，核心服务全部正常。',
  },
  {
    time: '2026-03-02 18:45',
    content: '更新 GitHub 令牌配置并刷新历史失效凭据。',
  },
  {
    time: '2026-03-01 11:30',
    content: '新增管理员 mimanchi 并绑定默认权限组。',
  },
])

function formatNumber(value) {
  return Number(value || 0).toLocaleString('zh-CN')
}

const totalAccounts = computed(() => (
  Number(overviewCounts.value.google || 0)
  + Number(overviewCounts.value.github || 0)
  + Number(overviewCounts.value.chatgpt || 0)
))

function buildPlatformSummaryItem({ key, label, total, path, tone, note }) {
  const mergedTotal = totalAccounts.value
  const share = mergedTotal > 0 ? Math.round((total / mergedTotal) * 100) : 0
  return {
    key,
    label,
    total,
    path,
    tone,
    note,
    share,
    shareText: `${share}%`,
    coverageWidth: `${Math.max(total > 0 ? share : 0, total > 0 ? 8 : 0)}%`,
    state: total >= 300 ? '充足' : total >= 120 ? '稳定' : total > 0 ? '偏低' : '空池',
  }
}

const platformSummary = computed(() => [
  buildPlatformSummaryItem({
    key: 'google',
    label: 'Google',
    total: Number(overviewCounts.value.google || 0),
    path: '/google/accounts',
    tone: 'slate',
    note: '同步、家庭组、学生资格',
  }),
  buildPlatformSummaryItem({
    key: 'github',
    label: 'GitHub',
    total: Number(overviewCounts.value.github || 0),
    path: '/github/accounts',
    tone: 'sage',
    note: 'Token、Star、代理维护',
  }),
  buildPlatformSummaryItem({
    key: 'chatgpt',
    label: 'ChatGPT',
    total: Number(overviewCounts.value.chatgpt || 0),
    path: '/chatgpt/accounts',
    tone: 'amber',
    note: '注册任务与账号巡检',
  }),
])

const dominantPlatform = computed(() => (
  [...platformSummary.value].sort((a, b) => b.total - a.total)[0] || null
))

const lightestPlatform = computed(() => (
  [...platformSummary.value].sort((a, b) => a.total - b.total)[0] || null
))

const activePlatforms = computed(() => platformSummary.value.filter((item) => item.total > 0).length)

const commandDeck = computed(() => [
  {
    label: '当前角色',
    value: roleLabel.value,
    hint: '权限视角',
  },
  {
    label: '主池模块',
    value: dominantPlatform.value?.label || '-',
    hint: dominantPlatform.value ? `${dominantPlatform.value.shareText} 占比` : '等待同步',
  },
  {
    label: '待补位模块',
    value: lightestPlatform.value?.label || '-',
    hint: lightestPlatform.value ? `${formatNumber(lightestPlatform.value.total)} 个账号` : '等待同步',
  },
  {
    label: '模块覆盖',
    value: `${activePlatforms.value}/3`,
    hint: '当前已有账号的平台数',
  },
])

const operationSignals = computed(() => [
  {
    title: '数据同步',
    value: loadingStats.value ? '进行中' : '已完成',
    detail: `最近刷新 ${lastSyncTime.value}`,
  },
  {
    title: '重点模块',
    value: dominantPlatform.value?.label || '-',
    detail: dominantPlatform.value ? `${formatNumber(dominantPlatform.value.total)} 个账号` : '等待同步',
  },
  {
    title: '待补位模块',
    value: lightestPlatform.value?.label || '-',
    detail: lightestPlatform.value ? `${formatNumber(lightestPlatform.value.total)} 个账号` : '等待同步',
  },
  {
    title: '模块覆盖',
    value: `${activePlatforms.value}/3`,
    detail: '当前有账号的平台数',
  },
])

const focusQueue = computed(() => {
  const highest = dominantPlatform.value
  const lowest = lightestPlatform.value
  return [
    {
      title: highest ? `维护 ${highest.label} 主池` : '等待主池识别',
      description: highest
        ? `当前体量 ${formatNumber(highest.total)}，占总资产 ${highest.shareText}，适合作为今日主工作区。`
        : '首页尚未同步到可用的模块体量数据。',
    },
    {
      title: lowest ? `补位 ${lowest.label} 账号池` : '等待低位模块识别',
      description: lowest
        ? `当前仅 ${formatNumber(lowest.total)} 个账号，建议优先检查可用性或安排补量。`
        : '同步完成后这里会给出待补位模块。',
    },
    {
      title: '刷新控制台概览',
      description: `最近同步时间 ${lastSyncTime.value}，必要时可再次刷新确认各模块总量变化。`,
    },
  ]
})

function handleQuickAction(path) {
  if (!path) return
  router.push(path)
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

    overviewCounts.value = {
      google: googleTotal,
      github: githubTotal,
      chatgpt: chatgptTotal,
    }

    stats.value = [
      {
        label: '总资产',
        value: formatNumber(mergedTotal),
        trend: '跨模块聚合',
        icon: UserFilled,
        tone: 'neutral',
      },
      {
        label: 'Google',
        value: formatNumber(googleTotal),
        trend: '同步 / 家庭组',
        icon: Monitor,
        tone: 'slate',
      },
      {
        label: 'GitHub',
        value: formatNumber(githubTotal),
        trend: 'Token / Star',
        icon: Collection,
        tone: 'sage',
      },
      {
        label: 'ChatGPT',
        value: formatNumber(chatgptTotal),
        trend: '注册 / 巡检',
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
        content: `已刷新首页概览，Google ${formatNumber(googleTotal)} / GitHub ${formatNumber(githubTotal)} / ChatGPT ${formatNumber(chatgptTotal)}。`,
      },
      ...activities.value.slice(0, 4),
    ]
  } catch {
    ElMessage.warning('概览数据刷新失败，已保留当前页面数据')
  } finally {
    loadingStats.value = false
  }
}

onMounted(fetchOverviewStats)
</script>

<template>
  <div class="dashboard-view">
    <section class="hero-panel">
      <div class="hero-main">
        <div class="hero-kicker">
          <el-icon><Calendar /></el-icon>
          <span>OmniGate Console</span>
        </div>

        <div class="hero-copy">
          <h1>{{ greeting }}，{{ authStore.username || '管理员' }}</h1>
          <p>统一掌握账号资产、模块密度和当日处理顺序。</p>
        </div>

        <div class="hero-meta">
          <span class="hero-meta-item">{{ roleLabel }}</span>
          <span class="hero-meta-item">{{ currentDate }}</span>
          <span class="hero-meta-item">最近同步 {{ lastSyncTime }}</span>
        </div>
      </div>

      <div class="hero-aside">
        <div class="hero-aside-header">
          <div>
            <span class="aside-kicker">Control Desk</span>
            <strong>核心视图</strong>
          </div>

          <el-button class="hero-refresh" @click="fetchOverviewStats" :loading="loadingStats">
            刷新概览
          </el-button>
        </div>

        <div class="command-grid">
          <article v-for="item in commandDeck" :key="item.label" class="command-card">
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
            <em>{{ item.hint }}</em>
          </article>
        </div>
      </div>
    </section>

    <section class="stats-grid" v-loading="loadingStats">
      <article v-for="item in stats" :key="item.label" class="stat-card">
        <div class="stat-top">
          <div class="stat-icon" :class="`tone-${item.tone}`">
            <el-icon><component :is="item.icon" /></el-icon>
          </div>
          <div class="stat-copy">
            <span class="stat-label">{{ item.label }}</span>
            <strong class="stat-value">{{ item.value }}</strong>
          </div>
        </div>
        <span class="stat-trend">{{ item.trend }}</span>
      </article>
    </section>

    <section class="dashboard-grid dashboard-grid--primary" v-loading="loadingStats">
      <article class="surface surface--wide">
        <header class="section-header">
          <div>
            <span class="section-kicker">Asset Matrix</span>
            <h3>模块资产矩阵</h3>
            <p>查看各模块体量、占比和进入入口。</p>
          </div>

          <div class="section-badge-group">
            <span class="section-badge">主池 {{ dominantPlatform?.label || '-' }}</span>
            <span class="section-badge">低位 {{ lightestPlatform?.label || '-' }}</span>
          </div>
        </header>

        <div class="matrix-list">
          <button
            v-for="item in platformSummary"
            :key="item.key"
            type="button"
            class="matrix-card"
            @click="handleQuickAction(item.path)"
          >
            <div class="matrix-head">
              <div class="matrix-copy">
                <strong>{{ item.label }}</strong>
                <span>{{ item.note }}</span>
              </div>

              <div class="matrix-side">
                <strong>{{ formatNumber(item.total) }}</strong>
                <em>{{ item.state }}</em>
              </div>
            </div>

            <div class="matrix-bar">
              <span class="matrix-bar__label">占比 {{ item.shareText }}</span>
              <span class="matrix-track">
                <i class="matrix-fill" :class="`tone-${item.tone}`" :style="{ width: item.coverageWidth }" />
              </span>
            </div>
          </button>
        </div>
      </article>

      <article class="surface">
        <header class="section-header section-header--compact">
          <div>
            <span class="section-kicker">System Pulse</span>
            <h3>运行信号</h3>
            <p>当前同步状态和资产焦点。</p>
          </div>
        </header>

        <div class="signal-list">
          <article v-for="item in operationSignals" :key="item.title" class="signal-card">
            <span>{{ item.title }}</span>
            <strong>{{ item.value }}</strong>
            <em>{{ item.detail }}</em>
          </article>
        </div>

        <div class="focus-block">
          <div class="focus-block__header">
            <span class="section-kicker">Priority Queue</span>
            <strong>今日处理顺序</strong>
          </div>

          <div class="focus-list">
            <article v-for="item in focusQueue" :key="item.title" class="focus-card">
              <strong>{{ item.title }}</strong>
              <p>{{ item.description }}</p>
            </article>
          </div>
        </div>
      </article>
    </section>

    <section class="dashboard-grid dashboard-grid--secondary">
      <article class="surface">
        <header class="section-header section-header--compact">
          <div>
            <span class="section-kicker">Workbench</span>
            <h3>常用入口</h3>
            <p>高频操作直接进入。</p>
          </div>
        </header>

        <div class="action-grid">
          <button
            v-for="item in quickActions"
            :key="item.title"
            type="button"
            class="action-card"
            @click="handleQuickAction(item.path)"
          >
            <span class="action-icon">
              <el-icon><component :is="item.icon" /></el-icon>
            </span>
            <div class="action-copy">
              <strong>{{ item.title }}</strong>
              <em>{{ item.description }}</em>
            </div>
            <el-icon class="action-arrow"><Right /></el-icon>
          </button>
        </div>
      </article>

      <article class="surface">
        <header class="section-header section-header--compact">
          <div>
            <span class="section-kicker">Recent Activity</span>
            <h3>动态记录</h3>
            <p>最近的刷新与维护动作。</p>
          </div>
        </header>

        <div class="activity-list">
          <article v-for="(item, index) in activities" :key="`${item.time}-${index}`" class="activity-item">
            <span class="activity-time">{{ item.time }}</span>
            <p>{{ item.content }}</p>
          </article>
        </div>
      </article>
    </section>
  </div>
</template>

<style scoped>
.dashboard-view {
  --dashboard-border: rgba(15, 23, 42, 0.08);
  --dashboard-surface: rgba(255, 255, 255, 0.96);
  --dashboard-shadow: 0 20px 40px rgba(15, 23, 42, 0.07);
  --dashboard-shadow-hover: 0 24px 48px rgba(15, 23, 42, 0.1);
  --dashboard-accent: #0369a1;
  --dashboard-text: #0f172a;
  --dashboard-muted: #64748b;
  display: grid;
  gap: 20px;
}

.hero-panel {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(320px, 0.9fr);
  gap: 20px;
  padding: 28px;
  overflow: hidden;
  border-radius: 28px;
  color: #e2e8f0;
  background: linear-gradient(135deg, rgba(2, 6, 23, 0.98) 0%, rgba(15, 23, 42, 0.96) 52%, rgba(15, 76, 129, 0.92) 100%);
  box-shadow: 0 28px 60px rgba(2, 6, 23, 0.24);
}

.hero-panel::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    linear-gradient(rgba(148, 163, 184, 0.08) 1px, transparent 1px),
    linear-gradient(90deg, rgba(148, 163, 184, 0.08) 1px, transparent 1px);
  background-size: 56px 56px;
  mask-image: linear-gradient(135deg, rgba(0, 0, 0, 0.72), transparent 88%);
  pointer-events: none;
}

.hero-main,
.hero-aside {
  position: relative;
  z-index: 1;
}

.hero-main {
  display: grid;
  gap: 18px;
  align-content: space-between;
  min-height: 220px;
}

.hero-kicker {
  width: fit-content;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  border: 1px solid rgba(226, 232, 240, 0.16);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.06);
  color: #e2e8f0;
  font-size: 0.78rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.hero-copy {
  display: grid;
  gap: 10px;
  max-width: 640px;
}

.hero-copy h1 {
  margin: 0;
  font-family: 'Manrope', 'Segoe UI', sans-serif;
  font-size: clamp(2rem, 4.2vw, 3rem);
  font-weight: 800;
  line-height: 1.05;
  letter-spacing: -0.04em;
  color: #f8fafc;
}

.hero-copy p {
  margin: 0;
  font-size: 1rem;
  line-height: 1.7;
  color: rgba(226, 232, 240, 0.82);
}

.hero-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.hero-meta-item {
  display: inline-flex;
  align-items: center;
  padding: 8px 14px;
  border-radius: 999px;
  border: 1px solid rgba(226, 232, 240, 0.14);
  background: rgba(255, 255, 255, 0.05);
  font-size: 0.82rem;
  color: #dbe7f3;
}

.hero-aside {
  display: grid;
  gap: 18px;
  padding: 18px;
  border-radius: 22px;
  border: 1px solid rgba(226, 232, 240, 0.12);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.1), rgba(255, 255, 255, 0.04));
  backdrop-filter: blur(10px);
  align-content: start;
}

.hero-aside-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.aside-kicker {
  display: block;
  font-size: 0.72rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: rgba(191, 219, 254, 0.72);
}

.hero-aside-header strong {
  display: block;
  margin-top: 4px;
  color: #f8fafc;
  font-size: 1.02rem;
}

.hero-refresh {
  --el-button-bg-color: rgba(255, 255, 255, 0.1);
  --el-button-border-color: rgba(226, 232, 240, 0.14);
  --el-button-hover-bg-color: rgba(255, 255, 255, 0.16);
  --el-button-hover-border-color: rgba(255, 255, 255, 0.22);
  --el-button-text-color: #f8fafc;
  --el-button-hover-text-color: #ffffff;
  border-radius: 999px;
  padding-inline: 16px;
}

.command-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.command-card {
  display: grid;
  gap: 6px;
  padding: 14px 16px;
  border-radius: 18px;
  border: 1px solid rgba(226, 232, 240, 0.08);
  background: rgba(2, 6, 23, 0.16);
}

.command-card span,
.command-card em {
  font-style: normal;
  color: rgba(226, 232, 240, 0.66);
  font-size: 0.76rem;
}

.command-card strong {
  color: #f8fafc;
  font-size: 1.18rem;
  line-height: 1.2;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.stat-card,
.surface {
  border-radius: 22px;
  border: 1px solid var(--dashboard-border);
  background: var(--dashboard-surface);
  box-shadow: var(--dashboard-shadow);
  backdrop-filter: blur(8px);
}

.stat-card {
  display: grid;
  gap: 16px;
  padding: 20px 22px;
  transition:
    transform 180ms ease,
    box-shadow 180ms ease,
    border-color 180ms ease;
}

.stat-card:hover {
  transform: translateY(-3px);
  box-shadow: var(--dashboard-shadow-hover);
  border-color: rgba(3, 105, 161, 0.18);
}

.stat-top {
  display: flex;
  align-items: center;
  gap: 14px;
}

.stat-copy {
  display: grid;
  gap: 8px;
}

.stat-icon {
  width: 48px;
  height: 48px;
  display: grid;
  place-items: center;
  border-radius: 16px;
  font-size: 1.15rem;
  border: 1px solid transparent;
}

.stat-icon.tone-neutral {
  color: #0f172a;
  background: rgba(15, 23, 42, 0.06);
  border-color: rgba(15, 23, 42, 0.06);
}

.stat-icon.tone-slate {
  color: #0369a1;
  background: rgba(3, 105, 161, 0.1);
  border-color: rgba(3, 105, 161, 0.1);
}

.stat-icon.tone-sage {
  color: #0f766e;
  background: rgba(15, 118, 110, 0.1);
  border-color: rgba(15, 118, 110, 0.1);
}

.stat-icon.tone-amber {
  color: #b45309;
  background: rgba(180, 83, 9, 0.1);
  border-color: rgba(180, 83, 9, 0.1);
}

.stat-label {
  color: var(--dashboard-muted);
  font-size: 0.84rem;
}

.stat-value {
  color: var(--dashboard-text);
  font-family: 'Manrope', 'Segoe UI', sans-serif;
  font-size: 1.9rem;
  line-height: 1;
  letter-spacing: -0.04em;
}

.stat-trend {
  color: #475569;
  font-size: 0.82rem;
}

.dashboard-grid {
  display: grid;
  gap: 16px;
}

.dashboard-grid--primary {
  grid-template-columns: minmax(0, 1.35fr) minmax(320px, 0.85fr);
}

.dashboard-grid--secondary {
  grid-template-columns: minmax(0, 1fr) minmax(360px, 0.92fr);
}

.surface {
  padding: 24px;
}

.section-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.section-header--compact {
  margin-bottom: 16px;
}

.section-kicker {
  display: block;
  margin-bottom: 8px;
  font-size: 0.72rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #64748b;
}

.section-header h3 {
  margin: 0;
  font-size: 1.08rem;
  color: var(--dashboard-text);
}

.section-header p {
  margin: 6px 0 0;
  color: var(--dashboard-muted);
  font-size: 0.85rem;
  line-height: 1.6;
}

.section-badge-group {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.section-badge {
  display: inline-flex;
  align-items: center;
  padding: 8px 12px;
  border-radius: 999px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: #f1f5f9;
  color: #334155;
  font-size: 0.78rem;
}

.matrix-list {
  display: grid;
  gap: 14px;
}

.matrix-card {
  width: 100%;
  display: grid;
  gap: 14px;
  padding: 18px;
  border: none;
  border-radius: 18px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  box-shadow: inset 0 0 0 1px rgba(15, 23, 42, 0.06);
  text-align: left;
  cursor: pointer;
  transition:
    transform 180ms ease,
    box-shadow 180ms ease,
    background 180ms ease;
}

.matrix-card:hover {
  transform: translateY(-2px);
  box-shadow:
    inset 0 0 0 1px rgba(3, 105, 161, 0.2),
    0 16px 32px rgba(15, 23, 42, 0.06);
  background: linear-gradient(180deg, #ffffff 0%, #f3f8fd 100%);
}

.matrix-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.matrix-copy {
  display: grid;
  gap: 4px;
}

.matrix-copy strong {
  color: var(--dashboard-text);
  font-size: 1rem;
}

.matrix-copy span {
  color: var(--dashboard-muted);
  font-size: 0.82rem;
}

.matrix-side {
  display: grid;
  justify-items: end;
  gap: 4px;
}

.matrix-side strong {
  color: var(--dashboard-text);
  font-family: 'Manrope', 'Segoe UI', sans-serif;
  font-size: 1.36rem;
  letter-spacing: -0.03em;
}

.matrix-side em {
  font-style: normal;
  font-size: 0.78rem;
  color: #475569;
}

.matrix-bar {
  display: grid;
  gap: 8px;
}

.matrix-bar__label {
  color: #475569;
  font-size: 0.78rem;
}

.matrix-track {
  position: relative;
  height: 8px;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.18);
}

.matrix-fill {
  display: block;
  height: 100%;
  border-radius: 999px;
}

.matrix-fill.tone-neutral {
  background: linear-gradient(90deg, #0f172a, #475569);
}

.matrix-fill.tone-slate {
  background: linear-gradient(90deg, #0369a1, #38bdf8);
}

.matrix-fill.tone-sage {
  background: linear-gradient(90deg, #0f766e, #2dd4bf);
}

.matrix-fill.tone-amber {
  background: linear-gradient(90deg, #b45309, #f59e0b);
}

.signal-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.signal-card {
  display: grid;
  gap: 6px;
  padding: 16px;
  border-radius: 18px;
  border: 1px solid rgba(15, 23, 42, 0.07);
  background: #f8fbff;
}

.signal-card span {
  color: var(--dashboard-muted);
  font-size: 0.76rem;
}

.signal-card strong {
  color: var(--dashboard-text);
  font-size: 1.08rem;
  letter-spacing: -0.03em;
}

.signal-card em {
  font-style: normal;
  color: #475569;
  font-size: 0.78rem;
  line-height: 1.5;
}

.focus-block {
  display: grid;
  gap: 14px;
  margin-top: 18px;
  padding-top: 18px;
  border-top: 1px solid rgba(148, 163, 184, 0.18);
}

.focus-block__header {
  display: grid;
  gap: 4px;
}

.focus-block__header strong {
  color: var(--dashboard-text);
  font-size: 0.98rem;
}

.focus-list {
  display: grid;
  gap: 10px;
}

.focus-card {
  display: grid;
  gap: 6px;
  padding: 16px;
  border-radius: 18px;
  background: linear-gradient(180deg, #0f172a 0%, #172c42 100%);
  color: #e2e8f0;
}

.focus-card strong {
  color: #f8fafc;
  font-size: 0.92rem;
}

.focus-card p {
  margin: 0;
  color: rgba(226, 232, 240, 0.76);
  font-size: 0.82rem;
  line-height: 1.6;
}

.action-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.action-card {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px;
  border: none;
  border-radius: 18px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  box-shadow: inset 0 0 0 1px rgba(15, 23, 42, 0.06);
  text-align: left;
  cursor: pointer;
  transition:
    transform 180ms ease,
    box-shadow 180ms ease;
}

.action-card:hover {
  transform: translateY(-2px);
  box-shadow:
    inset 0 0 0 1px rgba(3, 105, 161, 0.18),
    0 16px 32px rgba(15, 23, 42, 0.06);
}

.action-icon {
  width: 44px;
  height: 44px;
  display: grid;
  place-items: center;
  flex-shrink: 0;
  border-radius: 14px;
  color: #0369a1;
  background: rgba(3, 105, 161, 0.1);
}

.action-copy {
  display: grid;
  gap: 4px;
  min-width: 0;
  flex: 1;
}

.action-copy strong {
  color: var(--dashboard-text);
  font-size: 0.92rem;
}

.action-copy em {
  margin: 0;
  font-style: normal;
  color: var(--dashboard-muted);
  font-size: 0.78rem;
  line-height: 1.55;
}

.action-arrow {
  color: #94a3b8;
  font-size: 1rem;
  flex-shrink: 0;
}

.activity-list {
  display: grid;
  gap: 12px;
}

.activity-item {
  display: grid;
  gap: 6px;
  padding: 16px 18px;
  border-radius: 18px;
  border: 1px solid rgba(15, 23, 42, 0.07);
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
}

.activity-time {
  color: #0369a1;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.activity-item p {
  margin: 0;
  color: #334155;
  font-size: 0.84rem;
  line-height: 1.65;
}

@media (max-width: 1280px) {
  .dashboard-grid--primary,
  .dashboard-grid--secondary {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 1080px) {
  .hero-panel {
    grid-template-columns: 1fr;
  }

  .stats-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .command-grid,
  .signal-list,
  .action-grid {
    grid-template-columns: 1fr;
  }

  .hero-panel,
  .surface {
    padding: 20px;
  }

  .section-header,
  .hero-aside-header,
  .matrix-head {
    flex-direction: column;
    align-items: flex-start;
  }

  .section-badge-group {
    justify-content: flex-start;
  }
}

@media (max-width: 640px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }

  .hero-meta {
    flex-direction: column;
    align-items: flex-start;
  }

  .hero-copy h1 {
    font-size: clamp(1.7rem, 11vw, 2.4rem);
  }
}

@media (prefers-reduced-motion: reduce) {
  .stat-card,
  .matrix-card,
  .action-card {
    transition: none;
  }

  .stat-card:hover,
  .matrix-card:hover,
  .action-card:hover {
    transform: none;
  }
}
</style>
