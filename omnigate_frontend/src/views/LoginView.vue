<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Lock, User } from '@element-plus/icons-vue'

import { login } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const formRef = ref()
const loading = ref(false)

const formModel = reactive({
  loginAccount: '',
  password: '',
})

const formRules = {
  loginAccount: [{ required: true, message: '请输入账号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function handleSubmit() {
  if (!formRef.value) return
  await formRef.value.validate()

  loading.value = true
  try {
    const tokenResponse = await login(formModel)
    authStore.setTokenPayload(tokenResponse)

    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/google/accounts'
    await router.replace(redirect)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="glow-layer" />
    <section class="login-panel">
      <header class="login-header">
        <span class="pill">OmniGate Admin</span>
        <h1>资产管理控制台</h1>
        <p>请输入系统账号进行安全登录</p>
      </header>

      <el-form ref="formRef" :model="formModel" :rules="formRules" label-position="top" @submit.prevent>
        <el-form-item label="登录账号" prop="loginAccount">
          <el-input v-model="formModel.loginAccount" placeholder="用户名或邮箱" :prefix-icon="User" size="large" />
        </el-form-item>
        <el-form-item label="登录密码" prop="password">
          <el-input
            v-model="formModel.password"
            type="password"
            placeholder="请输入密码"
            :prefix-icon="Lock"
            show-password
            size="large"
            @keyup.enter="handleSubmit"
          />
        </el-form-item>
        <el-button class="submit-button" type="primary" size="large" :loading="loading" @click="handleSubmit">
          安全登录
        </el-button>
      </el-form>
    </section>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 20px;
  position: relative;
  overflow: hidden;
}

.glow-layer {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 22% 30%, rgba(18, 161, 115, 0.28), transparent 32%),
    radial-gradient(circle at 80% 18%, rgba(23, 32, 40, 0.22), transparent 36%),
    linear-gradient(135deg, rgba(17, 28, 37, 0.88), rgba(17, 28, 37, 0.74));
}

.login-panel {
  width: min(440px, 100%);
  position: relative;
  z-index: 1;
  background: rgba(244, 248, 247, 0.9);
  border: 1px solid rgba(255, 255, 255, 0.45);
  border-radius: 24px;
  box-shadow: 0 20px 52px rgba(8, 18, 24, 0.44);
  backdrop-filter: blur(16px);
  padding: 28px 24px 18px;
}

.login-header {
  margin-bottom: 18px;
}

.pill {
  display: inline-flex;
  border-radius: 999px;
  background: rgba(18, 161, 115, 0.12);
  border: 1px solid rgba(18, 161, 115, 0.25);
  color: var(--og-emerald-700);
  font-size: 0.73rem;
  font-weight: 600;
  padding: 4px 10px;
  margin-bottom: 8px;
}

.login-header h1 {
  margin: 0;
  font-family: 'Space Grotesk', sans-serif;
  font-size: 1.48rem;
  color: var(--og-slate-900);
}

.login-header p {
  margin: 7px 0 0;
  color: var(--og-slate-600);
  font-size: 0.9rem;
}

.submit-button {
  width: 100%;
  height: 44px;
  border-radius: 12px;
  margin-top: 8px;
}
</style>
