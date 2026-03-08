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

const panelCaption = computed(() => (
  nextDestination.value
    ? `登录后返回${nextDestination.value}`
    : '统一控制台入口'
))

const formCaption = computed(() => (
  nextDestination.value
    ? `继续前往${nextDestination.value}`
    : '输入账号继续'
))

const statusText = computed(() => {
  if (errorMessage.value) return errorMessage.value
  if (loading.value) return '正在验证身份'
  if (nextDestination.value) return `认证成功后将直达${nextDestination.value}`
  return '支持用户名或邮箱登录'
})

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
  <main class="login-page">
    <div class="ambient" aria-hidden="true">
      <span class="ambient-blur blur-left" />
      <span class="ambient-blur blur-right" />
      <span class="ambient-line line-left" />
      <span class="ambient-line line-right" />
    </div>

    <section class="login-scene">
      <section class="brand-stage" aria-label="OmniGate 登录入口">
        <div class="brand-topline">
          <div class="brand-signature">
            <span class="brand-mark">OG</span>
            <div class="brand-copy">
              <strong>OmniGate</strong>
              <span>Private Access</span>
            </div>
          </div>
        </div>

        <div class="stage-copy">
          <span class="eyebrow">Enterprise Login</span>
          <h1>OmniGate</h1>
          <p>{{ panelCaption }}</p>
        </div>

        <div class="platform-ribbon" aria-label="支持平台">
          <span>Google</span>
          <span>GitHub</span>
          <span>ChatGPT</span>
        </div>
      </section>

      <section class="login-column" aria-label="登录表单">
        <div class="form-shell">
          <header class="login-header">
            <p class="login-kicker">Secure sign in</p>
            <h2>登录</h2>
            <p class="login-subtitle">{{ formCaption }}</p>
          </header>

          <div
            class="status-note"
            :class="{ 'is-error': errorMessage, 'is-loading': loading }"
            :role="errorMessage ? 'alert' : 'status'"
            aria-live="polite"
          >
            {{ statusText }}
          </div>

          <el-form
            ref="formRef"
            :model="formModel"
            :rules="formRules"
            class="login-form"
            label-position="top"
            @submit.prevent="handleSubmit"
          >
            <el-form-item label="登录账号" prop="loginAccount" class="field-item">
              <el-input
                v-model.trim="formModel.loginAccount"
                placeholder="用户名或邮箱"
                :prefix-icon="User"
                size="large"
                clearable
                autocomplete="username"
                @keyup.enter="handleSubmit"
              />
            </el-form-item>

            <el-form-item label="登录密码" prop="password" class="field-item">
              <el-input
                v-model="formModel.password"
                type="password"
                placeholder="输入密码"
                :prefix-icon="Lock"
                show-password
                size="large"
                autocomplete="current-password"
                @keyup.enter="handleSubmit"
              />
            </el-form-item>

            <el-button class="submit-button" type="primary" size="large" native-type="submit" :loading="loading">
              {{ loading ? '正在验证' : '进入控制台' }}
            </el-button>
          </el-form>
        </div>
      </section>
    </section>
  </main>
</template>

<style scoped>
.login-page {
  --login-bg: #f8fafc;
  --login-surface: rgba(255, 255, 255, 0.88);
  --login-border: rgba(15, 23, 42, 0.1);
  --login-ink: #020617;
  --login-ink-soft: #0f172a;
  --login-muted: #475569;
  --login-muted-soft: #64748b;
  --login-accent: #0369a1;
  --login-danger: #b42318;

  position: relative;
  min-height: 100vh;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: clamp(16px, 3vw, 36px);
  background:
    radial-gradient(circle at 0% 0%, rgba(14, 116, 144, 0.08), transparent 28%),
    radial-gradient(circle at 100% 0%, rgba(15, 23, 42, 0.08), transparent 30%),
    linear-gradient(140deg, #f8fafc 0%, #eef3f8 52%, #f6f8fb 100%);
}

.ambient {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.ambient-blur,
.ambient-line {
  position: absolute;
}

.ambient-blur {
  border-radius: 999px;
  filter: blur(16px);
}

.blur-left {
  width: 280px;
  height: 280px;
  left: -80px;
  top: -100px;
  background: rgba(3, 105, 161, 0.12);
}

.blur-right {
  width: 340px;
  height: 340px;
  right: -110px;
  bottom: -120px;
  background: rgba(15, 23, 42, 0.1);
}

.ambient-line {
  width: 1px;
  top: 0;
  bottom: 0;
  background: linear-gradient(180deg, transparent, rgba(15, 23, 42, 0.08), transparent);
}

.line-left {
  left: 14%;
}

.line-right {
  right: 12%;
}

.login-scene {
  position: relative;
  z-index: 1;
  width: min(1120px, 100%);
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(360px, 440px);
  gap: clamp(20px, 4vw, 52px);
  align-items: center;
}

.brand-stage {
  position: relative;
  min-height: min(640px, calc(100vh - 88px));
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: clamp(24px, 4vw, 44px);
  border-radius: 40px;
  color: #f8fafc;
  overflow: hidden;
  background:
    radial-gradient(circle at 20% 18%, rgba(56, 189, 248, 0.18), transparent 22%),
    radial-gradient(circle at 86% 18%, rgba(255, 255, 255, 0.1), transparent 18%),
    linear-gradient(145deg, #0f172a 0%, #111827 50%, #0b1220 100%);
  box-shadow:
    0 30px 70px rgba(15, 23, 42, 0.22),
    inset 0 1px 0 rgba(255, 255, 255, 0.06);
}

.brand-stage::after {
  content: 'OG';
  position: absolute;
  right: 28px;
  bottom: 12px;
  font-family: 'Space Grotesk', sans-serif;
  font-size: clamp(7rem, 16vw, 12rem);
  font-weight: 700;
  line-height: 0.9;
  letter-spacing: -0.08em;
  color: rgba(255, 255, 255, 0.05);
  pointer-events: none;
}

.brand-topline {
  display: flex;
  align-items: center;
}

.brand-signature {
  display: flex;
  align-items: center;
  gap: 14px;
}

.brand-mark {
  width: 50px;
  height: 50px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  background: rgba(255, 255, 255, 0.08);
  font-family: 'Space Grotesk', sans-serif;
  font-size: 1rem;
  font-weight: 700;
  letter-spacing: 0.16em;
}

.brand-copy {
  display: grid;
  gap: 2px;
}

.brand-copy strong {
  font-size: 1rem;
  letter-spacing: 0.01em;
}

.brand-copy span {
  font-size: 0.78rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: rgba(248, 250, 252, 0.64);
}

.stage-copy {
  display: grid;
  gap: 14px;
}

.eyebrow {
  width: fit-content;
  display: inline-flex;
  align-items: center;
  padding: 7px 12px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.08);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: rgba(248, 250, 252, 0.84);
}

.stage-copy h1 {
  margin: 0;
  font-family: 'Space Grotesk', sans-serif;
  font-size: clamp(3rem, 5vw, 5rem);
  line-height: 0.92;
  letter-spacing: -0.06em;
}

.stage-copy p {
  margin: 0;
  font-size: 1rem;
  color: rgba(248, 250, 252, 0.72);
}

.platform-ribbon {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.platform-ribbon span {
  display: inline-flex;
  align-items: center;
  padding: 10px 14px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.06);
  color: rgba(248, 250, 252, 0.82);
  font-size: 0.84rem;
}

.login-column {
  width: 100%;
}

.form-shell {
  padding: clamp(22px, 3vw, 30px);
  border-radius: 32px;
  border: 1px solid var(--login-border);
  background: var(--login-surface);
  backdrop-filter: blur(16px);
  box-shadow:
    0 22px 50px rgba(15, 23, 42, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.6);
}

.login-header {
  display: grid;
  gap: 8px;
  margin-bottom: 20px;
}

.login-kicker {
  margin: 0;
  font-size: 0.76rem;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--login-accent);
}

.login-header h2 {
  margin: 0;
  font-family: 'Space Grotesk', sans-serif;
  font-size: clamp(2rem, 2.4vw, 2.5rem);
  letter-spacing: -0.05em;
  color: var(--login-ink);
}

.login-subtitle {
  margin: 0;
  color: var(--login-muted);
  font-size: 0.94rem;
}

.status-note {
  min-height: 20px;
  margin-bottom: 18px;
  color: var(--login-muted);
  font-size: 0.9rem;
  line-height: 1.55;
}

.status-note.is-loading {
  color: var(--login-accent);
}

.status-note.is-error {
  color: var(--login-danger);
}

.field-item {
  margin-bottom: 18px;
}

.login-form :deep(.el-form-item__label) {
  padding-bottom: 8px;
  font-weight: 700;
  color: var(--login-ink-soft);
  letter-spacing: 0.01em;
}

.login-form :deep(.el-input__wrapper) {
  min-height: 56px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.98);
  box-shadow:
    0 0 0 1px rgba(15, 23, 42, 0.12) inset,
    0 10px 24px rgba(15, 23, 42, 0.04);
  transition:
    box-shadow 180ms ease,
    transform 180ms ease,
    background-color 180ms ease;
}

.login-form :deep(.el-input__wrapper:hover) {
  box-shadow:
    0 0 0 1px rgba(15, 23, 42, 0.18) inset,
    0 12px 26px rgba(15, 23, 42, 0.06);
}

.login-form :deep(.el-input__wrapper.is-focus) {
  box-shadow:
    0 0 0 2px rgba(3, 105, 161, 0.22) inset,
    0 0 0 4px rgba(3, 105, 161, 0.12),
    0 14px 28px rgba(3, 105, 161, 0.12);
}

.login-form :deep(.el-input__prefix) {
  margin-right: 10px;
  color: var(--login-muted-soft);
}

.login-form :deep(.el-input__inner) {
  height: 44px;
  color: var(--login-ink);
  font-size: 1rem;
}

.login-form :deep(.el-input__inner::placeholder) {
  color: #7b8794;
}

.login-form :deep(.el-form-item__error) {
  position: static;
  margin-top: 8px;
}

.submit-button {
  width: 100%;
  height: 56px;
  margin-top: 6px;
  border: none;
  border-radius: 999px;
  font-size: 0.96rem;
  font-weight: 700;
  letter-spacing: 0.01em;
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
  box-shadow:
    0 18px 34px rgba(15, 23, 42, 0.16),
    inset 0 1px 0 rgba(255, 255, 255, 0.08);
  transition:
    transform 180ms ease,
    box-shadow 180ms ease,
    opacity 180ms ease;
}

.submit-button:hover {
  transform: translateY(-1px);
  box-shadow:
    0 20px 38px rgba(15, 23, 42, 0.2),
    inset 0 1px 0 rgba(255, 255, 255, 0.08);
}

@media (max-width: 980px) {
  .login-scene {
    grid-template-columns: 1fr;
  }

  .brand-stage {
    min-height: 260px;
  }
}

@media (max-width: 640px) {
  .login-page {
    padding: 14px;
  }

  .brand-stage {
    min-height: 220px;
    padding: 20px;
    border-radius: 28px;
  }

  .form-shell {
    padding: 20px 16px;
    border-radius: 26px;
  }

  .stage-copy h1 {
    font-size: clamp(2.4rem, 12vw, 3.4rem);
  }
}

@media (prefers-reduced-motion: reduce) {
  .login-form :deep(.el-input__wrapper),
  .submit-button {
    transition: none;
  }

  .submit-button:hover {
    transform: none;
  }
}
</style>
