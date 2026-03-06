<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Lock, User } from '@element-plus/icons-vue'

import { login } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const formRef = ref()
const loading = ref(false)
const errorMessage = ref('')

const formModel = reactive({
  loginAccount: '',
  password: '',
})

const formRules = {
  loginAccount: [{ required: true, message: '请输入账号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

const highlights = [
  { value: '3', label: '核心账号域统一管理' },
  { value: '2FA', label: '安全工具辅助支持' },
  { value: '20s', label: '请求超时兜底机制' },
]

const featureList = [
  '统一进入 Google、GitHub、ChatGPT 账号池，减少多入口切换。',
  '访问受保护页面时会自动记住目标地址，登录后直接继续当前任务。',
  'Access Token 失效后会自动尝试刷新，降低重复登录打断。',
]

const redirectPath = computed(() => (typeof route.query.redirect === 'string' ? route.query.redirect : ''))

const nextDestination = computed(() => {
  const path = redirectPath.value
  if (!path) {
    return ''
  }

  if (path.startsWith('/google/accounts')) {
    return 'Google 账号池'
  }

  if (path.startsWith('/github/accounts')) {
    return 'GitHub 账号池'
  }

  if (path.startsWith('/chatgpt/accounts')) {
    return 'ChatGPT 账号池'
  }

  if (path.startsWith('/dashboard')) {
    return '控制台概览'
  }

  if (path.startsWith('/tools/2fa')) {
    return '2FA 工具'
  }

  if (path.startsWith('/profile')) {
    return '个人中心'
  }

  return '刚才访问的页面'
})

const statusNotice = computed(() => {
  if (loading.value) {
    return '正在验证身份并建立安全会话，请稍候。'
  }

  if (nextDestination.value) {
    return `登录后将自动跳转到${nextDestination.value}。`
  }

  return '支持用户名或邮箱登录，密码区分大小写。'
})

const loginTips = computed(() => [
  '登录账号支持用户名或邮箱，两者都会按同一接口校验。',
  '密码区分大小写，输入完成后可直接按回车提交。',
  nextDestination.value
    ? `当前会话会在认证完成后恢复到${nextDestination.value}。`
    : '如果你是从业务页跳转而来，系统会尽量恢复你刚才的目标页面。',
])

watch(
  [() => formModel.loginAccount, () => formModel.password],
  () => {
    if (errorMessage.value) {
      errorMessage.value = ''
    }
  },
)

async function handleSubmit() {
  if (!formRef.value || loading.value) return

  try {
    await formRef.value.validate()
  } catch {
    return
  }

  loading.value = true
  errorMessage.value = ''
  try {
    const tokenResponse = await login(formModel)
    authStore.setTokenPayload(tokenResponse)

    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/google/accounts'
    await router.replace(redirect)
  } catch (error) {
    errorMessage.value = error?.message || '登录失败，请检查账号或密码后重试。'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="ambient ambient-one" />
    <div class="ambient ambient-two" />

    <section class="login-shell">
      <aside class="login-showcase" aria-label="OmniGate 系统介绍">
        <div class="showcase-block">
          <span class="eyebrow">OmniGate Admin</span>
          <h1>统一入口，快速回到你要处理的账号任务。</h1>
          <p>
            登录页改为左右分栏后，左侧负责传达系统价值与状态，右侧只专注完成登录动作，减少进入后台前的认知负担。
          </p>
        </div>

        <div class="showcase-grid">
          <article v-for="item in highlights" :key="item.label" class="metric-card">
            <strong>{{ item.value }}</strong>
            <span>{{ item.label }}</span>
          </article>
        </div>

        <div class="showcase-card">
          <span class="card-label">进入后可以直接做什么</span>
          <ul class="showcase-list">
            <li v-for="item in featureList" :key="item">
              {{ item }}
            </li>
          </ul>
        </div>
      </aside>

      <section class="login-panel">
        <header class="login-header">
          <span class="panel-tag">安全登录</span>
          <h2>欢迎回来</h2>
          <p>输入系统账号后继续访问 OmniGate 控制台。</p>
        </header>

        <div
          class="status-card"
          :class="{ 'is-error': errorMessage }"
          :role="errorMessage ? 'alert' : 'status'"
          aria-live="polite"
        >
          <strong>{{ errorMessage ? '登录未完成' : '登录提示' }}</strong>
          <span>{{ errorMessage || statusNotice }}</span>
        </div>

        <el-form
          ref="formRef"
          :model="formModel"
          :rules="formRules"
          class="login-form"
          label-position="top"
          @submit.prevent
        >
          <el-form-item label="登录账号" prop="loginAccount">
            <el-input
              v-model="formModel.loginAccount"
              placeholder="请输入用户名或邮箱"
              :prefix-icon="User"
              size="large"
              clearable
              autocomplete="username"
              @keyup.enter="handleSubmit"
            />
            <p class="field-hint">支持用户名或邮箱两种格式，建议使用你最常用的一种。</p>
          </el-form-item>

          <el-form-item label="登录密码" prop="password">
            <el-input
              v-model="formModel.password"
              type="password"
              placeholder="请输入密码"
              :prefix-icon="Lock"
              show-password
              size="large"
              autocomplete="current-password"
              @keyup.enter="handleSubmit"
            />
            <p class="field-hint">密码区分大小写，按回车也可以直接提交。</p>
          </el-form-item>

          <el-button class="submit-button" type="primary" size="large" :loading="loading" @click="handleSubmit">
            安全登录
          </el-button>
        </el-form>

        <div class="tips-section">
          <div class="tips-header">
            <span>登录提示</span>
            <span v-if="nextDestination">{{ nextDestination }}</span>
          </div>
          <ul class="tips-list">
            <li v-for="tip in loginTips" :key="tip">
              {{ tip }}
            </li>
          </ul>
        </div>
      </section>
    </section>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: clamp(16px, 4vw, 40px);
  background:
    linear-gradient(115deg, #111b22 0%, #17323d 44%, #eef3f3 44%, #f8fbfa 100%);
}

.ambient {
  position: absolute;
  border-radius: 50%;
  filter: blur(12px);
  pointer-events: none;
}

.ambient-one {
  width: 420px;
  height: 420px;
  top: -150px;
  left: -120px;
  background: rgba(18, 161, 115, 0.24);
}

.ambient-two {
  width: 360px;
  height: 360px;
  right: -120px;
  bottom: -100px;
  background: rgba(24, 46, 64, 0.18);
}

.login-shell {
  position: relative;
  z-index: 1;
  width: min(1180px, 100%);
  min-height: min(760px, calc(100vh - 48px));
  display: grid;
  grid-template-columns: minmax(0, 1.08fr) minmax(360px, 0.92fr);
  border-radius: 30px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.4);
  box-shadow: 0 30px 80px rgba(10, 18, 27, 0.2);
  backdrop-filter: blur(18px);
}

.login-showcase,
.login-panel {
  position: relative;
  padding: clamp(28px, 4vw, 48px);
}

.login-showcase {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 28px;
  color: #f3f8f8;
  background:
    radial-gradient(circle at 18% 20%, rgba(18, 161, 115, 0.18), transparent 28%),
    radial-gradient(circle at 86% 24%, rgba(255, 255, 255, 0.09), transparent 20%),
    linear-gradient(160deg, rgba(15, 24, 31, 0.95), rgba(17, 43, 54, 0.92));
}

.eyebrow,
.panel-tag,
.card-label {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  border-radius: 999px;
  font-size: 0.74rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.eyebrow {
  padding: 7px 12px;
  color: #dff8ee;
  border: 1px solid rgba(223, 248, 238, 0.18);
  background: rgba(255, 255, 255, 0.08);
}

.showcase-block h1 {
  margin: 18px 0 0;
  max-width: 10ch;
  font-family: 'Space Grotesk', sans-serif;
  font-size: clamp(2.3rem, 4vw, 4.2rem);
  line-height: 0.98;
  letter-spacing: -0.04em;
}

.showcase-block p {
  max-width: 39ch;
  margin: 18px 0 0;
  font-size: 1rem;
  line-height: 1.7;
  color: rgba(243, 248, 248, 0.78);
}

.showcase-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.metric-card {
  display: grid;
  gap: 8px;
  padding: 18px 16px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.12);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.08);
}

.metric-card strong {
  font-family: 'Space Grotesk', sans-serif;
  font-size: clamp(1.5rem, 2.2vw, 2rem);
  letter-spacing: -0.04em;
}

.metric-card span {
  color: rgba(243, 248, 248, 0.76);
  line-height: 1.5;
}

.showcase-card {
  padding: 22px 22px 24px;
  border-radius: 26px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.13), rgba(255, 255, 255, 0.07));
  border: 1px solid rgba(255, 255, 255, 0.14);
}

.card-label {
  padding: 6px 10px;
  color: rgba(223, 248, 238, 0.92);
  background: rgba(18, 161, 115, 0.14);
  border: 1px solid rgba(18, 161, 115, 0.2);
}

.showcase-list {
  list-style: none;
  margin: 18px 0 0;
  padding: 0;
  display: grid;
  gap: 14px;
}

.showcase-list li {
  position: relative;
  padding-left: 18px;
  color: rgba(243, 248, 248, 0.84);
  line-height: 1.7;
}

.showcase-list li::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0.72em;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #6de6b8;
  box-shadow: 0 0 0 6px rgba(109, 230, 184, 0.12);
}

.login-panel {
  display: flex;
  flex-direction: column;
  justify-content: center;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.92), rgba(247, 250, 249, 0.96));
}

.login-header {
  margin-bottom: 22px;
}

.panel-tag {
  padding: 7px 12px;
  color: var(--og-emerald-700);
  background: rgba(18, 161, 115, 0.1);
  border: 1px solid rgba(18, 161, 115, 0.18);
}

.login-header h2 {
  margin: 14px 0 0;
  font-family: 'Space Grotesk', sans-serif;
  font-size: clamp(2rem, 2vw, 2.5rem);
  letter-spacing: -0.04em;
  color: var(--og-slate-900);
}

.login-header p {
  margin: 10px 0 0;
  color: var(--og-slate-600);
  font-size: 0.96rem;
  line-height: 1.7;
}

.status-card {
  display: grid;
  gap: 6px;
  padding: 15px 16px;
  margin-bottom: 22px;
  border-radius: 18px;
  background: rgba(18, 161, 115, 0.08);
  border: 1px solid rgba(18, 161, 115, 0.14);
}

.status-card strong {
  color: var(--og-slate-900);
  font-size: 0.92rem;
}

.status-card span {
  color: var(--og-slate-700);
  line-height: 1.6;
}

.status-card.is-error {
  background: rgba(186, 62, 62, 0.08);
  border-color: rgba(186, 62, 62, 0.16);
}

.status-card.is-error strong,
.status-card.is-error span {
  color: #8f3131;
}

.login-form :deep(.el-form-item__label) {
  padding-bottom: 8px;
  font-weight: 700;
  color: var(--og-slate-700);
}

.login-form :deep(.el-form-item) {
  margin-bottom: 20px;
}

.login-form :deep(.el-input__wrapper) {
  min-height: 52px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow:
    0 0 0 1px rgba(27, 40, 54, 0.1) inset,
    0 12px 24px rgba(15, 28, 39, 0.05);
}

.login-form :deep(.el-input__wrapper.is-focus) {
  box-shadow:
    0 0 0 1.5px rgba(18, 161, 115, 0.55) inset,
    0 14px 26px rgba(18, 161, 115, 0.12);
}

.field-hint {
  margin: 8px 2px 0;
  font-size: 0.84rem;
  line-height: 1.5;
  color: var(--og-slate-500);
}

.submit-button {
  width: 100%;
  height: 50px;
  margin-top: 8px;
  border: none;
  border-radius: 16px;
  font-size: 1rem;
  font-weight: 700;
  background: linear-gradient(135deg, var(--og-emerald-500), #1b8d83);
  box-shadow: 0 18px 32px rgba(18, 161, 115, 0.22);
}

.submit-button:hover {
  transform: translateY(-1px);
  box-shadow: 0 20px 36px rgba(18, 161, 115, 0.28);
}

.tips-section {
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid rgba(27, 40, 54, 0.08);
}

.tips-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.tips-header span:first-child {
  font-weight: 700;
  color: var(--og-slate-800);
}

.tips-header span:last-child {
  padding: 5px 10px;
  border-radius: 999px;
  color: var(--og-emerald-700);
  background: rgba(18, 161, 115, 0.08);
  font-size: 0.82rem;
}

.tips-list {
  list-style: none;
  margin: 16px 0 0;
  padding: 0;
  display: grid;
  gap: 12px;
}

.tips-list li {
  position: relative;
  padding-left: 16px;
  color: var(--og-slate-600);
  line-height: 1.65;
}

.tips-list li::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0.72em;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--og-emerald-500);
  box-shadow: 0 0 0 5px rgba(18, 161, 115, 0.09);
}

@media (max-width: 980px) {
  .login-shell {
    min-height: auto;
    grid-template-columns: 1fr;
  }

  .showcase-block h1 {
    max-width: 12ch;
  }
}

@media (max-width: 640px) {
  .login-page {
    padding: 14px;
    background:
      linear-gradient(180deg, #111b22 0%, #17323d 28%, #eef3f3 28%, #f8fbfa 100%);
  }

  .login-shell {
    border-radius: 24px;
  }

  .login-showcase,
  .login-panel {
    padding: 24px 18px;
  }

  .showcase-grid {
    grid-template-columns: 1fr;
  }

  .showcase-block h1 {
    max-width: none;
  }

  .tips-header {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
