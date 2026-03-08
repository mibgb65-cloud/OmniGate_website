<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Check, CopyDocument, Delete, Download, Refresh } from '@element-plus/icons-vue'

import { deleteGithubAccount, getGithubAccount } from '@/api/github'
import TotpCodeTool from '@/components/security/TotpCodeTool.vue'
import { buildExportFilename, downloadTextFile, formatGithubAccountLine } from '@/utils/accountExport'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const detail = ref(null)
const deleting = ref(false)
const copiedField = ref('')
let copyFeedbackTimer = null

const accountId = computed(() => String(route.params.id || '').trim())

function resolveStatusText(status) {
  if (status === 'active') return '正常'
  if (status === 'locked') return '锁定'
  if (status === 'banned') return '封禁'
  return '-'
}

function toNullableText(value) {
  return value || '-'
}

function markCopied(fieldKey) {
  copiedField.value = fieldKey
  if (copyFeedbackTimer) {
    clearTimeout(copyFeedbackTimer)
  }
  copyFeedbackTimer = setTimeout(() => {
    copiedField.value = ''
    copyFeedbackTimer = null
  }, 900)
}

async function handleCopyValue(value, label, fieldKey) {
  const text = String(value ?? '').trim()
  if (!text) {
    ElMessage.warning(`${label}为空，无法复制`)
    return
  }

  try {
    await navigator.clipboard.writeText(text)
    markCopied(fieldKey)
    ElMessage.success(`${label}已复制`)
  } catch {
    ElMessage.error('复制失败，请手动复制')
  }
}

async function fetchDetail() {
  if (!accountId.value) {
    ElMessage.error('账号 ID 无效')
    router.replace('/github/accounts')
    return
  }

  loading.value = true
  try {
    const detailData = await getGithubAccount(accountId.value)
    detail.value = detailData || {}
  } catch {
    ElMessage.error('获取 GitHub 账号详情失败')
    router.replace('/github/accounts')
  } finally {
    loading.value = false
  }
}

async function handleDelete() {
  if (!detail.value?.id) return

  try {
    await ElMessageBox.confirm(`确认删除 GitHub 账号「${detail.value.username || detail.value.id}」吗？`, '危险操作确认', {
      type: 'warning',
      confirmButtonText: '确认删除',
      cancelButtonText: '取消',
      confirmButtonClass: 'el-button--danger',
    })
  } catch {
    return
  }

  deleting.value = true
  try {
    await deleteGithubAccount(detail.value.id)
    ElMessage.success('账号已删除')
    await router.replace('/github/accounts')
  } finally {
    deleting.value = false
  }
}

function handleExportAccount() {
  if (!detail.value) {
    ElMessage.warning('暂无可导出的 GitHub 账号')
    return
  }

  downloadTextFile({
    filename: buildExportFilename(`github-account-${detail.value?.username || detail.value?.id}`),
    content: formatGithubAccountLine(detail.value),
  })
  ElMessage.success('GitHub 账号已导出')
}

onMounted(fetchDetail)

onBeforeUnmount(() => {
  if (copyFeedbackTimer) {
    clearTimeout(copyFeedbackTimer)
    copyFeedbackTimer = null
  }
})
</script>

<template>
  <div class="detail-page" v-loading="loading">
    <section class="detail-hero">
      <div>
        <h1>GitHub 账号详情</h1>
        <p>{{ detail?.username || '-' }} · {{ detail?.email || '-' }}</p>
      </div>
      <div class="hero-actions">
        <el-button :icon="Download" @click="handleExportAccount">导出账号</el-button>
        <el-button type="danger" plain :icon="Delete" :loading="deleting" @click="handleDelete">删除账号</el-button>
        <el-button :icon="Refresh" @click="fetchDetail">刷新</el-button>
        <el-button type="primary" :icon="ArrowLeft" @click="router.push('/github/accounts')">返回列表</el-button>
      </div>
    </section>

    <section class="summary-grid">
      <article class="summary-card">
        <span>账号状态</span>
        <strong>{{ resolveStatusText(detail?.accountStatus) }}</strong>
      </article>
      <article class="summary-card">
        <span>代理 IP</span>
        <strong>{{ toNullableText(detail?.proxyIp) }}</strong>
      </article>
      <article class="summary-card">
        <span>创建时间</span>
        <strong>{{ toNullableText(detail?.createdAt) }}</strong>
      </article>
      <article class="summary-card">
        <span>更新时间</span>
        <strong>{{ toNullableText(detail?.updatedAt) }}</strong>
      </article>
    </section>

    <section class="card-block">
      <header><h3>基础信息</h3></header>
      <el-descriptions :column="2" class="detail-descriptions">
        <el-descriptions-item label="账号 ID">{{ toNullableText(detail?.id) }}</el-descriptions-item>
        <el-descriptions-item label="用户名">{{ toNullableText(detail?.username) }}</el-descriptions-item>
        <el-descriptions-item :span="2" class-name="credential-focus-content">
          <div class="credential-focus-row">
            <div class="credential-item credential-item--email">
              <span class="credential-key">邮箱</span>
              <span class="credential-value">{{ toNullableText(detail?.email) }}</span>
              <el-button
                text
                class="credential-copy-btn"
                :class="{ 'is-copied': copiedField === 'email' }"
                :icon="copiedField === 'email' ? Check : CopyDocument"
                :disabled="!detail?.email"
                @click="handleCopyValue(detail?.email, '邮箱', 'email')"
              >
                {{ copiedField === 'email' ? '已复制' : '复制' }}
              </el-button>
            </div>
            <div class="credential-item credential-item--password">
              <span class="credential-key">密码</span>
              <span class="credential-value">{{ toNullableText(detail?.password) }}</span>
              <el-button
                text
                class="credential-copy-btn"
                :class="{ 'is-copied': copiedField === 'password' }"
                :icon="copiedField === 'password' ? Check : CopyDocument"
                :disabled="!detail?.password"
                @click="handleCopyValue(detail?.password, '密码', 'password')"
              >
                {{ copiedField === 'password' ? '已复制' : '复制' }}
              </el-button>
            </div>
            <div class="credential-item credential-item--totp">
              <span class="credential-key">2FA</span>
              <span class="credential-value">{{ toNullableText(detail?.totpSecret) }}</span>
              <el-button
                text
                class="credential-copy-btn"
                :class="{ 'is-copied': copiedField === 'totp-secret' }"
                :icon="copiedField === 'totp-secret' ? Check : CopyDocument"
                :disabled="!detail?.totpSecret"
                @click="handleCopyValue(detail?.totpSecret, 'TOTP 密钥', 'totp-secret')"
              >
                {{ copiedField === 'totp-secret' ? '已复制' : '复制' }}
              </el-button>
            </div>
          </div>
        </el-descriptions-item>
        <el-descriptions-item label="账号状态">{{ resolveStatusText(detail?.accountStatus) }}</el-descriptions-item>
        <el-descriptions-item label="代理 IP">{{ toNullableText(detail?.proxyIp) }}</el-descriptions-item>
        <el-descriptions-item label="更新时间">{{ toNullableText(detail?.updatedAt) }}</el-descriptions-item>
      </el-descriptions>
    </section>

    <section class="card-block">
      <TotpCodeTool :secret="detail?.totpSecret" :allow-manual-input="false" />
    </section>
  </div>
</template>

<style scoped>
.detail-page {
  display: grid;
  gap: 16px;
}

.detail-hero {
  border-radius: 12px;
  padding: 20px;
  background:
    radial-gradient(circle at 86% 20%, rgba(99, 102, 241, 0.26), transparent 34%),
    linear-gradient(136deg, #1f2937 0%, #1e293b 56%, #111827 100%);
  color: #f8fafc;
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
}

.detail-hero h1 {
  margin: 0;
  font-size: 1.3rem;
}

.detail-hero p {
  margin: 6px 0 0;
  color: rgba(241, 245, 249, 0.82);
  font-size: 0.92rem;
}

.hero-actions {
  display: flex;
  gap: 8px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.summary-card {
  background: #ffffff;
  border-radius: 12px;
  border: 1px solid rgba(23, 37, 48, 0.08);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
  padding: 14px 16px;
}

.summary-card span {
  color: var(--og-slate-600);
  font-size: 0.8rem;
}

.summary-card strong {
  margin-top: 6px;
  display: block;
  color: var(--og-slate-900);
  font-size: 1.08rem;
}

.card-block {
  border-radius: 12px;
  border: 1px solid rgba(23, 37, 48, 0.08);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
  background: #ffffff;
  padding: 18px;
}

.card-block header {
  margin-bottom: 12px;
}

.card-block header h3 {
  margin: 0;
  color: var(--og-slate-900);
  font-size: 1rem;
}

:deep(.detail-descriptions .el-descriptions__table) {
  border-collapse: separate;
  border-spacing: 0 8px;
}

:deep(.detail-descriptions .el-descriptions__cell) {
  border: none !important;
  padding: 10px 12px;
}

:deep(.detail-descriptions .el-descriptions__label.el-descriptions__cell) {
  width: 110px;
  color: var(--og-slate-600);
  font-weight: 700;
  background: #f1f5f9;
  border-radius: 10px 0 0 10px;
}

:deep(.detail-descriptions .el-descriptions__content.el-descriptions__cell) {
  color: var(--og-slate-900);
  background: #f8fafc;
  border-radius: 0 10px 10px 0;
}

:deep(.detail-descriptions .credential-focus-content.el-descriptions__content.el-descriptions__cell) {
  border-radius: 10px;
  padding: 8px 10px;
}

.credential-focus-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

.credential-item {
  flex: 1 1 220px;
  min-width: 0;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  border-radius: 10px;
  padding: 8px 10px;
  border: 1px solid transparent;
}

.credential-item--email {
  background: rgba(37, 99, 235, 0.08);
  border-color: rgba(37, 99, 235, 0.26);
}

.credential-item--password {
  background: rgba(245, 158, 11, 0.12);
  border-color: rgba(245, 158, 11, 0.3);
}

.credential-item--totp {
  background: rgba(16, 185, 129, 0.1);
  border-color: rgba(16, 185, 129, 0.24);
}

.credential-key {
  font-weight: 800;
  white-space: nowrap;
}

.credential-item--email .credential-key {
  color: #1d4ed8;
}

.credential-item--password .credential-key {
  color: #b45309;
}

.credential-item--totp .credential-key {
  color: #047857;
}

.credential-value {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: 'Space Grotesk', sans-serif;
  color: var(--og-slate-900);
}

.credential-copy-btn {
  flex-shrink: 0;
  height: 28px;
  padding: 0 10px;
  border-radius: 999px;
  color: var(--og-slate-600);
  background: rgba(148, 163, 184, 0.12);
  transition:
    transform 180ms cubic-bezier(0.22, 1, 0.36, 1),
    background-color 180ms ease,
    color 180ms ease,
    box-shadow 180ms ease;
}

.credential-copy-btn:hover {
  color: #0f172a;
  background: rgba(148, 163, 184, 0.22);
}

.credential-copy-btn:active {
  transform: scale(0.92);
}

.credential-copy-btn.is-copied {
  color: #047857;
  background: rgba(16, 185, 129, 0.2);
  box-shadow: 0 6px 14px rgba(16, 185, 129, 0.2);
}

@media (prefers-reduced-motion: reduce) {
  .credential-copy-btn {
    transition: none !important;
  }
}

@media (max-width: 980px) {
  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .detail-hero {
    flex-direction: column;
    align-items: flex-start;
  }
}

@media (max-width: 640px) {
  .summary-grid {
    grid-template-columns: 1fr;
  }

  .credential-focus-row {
    gap: 8px;
  }

  .credential-item {
    gap: 6px;
    padding: 8px;
  }

  .hero-actions {
    width: 100%;
  }
}
</style>
