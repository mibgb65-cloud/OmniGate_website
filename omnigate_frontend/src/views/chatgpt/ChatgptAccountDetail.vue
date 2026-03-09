<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

import {
  deleteChatgptAccount,
  dispatchChatgptSessionSyncTask,
  getChatgptAccount,
  getChatgptTaskStatus,
  getChatgptTaskStatusByRootRunId,
  updateChatgptAccount,
  updateChatgptAccountStatus,
} from '@/api/chatgpt'
import { buildExportFilename, downloadTextFile, formatChatgptAccountLine } from '@/utils/accountExport'
import ChatgptDetailEditorPanel from '@/views/chatgpt/components/ChatgptDetailEditorPanel.vue'
import ChatgptDetailHero from '@/views/chatgpt/components/ChatgptDetailHero.vue'
import ChatgptDetailSidebar from '@/views/chatgpt/components/ChatgptDetailSidebar.vue'
import ChatgptDetailSummaryGrid from '@/views/chatgpt/components/ChatgptDetailSummaryGrid.vue'

const route = useRoute()
const router = useRouter()
const TASK_STATUS_POLL_INTERVAL_MS = 2400
const TASK_STATUS_RETRY_INTERVAL_MS = 4200

const loading = ref(false)
const saving = ref(false)
const deleting = ref(false)
const statusUpdating = ref(false)
const statusTarget = ref('')
const isEditing = ref(false)
const detail = ref(null)
const editorPanelRef = ref()
const copiedField = ref('')
const actionLoading = reactive({
  syncSession: false,
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
const subTierOptions = [
  { label: 'Free', value: 'free' },
  { label: 'Plus', value: 'plus' },
  { label: 'Team', value: 'team' },
  { label: 'Go', value: 'go' },
]
const statusOptions = [
  { label: '可用', value: 'active' },
  { label: '锁定', value: 'locked' },
  { label: '封禁', value: 'banned' },
]
const statusActionOptions = [
  { value: 'active', label: '可用', description: '适合继续登录与人工维护。', note: '允许继续使用', tone: 'success' },
  { value: 'locked', label: '锁定', description: '暂时阻断操作，等待后续排查。', note: '需要人工处理', tone: 'warning' },
  { value: 'banned', label: '封禁', description: '标记为不可恢复或不可再用。', note: '停用资产', tone: 'danger' },
]
const editForm = reactive({
  email: '',
  password: '',
  sessionToken: '',
  totpSecret: '',
  subTier: 'free',
  accountStatus: 'active',
  expireDate: '',
})

const dateTimeFormatter = new Intl.DateTimeFormat('zh-CN', {
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
})

const formRules = {
  email: [
    { required: true, message: '请输入账号邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: ['blur', 'change'] },
  ],
  password: [{
    trigger: ['blur', 'change'],
    validator: (_rule, value, callback) => {
      const normalized = normalizeCell(value)
      if (normalized && normalized.length > 255) return callback(new Error('密码长度不能超过255'))
      callback()
    },
  }],
  totpSecret: [{
    trigger: ['blur', 'change'],
    validator: (_rule, value, callback) => {
      const normalized = normalizeCell(value)
      if (normalized && normalized.length > 255) return callback(new Error('TOTP 密钥长度不能超过255'))
      callback()
    },
  }],
}

const readinessScore = computed(() => {
  const data = detail.value || {}
  const signals = [
    Boolean(data.email),
    Boolean(data.password),
    Boolean(data.totpSecret),
    Boolean(data.sessionToken),
    data.accountStatus === 'active',
  ]
  const completed = signals.filter(Boolean).length
  return Math.round((completed / signals.length) * 100)
})

const summaryItems = computed(() => {
  const data = detail.value || {}
  return [
    {
      label: '账号状态',
      value: formatAccountStatus(data.accountStatus),
      note: data.accountStatus === 'active' ? '允许继续处理' : '建议人工复核',
      tone: resolveStatusTag(data.accountStatus),
    },
    {
      label: '订阅层级',
      value: formatSubTier(data.subTier),
      note: data.subTier === 'free' ? '基础套餐' : '付费能力已记录',
      tone: resolveTierTag(data.subTier),
    },
    {
      label: '2FA 防护',
      value: data.totpSecret ? '已配置' : '未配置',
      note: data.totpSecret ? '可进行二次验证' : '建议尽快补录密钥',
      tone: data.totpSecret ? 'success' : 'warning',
    },
    {
      label: 'Session 状态',
      value: data.sessionToken ? '已写入' : '缺失',
      note: data.sessionToken ? `${String(data.sessionToken).length} 字符` : '暂无会话材料',
      tone: data.sessionToken ? 'primary' : 'neutral',
    },
  ]
})

const commandDeck = computed(() => {
  const data = detail.value || {}
  return [
    {
      label: '运维评分',
      value: `${readinessScore.value}%`,
      hint: readinessScore.value >= 80 ? '材料完整度较高' : '仍有资料待补齐',
      tone: readinessScore.value >= 80 ? 'success' : readinessScore.value >= 60 ? 'warning' : 'neutral',
    },
    {
      label: '内部编号',
      value: data.id ? `#${data.id}` : '-',
      hint: '数据库主键',
      tone: 'neutral',
    },
    {
      label: '到期日期',
      value: formatDisplayDate(data.expireDate, { includeTime: false }),
      hint: data.expireDate ? '需要关注续期' : '尚未设置生命周期',
      tone: 'warning',
    },
    {
      label: '最近更新',
      value: formatDisplayDate(data.updatedAt),
      hint: '最近一次回写时间',
      tone: 'primary',
    },
  ]
})

const statusActionCards = computed(() => statusActionOptions.map((item) => ({
  ...item,
  active: detail.value?.accountStatus === item.value,
  loading: statusUpdating.value && statusTarget.value === item.value,
})))

const credentialVaultItems = computed(() => {
  const data = detail.value || {}
  return [
    {
      key: 'email',
      label: '邮箱',
      value: toNullableText(data.email),
      rawValue: data.email,
      note: '主登录标识，用于面包屑和详情识别。',
      copyLabel: '复制邮箱',
      tone: data.email ? 'ready' : 'empty',
      multiline: false,
    },
    {
      key: 'password',
      label: '密码',
      value: toNullableText(data.password),
      rawValue: data.password,
      note: data.password ? '已录入登录密码，可用于人工接管。' : '未录入密码，需补录后再操作。',
      copyLabel: '复制密码',
      tone: data.password ? 'ready' : 'empty',
      multiline: false,
    },
    {
      key: 'totp-secret',
      label: '2FA / TOTP',
      value: toNullableText(data.totpSecret),
      rawValue: data.totpSecret,
      note: data.totpSecret ? '二次验证材料完整。' : '缺少 2FA 密钥，安全性较弱。',
      copyLabel: '复制 2FA',
      tone: data.totpSecret ? 'ready' : 'empty',
      multiline: true,
    },
    {
      key: 'session-token',
      label: 'SessionToken',
      value: toNullableText(data.sessionToken),
      rawValue: data.sessionToken,
      note: data.sessionToken
        ? `${String(data.sessionToken).length} 字符，可直接用于会话接管。`
        : '暂无会话令牌，需要重新建立登录状态。',
      copyLabel: '复制令牌',
      tone: data.sessionToken ? 'ready' : 'empty',
      multiline: true,
    },
  ]
})

const lifecycleItems = computed(() => {
  const data = detail.value || {}
  return [
    { label: '账号 ID', value: data.id ? `#${data.id}` : '-' },
    { label: '创建时间', value: formatDisplayDate(data.createdAt) },
    { label: '更新时间', value: formatDisplayDate(data.updatedAt) },
    { label: '到期日期', value: formatDisplayDate(data.expireDate, { includeTime: false }) },
    { label: '订阅层级', value: formatSubTier(data.subTier) },
    { label: '账号状态', value: formatAccountStatus(data.accountStatus) },
  ]
})

const postureItems = computed(() => {
  const data = detail.value || {}
  return [
    {
      label: '登录材料',
      value: data.password ? '完整' : '缺失密码',
      hint: data.password ? '可直接人工登录' : '密码未录入',
    },
    {
      label: '安全材料',
      value: data.totpSecret ? '已启用 2FA' : '未配置 2FA',
      hint: data.totpSecret ? '验证链路完整' : '建议补录密钥',
    },
    {
      label: '会话接管',
      value: data.sessionToken ? '可用' : '不可用',
      hint: data.sessionToken ? '已记录 SessionToken' : '暂无 SessionToken',
    },
  ]
})

function normalizeCell(value) {
  const text = String(value ?? '').trim()
  return text || undefined
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
  if (normalized === 'create_session') return '刷新 Session'
  if (normalized === 'batch_register_chatgpt_accounts') return '自动注册'
  return normalized || '-'
}

function isTerminalTaskStatus(status) {
  const normalized = normalizeTaskStatus(status)
  return ['success', 'failed', 'cancelled', 'timeout'].includes(normalized)
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
    await fetchDetail()
    ElMessage.success(`${taskLabel}已完成`)
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
      ? await getChatgptTaskStatusByRootRunId(rootRunId, { skipErrorMessage: true })
      : await getChatgptTaskStatus(taskRunId, { skipErrorMessage: true })

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

function activateTask(dispatchResult) {
  Object.assign(activeTask, createTaskState())
  activeTask.terminalNotified = false
  syncTaskState(dispatchResult)
  scheduleTaskStatusPoll(1200)
}

function toNullableText(value) {
  return value || '-'
}

function formatAccountStatus(status) {
  return ({ active: '可用', locked: '锁定', banned: '封禁' }[status]) || status || '-'
}

function formatSubTier(subTier) {
  return ({ free: 'Free', plus: 'Plus', team: 'Team', go: 'Go' }[subTier]) || subTier || '-'
}

function resolveStatusTag(status) {
  return status === 'active' ? 'success' : status === 'locked' ? 'warning' : status === 'banned' ? 'danger' : 'info'
}

function resolveTierTag(subTier) {
  return subTier === 'team' ? 'primary' : subTier === 'plus' ? 'success' : subTier === 'go' ? 'warning' : 'info'
}

function formatDisplayDate(value, options = {}) {
  const { includeTime = true } = options
  const normalized = String(value || '').trim()
  if (!normalized) {
    return '-'
  }
  if (!includeTime && /^\d{4}-\d{2}-\d{2}$/.test(normalized)) {
    return normalized
  }

  const parsed = new Date(normalized)
  if (Number.isNaN(parsed.getTime())) {
    return normalized
  }

  return includeTime ? dateTimeFormatter.format(parsed) : normalized.slice(0, 10)
}

function fillEditForm(data) {
  editForm.email = data?.email || ''
  editForm.password = ''
  editForm.sessionToken = data?.sessionToken || ''
  editForm.totpSecret = data?.totpSecret || ''
  editForm.subTier = data?.subTier || 'free'
  editForm.accountStatus = data?.accountStatus || 'active'
  editForm.expireDate = data?.expireDate || ''
}

function buildUpdatePayload() {
  const payload = {}
  const source = detail.value || {}
  const currentEmail = normalizeCell(editForm.email) || ''
  const currentPassword = normalizeCell(editForm.password)
  const currentToken = normalizeCell(editForm.sessionToken) || ''
  const currentTotpSecret = normalizeCell(editForm.totpSecret) || ''
  const currentSubTier = normalizeCell(editForm.subTier) || ''
  const currentStatus = normalizeCell(editForm.accountStatus) || ''
  const currentExpireDate = editForm.expireDate || ''

  if (currentEmail && currentEmail !== (source.email || '')) payload.email = currentEmail
  if (currentPassword) payload.password = currentPassword
  if (currentToken !== (source.sessionToken || '')) payload.sessionToken = currentToken
  if (currentTotpSecret !== (source.totpSecret || '')) payload.totpSecret = currentTotpSecret
  if (currentSubTier && currentSubTier !== (source.subTier || '')) payload.subTier = currentSubTier
  if (currentStatus && currentStatus !== (source.accountStatus || '')) payload.accountStatus = currentStatus
  if (currentExpireDate && currentExpireDate !== (source.expireDate || '')) payload.expireDate = currentExpireDate

  return payload
}

function syncBreadcrumbState(detailData) {
  if (!accountId.value || !detailData) {
    return
  }

  try {
    sessionStorage.setItem(`og-chatgpt-account-snapshot-${accountId.value}`, JSON.stringify(detailData))
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

function markCopied(fieldKey) {
  copiedField.value = fieldKey
  if (copyFeedbackTimer) {
    clearTimeout(copyFeedbackTimer)
  }
  copyFeedbackTimer = setTimeout(() => {
    copiedField.value = ''
    copyFeedbackTimer = null
  }, 1200)
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

function handleVaultCopy(item) {
  handleCopyValue(item?.rawValue, item?.label || '字段', item?.key || 'vault-item')
}

function handleBackToList() {
  router.push('/chatgpt/accounts')
}

async function fetchDetail() {
  if (!accountId.value) {
    ElMessage.error('账号 ID 无效')
    router.replace('/chatgpt/accounts')
    return
  }

  loading.value = true
  try {
    const detailData = await getChatgptAccount(accountId.value)
    detail.value = detailData || {}
    syncBreadcrumbState(detail.value)
    fillEditForm(detail.value)
  } catch {
    ElMessage.error('获取 ChatGPT 账号详情失败')
    router.replace('/chatgpt/accounts')
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  await editorPanelRef.value?.validate()
  const payload = buildUpdatePayload()
  if (!Object.keys(payload).length) {
    ElMessage.info('未检测到变更内容')
    return
  }

  saving.value = true
  try {
    await updateChatgptAccount(accountId.value, payload)
    ElMessage.success('账号信息已更新')
    await fetchDetail()
    isEditing.value = false
  } finally {
    saving.value = false
  }
}

function handleReset() {
  fillEditForm(detail.value || {})
  editorPanelRef.value?.clearValidation()
}

async function handleStartEdit() {
  fillEditForm(detail.value || {})
  isEditing.value = true
  await nextTick()
  editorPanelRef.value?.clearValidation()
}

function handleCancelEdit() {
  fillEditForm(detail.value || {})
  editorPanelRef.value?.clearValidation()
  isEditing.value = false
}

async function handleQuickStatus(nextStatus) {
  if (!detail.value?.id || !nextStatus || nextStatus === detail.value.accountStatus) {
    return
  }

  statusUpdating.value = true
  statusTarget.value = nextStatus
  try {
    await updateChatgptAccountStatus(detail.value.id, { accountStatus: nextStatus })
    detail.value.accountStatus = nextStatus
    editForm.accountStatus = nextStatus
    ElMessage.success(`状态已切换为 ${formatAccountStatus(nextStatus)}`)
  } finally {
    statusUpdating.value = false
    statusTarget.value = ''
  }
}

async function handleSyncSession() {
  if (!detail.value?.id || isTaskPending.value) {
    return
  }

  actionLoading.syncSession = true
  try {
    const dispatchResult = await dispatchChatgptSessionSyncTask(detail.value.id)
    activateTask(dispatchResult)
    ElMessage.success(`Session 更新任务已入队，taskRunId=${dispatchResult?.taskRunId || '-'}`)
  } finally {
    actionLoading.syncSession = false
  }
}

async function handleDelete() {
  if (!detail.value?.id) return

  try {
    await ElMessageBox.confirm(
      `确认删除 ChatGPT 账号「${detail.value.email || detail.value.id}」吗？`,
      '危险操作确认',
      {
        type: 'warning',
        confirmButtonText: '确认删除',
        cancelButtonText: '取消',
        confirmButtonClass: 'el-button--danger',
      },
    )
  } catch {
    return
  }

  deleting.value = true
  try {
    await deleteChatgptAccount(detail.value.id)
    ElMessage.success('账号已删除')
    await router.replace('/chatgpt/accounts')
  } finally {
    deleting.value = false
  }
}

function handleExportAccount() {
  if (!detail.value) {
    ElMessage.warning('暂无可导出的 ChatGPT 账号')
    return
  }

  downloadTextFile({
    filename: buildExportFilename(`chatgpt-account-${detail.value?.email || detail.value?.id}`),
    content: formatChatgptAccountLine(detail.value),
  })
  ElMessage.success('ChatGPT 账号已导出')
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
    <ChatgptDetailHero
      :detail="detail"
      :command-deck="commandDeck"
      :copied-field="copiedField"
      :editing="isEditing"
      :deleting="deleting"
      :format-account-status="formatAccountStatus"
      :resolve-status-tag="resolveStatusTag"
      :resolve-tier-tag="resolveTierTag"
      :format-sub-tier="formatSubTier"
      :format-display-date="formatDisplayDate"
      @back="handleBackToList"
      @refresh="fetchDetail"
      @export="handleExportAccount"
      @copy-email="handleCopyValue(detail?.email, '邮箱', 'hero-email')"
      @start-edit="handleStartEdit"
      @cancel-edit="handleCancelEdit"
      @delete="handleDelete"
    />

    <ChatgptDetailSummaryGrid :items="summaryItems" />

    <section class="workspace-grid">
      <ChatgptDetailEditorPanel
        ref="editorPanelRef"
        :detail="detail"
        :form="editForm"
        :form-rules="formRules"
        :sub-tier-options="subTierOptions"
        :status-options="statusOptions"
        :posture-items="postureItems"
        :editing="isEditing"
        :saving="saving"
        :format-account-status="formatAccountStatus"
        :format-display-date="formatDisplayDate"
        :format-sub-tier="formatSubTier"
        @start-edit="handleStartEdit"
        @cancel-edit="handleCancelEdit"
        @reset="handleReset"
        @save="handleSave"
      />

      <ChatgptDetailSidebar
        :status-action-cards="statusActionCards"
        :status-updating="statusUpdating"
        :credential-vault-items="credentialVaultItems"
        :copied-field="copiedField"
        :lifecycle-items="lifecycleItems"
        :totp-secret="detail?.totpSecret"
        :session-sync-loading="actionLoading.syncSession"
        :session-sync-disabled="!detail?.id || isTaskPending"
        :session-task="hasActiveTask ? activeTask : null"
        :session-task-status-text="resolveTaskStatusText(activeTask.status)"
        :session-task-tag-type="resolveTaskTagType(activeTask.status)"
        :session-task-alert-type="resolveTaskAlertType(activeTask.status)"
        :session-task-action-text="resolveTaskActionText(activeTask.action)"
        @quick-status="handleQuickStatus"
        @copy="handleVaultCopy"
        @sync-session="handleSyncSession"
      />
    </section>
  </div>
</template>

<style scoped>
.detail-page {
  display: grid;
  gap: 20px;
}

.workspace-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.16fr) minmax(330px, 0.84fr);
  gap: 18px;
}

@media (max-width: 1280px) {
  .workspace-grid {
    grid-template-columns: 1fr;
  }
}
</style>
