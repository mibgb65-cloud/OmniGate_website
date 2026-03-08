<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Check, CopyDocument, Delete, Plus, Refresh, RefreshRight } from '@element-plus/icons-vue'

import {
  getGoogleLatestTaskRunStatusByRootRunId,
  getGoogleTaskRunStatus,
  deleteGoogleAccount,
  dispatchGoogleAccountSyncTask,
  dispatchGoogleFamilyInviteTask,
  dispatchGoogleStudentEligibilitySyncTask,
  getGoogleAccountDetail,
  listGoogleFamilyMembers,
  listGoogleInviteLinks,
  updateGoogleAccountBase,
} from '@/api/google'
import TotpCodeTool from '@/components/security/TotpCodeTool.vue'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const loading = ref(false)
const detail = ref(null)
const familyMembers = ref([])
const inviteLinks = ref([])
const deleting = ref(false)
const copiedField = ref('')
const addMemberPanelOpen = ref(false)
const addingMember = ref(false)
const syncingBase = ref(false)
const syncingStudent = ref(false)
const baseEditing = ref(false)
const baseSaving = ref(false)
const newMemberEmail = ref('')
const baseEditFormRef = ref()
let copyFeedbackTimer = null
let logSeed = 0
let taskFlowToken = 0
let taskLogSocket = null
let taskBackgroundMonitorTimer = null
let activeTaskExecution = null
let taskLogFlushTimer = null
let pendingTaskLogs = []

const taskConsoleVisible = ref(false)
const taskRunning = ref(false)
const taskSocketConnected = ref(false)
const taskLabel = ref('')
const taskStatus = ref('idle')
const taskMeta = ref(null)
const taskLogs = ref([])
const taskProgress = reactive({
  current: 0,
  total: 0,
})
const baseEditForm = reactive({
  password: '',
  recoveryEmail: '',
  totpSecret: '',
  region: '',
  remark: '',
})

const TASK_LOG_WS_PATH = '/ws/task-log'
const TASK_DEBUG_QUERY_KEY = 'debug'
const TASK_LOG_RENDER_DELAY_MS = 220
const taskDebugPanelId = 'google-task-debug-panel'
const dateTimeFormatter = new Intl.DateTimeFormat(undefined, {
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
  hour12: false,
})
const dateFormatter = new Intl.DateTimeFormat(undefined, {
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
})

const accountId = computed(() => String(route.params.id || '').trim())
const memberEmailError = computed(() => {
  const email = String(newMemberEmail.value || '').trim()
  if (!email) return ''
  if (isValidEmail(email)) return ''
  return '请输入有效邮箱格式，例如 member@gmail.com'
})
const canSubmitMember = computed(() => {
  const email = String(newMemberEmail.value || '').trim()
  return Boolean(email) && !memberEmailError.value && !addingMember.value
})
const hasTaskLogs = computed(() => taskLogs.value.length > 0)
const taskStatusTagType = computed(() => {
  if (taskStatus.value === 'success') return 'success'
  if (taskStatus.value === 'warning') return 'warning'
  if (taskStatus.value === 'error') return 'danger'
  if (taskStatus.value === 'running' || taskStatus.value === 'queued') return 'primary'
  return 'info'
})
const taskStatusText = computed(() => {
  if (taskStatus.value === 'success') return '执行完成'
  if (taskStatus.value === 'warning') return '后台执行中'
  if (taskStatus.value === 'error') return '执行失败'
  if (taskStatus.value === 'running') return '执行中'
  if (taskStatus.value === 'queued') return '已入队'
  return '待启动'
})
const heroMetaItems = computed(() => {
  const data = detail.value || {}
  return [
    { label: '同步状态', value: resolveSyncText(data.syncStatus) },
    { label: '地区', value: toNullableText(data.region) },
    { label: '订阅', value: toNullableText(data.subTier) },
  ]
})
const taskTimelineLogs = computed(() => {
  const businessLogs = taskLogs.value.filter((item) => item.level !== 'debug')
  const source = businessLogs.length ? businessLogs : taskLogs.value
  return source.slice(-8)
})
const taskDebugLogs = computed(() => taskLogs.value.filter((item) => item.level === 'debug').slice(-24))
const taskDebugCount = computed(() => taskLogs.value.filter((item) => item.level === 'debug').length)
const taskAttemptText = computed(() => resolveAttemptText(taskMeta.value?.attemptNo, taskMeta.value?.maxAttempts))
const taskTransportText = computed(() => {
  if (taskSocketConnected.value) return '实时日志流'
  if (taskRunning.value || hasPendingBackgroundTask()) return '状态轮询'
  return '待连接'
})
const taskActivityState = computed(() => {
  const syncStatus = Number(detail.value?.syncStatus ?? 0)
  const latestLog = taskTimelineLogs.value[taskTimelineLogs.value.length - 1]

  if (taskStatus.value === 'queued') {
    return {
      tone: 'queued',
      eyebrow: '任务队列',
      title: taskLabel.value || '任务已提交',
      description: latestLog?.message || '任务已进入队列，等待 Worker 获取并执行',
    }
  }

  if (taskStatus.value === 'running') {
    return {
      tone: 'running',
      eyebrow: '执行中',
      title: taskLabel.value || '任务执行中',
      description: latestLog?.message || 'Worker 正在处理，完成后当前页面会自动刷新',
    }
  }

  if (taskStatus.value === 'success') {
    return {
      tone: 'success',
      eyebrow: '最新结果',
      title: taskLabel.value ? `${taskLabel.value}已完成` : '任务执行完成',
      description: latestLog?.message || '后端已回写最新数据，当前页面已经刷新',
    }
  }

  if (taskStatus.value === 'warning') {
    return {
      tone: 'warning',
      eyebrow: '后台继续执行',
      title: taskLabel.value || '任务仍在后台执行',
      description: '当前页面会继续监听任务状态，并在完成后自动刷新数据',
    }
  }

  if (taskStatus.value === 'error') {
    return {
      tone: 'error',
      eyebrow: '异常',
      title: taskLabel.value ? `${taskLabel.value}执行失败` : '任务执行失败',
      description: latestLog?.message || String(taskMeta.value?.errorMessage || '').trim() || '可展开调试详情查看错误信息',
    }
  }

  if (syncStatus === 2) {
    return {
      tone: 'running',
      eyebrow: '最近任务',
      title: '账号同步仍在执行中',
      description: '后端正在处理这条账号数据，当前页面会显示最新状态',
    }
  }

  if (syncStatus === 3) {
    return {
      tone: 'success',
      eyebrow: '最近结果',
      title: '账号数据已同步',
      description: detail.value?.updatedAt ? `最近更新时间：${formatDisplayDate(detail.value.updatedAt)}` : '最近一次同步已成功完成',
    }
  }

  if (syncStatus === 4) {
    return {
      tone: 'error',
      eyebrow: '最近结果',
      title: '最近一次同步失败',
      description: '可以重新发起同步，或展开调试详情查看历史记录',
    }
  }

  if (syncStatus === 1) {
    return {
      tone: 'queued',
      eyebrow: '最近任务',
      title: '同步任务正在等待执行',
      description: '任务已排队，等待 Worker 继续处理',
    }
  }

  return {
    tone: 'idle',
    eyebrow: '任务活动',
    title: '暂无进行中的任务',
    description: '点击上方操作按钮后，这里会展示任务状态、关键节点和调试详情',
  }
})
const taskInfoChips = computed(() => {
  const items = [
    { label: '同步状态', value: resolveSyncText(detail.value?.syncStatus) },
    { label: '日志通道', value: taskTransportText.value },
    { label: '执行尝试', value: taskAttemptText.value },
    { label: '页面数据', value: detail.value?.updatedAt ? `更新于 ${formatDisplayDate(detail.value.updatedAt)}` : '尚未回写' },
  ]
  return items
})
const sidebarCoverageItems = computed(() => {
  const data = detail.value || {}
  return [
    {
      label: '基础资料',
      value: toNullableText(data.region) === '-' ? '等待补全' : `地区 ${toNullableText(data.region)}`,
      hint: data.recoveryEmail ? '已记录辅助邮箱' : '未记录辅助邮箱',
    },
    {
      label: '订阅快照',
      value: toNullableText(data.subTier),
      hint: data.expireDate ? `到期 ${formatDisplayDate(data.expireDate, { includeTime: false })}` : '暂无到期信息',
    },
    {
      label: '家庭组',
      value: resolveBinaryText(data.familyStatus, '已开通', '未开通'),
      hint: `已邀请 ${data.invitedCount ?? 0} 人`,
    },
    {
      label: '邀请链接',
      value: resolveBinaryText(data.inviteLinkStatus, '已生成', '暂无链接'),
      hint: inviteLinks.value.length ? `${inviteLinks.value.length} 条记录` : '等待同步生成',
    },
  ]
})
const sidebarActionNotes = computed(() => {
  const data = detail.value || {}
  const notes = [
    {
      title: '同步账号信息',
      description: '刷新基础资料、订阅状态、家庭组与邀请链接快照。',
    },
    {
      title: data.studentLink ? '重新同步学生认证' : '同步学生认证',
      description: data.studentLink ? '已有学生资格链接，需要复查时再重新同步。' : '当前还没有学生资格结果，可补齐认证信息。',
    },
    {
      title: familyMembers.value.length ? '继续处理邀请' : '添加家庭成员',
      description: familyMembers.value.length ? '家庭组已有成员，可继续复制邀请链接向外分发。' : '当前家庭组为空，可以从左侧直接发起成员邀请。',
    },
  ]
  return notes
})

const summaryItems = computed(() => {
  const data = detail.value || {}
  return [
    { label: '同步状态', value: resolveSyncText(data.syncStatus) },
    { label: '家庭组状态', value: resolveBinaryText(data.familyStatus, '已开通', '未开通') },
    { label: '邀请链接状态', value: resolveBinaryText(data.inviteLinkStatus, '已生成', '无链接') },
    { label: '已邀请人数', value: data.invitedCount ?? 0 },
  ]
})

const baseFormRules = {
  password: [
    {
      trigger: ['blur', 'change'],
      validator: (_rule, value, callback) => {
        const normalized = normalizeTextInput(value)
        if (normalized && normalized.length > 255) {
          callback(new Error('密码长度不能超过255'))
          return
        }
        callback()
      },
    },
  ],
  recoveryEmail: [
    {
      trigger: ['blur', 'change'],
      validator: (_rule, value, callback) => {
        const normalized = normalizeTextInput(value)
        if (!normalized) {
          callback()
          return
        }
        const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
        if (!emailPattern.test(normalized)) {
          callback(new Error('辅助邮箱格式不正确'))
          return
        }
        callback()
      },
    },
  ],
  totpSecret: [
    {
      trigger: ['blur', 'change'],
      validator: (_rule, value, callback) => {
        const normalized = normalizeTextInput(value)
        const original = normalizeTextInput(detail.value?.totpSecret)
        if (!normalized && original) {
          callback(new Error('TOTP 密钥不能为空；如需保留请不要清空'))
          return
        }
        if (normalized && normalized.length > 255) {
          callback(new Error('TOTP 密钥长度不能超过255'))
          return
        }
        callback()
      },
    },
  ],
  region: [
    {
      trigger: ['blur', 'change'],
      validator: (_rule, value, callback) => {
        if (String(value ?? '').trim().length > 64) {
          callback(new Error('地区长度不能超过64'))
          return
        }
        callback()
      },
    },
  ],
  remark: [
    {
      trigger: ['blur', 'change'],
      validator: (_rule, value, callback) => {
        if (String(value ?? '').trim().length > 255) {
          callback(new Error('备注长度不能超过255'))
          return
        }
        callback()
      },
    },
  ],
}

function toNullableText(value) {
  return value || '-'
}

function normalizeDateInput(value) {
  if (!value) return null
  if (value instanceof Date) {
    return Number.isNaN(value.getTime()) ? null : value
  }

  const text = String(value).trim()
  if (!text) return null

  const normalized = text.replace(' ', 'T').replace(/([+-]\d{2})$/, '$1:00')
  const parsed = new Date(normalized)
  if (Number.isNaN(parsed.getTime())) {
    return null
  }
  return parsed
}

function formatDisplayDate(value, options = {}) {
  if (!value) return '-'
  const { includeTime = true } = options
  const parsed = normalizeDateInput(value)
  if (!parsed) {
    return String(value)
  }
  return includeTime ? dateTimeFormatter.format(parsed) : dateFormatter.format(parsed)
}

function normalizeTextInput(value) {
  return String(value ?? '').trim()
}

function normalizeNullableUpdateValue(value) {
  return normalizeTextInput(value)
}

function resolveSyncText(status) {
  if (status === 1) return '等待执行'
  if (status === 2) return '执行中'
  if (status === 3) return '同步成功'
  if (status === 4) return '同步失败'
  return '未开始'
}

function resolveBinaryText(status, trueLabel, falseLabel) {
  if (status === 1) return trueLabel
  return falseLabel
}

function resolveFamilyRoleText(role) {
  if (role === 1) return '管理员'
  if (role === 2) return '成员'
  return '-'
}

function resolveLogLevelText(level) {
  if (level === 'success') return '成功'
  if (level === 'warning') return '警告'
  if (level === 'error') return '错误'
  if (level === 'debug') return '调试'
  return '信息'
}

function resolveAttemptText(attemptNo, maxAttempts) {
  const currentAttempt = Number(attemptNo || 0)
  const totalAttempts = Number(maxAttempts || 0)
  if (currentAttempt > 0 && totalAttempts > 0) {
    return `第 ${currentAttempt}/${totalAttempts} 次`
  }
  if (currentAttempt > 0) {
    return `第 ${currentAttempt} 次`
  }
  return '待分配'
}

function wait(ms) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms)
  })
}

function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
}

function resetAddMemberForm() {
  newMemberEmail.value = ''
}

function fillBaseEditForm(data) {
  baseEditForm.password = ''
  baseEditForm.recoveryEmail = data?.recoveryEmail || ''
  baseEditForm.totpSecret = data?.totpSecret || ''
  baseEditForm.region = data?.region || ''
  baseEditForm.remark = data?.remark || ''
}

function buildBaseUpdatePayload() {
  const source = detail.value || {}
  const payload = {}

  const password = normalizeTextInput(baseEditForm.password)
  if (password) {
    payload.password = password
  }

  const recoveryEmail = normalizeNullableUpdateValue(baseEditForm.recoveryEmail)
  if (recoveryEmail !== normalizeTextInput(source.recoveryEmail)) {
    payload.recoveryEmail = recoveryEmail
  }

  const totpSecret = normalizeNullableUpdateValue(baseEditForm.totpSecret)
  if (totpSecret !== normalizeTextInput(source.totpSecret)) {
    payload.totpSecret = totpSecret
  }

  const region = normalizeNullableUpdateValue(baseEditForm.region)
  if (region !== normalizeTextInput(source.region)) {
    payload.region = region
  }

  const remark = normalizeNullableUpdateValue(baseEditForm.remark)
  if (remark !== normalizeTextInput(source.remark)) {
    payload.remark = remark
  }

  return payload
}

function openAddMemberPanel() {
  addMemberPanelOpen.value = true
}

function closeAddMemberPanel() {
  addMemberPanelOpen.value = false
  resetAddMemberForm()
}

function startBaseEditing() {
  fillBaseEditForm(detail.value || {})
  baseEditing.value = true
  baseEditFormRef.value?.clearValidate()
}

function cancelBaseEditing() {
  fillBaseEditForm(detail.value || {})
  baseEditing.value = false
  baseEditFormRef.value?.clearValidate()
}

async function saveBaseEditing() {
  if (!detail.value?.id) return
  await baseEditFormRef.value?.validate()

  const payload = buildBaseUpdatePayload()
  if (!Object.keys(payload).length) {
    ElMessage.info('未检测到基础信息变更')
    baseEditing.value = false
    return
  }

  baseSaving.value = true
  try {
    await updateGoogleAccountBase(detail.value.id, payload)
    await fetchDetail({ silent: true, silentError: false })
    baseEditing.value = false
    baseEditFormRef.value?.clearValidate()
    ElMessage.success('基础信息已更新')
  } finally {
    baseSaving.value = false
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

function getSnapshotById(id) {
  if (!id) return null
  try {
    const raw = sessionStorage.getItem(`og-google-account-snapshot-${id}`)
    if (!raw) return null
    return JSON.parse(raw)
  } catch {
    return null
  }
}

async function fetchDetail(options = {}) {
  const { silent = false, silentError = false } = options

  if (!accountId.value) {
    if (!silentError) {
      ElMessage.error('账号 ID 无效')
    }
    router.replace('/google/accounts')
    return false
  }

  if (!silent) {
    const snapshot = getSnapshotById(accountId.value)
    if (snapshot) {
      detail.value = {
        ...(detail.value || {}),
        ...snapshot,
      }
    }
    loading.value = true
  }

  try {
    const [detailData, familyData, inviteData] = await Promise.all([
      getGoogleAccountDetail(accountId.value),
      listGoogleFamilyMembers(accountId.value).catch(() => []),
      listGoogleInviteLinks(accountId.value).catch(() => []),
    ])

    detail.value = detailData || {}
    if (!baseEditing.value) {
      fillBaseEditForm(detail.value)
    }
    familyMembers.value = Array.isArray(familyData) ? familyData : []
    inviteLinks.value = Array.isArray(inviteData) ? inviteData : []
    return true
  } catch {
    if (!silent) {
      familyMembers.value = []
      inviteLinks.value = []
      if (detail.value && Object.keys(detail.value).length > 0) {
        if (!silentError) {
          ElMessage.warning('详情接口异常，已展示列表页快照数据')
        }
        return false
      }
      detail.value = {}
    }
    if (!silentError) {
      ElMessage.warning('暂无可展示的详情数据')
    }
    return false
  } finally {
    if (!silent) {
      loading.value = false
    }
  }
}

async function handleDelete() {
  if (!detail.value?.id) return

  try {
    await ElMessageBox.confirm(`确认删除 Google 账号「${detail.value.email || detail.value.id}」吗？`, '危险操作确认', {
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
    await deleteGoogleAccount(detail.value.id)
    ElMessage.success('账号已删除')
    await router.replace('/google/accounts')
  } finally {
    deleting.value = false
  }
}

function formatLogTime(date = new Date()) {
  const hour = String(date.getHours()).padStart(2, '0')
  const minute = String(date.getMinutes()).padStart(2, '0')
  const second = String(date.getSeconds()).padStart(2, '0')
  return `${hour}:${minute}:${second}`
}

function resolveTaskLogWsUrl() {
  const customUrl = String(import.meta.env.VITE_TASK_LOG_WS_URL || '').trim()
  if (customUrl) {
    return customUrl
  }

  const apiBaseUrl = String(import.meta.env.VITE_API_BASE_URL || '').trim()
  if (apiBaseUrl) {
    if (/^wss?:\/\//i.test(apiBaseUrl)) {
      return `${apiBaseUrl.replace(/\/+$/, '').replace(/\/api$/i, '')}${TASK_LOG_WS_PATH}`
    }
    if (/^https?:\/\//i.test(apiBaseUrl)) {
      return `${apiBaseUrl.replace(/^http/i, 'ws').replace(/\/+$/, '').replace(/\/api$/i, '')}${TASK_LOG_WS_PATH}`
    }
  }

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}${TASK_LOG_WS_PATH}`
}

function toInt(value) {
  if (value === null || value === undefined || value === '') return undefined
  const parsed = Number(value)
  if (!Number.isFinite(parsed)) return undefined
  return Math.trunc(parsed)
}

function mapIncomingLogLevel(rawLevel) {
  const normalized = String(rawLevel || 'INFO').trim().toUpperCase()
  if (normalized === 'ERROR' || normalized === 'FATAL') return 'error'
  if (normalized === 'WARN' || normalized === 'WARNING') return 'warning'
  if (normalized === 'DEBUG' || normalized === 'TRACE') return 'debug'
  if (normalized === 'SUCCESS' || normalized === 'OK') return 'success'
  return 'info'
}

function normalizeIncomingStatus(rawStatus) {
  const normalized = String(rawStatus || '').trim().toLowerCase()
  if (!normalized) return ''
  if (normalized === 'queued' || normalized === 'running' || normalized === 'success') return normalized
  if (normalized === 'failed' || normalized === 'timeout' || normalized === 'cancelled') return normalized
  return ''
}

function unpackIncomingPayload(raw) {
  if (raw === null || raw === undefined || raw === '') return []
  if (Array.isArray(raw)) {
    return raw.flatMap((item) => unpackIncomingPayload(item))
  }

  if (typeof raw === 'string') {
    const trimmed = raw.trim()
    if (!trimmed) return []
    try {
      return unpackIncomingPayload(JSON.parse(trimmed))
    } catch {
      return [{ message: trimmed, level: 'INFO' }]
    }
  }

  if (typeof raw !== 'object') {
    return []
  }

  const payload = raw
  if (Array.isArray(payload.logs)) {
    return payload.logs.flatMap((item) => unpackIncomingPayload(item))
  }
  if (payload.payload && typeof payload.payload === 'object') {
    return unpackIncomingPayload(payload.payload)
  }
  if (payload.data) {
    const nested = unpackIncomingPayload(payload.data)
    if (nested.length) return nested
  }

  return [payload]
}

function isPayloadForCurrentTask(payload, { taskRunId, rootRunId }) {
  const taskIdCandidates = [
    payload.task_id,
    payload.taskId,
    payload.task_run_id,
    payload.taskRunId,
    payload.run_id,
    payload.runId,
  ]
    .map((item) => String(item || '').trim())
    .filter(Boolean)

  const rootIdCandidates = [payload.root_run_id, payload.rootRunId]
    .map((item) => String(item || '').trim())
    .filter(Boolean)

  if (rootRunId) {
    if (rootIdCandidates.length) {
      return rootIdCandidates.includes(rootRunId)
    }
    if (taskRunId && taskIdCandidates.length) {
      return taskIdCandidates.includes(taskRunId)
    }
    return true
  }

  if (taskRunId && taskIdCandidates.length && !taskIdCandidates.includes(taskRunId)) {
    return false
  }

  return true
}

function closeTaskLogSocket(reason = '') {
  if (!taskLogSocket) return
  const current = taskLogSocket
  taskLogSocket = null
  taskSocketConnected.value = false
  try {
    current.close(1000, reason || 'close')
  } catch {
    // ignore close error
  }
}

function buildTaskLogWsUrl(taskRunId, rootRunId) {
  const baseUrl = resolveTaskLogWsUrl()
  const url = new URL(baseUrl, window.location.origin)
  url.searchParams.set('task_id', taskRunId)
  url.searchParams.set('task_run_id', taskRunId)
  if (rootRunId) {
    url.searchParams.set('root_run_id', rootRunId)
  }
  if (authStore.accessToken) {
    url.searchParams.set('access_token', authStore.accessToken)
  }
  return url.toString()
}

async function handleIncomingTaskLogMessage(rawMessage, taskIdentity) {
  const payloads = unpackIncomingPayload(rawMessage)
  if (!payloads.length) return

  for (const payload of payloads) {
    if (!isPayloadForCurrentTask(payload, taskIdentity)) {
      continue
    }

    const nextStatus = normalizeIncomingStatus(payload.status || payload.task_status || payload.run_status)
    if (nextStatus) {
      taskMeta.value = {
        ...(taskMeta.value || {}),
        taskRunId: payload.taskRunId || payload.task_run_id || payload.task_id || taskMeta.value?.taskRunId,
        rootRunId: payload.rootRunId || payload.root_run_id || taskMeta.value?.rootRunId,
        status: nextStatus,
        errorMessage: payload.errorMessage || payload.error_message || taskMeta.value?.errorMessage,
      }
      syncActiveTaskExecutionIdentity(
        String(taskMeta.value?.taskRunId || '').trim(),
        String(taskMeta.value?.rootRunId || '').trim(),
      )
    }
    if (nextStatus === 'queued') {
      taskStatus.value = 'queued'
      taskRunning.value = true
    } else if (nextStatus === 'running') {
      taskStatus.value = 'running'
      taskRunning.value = true
    } else if (nextStatus === 'success') {
      taskStatus.value = 'success'
      taskRunning.value = false
      taskProgress.current = Math.max(taskProgress.current, taskProgress.total || taskProgress.current)
      closeTaskLogSocket('success')
    } else if (nextStatus === 'failed' || nextStatus === 'timeout' || nextStatus === 'cancelled') {
      taskStatus.value = 'error'
      taskRunning.value = false
      closeTaskLogSocket(nextStatus)
    }

    const message = String(payload.message || payload.msg || payload.content || '').trim()
    if (message) {
      appendTaskLog({
        level: mapIncomingLogLevel(payload.level),
        message,
        step: toInt(payload.step),
        stepTotal: toInt(payload.step_total ?? payload.stepTotal),
      })
    }

    if (nextStatus && isTerminalTaskStatus(nextStatus)) {
      await finalizeActiveTask(taskMeta.value || payload, {
        notify: !activeTaskExecution?.foregroundMonitoring,
      })
    }
  }
}

function openTaskLogSocket(taskRunId, rootRunId) {
  closeTaskLogSocket('replace')

  const wsUrl = buildTaskLogWsUrl(taskRunId, rootRunId)
  const socket = new WebSocket(wsUrl)
  taskLogSocket = socket
  taskSocketConnected.value = false

  socket.onopen = () => {
    if (taskLogSocket !== socket) return
    taskSocketConnected.value = true
    appendTaskLog({
      level: 'success',
      message: '已连接实时日志流',
      step: Math.max(taskProgress.current, 6),
      stepTotal: Math.max(taskProgress.total, 10),
    })

    const subscribePayloads = [
      { type: 'subscribe', task_id: taskRunId, task_run_id: taskRunId, root_run_id: rootRunId || undefined },
      { action: 'subscribe', taskId: taskRunId, taskRunId, rootRunId: rootRunId || undefined },
    ]
    subscribePayloads.forEach((item) => {
      try {
        socket.send(JSON.stringify(item))
      } catch {
        // ignore unsupported protocol
      }
    })
  }

  socket.onmessage = (event) => {
    if (taskLogSocket !== socket) return
    void handleIncomingTaskLogMessage(event.data, { taskRunId, rootRunId })
  }

  socket.onerror = () => {
    if (taskLogSocket !== socket) return
    taskSocketConnected.value = false
    appendTaskLog({
      level: 'warning',
      message: '实时日志连接出现异常，切换为状态轮询',
    })
  }

  socket.onclose = () => {
    if (taskLogSocket !== socket) return
    taskLogSocket = null
    taskSocketConnected.value = false
    if (taskStatus.value === 'running' || taskStatus.value === 'queued') {
      appendTaskLog({
        level: 'warning',
        message: '实时日志连接已断开，正在继续轮询任务状态',
      })
    }
  }
}

function toggleTaskConsole() {
  setTaskConsoleVisible(!taskConsoleVisible.value)
}

function setTaskConsoleVisible(nextVisible, options = {}) {
  const { syncQuery = true } = options
  taskConsoleVisible.value = nextVisible

  if (!syncQuery) return

  const queryVisible = String(route.query[TASK_DEBUG_QUERY_KEY] || '') === '1'
  if (queryVisible === nextVisible) return

  const nextQuery = { ...route.query }
  if (nextVisible) {
    nextQuery[TASK_DEBUG_QUERY_KEY] = '1'
  } else {
    delete nextQuery[TASK_DEBUG_QUERY_KEY]
  }

  router.replace({ query: nextQuery }).catch(() => {})
}

function resetTaskConsole() {
  stopTaskBackgroundMonitor()
  activeTaskExecution = null
  closeTaskLogSocket('reset')
  clearPendingTaskLogs()
  taskLogs.value = []
  taskMeta.value = null
  taskLabel.value = ''
  taskStatus.value = 'idle'
  taskSocketConnected.value = false
  taskProgress.current = 0
  taskProgress.total = 0
}

function clearTaskConsoleIfIdle() {
  if (taskRunning.value) return
  if (hasPendingBackgroundTask()) {
    ElMessage.info('后台任务仍在执行，完成后会自动刷新当前页面')
    return
  }
  resetTaskConsole()
}

function stopTaskBackgroundMonitor() {
  if (taskBackgroundMonitorTimer && typeof window !== 'undefined') {
    window.clearTimeout(taskBackgroundMonitorTimer)
  }
  taskBackgroundMonitorTimer = null
}

function stopTaskLogFlushTimer() {
  if (taskLogFlushTimer && typeof window !== 'undefined') {
    window.clearTimeout(taskLogFlushTimer)
  }
  taskLogFlushTimer = null
}

function clearPendingTaskLogs() {
  stopTaskLogFlushTimer()
  pendingTaskLogs = []
}

function flushPendingTaskLogs() {
  stopTaskLogFlushTimer()
  if (!pendingTaskLogs.length) return

  const queuedEntries = pendingTaskLogs
  pendingTaskLogs = []
  taskLogs.value = [...taskLogs.value, ...queuedEntries].slice(-300)

  queuedEntries.forEach((entry) => {
    if (entry.stepTotal) {
      taskProgress.total = Math.max(taskProgress.total, entry.stepTotal)
    }
    if (entry.step) {
      taskProgress.current = Math.max(taskProgress.current, entry.step)
    }
  })
}

function scheduleTaskLogFlush() {
  if (typeof window === 'undefined') {
    flushPendingTaskLogs()
    return
  }
  if (taskLogFlushTimer) return
  taskLogFlushTimer = window.setTimeout(() => {
    flushPendingTaskLogs()
  }, TASK_LOG_RENDER_DELAY_MS)
}

function hasPendingBackgroundTask() {
  return Boolean(activeTaskExecution && !activeTaskExecution.foregroundMonitoring && !activeTaskExecution.finalizedStatus)
}

function syncActiveTaskExecutionIdentity(taskRunId, rootRunId) {
  if (!activeTaskExecution || activeTaskExecution.token !== taskFlowToken) return
  if (taskRunId) {
    activeTaskExecution.taskRunId = taskRunId
  }
  if (rootRunId) {
    activeTaskExecution.rootRunId = rootRunId
  }
}

function buildResolvedTaskSnapshot(statusSnapshot) {
  const execution = activeTaskExecution || {}
  const nextStatus = normalizeIncomingStatus(statusSnapshot?.status || statusSnapshot?.task_status || statusSnapshot?.run_status || taskMeta.value?.status)
  return {
    ...(taskMeta.value || {}),
    ...(statusSnapshot || {}),
    taskRunId:
      statusSnapshot?.taskRunId ||
      statusSnapshot?.task_run_id ||
      statusSnapshot?.task_id ||
      execution.taskRunId ||
      taskMeta.value?.taskRunId,
    rootRunId:
      statusSnapshot?.rootRunId ||
      statusSnapshot?.root_run_id ||
      execution.rootRunId ||
      taskMeta.value?.rootRunId,
    status: nextStatus || normalizeIncomingStatus(taskMeta.value?.status),
  }
}

async function runTaskLifecycleCallback(callback, statusSnapshot) {
  if (typeof callback !== 'function') return
  try {
    await callback(statusSnapshot)
  } catch {
    // ignore post-task refresh failure
  }
}

async function finalizeActiveTask(statusSnapshot, { notify = false } = {}) {
  const resolvedSnapshot = buildResolvedTaskSnapshot(statusSnapshot)
  const nextStatus = normalizeIncomingStatus(resolvedSnapshot?.status)
  if (!nextStatus || !isTerminalTaskStatus(nextStatus)) {
    return null
  }

  const execution = activeTaskExecution
  if (execution && execution.token === taskFlowToken) {
    if (execution.finalizedStatus === nextStatus) {
      return nextStatus === 'success' ? 'completed' : 'failed'
    }
    execution.finalizedStatus = nextStatus
    execution.foregroundMonitoring = false
    syncActiveTaskExecutionIdentity(
      String(resolvedSnapshot?.taskRunId || '').trim(),
      String(resolvedSnapshot?.rootRunId || '').trim(),
    )
  }

  stopTaskBackgroundMonitor()

  if (nextStatus === 'success') {
    await runTaskLifecycleCallback(execution?.afterSuccess, resolvedSnapshot)
    if (notify) {
      ElMessage.success(`${execution?.taskName || '任务'}已完成，页面已刷新`)
    }
    return 'completed'
  }

  await runTaskLifecycleCallback(execution?.afterFailure, resolvedSnapshot)
  if (notify) {
    ElMessage.warning(`${execution?.taskName || '任务'}执行结束，请检查最新状态`)
  }
  return 'failed'
}

function startTaskBackgroundMonitor(monitorIntervalMs = 2000) {
  stopTaskBackgroundMonitor()
  if (typeof window === 'undefined' || !activeTaskExecution) return

  const executionToken = activeTaskExecution.token
  const tick = async () => {
    const execution = activeTaskExecution
    if (!execution || execution.token !== executionToken) {
      stopTaskBackgroundMonitor()
      return
    }

    const statusSnapshot = await fetchTaskStatusSnapshot(execution.taskRunId, execution.rootRunId)
    if (statusSnapshot) {
      applyTaskStatusSnapshot(execution.taskName, statusSnapshot)
      const nextStatus = normalizeIncomingStatus(statusSnapshot?.status)
      if (nextStatus && isTerminalTaskStatus(nextStatus)) {
        await finalizeActiveTask(statusSnapshot, { notify: true })
        return
      }
    }

    taskBackgroundMonitorTimer = window.setTimeout(tick, monitorIntervalMs)
  }

  taskBackgroundMonitorTimer = window.setTimeout(tick, monitorIntervalMs)
}

function appendTaskLog({
  level = 'info',
  message = '',
  step,
  stepTotal,
}) {
  const normalizedStep = Number.isFinite(step) ? Number(step) : undefined
  const normalizedTotal = Number.isFinite(stepTotal) ? Number(stepTotal) : undefined

  const entry = {
    id: `${Date.now()}-${++logSeed}`,
    level,
    message: String(message || '').trim() || '-',
    time: formatLogTime(),
    step: normalizedStep,
    stepTotal: normalizedTotal,
  }

  pendingTaskLogs.push(entry)
  scheduleTaskLogFlush()
}

async function emitTaskDispatchPlan(taskName, stepTotal) {
  appendTaskLog({ level: 'info', message: `开始准备任务：${taskName}`, step: 1, stepTotal })
  await wait(260)
  appendTaskLog({ level: 'debug', message: '校验账号与参数', step: 2, stepTotal })
  await wait(240)
  appendTaskLog({ level: 'debug', message: '生成任务负载并连接调度器', step: 3, stepTotal })
  await wait(260)
  appendTaskLog({ level: 'info', message: '提交任务到队列', step: 4, stepTotal })
}

function isTerminalTaskStatus(status) {
  return status === 'success' || status === 'failed' || status === 'timeout' || status === 'cancelled'
}

function resolveTaskStatusLogLevel(status) {
  if (status === 'success') return 'success'
  if (status === 'failed' || status === 'timeout' || status === 'cancelled') return 'error'
  if (status === 'running') return 'info'
  return 'warning'
}

function resolveTaskStatusProgressStep(status) {
  if (status === 'success' || status === 'failed' || status === 'timeout' || status === 'cancelled') return 10
  if (status === 'running') return 8
  return 6
}

function buildTaskStatusMessage(taskName, statusSnapshot) {
  const status = normalizeIncomingStatus(statusSnapshot?.status)
  const attemptNo = Number(statusSnapshot?.attemptNo || 0)
  const maxAttempts = Number(statusSnapshot?.maxAttempts || 0)
  const attemptText = attemptNo && maxAttempts ? `（第 ${attemptNo}/${maxAttempts} 次）` : ''
  if (status === 'queued') return `${taskName} 已进入等待队列${attemptText}`
  if (status === 'running') return `${taskName} 开始执行${attemptText}`
  if (status === 'success') return `${taskName} 执行完成${attemptText}`
  if (status === 'timeout') return `${taskName} 执行超时${attemptText}`
  if (status === 'cancelled') return `${taskName} 已取消${attemptText}`
  if (status === 'failed') {
    const errorText = String(statusSnapshot?.errorMessage || '').trim()
    return errorText ? `${taskName} 执行失败：${errorText}` : `${taskName} 执行失败${attemptText}`
  }
  return ''
}

function applyTaskStatusSnapshot(taskName, statusSnapshot) {
  const nextStatus = normalizeIncomingStatus(statusSnapshot?.status)
  if (!nextStatus) return

  const prevTaskRunId = String(taskMeta.value?.taskRunId || '')
  const prevAttemptNo = Number(taskMeta.value?.attemptNo || 0)
  const prevStatus = normalizeIncomingStatus(taskMeta.value?.status)
  const nextTaskRunId = String(statusSnapshot?.taskRunId || statusSnapshot?.task_run_id || '')
  const nextAttemptNo = Number(statusSnapshot?.attemptNo || 0)

  taskMeta.value = {
    ...(taskMeta.value || {}),
    ...statusSnapshot,
    status: nextStatus,
  }
  syncActiveTaskExecutionIdentity(
    String(taskMeta.value?.taskRunId || '').trim(),
    String(taskMeta.value?.rootRunId || '').trim(),
  )

  if (nextStatus === 'queued') {
    taskStatus.value = 'queued'
    taskRunning.value = true
  } else if (nextStatus === 'running') {
    taskStatus.value = 'running'
    taskRunning.value = true
  } else if (nextStatus === 'success') {
    taskStatus.value = 'success'
    taskRunning.value = false
  } else {
    taskStatus.value = 'error'
    taskRunning.value = false
  }

  const progressStep = resolveTaskStatusProgressStep(nextStatus)
  taskProgress.current = Math.max(taskProgress.current, progressStep)
  taskProgress.total = Math.max(taskProgress.total, 10)

  if (prevStatus === nextStatus && prevTaskRunId === nextTaskRunId && prevAttemptNo === nextAttemptNo) {
    return
  }

  const message = buildTaskStatusMessage(taskName, statusSnapshot)
  if (!message) return
  appendTaskLog({
    level: resolveTaskStatusLogLevel(nextStatus),
    message,
    step: progressStep,
    stepTotal: 10,
  })
}

async function fetchTaskStatusSnapshot(taskRunId, rootRunId) {
  try {
    if (rootRunId) {
      return await getGoogleLatestTaskRunStatusByRootRunId(rootRunId)
    }
    if (taskRunId) {
      return await getGoogleTaskRunStatus(taskRunId)
    }
  } catch {
    return null
  }
  return null
}

async function runTaskWithConsole({
  taskName,
  dispatch,
  afterSuccess,
  afterFailure,
  monitorRounds = 20,
  monitorIntervalMs = 1500,
}) {
  if (taskRunning.value) {
    ElMessage.warning('当前已有任务正在执行，请稍后再试')
    return 'failed'
  }

  const currentToken = Date.now()
  taskFlowToken = currentToken
  stopTaskBackgroundMonitor()
  closeTaskLogSocket('new-task')
  activeTaskExecution = {
    token: currentToken,
    taskName,
    afterSuccess,
    afterFailure,
    taskRunId: '',
    rootRunId: '',
    foregroundMonitoring: true,
    finalizedStatus: '',
  }
  taskRunning.value = true
  taskSocketConnected.value = false
  taskLabel.value = taskName
  taskStatus.value = 'queued'
  taskMeta.value = null
  taskProgress.current = 0
  taskProgress.total = 10
  setTaskConsoleVisible(false)

  try {
    await emitTaskDispatchPlan(taskName, 10)
    if (taskFlowToken !== currentToken) return 'failed'

    const dispatchResult = await dispatch()
    if (taskFlowToken !== currentToken) return 'failed'

    taskMeta.value = dispatchResult || null
    applyTaskStatusSnapshot(taskName, {
      ...(dispatchResult || {}),
      status: dispatchResult?.status || 'queued',
    })
    appendTaskLog({
      level: 'success',
      message: `任务已入队，taskRunId=${dispatchResult?.taskRunId || '-'}`,
      step: 5,
      stepTotal: 10,
    })
    appendTaskLog({
      level: 'info',
      message: '等待 Worker 执行并回写数据',
      step: 6,
      stepTotal: 10,
    })

    const taskRunId = String(dispatchResult?.taskRunId || '').trim()
    const rootRunId = String(dispatchResult?.rootRunId || '').trim()
    syncActiveTaskExecutionIdentity(taskRunId, rootRunId)
    if (taskRunId) {
      openTaskLogSocket(taskRunId, rootRunId)
    } else {
      appendTaskLog({
        level: 'warning',
        message: '任务返回缺少 taskRunId，无法接入实时日志流',
      })
    }

    for (let round = 1; round <= monitorRounds; round += 1) {
      await wait(monitorIntervalMs)
      if (taskFlowToken !== currentToken) return 'failed'

      const statusSnapshot = await fetchTaskStatusSnapshot(taskRunId, rootRunId)
      if (statusSnapshot) {
        applyTaskStatusSnapshot(taskName, statusSnapshot)
      }

      const currentStatus = normalizeIncomingStatus(statusSnapshot?.status || taskMeta.value?.status)
      if (currentStatus === 'success' || taskStatus.value === 'success') {
        await finalizeActiveTask(statusSnapshot || taskMeta.value)
        closeTaskLogSocket('completed')
        return 'completed'
      }
      if (currentStatus && isTerminalTaskStatus(currentStatus) && currentStatus !== 'success') {
        await finalizeActiveTask(statusSnapshot || taskMeta.value)
        closeTaskLogSocket(currentStatus)
        return 'failed'
      }

      if (!taskSocketConnected.value && round % 2 === 0) {
        appendTaskLog({
          level: 'debug',
          message: `等待实时日志连接，当前轮询 ${round}/${monitorRounds}`,
          step: Math.min(9, 6 + round),
          stepTotal: 10,
        })
      }
    }

    taskStatus.value = 'warning'
    taskRunning.value = false
    if (activeTaskExecution && activeTaskExecution.token === currentToken) {
      activeTaskExecution.foregroundMonitoring = false
    }
    startTaskBackgroundMonitor(Math.max(2000, monitorIntervalMs))
    appendTaskLog({
      level: 'warning',
      message: '任务仍在后台执行，完成后会自动刷新当前页面',
      step: 10,
      stepTotal: 10,
    })
    return 'pending'
  } catch (error) {
    taskStatus.value = 'error'
    taskRunning.value = false
    closeTaskLogSocket('failed')
    appendTaskLog({
      level: 'error',
      message: error?.message || `${taskName} 启动失败`,
      step: 10,
      stepTotal: 10,
    })
    return 'failed'
  } finally {
    if (taskFlowToken === currentToken) {
      if (taskStatus.value !== 'running' && taskStatus.value !== 'queued') {
        taskRunning.value = false
      }
    }
  }
}

async function handleSyncAccountTask() {
  if (!detail.value?.id) return
  syncingBase.value = true
  const result = await runTaskWithConsole({
    taskName: 'Google 账号信息同步',
    dispatch: () => dispatchGoogleAccountSyncTask(detail.value.id),
    afterSuccess: () => fetchDetail({ silent: true, silentError: true }),
    afterFailure: () => fetchDetail({ silent: true, silentError: true }),
  })
  syncingBase.value = false

  if (result === 'completed') {
    ElMessage.success('账号信息同步完成')
  } else if (result === 'pending') {
    ElMessage.info('同步任务已提交，正在后台执行')
  }
}

async function handleSyncStudentTask() {
  if (!detail.value?.id) return
  syncingStudent.value = true
  const result = await runTaskWithConsole({
    taskName: '学生认证链接同步',
    dispatch: () => dispatchGoogleStudentEligibilitySyncTask(detail.value.id),
    afterSuccess: () => fetchDetail({ silent: true, silentError: true }),
    afterFailure: () => fetchDetail({ silent: true, silentError: true }),
  })
  syncingStudent.value = false

  if (result === 'completed') {
    ElMessage.success('学生认证链接已更新')
  } else if (result === 'pending') {
    ElMessage.info('学生认证任务已提交，正在后台执行')
  }
}

async function handleAddFamilyMember() {
  const email = String(newMemberEmail.value || '').trim()
  if (!email) {
    ElMessage.warning('请先输入需要添加的邮箱')
    return
  }
  if (!isValidEmail(email)) {
    ElMessage.warning('邮箱格式不正确，请检查后重试')
    return
  }

  const exists = familyMembers.value.some((item) => String(item?.memberEmail || '').toLowerCase() === email.toLowerCase())
  if (exists) {
    ElMessage.warning('该邮箱已存在于家庭组成员中')
    return
  }
  if (!detail.value?.id) {
    ElMessage.warning('账号详情未加载完成，请稍后重试')
    return
  }

  addingMember.value = true
  const result = await runTaskWithConsole({
    taskName: `家庭组邀请（${email}）`,
    dispatch: () => dispatchGoogleFamilyInviteTask(detail.value.id, email),
    afterSuccess: () => fetchDetail({ silent: true, silentError: true }),
    afterFailure: () => fetchDetail({ silent: true, silentError: true }),
  })
  addingMember.value = false

  if (result === 'completed') {
    ElMessage.success('成员邀请完成')
    closeAddMemberPanel()
    return
  }
  if (result === 'pending') {
    ElMessage.info('成员邀请任务已提交，后台执行中')
    closeAddMemberPanel()
  }
}

onMounted(() => {
  setTaskConsoleVisible(String(route.query[TASK_DEBUG_QUERY_KEY] || '') === '1', { syncQuery: false })
  fetchDetail()
})

watch(
  () => route.query[TASK_DEBUG_QUERY_KEY],
  (value) => {
    const nextVisible = String(value || '') === '1'
    if (taskConsoleVisible.value !== nextVisible) {
      setTaskConsoleVisible(nextVisible, { syncQuery: false })
    }
  }
)

watch(accountId, (nextId, prevId) => {
  if (nextId && nextId !== prevId) {
    taskFlowToken = Date.now()
    baseEditing.value = false
    resetTaskConsole()
    fetchDetail()
  }
})

onBeforeUnmount(() => {
  taskFlowToken = Date.now()
  baseEditing.value = false
  setTaskConsoleVisible(false, { syncQuery: false })
  resetTaskConsole()
  clearPendingTaskLogs()
  if (copyFeedbackTimer) {
    clearTimeout(copyFeedbackTimer)
    copyFeedbackTimer = null
  }
})
</script>

<template>
  <div class="detail-page">
    <div class="detail-main" v-loading="loading">
      <section class="detail-hero card-enter">
        <div class="hero-copy">
          <span class="hero-eyebrow">Google 账号工作台</span>
          <h1>{{ detail?.email || 'Google 账号详情' }}</h1>
          <p>{{ detail?.recoveryEmail ? `辅助邮箱：${detail.recoveryEmail}` : '查看账号资料、同步状态与任务活动' }}</p>
          <div class="hero-meta">
            <div v-for="item in heroMetaItems" :key="item.label" class="hero-meta-item">
              <span>{{ item.label }}</span>
              <strong>{{ item.value }}</strong>
            </div>
          </div>
        </div>
        <div class="hero-actions">
          <section class="hero-action-toolbar" aria-label="快捷操作">
            <span class="hero-action-kicker">快捷操作</span>
            <div class="hero-primary-actions">
              <el-button
                class="hero-primary-button hero-primary-button--sync"
                type="warning"
                size="small"
                :icon="RefreshRight"
                :loading="syncingBase"
                :disabled="taskRunning"
                @click="handleSyncAccountTask"
              >
                同步账号信息
              </el-button>
              <el-button
                class="hero-primary-button hero-primary-button--student"
                type="success"
                size="small"
                :icon="RefreshRight"
                :loading="syncingStudent"
                :disabled="taskRunning"
                @click="handleSyncStudentTask"
              >
                同步学生认证
              </el-button>
            </div>
            <div class="hero-secondary-actions">
              <el-button class="hero-secondary-button" size="small" :icon="Refresh" @click="fetchDetail()">刷新</el-button>
              <router-link class="hero-nav-link" to="/google/accounts">返回列表</router-link>
              <el-button
                class="hero-secondary-button hero-secondary-button--danger"
                size="small"
                type="danger"
                plain
                :icon="Delete"
                :loading="deleting"
                @click="handleDelete"
              >
                删除账号
              </el-button>
            </div>
          </section>
        </div>
      </section>

      <section class="summary-grid card-enter">
        <article
          v-for="item in summaryItems"
          :key="item.label"
          class="summary-card"
          :class="{ 'summary-card--accent': item.label === '同步状态' }"
        >
          <span>{{ item.label }}</span>
          <strong>{{ item.value }}</strong>
        </article>
      </section>

      <section class="detail-content-grid">
        <div class="detail-primary-column">
          <section class="card-block card-enter">
            <header class="section-header">
              <div>
                <h2>基础信息</h2>
                <p>{{ baseEditing ? '可直接修改密码、辅助邮箱、TOTP、地区与备注' : '当前账号的身份、凭据与地区信息' }}</p>
              </div>
              <div class="section-actions">
                <template v-if="baseEditing">
                  <el-button size="small" @click="cancelBaseEditing">取消</el-button>
                  <el-button size="small" type="primary" :loading="baseSaving" @click="saveBaseEditing">保存修改</el-button>
                </template>
                <el-button v-else size="small" type="primary" plain @click="startBaseEditing">编辑资料</el-button>
              </div>
            </header>
            <div class="base-account-strip">
              <div class="base-account-chip">
                <span>账号ID</span>
                <strong>{{ toNullableText(detail?.id) }}</strong>
              </div>
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
              <p class="base-account-hint">主邮箱当前保持只读，辅助邮箱、地区、密码、TOTP 与备注可直接回写后端。</p>
            </div>

            <el-form
              v-if="baseEditing"
              ref="baseEditFormRef"
              :model="baseEditForm"
              :rules="baseFormRules"
              label-width="104px"
              class="base-edit-form"
            >
              <div class="base-edit-grid">
                <el-form-item label="辅助邮箱" prop="recoveryEmail">
                  <el-input
                    v-model="baseEditForm.recoveryEmail"
                    type="email"
                    inputmode="email"
                    autocomplete="email"
                    spellcheck="false"
                    clearable
                    placeholder="可为空，留空会清除辅助邮箱"
                  />
                </el-form-item>
                <el-form-item label="地区" prop="region">
                  <el-input
                    v-model="baseEditForm.region"
                    autocapitalize="characters"
                    spellcheck="false"
                    clearable
                    placeholder="例如 US / JP / HK"
                  />
                </el-form-item>
                <el-form-item label="登录密码" prop="password">
                  <el-input
                    v-model="baseEditForm.password"
                    type="password"
                    autocomplete="new-password"
                    spellcheck="false"
                    show-password
                    placeholder="留空表示不修改密码"
                  />
                </el-form-item>
                <el-form-item label="TOTP 密钥" prop="totpSecret">
                  <el-input
                    v-model="baseEditForm.totpSecret"
                    autocomplete="off"
                    autocapitalize="off"
                    spellcheck="false"
                    placeholder="不能为空；如需保留请勿删除"
                  />
                </el-form-item>
              </div>
              <el-form-item label="备注" prop="remark" class="base-edit-remark">
                <el-input
                  v-model="baseEditForm.remark"
                  type="textarea"
                  :rows="3"
                  maxlength="255"
                  show-word-limit
                  placeholder="可为空，留空会清除备注"
                />
              </el-form-item>
            </el-form>

            <el-descriptions v-else :column="2" class="detail-descriptions">
              <el-descriptions-item label="辅助邮箱">{{ toNullableText(detail?.recoveryEmail) }}</el-descriptions-item>
              <el-descriptions-item label="地区">{{ toNullableText(detail?.region) }}</el-descriptions-item>
              <el-descriptions-item label="备注">{{ toNullableText(detail?.remark) }}</el-descriptions-item>
            </el-descriptions>
          </section>

          <section class="card-block card-enter">
            <header class="section-header">
              <div>
                <h2>动态验证码</h2>
                <p>用于快速验证 TOTP 是否可用</p>
              </div>
            </header>
            <TotpCodeTool :secret="detail?.totpSecret" :allow-manual-input="false" />
          </section>

          <section class="card-block card-enter">
            <header class="section-header">
              <div>
                <h2>订阅与备注</h2>
                <p>同步结果、学生认证与更新时间</p>
              </div>
            </header>
            <el-descriptions :column="2" class="detail-descriptions">
              <el-descriptions-item label="订阅类型">{{ toNullableText(detail?.subTier) }}</el-descriptions-item>
              <el-descriptions-item label="到期日期">{{ toNullableText(detail?.expireDate) }}</el-descriptions-item>
              <el-descriptions-item label="学生认证链接">
                <div v-if="detail?.studentLink" class="detail-link-field">
                  <a
                    :href="detail.studentLink"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="text-link detail-link-url"
                    :title="detail.studentLink"
                  >
                    {{ detail.studentLink }}
                  </a>
                  <el-button
                    text
                    size="small"
                    class="credential-copy-btn detail-link-copy"
                    :class="{ 'is-copied': copiedField === 'student-link' }"
                    :icon="copiedField === 'student-link' ? Check : CopyDocument"
                    @click="handleCopyValue(detail.studentLink, '学生认证链接', 'student-link')"
                  >
                    {{ copiedField === 'student-link' ? '已复制' : '复制链接' }}
                  </el-button>
                </div>
                <span v-else>-</span>
              </el-descriptions-item>
              <el-descriptions-item label="备注">{{ toNullableText(detail?.remark) }}</el-descriptions-item>
              <el-descriptions-item label="创建时间">{{ formatDisplayDate(detail?.createdAt) }}</el-descriptions-item>
              <el-descriptions-item label="更新时间">{{ formatDisplayDate(detail?.updatedAt) }}</el-descriptions-item>
            </el-descriptions>
          </section>

          <section class="relation-grid card-enter">
            <article class="relation-card">
              <header class="relation-header">
                <div>
                  <h2>家庭组成员</h2>
                  <p>成员列表与邀请状态</p>
                </div>
                <el-button type="primary" plain size="small" :icon="Plus" :disabled="taskRunning" @click="openAddMemberPanel">添加成员</el-button>
              </header>

              <transition name="expand-fade">
                <div v-if="addMemberPanelOpen" class="member-composer">
                  <div class="member-composer-main">
                    <el-input
                      v-model="newMemberEmail"
                      type="email"
                      inputmode="email"
                      autocomplete="email"
                      spellcheck="false"
                      clearable
                      class="composer-input"
                      placeholder="输入成员邮箱，例如 member@gmail.com"
                      @keyup.enter="handleAddFamilyMember"
                    />
                    <el-button :loading="addingMember" :disabled="!canSubmitMember || taskRunning" type="primary" @click="handleAddFamilyMember">
                      提交邀请
                    </el-button>
                    <el-button @click="closeAddMemberPanel">取消</el-button>
                  </div>
                  <p v-if="memberEmailError" class="composer-error">{{ memberEmailError }}</p>
                </div>
              </transition>

              <el-empty v-if="!familyMembers.length" description="暂无家庭组成员数据" />
              <transition-group v-else name="compact-list" tag="ul" class="compact-list">
                <li v-for="item in familyMembers" :key="`family-${item.id}`" class="compact-item">
                  <div class="item-main">
                    <strong>{{ toNullableText(item.memberName) }}</strong>
                    <el-tag size="small" effect="light">{{ resolveFamilyRoleText(item.memberRole) }}</el-tag>
                  </div>
                  <p>{{ toNullableText(item.memberEmail) }}</p>
                  <small>邀请日期：{{ formatDisplayDate(item.inviteDate, { includeTime: false }) }}</small>
                </li>
              </transition-group>
            </article>

            <article class="relation-card">
              <header class="relation-header">
                <div>
                  <h2>邀请链接</h2>
                  <p>复制与使用次数</p>
                </div>
              </header>

              <el-empty v-if="!inviteLinks.length" description="暂无邀请链接数据" />
              <transition-group v-else name="compact-list" tag="ul" class="compact-list">
                <li v-for="item in inviteLinks" :key="`invite-${item.id}`" class="compact-item">
                  <div class="item-main">
                    <el-tag size="small" type="success" effect="light">已使用 {{ item.usedCount || 0 }} 次</el-tag>
                    <el-button
                      text
                      class="invite-copy-btn"
                      :class="{ 'is-copied': copiedField === `invite-${item.id}` }"
                      :icon="copiedField === `invite-${item.id}` ? Check : CopyDocument"
                      @click.stop="handleCopyValue(item.inviteUrl, '邀请链接', `invite-${item.id}`)"
                    >
                      {{ copiedField === `invite-${item.id}` ? '已复制' : '复制链接' }}
                    </el-button>
                  </div>
                  <a :href="item.inviteUrl" target="_blank" rel="noopener noreferrer" class="text-link text-link--truncate">
                    {{ toNullableText(item.inviteUrl) }}
                  </a>
                </li>
              </transition-group>
            </article>
          </section>
        </div>

        <aside class="detail-sidebar-column card-enter">
          <section class="task-activity-card">
            <header class="task-activity-header">
              <div>
                <h2>任务活动</h2>
                <p>实时状态、关键轨迹与调试详情</p>
              </div>
              <div class="task-activity-actions">
                <el-button
                  text
                  size="small"
                  :aria-expanded="taskConsoleVisible ? 'true' : 'false'"
                  :aria-controls="taskDebugPanelId"
                  @click="toggleTaskConsole"
                >
                  {{ taskConsoleVisible ? '收起调试' : '展开调试' }}
                </el-button>
                <el-button
                  text
                  size="small"
                  :disabled="taskRunning || hasPendingBackgroundTask()"
                  @click="clearTaskConsoleIfIdle"
                >
                  清空记录
                </el-button>
              </div>
            </header>

            <div class="activity-state-card" :class="`is-${taskActivityState.tone}`">
              <div class="activity-state-copy">
                <span>{{ taskActivityState.eyebrow }}</span>
                <strong>{{ taskActivityState.title }}</strong>
                <p>{{ taskActivityState.description }}</p>
              </div>
              <div class="activity-state-side">
                <el-tag size="small" :type="taskStatusTagType">
                  {{ taskStatus === 'idle' ? resolveSyncText(detail?.syncStatus) : taskStatusText }}
                </el-tag>
                <small>{{ taskSocketConnected ? '实时流已连接' : taskTransportText }}</small>
              </div>
            </div>

            <div class="task-info-grid">
              <article v-for="item in taskInfoChips" :key="item.label" class="task-info-card">
                <span>{{ item.label }}</span>
                <strong>{{ item.value }}</strong>
              </article>
            </div>

            <section class="activity-section">
              <div class="activity-section-head">
                <div>
                  <h3>关键轨迹</h3>
                  <p>只保留任务状态与用户可感知节点</p>
                </div>
                <small>{{ hasTaskLogs ? `最近 ${taskTimelineLogs.length} 条` : '暂无任务轨迹' }}</small>
              </div>

              <div class="activity-log-viewport">
                <div v-if="!hasTaskLogs" class="activity-empty-state activity-empty-state--timeline">
                  <strong>这里会展示任务的关键状态</strong>
                  <p>触发同步或邀请任务后，页面会持续展示队列状态、执行结果和自动回写情况。</p>
                </div>

                <ul v-else class="activity-timeline">
                  <li v-for="item in taskTimelineLogs" :key="item.id" class="activity-timeline-item">
                    <span class="log-dot" :class="`is-${item.level}`"></span>
                    <div class="activity-timeline-content">
                      <div class="activity-timeline-head">
                        <strong>{{ item.message }}</strong>
                        <small>{{ item.time }}</small>
                      </div>
                      <p>{{ resolveLogLevelText(item.level) }}</p>
                    </div>
                  </li>
                </ul>
              </div>
            </section>

            <section class="activity-section activity-debug-shell" :class="{ 'is-open': taskConsoleVisible }">
              <div class="activity-section-head">
                <div>
                  <h3>调试详情</h3>
                  <p>保留 run/root 与原始日志，不干扰主状态阅读</p>
                </div>
                <small>{{ taskDebugCount ? `${taskDebugCount} 条调试日志` : '按需展开' }}</small>
              </div>

              <transition name="expand-fade">
                <div v-if="taskConsoleVisible" :id="taskDebugPanelId" class="activity-debug-panel">
                  <div class="activity-debug-frame">
                    <dl class="debug-meta-grid">
                      <div>
                        <dt>task run</dt>
                        <dd class="mono-chip">{{ taskMeta?.taskRunId || '-' }}</dd>
                      </div>
                      <div>
                        <dt>root run</dt>
                        <dd class="mono-chip">{{ taskMeta?.rootRunId || '-' }}</dd>
                      </div>
                      <div>
                        <dt>错误信息</dt>
                        <dd>{{ toNullableText(taskMeta?.errorMessage) }}</dd>
                      </div>
                      <div>
                        <dt>调试日志</dt>
                        <dd>{{ taskDebugCount || 0 }} 条</dd>
                      </div>
                    </dl>

                    <div v-if="taskDebugLogs.length" class="debug-log-panel">
                      <ul class="debug-log-list">
                        <li v-for="item in taskDebugLogs" :key="`debug-${item.id}`" class="debug-log-item">
                          <span>{{ item.time }}</span>
                          <code>{{ item.message }}</code>
                        </li>
                      </ul>
                    </div>

                    <div v-else class="debug-empty-state">
                      当前没有额外的调试日志。关键状态已经直接展示在上面的任务轨迹中。
                    </div>
                  </div>
                </div>
              </transition>
            </section>

            <section class="sidebar-support-card">
              <header class="sidebar-support-header">
                <div>
                  <h3>同步范围</h3>
                  <p>把右侧留白改成一块可读的快照和下一步动作。</p>
                </div>
              </header>

              <div class="sidebar-support-grid">
                <article v-for="item in sidebarCoverageItems" :key="item.label" class="sidebar-support-item">
                  <span>{{ item.label }}</span>
                  <strong>{{ item.value }}</strong>
                  <p>{{ item.hint }}</p>
                </article>
              </div>

              <section class="sidebar-note-section">
                <div class="sidebar-note-head">
                  <h4>下一步动作</h4>
                  <small>按当前账号状态动态提示</small>
                </div>

                <ul class="sidebar-note-list">
                  <li v-for="item in sidebarActionNotes" :key="item.title" class="sidebar-note-item">
                    <strong>{{ item.title }}</strong>
                    <p>{{ item.description }}</p>
                  </li>
                </ul>
              </section>
            </section>
          </section>
        </aside>
      </section>
    </div>
  </div>
</template>

<style scoped>
.detail-page {
  --detail-gap: 16px;
  --detail-panel-bg: #ffffff;
  --detail-panel-border: rgba(23, 37, 48, 0.08);
  --detail-panel-shadow: 0 12px 32px rgba(15, 23, 42, 0.08);
  --detail-panel-muted: #64748b;
  --detail-panel-text: #0f172a;
  position: relative;
  width: 100%;
}

.detail-main {
  display: grid;
  gap: var(--detail-gap);
  width: 100%;
  min-width: 0;
}

.detail-hero {
  border-radius: 20px;
  padding: 24px;
  background:
    radial-gradient(circle at 86% 18%, rgba(59, 130, 246, 0.24), transparent 34%),
    radial-gradient(circle at 12% 12%, rgba(16, 185, 129, 0.16), transparent 24%),
    linear-gradient(140deg, #102033 0%, #19304a 54%, #1d3d58 100%);
  color: #f8fbff;
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: flex-start;
  box-shadow: 0 20px 44px rgba(15, 23, 42, 0.16);
}

.hero-copy {
  min-width: 0;
  display: grid;
  gap: 12px;
}

.hero-eyebrow {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: rgba(248, 250, 252, 0.92);
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.18);
}

.detail-hero h1 {
  margin: 0;
  font-size: clamp(1.45rem, 2vw, 1.9rem);
  line-height: 1.12;
  overflow-wrap: anywhere;
}

.detail-hero p {
  margin: 0;
  max-width: 680px;
  color: rgba(241, 245, 249, 0.84);
  font-size: 0.95rem;
}

.hero-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.hero-meta-item {
  min-width: 112px;
  padding: 10px 12px;
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.16);
  background: rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(10px);
  display: grid;
  gap: 4px;
}

.hero-meta-item span {
  font-size: 0.74rem;
  color: rgba(226, 232, 240, 0.72);
}

.hero-meta-item strong {
  color: #f8fafc;
  font-size: 0.9rem;
  font-weight: 700;
}

.hero-actions {
  width: min(388px, 100%);
  align-self: stretch;
}

.hero-action-toolbar {
  min-width: 0;
  padding: 14px;
  border-radius: 20px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.1), rgba(255, 255, 255, 0.04));
  backdrop-filter: blur(16px);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.08),
    0 10px 24px rgba(15, 23, 42, 0.12);
  display: grid;
  gap: 10px;
}

.hero-action-kicker {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  min-height: 24px;
  padding: 0 10px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  background: rgba(15, 23, 42, 0.18);
  color: rgba(241, 245, 249, 0.88);
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.hero-primary-actions {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.hero-primary-button {
  width: 100%;
  min-height: 44px;
  min-width: 0;
  border-radius: 14px;
  padding-inline: 14px;
  font-weight: 700;
  border-width: 1px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.14);
}

.hero-primary-actions :deep(.el-button) {
  margin-left: 0 !important;
  justify-content: center;
}

.hero-primary-button--sync {
  border-color: rgba(251, 191, 36, 0.26);
  background: linear-gradient(180deg, rgba(251, 191, 36, 0.22), rgba(245, 158, 11, 0.18));
  color: #fff7ed;
}

.hero-primary-button--sync:hover {
  border-color: rgba(252, 211, 77, 0.34);
  background: linear-gradient(180deg, rgba(251, 191, 36, 0.3), rgba(245, 158, 11, 0.24));
  color: #ffffff;
}

.hero-primary-button--student {
  border-color: rgba(52, 211, 153, 0.24);
  background: linear-gradient(180deg, rgba(52, 211, 153, 0.18), rgba(16, 185, 129, 0.16));
  color: #ecfdf5;
}

.hero-primary-button--student:hover {
  border-color: rgba(110, 231, 183, 0.3);
  background: linear-gradient(180deg, rgba(52, 211, 153, 0.26), rgba(16, 185, 129, 0.22));
  color: #ffffff;
}

.hero-secondary-actions {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.hero-secondary-actions :deep(.el-button) {
  margin-left: 0 !important;
}

.hero-secondary-button,
.hero-nav-link {
  min-width: 0;
  min-height: 36px;
  border-radius: 12px;
  font-weight: 700;
  font-size: 13px;
  line-height: 1;
  white-space: nowrap;
}

.hero-nav-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 12px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  background: rgba(15, 23, 42, 0.16);
  color: #f8fafc;
  text-decoration: none;
  transition:
    border-color 180ms ease,
    background-color 180ms ease,
    color 180ms ease,
    box-shadow 180ms ease;
}

.hero-nav-link:hover {
  border-color: rgba(255, 255, 255, 0.22);
  background: rgba(15, 23, 42, 0.24);
  color: #ffffff;
}

.hero-secondary-button {
  width: 100%;
  padding-inline: 10px;
  border-color: rgba(255, 255, 255, 0.14);
  background: rgba(15, 23, 42, 0.16);
  color: #f8fafc;
}

.hero-secondary-button:hover {
  border-color: rgba(255, 255, 255, 0.22);
  background: rgba(15, 23, 42, 0.24);
  color: #ffffff;
}

.hero-secondary-button--danger {
  border-color: rgba(248, 113, 113, 0.2);
  background: rgba(127, 29, 29, 0.14);
  color: #ffe4e6;
}

.hero-secondary-button--danger:hover {
  border-color: rgba(248, 113, 113, 0.3);
  background: rgba(127, 29, 29, 0.22);
  color: #fff1f2;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.summary-card {
  background: linear-gradient(180deg, #ffffff, #f8fafc);
  border-radius: 16px;
  border: 1px solid var(--detail-panel-border);
  box-shadow: var(--detail-panel-shadow);
  padding: 16px;
  display: grid;
  gap: 8px;
}

.summary-card--accent {
  background:
    radial-gradient(circle at top right, rgba(37, 99, 235, 0.12), transparent 44%),
    linear-gradient(180deg, #ffffff, #eff6ff);
  border-color: rgba(37, 99, 235, 0.18);
}

.summary-card span {
  color: var(--detail-panel-muted);
  font-size: 0.8rem;
}

.summary-card strong {
  display: block;
  color: var(--detail-panel-text);
  font-size: 1.08rem;
}

.detail-content-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.72fr) minmax(320px, 0.98fr);
  gap: var(--detail-gap);
  align-items: flex-start;
}

.detail-primary-column,
.detail-sidebar-column {
  display: grid;
  gap: var(--detail-gap);
  min-width: 0;
}

.card-block {
  border-radius: 18px;
  border: 1px solid var(--detail-panel-border);
  box-shadow: var(--detail-panel-shadow);
  background: var(--detail-panel-bg);
  padding: 18px;
}

.section-header {
  margin-bottom: 14px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.section-header h2,
.section-header h3 {
  margin: 0;
  color: var(--detail-panel-text);
  font-size: 1rem;
}

.section-header p {
  margin: 4px 0 0;
  font-size: 0.8rem;
  color: var(--detail-panel-muted);
}

.section-actions {
  display: inline-flex;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 8px;
}

.section-actions :deep(.el-button) {
  margin-left: 0 !important;
  border-radius: 12px;
  font-weight: 700;
}

.base-account-strip {
  margin-bottom: 16px;
  padding: 14px;
  border-radius: 16px;
  border: 1px solid rgba(59, 130, 246, 0.16);
  background:
    radial-gradient(circle at top right, rgba(37, 99, 235, 0.08), transparent 42%),
    linear-gradient(145deg, #ffffff, #f8fafc);
  display: grid;
  grid-template-columns: minmax(144px, 176px) minmax(0, 1fr);
  gap: 12px;
  align-items: center;
}

.base-account-chip {
  align-self: stretch;
  border-radius: 14px;
  padding: 12px;
  background: rgba(15, 23, 42, 0.04);
  border: 1px solid rgba(148, 163, 184, 0.22);
  display: grid;
  gap: 6px;
}

.base-account-chip span {
  font-size: 0.74rem;
  color: var(--detail-panel-muted);
}

.base-account-chip strong {
  color: var(--detail-panel-text);
  font-size: 1rem;
  font-weight: 800;
  line-height: 1.2;
  word-break: break-all;
}

.base-account-hint {
  grid-column: 1 / -1;
  margin: 0;
  color: #475569;
  font-size: 0.8rem;
  line-height: 1.45;
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

.base-edit-form {
  padding: 16px;
  border-radius: 16px;
  border: 1px solid rgba(59, 130, 246, 0.16);
  background:
    linear-gradient(180deg, rgba(239, 246, 255, 0.68), rgba(248, 250, 252, 0.92));
}

.base-edit-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 16px;
}

.base-edit-form :deep(.el-form-item) {
  margin-bottom: 16px;
}

.base-edit-form :deep(.el-form-item__label) {
  color: #334155;
  font-weight: 700;
}

.base-edit-form :deep(.el-input__wrapper),
.base-edit-form :deep(.el-textarea__inner) {
  border-radius: 12px;
  box-shadow: 0 0 0 1px rgba(148, 163, 184, 0.2) inset;
}

.base-edit-form :deep(.el-input__wrapper:hover),
.base-edit-form :deep(.el-textarea__inner:hover) {
  box-shadow: 0 0 0 1px rgba(37, 99, 235, 0.26) inset;
}

.base-edit-form :deep(.el-input__wrapper.is-focus),
.base-edit-form :deep(.el-textarea__inner:focus) {
  box-shadow: 0 0 0 1px rgba(37, 99, 235, 0.42) inset;
}

.base-edit-remark {
  margin-bottom: 0;
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

.text-link {
  color: var(--og-emerald-700);
  text-decoration: none;
}

.text-link:hover {
  text-decoration: underline;
}

.hero-primary-button:focus-visible,
.hero-secondary-button:focus-visible,
.hero-nav-link:focus-visible,
.credential-copy-btn:focus-visible,
.invite-copy-btn:focus-visible,
.text-link:focus-visible {
  outline: 2px solid #2563eb;
  outline-offset: 2px;
}

.text-link--truncate {
  display: inline-block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.detail-link-field {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.detail-link-url {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 600;
}

.detail-link-copy {
  justify-self: end;
}

.relation-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.relation-card {
  border-radius: 18px;
  border: 1px solid var(--detail-panel-border);
  box-shadow: var(--detail-panel-shadow);
  background: var(--detail-panel-bg);
  padding: 16px;
  min-width: 0;
}

.relation-header {
  margin-bottom: 14px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.relation-header h2,
.relation-header h3 {
  margin: 0;
  color: var(--detail-panel-text);
  font-size: 1rem;
}

.relation-header p {
  margin: 4px 0 0;
  font-size: 0.8rem;
  color: var(--detail-panel-muted);
}

.member-composer {
  margin-bottom: 10px;
  padding: 10px;
  border-radius: 12px;
  border: 1px solid rgba(59, 130, 246, 0.25);
  background: linear-gradient(135deg, rgba(239, 246, 255, 0.9), rgba(248, 250, 252, 0.95));
  display: grid;
  gap: 8px;
}

.member-composer-main {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  gap: 8px;
  align-items: center;
}

.composer-input :deep(.el-input__wrapper) {
  border-radius: 10px;
  box-shadow: 0 0 0 1px rgba(59, 130, 246, 0.26) inset;
}

.composer-error {
  margin: 0;
  color: #b91c1c;
  font-size: 0.78rem;
  font-weight: 600;
}

.compact-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 8px;
  max-height: 320px;
  overflow: auto;
}

.compact-item {
  border-radius: 12px;
  border: 1px solid rgba(148, 163, 184, 0.24);
  background: linear-gradient(145deg, #ffffff, #f8fafc);
  padding: 10px;
  display: grid;
  gap: 6px;
}

.item-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  min-width: 0;
}

.item-main strong {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--detail-panel-text);
}

.compact-item p {
  margin: 0;
  color: #334155;
  font-size: 0.88rem;
  line-height: 1.42;
  word-break: break-all;
}

.compact-item small {
  color: var(--detail-panel-muted);
  font-size: 0.75rem;
}

.invite-copy-btn {
  border-radius: 999px;
  background: rgba(59, 130, 246, 0.14);
  color: #1d4ed8;
  padding: 0 10px;
  transition:
    transform 180ms cubic-bezier(0.22, 1, 0.36, 1),
    background-color 180ms ease,
    color 180ms ease;
}

.invite-copy-btn:hover {
  color: #1e40af;
  background: rgba(59, 130, 246, 0.22);
}

.invite-copy-btn:active {
  transform: scale(0.94);
}

.invite-copy-btn.is-copied {
  color: #047857;
  background: rgba(16, 185, 129, 0.2);
}

.task-activity-card {
  position: sticky;
  top: 88px;
  border-radius: 18px;
  border: 1px solid var(--detail-panel-border);
  box-shadow: var(--detail-panel-shadow);
  background:
    linear-gradient(180deg, #ffffff, #f8fbff 48%, #f8fafc 100%);
  padding: 18px;
  display: grid;
  gap: 16px;
}

.sidebar-support-card {
  display: grid;
  gap: 14px;
  margin-top: 2px;
  padding: 14px;
  border-radius: 16px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.92));
}

.sidebar-support-header h2,
.sidebar-support-header h3 {
  margin: 0;
  color: var(--detail-panel-text);
  font-size: 1rem;
}

.sidebar-support-header p {
  margin: 4px 0 0;
  font-size: 0.8rem;
  color: var(--detail-panel-muted);
}

.sidebar-support-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.sidebar-support-item {
  min-width: 0;
  padding: 12px;
  border-radius: 14px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  background:
    radial-gradient(circle at top right, rgba(37, 99, 235, 0.08), transparent 46%),
    linear-gradient(180deg, #ffffff, #f8fafc);
  display: grid;
  gap: 6px;
}

.sidebar-support-item span {
  font-size: 0.74rem;
  color: var(--detail-panel-muted);
}

.sidebar-support-item strong {
  color: var(--detail-panel-text);
  font-size: 0.92rem;
  line-height: 1.4;
}

.sidebar-support-item p {
  margin: 0;
  color: #475569;
  font-size: 0.78rem;
  line-height: 1.5;
}

.sidebar-note-section {
  display: grid;
  gap: 10px;
  padding-top: 14px;
  border-top: 1px solid rgba(148, 163, 184, 0.2);
}

.sidebar-note-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.sidebar-note-head h3 {
  margin: 0;
  color: var(--detail-panel-text);
  font-size: 0.96rem;
}

.sidebar-note-head h4 {
  margin: 0;
  color: var(--detail-panel-text);
  font-size: 0.96rem;
}

.sidebar-note-head small {
  color: var(--detail-panel-muted);
  font-size: 0.75rem;
}

.sidebar-note-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 8px;
}

.sidebar-note-item {
  padding: 12px;
  border-radius: 14px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: rgba(248, 250, 252, 0.78);
}

.sidebar-note-item strong {
  display: block;
  color: var(--detail-panel-text);
  font-size: 0.88rem;
}

.sidebar-note-item p {
  margin: 6px 0 0;
  color: #475569;
  font-size: 0.8rem;
  line-height: 1.5;
}

.task-activity-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.task-activity-header h2,
.task-activity-header h3 {
  margin: 0;
  color: var(--detail-panel-text);
  font-size: 1rem;
}

.task-activity-header p {
  margin: 4px 0 0;
  font-size: 0.8rem;
  color: var(--detail-panel-muted);
}

.task-activity-actions {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 4px;
  justify-content: flex-end;
}

.activity-state-card {
  padding: 16px;
  border-radius: 18px;
  display: flex;
  justify-content: space-between;
  gap: 14px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  background: #f8fafc;
}

.activity-state-card.is-idle {
  background: linear-gradient(180deg, #ffffff, #f8fafc);
}

.activity-state-card.is-queued,
.activity-state-card.is-warning {
  background: linear-gradient(180deg, rgba(255, 251, 235, 0.96), rgba(254, 243, 199, 0.88));
  border-color: rgba(217, 119, 6, 0.22);
}

.activity-state-card.is-running {
  background: linear-gradient(180deg, rgba(239, 246, 255, 0.96), rgba(219, 234, 254, 0.88));
  border-color: rgba(37, 99, 235, 0.2);
}

.activity-state-card.is-success {
  background: linear-gradient(180deg, rgba(236, 253, 245, 0.96), rgba(209, 250, 229, 0.88));
  border-color: rgba(5, 150, 105, 0.2);
}

.activity-state-card.is-error {
  background: linear-gradient(180deg, rgba(254, 242, 242, 0.98), rgba(254, 226, 226, 0.92));
  border-color: rgba(220, 38, 38, 0.2);
}

.activity-state-copy {
  min-width: 0;
  display: grid;
  gap: 6px;
}

.activity-state-copy span {
  font-size: 0.74rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--detail-panel-muted);
}

.activity-state-copy strong {
  font-size: 1.08rem;
  color: var(--detail-panel-text);
}

.activity-state-copy p {
  margin: 0;
  color: #334155;
  font-size: 0.88rem;
  line-height: 1.55;
}

.activity-state-side {
  flex-shrink: 0;
  display: grid;
  gap: 8px;
  justify-items: end;
  text-align: right;
}

.activity-state-side small {
  color: var(--detail-panel-muted);
  font-size: 0.74rem;
}

.task-info-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.task-info-card {
  padding: 12px;
  border-radius: 14px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  background: #ffffff;
  display: grid;
  gap: 6px;
}

.task-info-card span {
  font-size: 0.76rem;
  color: var(--detail-panel-muted);
}

.task-info-card strong {
  color: var(--detail-panel-text);
  font-size: 0.92rem;
  line-height: 1.45;
  overflow-wrap: anywhere;
}

.activity-section {
  display: grid;
  gap: 10px;
  padding-top: 16px;
  border-top: 1px solid rgba(148, 163, 184, 0.22);
}

.activity-debug-shell {
  gap: 0;
  padding-top: 0;
  border-top: none;
  border-radius: 18px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  background: linear-gradient(180deg, rgba(248, 250, 252, 0.86), rgba(255, 255, 255, 0.98));
  overflow: hidden;
}

.activity-debug-shell .activity-section-head {
  padding: 14px 16px;
}

.activity-debug-shell.is-open .activity-section-head {
  border-bottom: 1px solid rgba(148, 163, 184, 0.18);
}

.activity-section-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.activity-section-head h3,
.activity-section-head h4 {
  margin: 0;
  color: var(--detail-panel-text);
}

.activity-section-head p {
  margin: 4px 0 0;
  font-size: 0.8rem;
  color: var(--detail-panel-muted);
}

.activity-section-head small {
  flex-shrink: 0;
  margin-top: 2px;
  color: var(--detail-panel-muted);
  font-size: 0.76rem;
}

.activity-empty-state,
.debug-empty-state {
  padding: 14px;
  border-radius: 14px;
  border: 1px dashed rgba(148, 163, 184, 0.36);
  background: rgba(248, 250, 252, 0.78);
}

.activity-empty-state strong {
  display: block;
  margin-bottom: 6px;
  color: var(--detail-panel-text);
  font-size: 0.92rem;
}

.activity-empty-state p,
.debug-empty-state {
  margin: 0;
  color: var(--detail-panel-muted);
  font-size: 0.84rem;
  line-height: 1.55;
}

.activity-empty-state--timeline {
  min-height: 100%;
}

.activity-log-viewport {
  min-height: 264px;
  max-height: 264px;
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-gutter: stable;
  scrollbar-width: thin;
  overflow-anchor: none;
  padding-right: 4px;
}

.activity-timeline {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 10px;
}

.activity-timeline-item {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 10px;
  padding: 12px;
  border-radius: 14px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  background: #ffffff;
}

.activity-timeline-content {
  min-width: 0;
  display: grid;
  gap: 4px;
}

.activity-timeline-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.activity-timeline-head strong {
  color: var(--detail-panel-text);
  font-size: 0.86rem;
  line-height: 1.5;
}

.activity-timeline-head small {
  flex-shrink: 0;
  color: var(--detail-panel-muted);
  font-size: 0.74rem;
}

.activity-timeline-content p {
  margin: 0;
  color: var(--detail-panel-muted);
  font-size: 0.8rem;
}

.activity-debug-panel {
  padding: 14px 16px 16px;
}

.activity-debug-frame {
  display: grid;
  gap: 12px;
}

.debug-meta-grid {
  margin: 0;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.debug-meta-grid div {
  min-width: 0;
  padding: 12px;
  border-radius: 14px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  background: #ffffff;
  display: grid;
  gap: 6px;
}

.debug-meta-grid dt {
  font-size: 0.74rem;
  color: var(--detail-panel-muted);
}

.debug-meta-grid dd {
  margin: 0;
  color: var(--detail-panel-text);
  font-size: 0.84rem;
  line-height: 1.45;
  overflow-wrap: anywhere;
}

.mono-chip,
.debug-log-item span,
.debug-log-item code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
}

.mono-chip {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  max-width: 100%;
  padding: 6px 8px;
  border-radius: 10px;
  color: #e2e8f0;
  background: #0f172a;
  font-size: 0.74rem;
}

.debug-log-panel {
  height: 240px;
  overflow: auto;
  padding: 8px;
  border-radius: 16px;
  background: linear-gradient(180deg, #0f172a, #111c2d);
  border: 1px solid rgba(15, 23, 42, 0.2);
  overscroll-behavior: contain;
  scrollbar-gutter: stable;
  overflow-anchor: none;
}

.debug-log-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 8px;
}

.debug-log-item {
  display: grid;
  gap: 6px;
  padding: 9px 10px;
  border-radius: 12px;
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(148, 163, 184, 0.18);
}

.debug-log-item span {
  color: #94a3b8;
  font-size: 0.72rem;
}

.debug-log-item code {
  color: #e2e8f0;
  font-size: 0.78rem;
  line-height: 1.55;
  white-space: pre-wrap;
  word-break: break-word;
}

.task-console {
  position: fixed;
  top: 86px;
  right: 16px;
  width: 360px;
  height: calc(100vh - 104px);
  border-radius: 14px;
  border: 1px solid rgba(15, 23, 42, 0.12);
  background: rgba(255, 255, 255, 0.96);
  backdrop-filter: blur(10px);
  box-shadow: 0 18px 44px rgba(15, 23, 42, 0.18);
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr) auto;
  z-index: 20;
  overflow: hidden;
}

.task-console-header {
  padding: 12px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.24);
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.task-console-header h3 {
  margin: 0;
  font-size: 0.96rem;
  color: var(--og-slate-900);
}

.task-console-header p {
  margin: 4px 0 0;
  font-size: 0.78rem;
  color: var(--og-slate-500);
}

.console-actions {
  display: inline-flex;
  align-items: center;
  gap: 2px;
}

.console-close {
  width: 28px;
  height: 28px;
  border-radius: 999px;
}

.task-meta {
  padding: 10px 12px 8px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.2);
}

.task-meta span {
  font-size: 0.72rem;
  color: var(--og-slate-500);
}

.socket-flag {
  display: inline-flex;
  align-items: center;
  height: 22px;
  padding: 0 8px;
  border-radius: 999px;
  font-size: 0.7rem;
  color: #92400e !important;
  background: rgba(251, 191, 36, 0.16);
  border: 1px solid rgba(245, 158, 11, 0.28);
}

.socket-flag.is-connected {
  color: #065f46 !important;
  background: rgba(16, 185, 129, 0.16);
  border-color: rgba(16, 185, 129, 0.32);
}

.task-log-list {
  list-style: none;
  margin: 0;
  padding: 10px 10px 12px;
  display: grid;
  gap: 8px;
  overflow-y: auto;
}

.task-log-item {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 8px;
  padding: 8px;
  border-radius: 10px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  background: linear-gradient(180deg, #ffffff, #f8fafc);
}

.log-dot {
  width: 8px;
  height: 8px;
  margin-top: 6px;
  border-radius: 999px;
  background: #64748b;
  box-shadow: 0 0 0 3px rgba(100, 116, 139, 0.16);
}

.log-dot.is-debug {
  background: #0ea5e9;
  box-shadow: 0 0 0 3px rgba(14, 165, 233, 0.18);
}

.log-dot.is-info {
  background: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.16);
}

.log-dot.is-success {
  background: #059669;
  box-shadow: 0 0 0 3px rgba(5, 150, 105, 0.18);
}

.log-dot.is-warning {
  background: #d97706;
  box-shadow: 0 0 0 3px rgba(217, 119, 6, 0.18);
}

.log-dot.is-error {
  background: #dc2626;
  box-shadow: 0 0 0 3px rgba(220, 38, 38, 0.2);
}

.log-content {
  min-width: 0;
}

.log-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.log-title-row strong {
  font-size: 0.77rem;
  color: var(--og-slate-700);
}

.log-title-row small {
  flex-shrink: 0;
  color: var(--og-slate-500);
  font-size: 0.72rem;
}

.log-content p {
  margin: 4px 0 0;
  color: var(--og-slate-900);
  font-size: 0.82rem;
  line-height: 1.35;
  word-break: break-word;
}

.log-step {
  display: block;
  margin-top: 4px;
  color: var(--og-slate-500);
}

.progress-panel {
  padding: 10px 12px 12px;
  border-top: 1px solid rgba(148, 163, 184, 0.22);
  background: rgba(248, 250, 252, 0.92);
  display: grid;
  gap: 7px;
}

.progress-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 0.8rem;
  color: var(--og-slate-700);
}

.progress-head strong {
  font-size: 0.92rem;
  color: #0f766e;
}

.progress-track {
  width: 100%;
  height: 10px;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.08);
  overflow: hidden;
}

.progress-value {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #14b8a6, #22c55e);
  box-shadow: 0 2px 10px rgba(20, 184, 166, 0.38);
  transition:
    width 580ms cubic-bezier(0.22, 1.28, 0.32, 1),
    box-shadow 280ms ease;
}

.progress-panel small {
  color: var(--og-slate-500);
  font-size: 0.75rem;
}

.console-float-button {
  position: fixed;
  right: 16px;
  bottom: 24px;
  border: 0;
  border-radius: 999px;
  padding: 10px 14px;
  color: #0f172a;
  background: linear-gradient(135deg, #dbeafe, #ecfeff);
  box-shadow: 0 12px 26px rgba(37, 99, 235, 0.26);
  cursor: pointer;
  z-index: 18;
  transition:
    transform 220ms cubic-bezier(0.22, 1, 0.36, 1),
    box-shadow 220ms ease,
    filter 220ms ease;
}

.console-float-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 16px 30px rgba(37, 99, 235, 0.3);
  filter: saturate(1.06);
}

.console-float-button:active {
  transform: translateY(0);
}

.console-slide-enter-active,
.console-slide-leave-active {
  transition:
    transform 460ms cubic-bezier(0.2, 1.25, 0.28, 1),
    opacity 260ms ease;
}

.console-slide-enter-from,
.console-slide-leave-to {
  opacity: 0;
  transform: translateX(28px) scale(0.98);
}

.expand-fade-enter-active,
.expand-fade-leave-active {
  transition:
    opacity 220ms ease,
    transform 220ms ease;
}

.expand-fade-enter-from,
.expand-fade-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

.compact-list-enter-active,
.compact-list-leave-active {
  transition:
    opacity 220ms cubic-bezier(0.22, 1, 0.36, 1),
    transform 220ms cubic-bezier(0.22, 1, 0.36, 1);
}

.compact-list-enter-from,
.compact-list-leave-to {
  opacity: 0;
  transform: translateY(6px);
}

.card-enter {
  animation: cardRise 380ms cubic-bezier(0.22, 1, 0.36, 1) both;
}

.card-enter:nth-child(2) {
  animation-delay: 50ms;
}

.card-enter:nth-child(3) {
  animation-delay: 90ms;
}

.card-enter:nth-child(4) {
  animation-delay: 130ms;
}

.card-enter:nth-child(5) {
  animation-delay: 170ms;
}

.card-enter:nth-child(6) {
  animation-delay: 210ms;
}

@keyframes cardRise {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (prefers-reduced-motion: reduce) {
  .card-enter,
  .compact-list-enter-active,
  .compact-list-leave-active,
  .detail-main {
    animation: none !important;
    transition: none !important;
  }
}

@media (max-width: 1280px) {
  .detail-content-grid {
    grid-template-columns: 1fr;
  }

  .task-activity-card {
    position: static;
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

  .hero-actions {
    width: 100%;
  }

  .base-account-strip {
    grid-template-columns: 1fr;
  }

  .relation-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .base-edit-grid,
  .task-info-grid,
  .debug-meta-grid,
  .sidebar-support-grid {
    grid-template-columns: 1fr;
  }

  .activity-state-card {
    flex-direction: column;
  }

  .activity-state-side {
    justify-items: start;
    text-align: left;
  }

  .activity-log-viewport {
    min-height: 232px;
    max-height: 232px;
  }

  .detail-link-field {
    grid-template-columns: 1fr;
    align-items: stretch;
  }

  .detail-link-url {
    white-space: normal;
    overflow: visible;
    text-overflow: initial;
    overflow-wrap: anywhere;
  }

  .detail-link-copy {
    justify-self: start;
  }
}

@media (max-width: 640px) {
  .summary-grid {
    grid-template-columns: 1fr;
  }

  .member-composer-main {
    grid-template-columns: 1fr;
  }

  .credential-focus-row {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
  }

  .credential-item {
    gap: 6px;
    padding: 8px;
  }

  .hero-meta {
    width: 100%;
  }

  .hero-meta {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .hero-primary-actions,
  .hero-secondary-actions {
    grid-template-columns: 1fr;
  }

  .task-activity-actions :deep(.el-button) {
    width: 100%;
    margin-left: 0 !important;
  }

  .section-header,
  .relation-header,
  .task-activity-header,
  .activity-section-head,
  .sidebar-note-head {
    flex-direction: column;
  }

  .section-actions {
    width: 100%;
    justify-content: flex-start;
  }
}
</style>
