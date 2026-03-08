<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Check, CopyDocument, Delete, Download, Refresh } from '@element-plus/icons-vue'

import {
  deleteGithubAccount,
  dispatchGithubGenerateTokenTask,
  dispatchGithubStarRepoTask,
  getGithubAccount,
  getGithubLatestTaskRunStatusByRootRunId,
  getGithubTaskRunStatus,
} from '@/api/github'
import TotpCodeTool from '@/components/security/TotpCodeTool.vue'
import { buildExportFilename, downloadTextFile, formatGithubAccountLine } from '@/utils/accountExport'

const route = useRoute()
const router = useRouter()
const TASK_STATUS_POLL_INTERVAL_MS = 2400
const TASK_STATUS_RETRY_INTERVAL_MS = 4200

const loading = ref(false)
const detail = ref(null)
const deleting = ref(false)
const copiedField = ref('')
const actionLoading = reactive({
  generateToken: false,
  starRepo: false,
})
const activeTask = reactive(createTaskState())
let copyFeedbackTimer = null
let taskStatusPollTimer = null

const accountId = computed(() => String(route.params.id || '').trim())
const hasActiveTask = computed(() => Boolean(activeTask.taskRunId || activeTask.rootRunId))
const isTaskPending = computed(() => {
  const status = normalizeTaskStatus(activeTask.status)
  return status === 'queued' || status === 'running'
})

function resolveStatusText(status) {
  if (status === 'active') return '正常'
  if (status === 'locked') return '锁定'
  if (status === 'banned') return '封禁'
  return '-'
}

function normalizeTaskStatus(status) {
  return String(status || '').trim().toLowerCase()
}

function resolveTaskStatusText(status) {
  const normalized = normalizeTaskStatus(status)
  if (normalized === 'queued') return '排队中'
  if (normalized === 'running') return '执行中'
  if (normalized === 'success') return '已成功'
  if (normalized === 'failed') return '已失败'
  if (normalized === 'cancelled') return '已取消'
  if (normalized === 'timeout') return '已超时'
  return '未开始'
}

function resolveTaskTagType(status) {
  const normalized = normalizeTaskStatus(status)
  if (normalized === 'success') return 'success'
  if (normalized === 'failed' || normalized === 'cancelled' || normalized === 'timeout') return 'danger'
  if (normalized === 'running') return 'warning'
  return 'info'
}

function resolveTaskAlertType(status) {
  const normalized = normalizeTaskStatus(status)
  if (normalized === 'success') return 'success'
  if (normalized === 'failed' || normalized === 'cancelled' || normalized === 'timeout') return 'error'
  if (normalized === 'running') return 'warning'
  return 'info'
}

function resolveTaskActionText(action) {
  const normalized = String(action || '').trim()
  if (normalized === 'generate_github_token_by_account_id') return '生成 Token'
  if (normalized === 'star_github_repo_by_account_id') return 'Star 仓库'
  return normalized || '-'
}

function isTerminalTaskStatus(status) {
  const normalized = normalizeTaskStatus(status)
  return ['success', 'failed', 'cancelled', 'timeout'].includes(normalized)
}

function toNullableText(value) {
  return value || '-'
}

function createTaskState() {
  return {
    taskRunId: '',
    rootRunId: '',
    action: '',
    status: '',
    errorMessage: '',
    lastCheckpoint: '',
    attemptNo: '',
    maxAttempts: '',
    repoUrl: '',
    terminalNotified: false,
  }
}

function syncTaskState(taskData = {}) {
  activeTask.taskRunId = String(taskData?.taskRunId || activeTask.taskRunId || '').trim()
  activeTask.rootRunId = String(taskData?.rootRunId || activeTask.rootRunId || '').trim()
  activeTask.action = String(taskData?.action || activeTask.action || '').trim()
  activeTask.status = String(taskData?.status || activeTask.status || '').trim()
  activeTask.errorMessage = String(taskData?.errorMessage || activeTask.errorMessage || '').trim()
  activeTask.lastCheckpoint = String(taskData?.lastCheckpoint || activeTask.lastCheckpoint || '').trim()
  activeTask.attemptNo = taskData?.attemptNo ?? activeTask.attemptNo ?? ''
  activeTask.maxAttempts = taskData?.maxAttempts ?? activeTask.maxAttempts ?? ''
  activeTask.repoUrl = String(taskData?.repoUrl || activeTask.repoUrl || '').trim()
}

function stopTaskStatusPolling() {
  if (taskStatusPollTimer) {
    clearTimeout(taskStatusPollTimer)
    taskStatusPollTimer = null
  }
}

function scheduleTaskStatusPoll(delay = TASK_STATUS_POLL_INTERVAL_MS) {
  stopTaskStatusPolling()
  if (!activeTask.rootRunId && !activeTask.taskRunId) {
    return
  }
  taskStatusPollTimer = setTimeout(() => {
    void pollTaskStatus()
  }, delay)
}

async function handleTerminalTaskStatus() {
  if (activeTask.terminalNotified) {
    return
  }
  activeTask.terminalNotified = true

  const status = normalizeTaskStatus(activeTask.status)
  const taskLabel = resolveTaskActionText(activeTask.action)
  if (status === 'success') {
    ElMessage.success(`${taskLabel}已完成`)
    if (activeTask.action === 'generate_github_token_by_account_id') {
      await fetchDetail()
    }
    return
  }

  ElMessage.error(activeTask.errorMessage || `${taskLabel}执行失败`)
}

async function pollTaskStatus() {
  const rootRunId = String(activeTask.rootRunId || '').trim()
  const taskRunId = String(activeTask.taskRunId || '').trim()
  if (!rootRunId && !taskRunId) {
    return
  }

  try {
    const statusSnapshot = rootRunId
      ? await getGithubLatestTaskRunStatusByRootRunId(rootRunId, { skipErrorMessage: true })
      : await getGithubTaskRunStatus(taskRunId, { skipErrorMessage: true })

    if (!statusSnapshot) {
      scheduleTaskStatusPoll(TASK_STATUS_RETRY_INTERVAL_MS)
      return
    }

    syncTaskState(statusSnapshot)

    if (isTerminalTaskStatus(activeTask.status)) {
      stopTaskStatusPolling()
      await handleTerminalTaskStatus()
      return
    }

    scheduleTaskStatusPoll()
  } catch {
    scheduleTaskStatusPoll(TASK_STATUS_RETRY_INTERVAL_MS)
  }
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

function syncBreadcrumbState(detailData) {
  if (!accountId.value || !detailData) {
    return
  }

  try {
    sessionStorage.setItem(`og-github-account-snapshot-${accountId.value}`, JSON.stringify(detailData))
  } catch {
    // ignore snapshot persistence failure
  }

  const email = String(detailData?.email || '').trim()
  if (!email || String(route.query.email || '').trim() === email) {
    return
  }

  router.replace({
    query: {
      ...route.query,
      email,
    },
  }).catch(() => {})
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
    syncBreadcrumbState(detail.value)
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

function activateTask(dispatchResult, extra = {}) {
  Object.assign(activeTask, createTaskState())
  activeTask.terminalNotified = false
  syncTaskState({
    ...dispatchResult,
    ...extra,
  })
  scheduleTaskStatusPoll(1200)
}

async function handleGenerateToken() {
  if (!detail.value?.id || isTaskPending.value) return

  actionLoading.generateToken = true
  try {
    const dispatchResult = await dispatchGithubGenerateTokenTask(detail.value.id)
    activateTask(dispatchResult)
    ElMessage.success(`生成 Token 任务已入队，taskRunId=${dispatchResult?.taskRunId || '-'}`)
  } finally {
    actionLoading.generateToken = false
  }
}

async function handleStarRepo() {
  if (!detail.value?.id || isTaskPending.value) return

  let repoUrl = ''
  try {
    const { value } = await ElMessageBox.prompt('请输入需要执行 Star 的 GitHub 仓库地址', 'Star 仓库', {
      inputPlaceholder: 'https://github.com/owner/repo',
      inputValue: activeTask.repoUrl || '',
      confirmButtonText: '提交任务',
      cancelButtonText: '取消',
      inputValidator: (value) => String(value || '').trim() ? true : '仓库地址不能为空',
    })
    repoUrl = String(value || '').trim()
  } catch {
    return
  }

  actionLoading.starRepo = true
  try {
    const dispatchResult = await dispatchGithubStarRepoTask(detail.value.id, repoUrl)
    activateTask(dispatchResult, { repoUrl: dispatchResult?.repoUrl || repoUrl })
    ElMessage.success(`Star 仓库任务已入队，taskRunId=${dispatchResult?.taskRunId || '-'}`)
  } finally {
    actionLoading.starRepo = false
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
  stopTaskStatusPolling()
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
            <div class="credential-item credential-item--token">
              <span class="credential-key">Token</span>
              <span class="credential-value">{{ toNullableText(detail?.accessToken) }}</span>
              <el-button
                text
                class="credential-copy-btn"
                :class="{ 'is-copied': copiedField === 'access-token' }"
                :icon="copiedField === 'access-token' ? Check : CopyDocument"
                :disabled="!detail?.accessToken"
                @click="handleCopyValue(detail?.accessToken, 'Access Token', 'access-token')"
              >
                {{ copiedField === 'access-token' ? '已复制' : '复制' }}
              </el-button>
            </div>
          </div>
        </el-descriptions-item>
        <el-descriptions-item label="账号状态">{{ resolveStatusText(detail?.accountStatus) }}</el-descriptions-item>
        <el-descriptions-item label="代理 IP">{{ toNullableText(detail?.proxyIp) }}</el-descriptions-item>
        <el-descriptions-item label="Token Note">{{ toNullableText(detail?.accessTokenNote) }}</el-descriptions-item>
        <el-descriptions-item label="更新时间">{{ toNullableText(detail?.updatedAt) }}</el-descriptions-item>
      </el-descriptions>
    </section>

    <section class="card-block">
      <header class="section-header">
        <div>
          <h3>自动化操作</h3>
          <p>通过后端任务队列触发 GitHub 登录、生成 Token 和仓库 Star 操作。</p>
        </div>
        <div class="automation-actions">
          <el-button type="primary" :loading="actionLoading.generateToken" :disabled="isTaskPending || !detail?.id" @click="handleGenerateToken">
            生成操作 Token
          </el-button>
          <el-button type="success" plain :loading="actionLoading.starRepo" :disabled="isTaskPending || !detail?.id" @click="handleStarRepo">
            Star 仓库
          </el-button>
        </div>
      </header>

      <div v-if="hasActiveTask" class="task-status-card">
        <el-alert :type="resolveTaskAlertType(activeTask.status)" :closable="false" show-icon>
          <template #title>
            最近任务：{{ resolveTaskActionText(activeTask.action) }} · {{ resolveTaskStatusText(activeTask.status) }}
          </template>
          <div class="task-meta-grid">
            <div class="task-meta-item">
              <span>状态</span>
              <el-tag :type="resolveTaskTagType(activeTask.status)" effect="light">
                {{ resolveTaskStatusText(activeTask.status) }}
              </el-tag>
            </div>
            <div class="task-meta-item">
              <span>TaskRunId</span>
              <strong>{{ activeTask.taskRunId || '-' }}</strong>
            </div>
            <div class="task-meta-item">
              <span>RootRunId</span>
              <strong>{{ activeTask.rootRunId || '-' }}</strong>
            </div>
            <div class="task-meta-item">
              <span>重试</span>
              <strong>{{ activeTask.attemptNo || '-' }} / {{ activeTask.maxAttempts || '-' }}</strong>
            </div>
            <div class="task-meta-item" v-if="activeTask.repoUrl">
              <span>仓库</span>
              <strong>{{ activeTask.repoUrl }}</strong>
            </div>
            <div class="task-meta-item" v-if="activeTask.lastCheckpoint">
              <span>检查点</span>
              <strong>{{ activeTask.lastCheckpoint }}</strong>
            </div>
          </div>
          <p v-if="activeTask.errorMessage" class="task-error-text">{{ activeTask.errorMessage }}</p>
        </el-alert>
      </div>
      <el-empty v-else description="暂未发起 GitHub 自动化任务" />
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

.section-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.section-header p {
  margin: 6px 0 0;
  color: var(--og-slate-600);
  font-size: 0.9rem;
}

.automation-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.task-status-card {
  margin-top: 10px;
}

.task-meta-grid {
  margin-top: 12px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.task-meta-item {
  border-radius: 10px;
  background: rgba(248, 250, 252, 0.9);
  border: 1px solid rgba(148, 163, 184, 0.18);
  padding: 10px 12px;
  display: grid;
  gap: 6px;
}

.task-meta-item span {
  font-size: 0.78rem;
  color: var(--og-slate-600);
}

.task-meta-item strong {
  color: var(--og-slate-900);
  word-break: break-all;
}

.task-error-text {
  margin: 12px 0 0;
  color: #991b1b;
  word-break: break-word;
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

.credential-item--token {
  background: rgba(15, 23, 42, 0.06);
  border-color: rgba(15, 23, 42, 0.14);
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

.credential-item--token .credential-key {
  color: #0f172a;
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

  .section-header {
    flex-direction: column;
  }

  .task-meta-grid {
    grid-template-columns: 1fr;
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
