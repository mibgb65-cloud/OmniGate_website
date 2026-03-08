<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Check, Refresh, Setting } from '@element-plus/icons-vue'

import { getCloudMailSystemSettings, updateCloudMailSystemSettings } from '@/api/systemSettings'

const loading = ref(false)
const saving = ref(false)
const formRef = ref()

const form = reactive({
  accountEmail: '',
  password: '',
  authUrl: '',
  registrationEmailSuffix: '',
})

const formRules = {
  accountEmail: [
    { required: true, message: '请输入 CloudMail 账号邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: ['blur', 'change'] },
    { min: 1, max: 255, message: '邮箱长度不能超过 255 位', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入 CloudMail 登录密码', trigger: 'blur' },
    { min: 1, max: 255, message: '密码长度不能超过 255 位', trigger: 'blur' },
  ],
  authUrl: [
    { required: true, message: '请输入 CloudMail 登录网址', trigger: 'blur' },
    { min: 1, max: 512, message: '登录网址长度不能超过 512 位', trigger: 'blur' },
    { pattern: /^https?:\/\/.+/i, message: '登录网址必须以 http:// 或 https:// 开头', trigger: 'blur' },
  ],
  registrationEmailSuffix: [
    { required: true, message: '请输入 ChatGPT 注册邮箱后缀', trigger: 'blur' },
    { min: 1, max: 255, message: '邮箱后缀长度不能超过 255 位', trigger: 'blur' },
    { pattern: /^@?[^\s@]+\.[^\s@]+$/, message: '邮箱后缀格式不正确，例如 198994216.xyz', trigger: 'blur' },
  ],
}

const statusCards = computed(() => {
  const filledCount = [form.accountEmail, form.password, form.authUrl, form.registrationEmailSuffix]
    .filter((item) => String(item || '').trim())
    .length
  return [
    {
      label: '已填写字段',
      value: filledCount,
      hint: '共 4 项必填',
    },
    {
      label: '账号邮箱',
      value: form.accountEmail ? '已配置' : '未配置',
      hint: '用于 CloudMail 鉴权登录',
    },
    {
      label: '登录密码',
      value: form.password ? '已配置' : '未配置',
      hint: '仅管理员可在此页查看和修改',
    },
    {
      label: '登录网址',
      value: form.authUrl ? '已配置' : '未配置',
      hint: '后续接口会基于它拼接 API 地址',
    },
    {
      label: '注册后缀',
      value: form.registrationEmailSuffix || '未配置',
      hint: '用于生成 ChatGPT 随机注册邮箱域名',
    },
  ]
})

const pageSummary = computed(() => {
  if (loading.value) {
    return '正在从 system_settings 读取当前 CloudMail 配置。'
  }

  const hasAllValues = [form.accountEmail, form.password, form.authUrl, form.registrationEmailSuffix]
    .every((item) => String(item || '').trim())
  return hasAllValues
    ? '当前 CloudMail 和 ChatGPT 注册邮箱配置均已就绪，管理员可以直接更新并保存。'
    : '当前还有必填项未配置，保存后会写入 system_settings 表。'
})

function applySettings(data) {
  form.accountEmail = String(data?.accountEmail || '').trim()
  form.password = String(data?.password || '').trim()
  form.authUrl = String(data?.authUrl || '').trim()
  form.registrationEmailSuffix = String(data?.registrationEmailSuffix || '').trim()
}

async function fetchSettings() {
  loading.value = true
  try {
    const data = await getCloudMailSystemSettings()
    applySettings(data)
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  if (!formRef.value || saving.value) {
    return
  }

  await formRef.value.validate()
  saving.value = true
  try {
    await updateCloudMailSystemSettings({
      accountEmail: String(form.accountEmail || '').trim(),
      password: String(form.password || '').trim(),
      authUrl: String(form.authUrl || '').trim(),
      registrationEmailSuffix: String(form.registrationEmailSuffix || '').trim(),
    })
    ElMessage.success('CloudMail 配置已保存')
    await fetchSettings()
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  fetchSettings()
})
</script>

<template>
  <div class="page-shell">
    <section class="hero-card">
      <div class="hero-copy">
        <span class="hero-kicker">System Settings</span>
        <h1>CloudMail 配置中心</h1>
        <p>
          把 CloudMail 登录邮箱、密码、登录网址，以及 ChatGPT 注册邮箱后缀集中放到一个管理入口里，由管理员直接维护。
          保存后数据会写入 <code>system_settings</code> 表，供后续服务读取。
        </p>
      </div>

      <div class="hero-side">
        <div class="hero-actions">
          <el-button :icon="Refresh" :loading="loading" @click="fetchSettings">刷新配置</el-button>
          <el-button type="primary" :icon="Check" :loading="saving" @click="handleSave">保存配置</el-button>
        </div>

        <div class="stats-grid">
          <article v-for="item in statusCards" :key="item.label" class="stat-item">
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
            <p>{{ item.hint }}</p>
          </article>
        </div>
      </div>
    </section>

    <section class="workspace-grid">
      <el-card class="workspace-card" shadow="never">
        <template #header>
          <div class="section-head">
            <div>
              <span class="section-kicker">CloudMail Credentials</span>
              <h2>管理员配置表单</h2>
              <p>{{ pageSummary }}</p>
            </div>
          </div>
        </template>

        <div v-loading="loading" class="form-wrap">
          <el-form ref="formRef" :model="form" :rules="formRules" label-position="top" class="settings-form" @submit.prevent>
            <el-form-item label="账号邮箱" prop="accountEmail">
              <el-input
                v-model="form.accountEmail"
                placeholder="例如：admin@example.com"
                autocomplete="off"
              />
            </el-form-item>

            <el-form-item label="登录密码" prop="password">
              <el-input
                v-model="form.password"
                type="password"
                show-password
                placeholder="请输入 CloudMail 登录密码"
                autocomplete="new-password"
              />
            </el-form-item>

            <el-form-item class="full-span" label="登录网址" prop="authUrl">
              <el-input
                v-model="form.authUrl"
                placeholder="例如：https://cloudmail.example.com/login"
                autocomplete="off"
              />
            </el-form-item>

            <el-form-item class="full-span" label="ChatGPT 注册邮箱后缀" prop="registrationEmailSuffix">
              <el-input
                v-model="form.registrationEmailSuffix"
                placeholder="例如：198994216.xyz"
                autocomplete="off"
              />
              <div class="field-tip">只填域名部分即可，建议不要带 <code>@</code>。</div>
            </el-form-item>
          </el-form>
        </div>
      </el-card>

      <aside class="tips-panel">
        <article class="tip-card">
          <div class="tip-icon">
            <el-icon><Setting /></el-icon>
          </div>
          <div class="tip-copy">
            <h3>存储说明</h3>
            <p><code>system_settings.value</code> 目前是 <code>VARCHAR(1024)</code>，存邮箱、密码、登录网址和邮箱后缀都够用。</p>
          </div>
        </article>

        <article class="tip-card">
          <div class="tip-copy">
            <h3>配置键</h3>
            <ul>
              <li><code>cloudmail.account_email</code></li>
              <li><code>cloudmail.password</code></li>
              <li><code>cloudmail.auth_url</code></li>
              <li><code>chatgpt.registration_email_suffix</code></li>
            </ul>
          </div>
        </article>

        <article class="tip-card">
          <div class="tip-copy">
            <h3>使用约束</h3>
            <p>后端接口已限制为管理员访问，前端这里只负责录入和更新，不做额外业务推断。</p>
          </div>
        </article>
      </aside>
    </section>
  </div>
</template>

<style scoped>
.page-shell {
  --settings-ink: #13212b;
  --settings-muted: #607280;
  --settings-border: rgba(19, 33, 43, 0.08);
  --settings-border-strong: rgba(16, 140, 108, 0.22);
  --settings-panel: rgba(255, 255, 255, 0.92);
  display: grid;
  gap: 18px;
}

.page-shell,
.page-shell > *,
.hero-card,
.hero-copy,
.hero-side,
.workspace-grid,
.workspace-card,
.form-wrap,
.settings-form,
.tips-panel,
.tip-card {
  min-width: 0;
}

.hero-card {
  display: grid;
  grid-template-columns: 1.15fr 1fr;
  gap: 18px;
  padding: 24px;
  border-radius: 24px;
  border: 1px solid var(--settings-border-strong);
  background:
    radial-gradient(circle at 84% 18%, rgba(16, 140, 108, 0.22), transparent 32%),
    linear-gradient(135deg, #f3fbf8 0%, #eef7f5 44%, #f7fbfc 100%);
  box-shadow: 0 18px 40px rgba(16, 24, 40, 0.06);
}

.hero-copy {
  display: grid;
  align-content: start;
  gap: 10px;
}

.hero-kicker,
.section-kicker {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(19, 33, 43, 0.06);
  color: #325362;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.hero-copy h1,
.section-head h2 {
  margin: 0;
  font-family: 'Space Grotesk', 'PingFang SC', sans-serif;
  color: var(--settings-ink);
}

.hero-copy h1 {
  font-size: 1.5rem;
}

.hero-copy p,
.section-head p,
.tip-copy p {
  margin: 0;
  color: var(--settings-muted);
  line-height: 1.7;
}

.hero-copy code,
.tip-copy code {
  padding: 1px 6px;
  border-radius: 8px;
  background: rgba(19, 33, 43, 0.08);
  color: #214556;
}

.hero-side {
  display: grid;
  gap: 14px;
}

.hero-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  flex-wrap: wrap;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.stat-item {
  display: grid;
  gap: 6px;
  padding: 14px 16px;
  border-radius: 18px;
  border: 1px solid rgba(19, 33, 43, 0.08);
  background: rgba(255, 255, 255, 0.82);
}

.stat-item span {
  color: #587181;
  font-size: 0.82rem;
}

.stat-item strong {
  font-family: 'Space Grotesk', 'PingFang SC', sans-serif;
  color: var(--settings-ink);
  font-size: 1.2rem;
}

.stat-item p {
  margin: 0;
  color: var(--settings-muted);
  font-size: 0.84rem;
  line-height: 1.55;
}

.workspace-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.45fr) minmax(280px, 0.85fr);
  gap: 18px;
}

.workspace-card {
  border-radius: 22px;
  border: 1px solid var(--settings-border);
  background: var(--settings-panel);
  box-shadow: 0 14px 32px rgba(16, 24, 40, 0.06);
}

.section-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.form-wrap {
  padding-top: 4px;
}

.settings-form {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 14px;
}

.settings-form .full-span {
  grid-column: 1 / -1;
}

.settings-form :deep(.el-form-item__label) {
  font-weight: 700;
  color: #3b5361;
}

.field-tip {
  margin-top: 6px;
  color: var(--settings-muted);
  font-size: 0.82rem;
  line-height: 1.5;
}

.field-tip code {
  padding: 1px 6px;
  border-radius: 8px;
  background: rgba(19, 33, 43, 0.08);
  color: #214556;
}

.settings-form :deep(.el-input__wrapper) {
  border-radius: 12px;
}

.tips-panel {
  display: grid;
  align-content: start;
  gap: 14px;
}

.tip-card {
  display: grid;
  gap: 12px;
  padding: 18px;
  border-radius: 20px;
  border: 1px solid rgba(19, 33, 43, 0.08);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(246, 250, 249, 0.98));
  box-shadow: 0 14px 28px rgba(16, 24, 40, 0.05);
}

.tip-icon {
  width: 44px;
  height: 44px;
  border-radius: 14px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, rgba(16, 140, 108, 0.18), rgba(19, 33, 43, 0.08));
  color: #1d5b57;
  font-size: 1.2rem;
}

.tip-copy {
  display: grid;
  gap: 8px;
}

.tip-copy h3 {
  margin: 0;
  color: var(--settings-ink);
  font-size: 1rem;
}

.tip-copy ul {
  margin: 0;
  padding-left: 18px;
  color: var(--settings-muted);
  display: grid;
  gap: 8px;
}

@media (max-width: 1180px) {
  .hero-card,
  .workspace-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .page-shell {
    gap: 14px;
  }

  .hero-card,
  .workspace-card :deep(.el-card__body) {
    padding: 16px;
  }

  .stats-grid,
  .settings-form {
    grid-template-columns: 1fr;
  }

  .hero-actions {
    justify-content: flex-start;
  }

  .hero-actions :deep(.el-button) {
    flex: 1 1 100%;
  }

  .settings-form .full-span {
    grid-column: auto;
  }
}
</style>
