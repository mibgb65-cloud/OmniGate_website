<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Download, EditPen, Plus, Refresh, Search, Upload, View } from '@element-plus/icons-vue'
import {
  batchDeleteChatgptAccounts,
  batchUpdateChatgptAccountSold,
  batchUpdateChatgptAccountStatus,
  createChatgptAccount,
  createChatgptAccountsBatch,
  deleteChatgptAccount,
  dispatchChatgptBatchRegisterTask,
  getChatgptTaskStatusByRootRunId,
  pageChatgptAccounts,
  updateChatgptAccount,
} from '@/api/chatgpt'
import {
  buildExportFilename,
  downloadTextFile,
  fetchAllPagedRecords,
  formatChatgptAccountLine,
} from '@/utils/accountExport'

const route = useRoute()
const router = useRouter()
const tableRef = ref()
const loading = ref(false)
const rows = ref([])
const selectedRows = ref([])
const deletingId = ref(null)
const rowSoldUpdatingId = ref(null)
const filterForm = reactive({ email: '', subTier: undefined, accountStatus: undefined, sold: undefined })
const DEFAULT_PAGE_SIZE = 10
const TASK_ROUTE_QUERY_KEY = 'taskRootRunId'
const TASK_SNAPSHOT_STORAGE_KEY = 'og-chatgpt-auto-register-task'
const DETAIL_EMAIL_QUERY_KEY = 'accountEmail'
const LIST_RETURN_QUERY_KEY = 'listQuery'
const MANAGED_QUERY_KEYS = ['email', 'subTier', 'accountStatus', 'sold', 'page', 'size', TASK_ROUTE_QUERY_KEY]
const pager = reactive({ current: 1, size: DEFAULT_PAGE_SIZE, total: 0 })
const subTierOptions = [{ label: 'Free', value: 'free' }, { label: 'Plus', value: 'plus' }, { label: 'Team', value: 'team' }, { label: 'Go', value: 'go' }]
const statusOptions = [{ label: '可用', value: 'active' }, { label: '锁定', value: 'locked' }, { label: '封禁', value: 'banned' }]
const soldOptions = [{ label: '未出售', value: false }, { label: '已出售', value: true }]
const accountDialogVisible = ref(false)
const accountDialogMode = ref('create')
const accountFormRef = ref()
const savingAccount = ref(false)
const originalAccount = ref(null)
const accountForm = reactive({ id: null, email: '', password: '', sessionToken: '', totpSecret: '', subTier: 'free', accountStatus: 'active', sold: false, expireDate: '' })
const batchDialogVisible = ref(false)
const batchRawText = ref('')
const batchCreating = ref(false)
const autoRegisterDialogVisible = ref(false)
const autoRegisterFormRef = ref()
const autoRegisterSubmitting = ref(false)
const latestAutoRegisterTask = ref(null)
const autoRegisterForm = reactive({ signupCount: 1 })
const statusBatchValue = ref('active')
const statusBatchLoading = ref(false)
const soldBatchValue = ref(false)
const soldBatchLoading = ref(false)
const batchDeleting = ref(false)
const TASK_STATUS_POLL_INTERVAL_MS = 3000
const TASK_STATUS_RETRY_INTERVAL_MS = 5000
const TERMINAL_TASK_STATUSES = new Set(['success', 'failed', 'cancelled', 'timeout'])
let taskStatusPollTimer = null

const selectedIds = computed(() => selectedRows.value.map((row) => row.id).filter(Boolean))
const hasSelection = computed(() => selectedIds.value.length > 0)
const resultSummary = computed(() => `筛选结果 ${pager.total} 条`)
const dashboardStats = computed(() => [
  { label: '筛选结果', value: pager.total, note: '当前条件下的总账号数' },
  { label: '未出售库存', value: rows.value.filter((row) => !row.sold).length, note: '当前页仍可继续分配' },
  { label: '材料完整', value: rows.value.filter((row) => row.password && row.totpSecret && row.sessionToken).length, note: '密码 + 2FA + Session 齐全' },
  { label: '已勾选', value: selectedIds.value.length, note: hasSelection.value ? '批量工作台已激活' : '勾选后可批量处理' },
])
const activeFilterTags = computed(() => {
  const tags = []
  if (normalizeCell(filterForm.email)) tags.push({ key: 'email', label: '邮箱', value: filterForm.email.trim() })
  if (!isFilterUnset(filterForm.subTier)) tags.push({ key: 'subTier', label: '层级', value: formatSubTier(filterForm.subTier) })
  if (!isFilterUnset(filterForm.accountStatus)) tags.push({ key: 'accountStatus', label: '状态', value: formatAccountStatus(filterForm.accountStatus) })
  if (!isFilterUnset(filterForm.sold)) tags.push({ key: 'sold', label: '出售', value: formatSoldStatus(filterForm.sold) })
  return tags
})
const latestAutoRegisterTaskStatusLabel = computed(() => formatTaskStatus(latestAutoRegisterTask.value?.status))
const latestAutoRegisterTaskAlertType = computed(() => resolveTaskAlertType(latestAutoRegisterTask.value?.status))
const latestAutoRegisterTaskProgressLabel = computed(() => {
  const requestedCount = Number(latestAutoRegisterTask.value?.requestedCount || 0)
  const currentIndex = Number(latestAutoRegisterTask.value?.currentIndex || 0)
  if (requestedCount <= 0 || currentIndex <= 0) return ''
  return `${Math.min(currentIndex, requestedCount)}/${requestedCount}`
})
const latestAutoRegisterTaskTitle = computed(() => {
  const status = normalizeTaskStatus(latestAutoRegisterTask.value?.status)
  if (!status) return '最近一次自动注册任务'
  return isTerminalTaskStatus(status) ? `最近一次自动注册队列已结束（${formatTaskStatus(status)}）` : `最近一次自动注册队列进行中（${formatTaskStatus(status)}）`
})
const exportButtonLabel = computed(() => (
  selectedRows.value.length
    ? `导出已选（${selectedRows.value.length}）`
    : '导出筛选结果'
))
const selectionInsights = computed(() => {
  if (!selectedRows.value.length) return []
  return [
    { label: '可用', value: selectedRows.value.filter((row) => row.accountStatus === 'active').length },
    { label: '已售', value: selectedRows.value.filter((row) => Boolean(row.sold)).length },
    { label: 'Free', value: selectedRows.value.filter((row) => row.subTier === 'free').length },
  ]
})
const inventoryLanes = computed(() => [
  {
    key: 'ready',
    label: '可立即接管',
    value: rows.value.filter((row) => row.accountStatus === 'active' && !row.sold && row.password && row.totpSecret && row.sessionToken).length,
    note: '密码、2FA、Session 齐全，且账号仍在库存中',
    tone: 'success',
  },
  {
    key: 'material-gap',
    label: '待补材料',
    value: rows.value.filter((row) => !row.password || !row.totpSecret || !row.sessionToken).length,
    note: '至少缺少一项接管材料，需要补录后再分配',
    tone: 'warning',
  },
  {
    key: 'sold',
    label: '已售资产',
    value: rows.value.filter((row) => Boolean(row.sold)).length,
    note: '当前页已做出售登记，后续以售后维护为主',
    tone: 'danger',
  },
  {
    key: 'risk',
    label: '异常状态',
    value: rows.value.filter((row) => ['locked', 'banned'].includes(row.accountStatus)).length,
    note: '锁定或封禁账号，适合优先排查',
    tone: 'neutral',
  },
])
const accountRules = {
  email: [{ required: true, message: '请输入账号邮箱', trigger: 'blur' }, { type: 'email', message: '邮箱格式不正确', trigger: ['blur', 'change'] }],
  password: [{
    trigger: ['blur', 'change'],
    validator: (_rule, value, callback) => {
      const normalized = normalizeCell(value)
      if (accountDialogMode.value === 'create' && !normalized) return callback(new Error('新增时密码不能为空'))
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

const autoRegisterRules = {
  signupCount: [{
    trigger: ['blur', 'change'],
    validator: (_rule, value, callback) => {
      const count = Number(value)
      if (!Number.isInteger(count) || count <= 0) return callback(new Error('注册数量必须是大于 0 的整数'))
      callback()
    },
  }],
}

function normalizeCell(value) { const text = String(value ?? '').trim(); return text || undefined }
function isFilterUnset(value) { return value === undefined || value === null || value === '' }
function normalizeFilterValue(value) { return isFilterUnset(value) ? undefined : value }
function readQueryValue(query, key) { const value = query?.[key]; return Array.isArray(value) ? value[0] : value }
function parseQueryBoolean(value) {
  const normalized = String(value ?? '').trim().toLowerCase()
  if (normalized === '1' || normalized === 'true') return true
  if (normalized === '0' || normalized === 'false') return false
  return undefined
}
function parsePositiveInteger(value, fallback) {
  const parsed = Number(value)
  return Number.isInteger(parsed) && parsed > 0 ? parsed : fallback
}
function serializeQueryObject(query) {
  const params = new URLSearchParams()
  Object.entries(query || {}).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return
    if (Array.isArray(value)) {
      value.forEach((item) => {
        if (item !== undefined && item !== null && item !== '') params.append(key, String(item))
      })
      return
    }
    params.append(key, String(value))
  })
  return params.toString()
}
function detectDelimiter(line) { if (line.includes('----')) return '----'; if (line.includes('\t')) return '\t'; if (line.includes('|')) return '|'; return ',' }
function toNullableText(value) { return value || '-' }
function formatAccountStatus(status) { return ({ active: '可用', locked: '锁定', banned: '封禁' }[status]) || status || '-' }
function formatSubTier(subTier) { return ({ free: 'Free', plus: 'Plus', team: 'Team', go: 'Go' }[subTier]) || subTier || '-' }
function formatSoldStatus(sold) { return sold ? '已出售' : '未出售' }
function resolveStatusTag(status) { return status === 'active' ? 'success' : status === 'locked' ? 'warning' : status === 'banned' ? 'danger' : 'info' }
function resolveTierTag(subTier) { return subTier === 'team' ? 'primary' : subTier === 'plus' ? 'success' : subTier === 'go' ? 'warning' : 'info' }
function resolveSoldTag(sold) { return sold ? 'danger' : 'success' }
function normalizeTaskStatus(status) { return String(status ?? '').trim().toLowerCase() }
function isTerminalTaskStatus(status) { return TERMINAL_TASK_STATUSES.has(normalizeTaskStatus(status)) }
function formatTaskStatus(status) { return ({ queued: '排队中', running: '执行中', success: '成功', failed: '失败', cancelled: '已取消', timeout: '超时' }[normalizeTaskStatus(status)]) || status || '-' }
function resolveTaskAlertType(status) { const s = normalizeTaskStatus(status); return s === 'success' ? 'success' : ['failed', 'cancelled', 'timeout'].includes(s) ? 'error' : s === 'running' ? 'warning' : 'info' }
function buildFilterParams() { return { email: normalizeCell(filterForm.email), subTier: normalizeFilterValue(filterForm.subTier), accountStatus: normalizeFilterValue(filterForm.accountStatus), sold: normalizeFilterValue(filterForm.sold) } }
function buildListQuery(options = {}) {
  const nextQuery = { ...route.query }
  MANAGED_QUERY_KEYS.forEach((key) => delete nextQuery[key])

  const email = normalizeCell(filterForm.email)
  const taskRootRunId = normalizeCell(
    options.taskRootRunId === undefined
      ? (latestAutoRegisterTask.value?.rootRunId && !isTerminalTaskStatus(latestAutoRegisterTask.value?.status)
          ? latestAutoRegisterTask.value.rootRunId
          : readQueryValue(route.query, TASK_ROUTE_QUERY_KEY))
      : options.taskRootRunId,
  )

  if (email) nextQuery.email = email
  if (!isFilterUnset(filterForm.subTier)) nextQuery.subTier = String(filterForm.subTier)
  if (!isFilterUnset(filterForm.accountStatus)) nextQuery.accountStatus = String(filterForm.accountStatus)
  if (!isFilterUnset(filterForm.sold)) nextQuery.sold = filterForm.sold ? '1' : '0'
  if (pager.current > 1) nextQuery.page = String(pager.current)
  if (pager.size !== DEFAULT_PAGE_SIZE) nextQuery.size = String(pager.size)
  if (taskRootRunId) nextQuery[TASK_ROUTE_QUERY_KEY] = taskRootRunId

  return nextQuery
}
function syncPageStateToQuery(options = {}) { router.replace({ query: buildListQuery(options) }).catch(() => {}) }
function applyListStateFromRoute() {
  const email = normalizeCell(readQueryValue(route.query, 'email'))
  const subTier = normalizeCell(readQueryValue(route.query, 'subTier'))
  const accountStatus = normalizeCell(readQueryValue(route.query, 'accountStatus'))

  filterForm.email = email || ''
  filterForm.subTier = subTierOptions.some((item) => item.value === subTier) ? subTier : undefined
  filterForm.accountStatus = statusOptions.some((item) => item.value === accountStatus) ? accountStatus : undefined
  filterForm.sold = parseQueryBoolean(readQueryValue(route.query, 'sold'))
  pager.current = parsePositiveInteger(readQueryValue(route.query, 'page'), 1)
  pager.size = parsePositiveInteger(readQueryValue(route.query, 'size'), DEFAULT_PAGE_SIZE)
}
function readPersistedTaskSnapshot() {
  try {
    const raw = sessionStorage.getItem(TASK_SNAPSHOT_STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    return parsed && typeof parsed === 'object' ? parsed : null
  } catch {
    return null
  }
}
function persistTaskSnapshot(task) {
  try {
    if (!task) sessionStorage.removeItem(TASK_SNAPSHOT_STORAGE_KEY)
    else sessionStorage.setItem(TASK_SNAPSHOT_STORAGE_KEY, JSON.stringify(task))
  } catch {
    // ignore persistence failure
  }
}
function setLatestAutoRegisterTaskSnapshot(task) {
  latestAutoRegisterTask.value = task ? { ...task } : null
  persistTaskSnapshot(latestAutoRegisterTask.value)
}
function stopTaskStatusPolling() { if (taskStatusPollTimer) { clearTimeout(taskStatusPollTimer); taskStatusPollTimer = null } }
function scheduleTaskStatusPoll(rootRunId, delay = TASK_STATUS_POLL_INTERVAL_MS) { stopTaskStatusPolling(); if (rootRunId) taskStatusPollTimer = setTimeout(() => pollTaskStatus(rootRunId), delay) }
async function refreshLatestAutoRegisterTask(rootRunId) {
  const statusResult = await getChatgptTaskStatusByRootRunId(rootRunId, { skipErrorMessage: true })
  if (!statusResult) return null
  const requestedCount = Number(statusResult.requestedCount || latestAutoRegisterTask.value?.requestedCount || 0) || undefined
  const mergedTask = { ...(latestAutoRegisterTask.value?.rootRunId === rootRunId ? latestAutoRegisterTask.value : { rootRunId }), ...statusResult, requestedCount }
  setLatestAutoRegisterTaskSnapshot(mergedTask)
  return mergedTask
}

async function pollTaskStatus(rootRunId) {
  if (!rootRunId) return
  try {
    const latestTask = await refreshLatestAutoRegisterTask(rootRunId)
    if (!latestTask) return scheduleTaskStatusPoll(rootRunId, TASK_STATUS_RETRY_INTERVAL_MS)
    if (latestAutoRegisterTask.value?.rootRunId !== rootRunId) return
    const normalizedStatus = normalizeTaskStatus(latestTask.status)
    if (!isTerminalTaskStatus(normalizedStatus)) return scheduleTaskStatusPoll(rootRunId)
    stopTaskStatusPolling()
    syncPageStateToQuery({ taskRootRunId: undefined })
    await fetchChatgptAccounts()
    if (normalizedStatus === 'success') return ElMessage.success('自动注册任务已完成，账号池列表已自动刷新')
    const errorText = latestTask.errorMessage ? `：${latestTask.errorMessage}` : ''
    ElMessage.warning(`自动注册任务已结束，状态 ${formatTaskStatus(normalizedStatus)}${errorText}，列表已自动刷新`)
  } catch {
    if (latestAutoRegisterTask.value?.rootRunId === rootRunId) scheduleTaskStatusPoll(rootRunId, TASK_STATUS_RETRY_INTERVAL_MS)
  }
}
async function restoreAutoRegisterTaskState() {
  const routeRootRunId = normalizeCell(readQueryValue(route.query, TASK_ROUTE_QUERY_KEY))
  const persistedTask = readPersistedTaskSnapshot()
  if (persistedTask) setLatestAutoRegisterTaskSnapshot(persistedTask)

  const activeRootRunId = routeRootRunId || (
    persistedTask?.rootRunId && !isTerminalTaskStatus(persistedTask.status)
      ? normalizeCell(persistedTask.rootRunId)
      : undefined
  )

  if (!activeRootRunId) return

  if (!persistedTask || persistedTask.rootRunId !== activeRootRunId) {
    setLatestAutoRegisterTaskSnapshot({ rootRunId: activeRootRunId, status: 'queued', requestedCount: persistedTask?.requestedCount })
  }
  if (!routeRootRunId) syncPageStateToQuery({ taskRootRunId: activeRootRunId })

  try {
    const latestTask = await refreshLatestAutoRegisterTask(activeRootRunId)
    if (!latestTask) return scheduleTaskStatusPoll(activeRootRunId, TASK_STATUS_RETRY_INTERVAL_MS)
    if (isTerminalTaskStatus(latestTask.status)) {
      syncPageStateToQuery({ taskRootRunId: undefined })
      return
    }
    scheduleTaskStatusPoll(activeRootRunId)
  } catch {
    if (latestAutoRegisterTask.value?.rootRunId === activeRootRunId) scheduleTaskStatusPoll(activeRootRunId, TASK_STATUS_RETRY_INTERVAL_MS)
  }
}

function applyFilterPreset(preset) {
  if (preset === 'all') {
    filterForm.email = ''
    filterForm.subTier = undefined
    filterForm.accountStatus = undefined
    filterForm.sold = undefined
  }
  if (preset === 'operable') {
    filterForm.email = ''
    filterForm.subTier = undefined
    filterForm.accountStatus = 'active'
    filterForm.sold = false
  }
  if (preset === 'sold') {
    filterForm.email = ''
    filterForm.subTier = undefined
    filterForm.accountStatus = undefined
    filterForm.sold = true
  }
  if (preset === 'free-stock') {
    filterForm.email = ''
    filterForm.subTier = 'free'
    filterForm.accountStatus = 'active'
    filterForm.sold = false
  }
  pager.current = 1
  syncPageStateToQuery()
  fetchChatgptAccounts()
}
function isPresetActive(preset) {
  const emailEmpty = !normalizeCell(filterForm.email)
  if (preset === 'all') return emailEmpty && isFilterUnset(filterForm.subTier) && isFilterUnset(filterForm.accountStatus) && isFilterUnset(filterForm.sold)
  if (preset === 'operable') return emailEmpty && isFilterUnset(filterForm.subTier) && filterForm.accountStatus === 'active' && filterForm.sold === false
  if (preset === 'sold') return emailEmpty && isFilterUnset(filterForm.subTier) && isFilterUnset(filterForm.accountStatus) && filterForm.sold === true
  if (preset === 'free-stock') return emailEmpty && filterForm.subTier === 'free' && filterForm.accountStatus === 'active' && filterForm.sold === false
  return false
}
function clearSingleFilter(key) { if (key === 'email') filterForm.email = ''; else filterForm[key] = undefined; pager.current = 1; syncPageStateToQuery(); fetchChatgptAccounts() }
function validateStatus(status, lineIndex) { const normalized = normalizeCell(status); if (!normalized) return undefined; if (!statusOptions.some((item) => item.value === normalized)) throw new Error(`第 ${lineIndex + 1} 行账号状态仅支持 active/locked/banned`); return normalized }
function validateSubTier(subTier, lineIndex) { const normalized = normalizeCell(subTier); if (!normalized) return undefined; if (!subTierOptions.some((item) => item.value === normalized)) throw new Error(`第 ${lineIndex + 1} 行订阅层级仅支持 free/plus/team/go`); return normalized }
function validateExpireDate(expireDate, lineIndex) { const normalized = normalizeCell(expireDate); if (!normalized) return undefined; if (!/^\d{4}-\d{2}-\d{2}$/.test(normalized)) throw new Error(`第 ${lineIndex + 1} 行到期日期必须是 yyyy-MM-dd`); return normalized }
function parseBatchImportText(rawText) {
  return rawText.split(/\r?\n/).map((line) => line.trim()).filter(Boolean).map((line, index) => {
    const cells = line.split(detectDelimiter(line)).map((cell) => cell.trim())
    if (cells.length < 2) throw new Error(`第 ${index + 1} 行字段不足，至少需要 email,password`)
    const [email, password, sessionToken, fourth, fifth, sixth, seventh] = cells
    if (!normalizeCell(email) || !normalizeCell(password)) throw new Error(`第 ${index + 1} 行存在必填字段为空（email/password）`)
    const useExtendedFormat = cells.length >= 7
    return {
      email,
      password,
      sessionToken: normalizeCell(sessionToken),
      totpSecret: useExtendedFormat ? normalizeCell(fourth) : undefined,
      subTier: validateSubTier(useExtendedFormat ? fifth : fourth, index),
      accountStatus: validateStatus(useExtendedFormat ? sixth : fifth, index),
      expireDate: validateExpireDate(useExtendedFormat ? seventh : sixth, index),
    }
  })
}

async function fetchChatgptAccounts() {
  loading.value = true
  try {
    const pageData = await pageChatgptAccounts({ current: pager.current, size: pager.size, ...buildFilterParams() })
    rows.value = pageData?.records || []
    selectedRows.value = []
    pager.total = Number(pageData?.total || 0)
    pager.current = Number(pageData?.current || pager.current)
    pager.size = Number(pageData?.size || pager.size)
    syncPageStateToQuery()
  } finally { loading.value = false }
}

function handleSearch() { pager.current = 1; syncPageStateToQuery(); fetchChatgptAccounts() }
function handleReset() { filterForm.email = ''; filterForm.subTier = undefined; filterForm.accountStatus = undefined; filterForm.sold = undefined; pager.current = 1; syncPageStateToQuery(); fetchChatgptAccounts() }
function handleCurrentChange(page) { pager.current = page; syncPageStateToQuery(); fetchChatgptAccounts() }
function handleSizeChange(size) { pager.current = 1; pager.size = size; syncPageStateToQuery(); fetchChatgptAccounts() }
function handleSelectionChange(selection) { selectedRows.value = selection || [] }
function isRowSelected(rowId) { return selectedRows.value.some((row) => row?.id === rowId) }
function handleRowClick(row) {
  if (!row?.id) return
  try {
    sessionStorage.setItem(`og-chatgpt-account-snapshot-${row.id}`, JSON.stringify(row))
  } catch {
    // ignore snapshot persistence failure
  }
  const serializedListQuery = serializeQueryObject(buildListQuery())
  const detailQuery = {}
  if (row?.email) detailQuery[DETAIL_EMAIL_QUERY_KEY] = row.email
  if (serializedListQuery) detailQuery[LIST_RETURN_QUERY_KEY] = serializedListQuery
  router.push({
    path: `/chatgpt/accounts/${row.id}`,
    query: Object.keys(detailQuery).length ? detailQuery : undefined,
  })
}
function handleMobileRowSelection(row, checked) {
  if (!row?.id) return
  if (tableRef.value?.toggleRowSelection) {
    tableRef.value.toggleRowSelection(row, checked)
    return
  }
  selectedRows.value = checked
    ? [...selectedRows.value.filter((item) => item?.id !== row.id), row]
    : selectedRows.value.filter((item) => item?.id !== row.id)
}
function clearCurrentSelection() { tableRef.value?.clearSelection?.(); selectedRows.value = [] }
function resetAccountForm() { Object.assign(accountForm, { id: null, email: '', password: '', sessionToken: '', totpSecret: '', subTier: 'free', accountStatus: 'active', sold: false, expireDate: '' }); originalAccount.value = null }
function openCreateDialog() { accountDialogMode.value = 'create'; resetAccountForm(); accountDialogVisible.value = true; nextTick(() => accountFormRef.value?.clearValidate()) }
function openAutoRegisterDialog() { autoRegisterForm.signupCount = 1; autoRegisterDialogVisible.value = true; nextTick(() => autoRegisterFormRef.value?.clearValidate()) }
function openEditDialog(row) {
  if (!row?.id) return
  accountDialogMode.value = 'edit'
  Object.assign(accountForm, { id: row.id, email: row.email || '', password: '', sessionToken: row.sessionToken || '', totpSecret: row.totpSecret || '', subTier: row.subTier || 'free', accountStatus: row.accountStatus || 'active', sold: Boolean(row.sold), expireDate: row.expireDate || '' })
  originalAccount.value = { email: row.email || '', sessionToken: row.sessionToken || '', totpSecret: row.totpSecret || '', subTier: row.subTier || '', accountStatus: row.accountStatus || '', sold: Boolean(row.sold), expireDate: row.expireDate || '' }
  accountDialogVisible.value = true
  nextTick(() => accountFormRef.value?.clearValidate())
}

function buildCreatePayload() { return { email: normalizeCell(accountForm.email), password: normalizeCell(accountForm.password), sessionToken: normalizeCell(accountForm.sessionToken), totpSecret: normalizeCell(accountForm.totpSecret), subTier: normalizeCell(accountForm.subTier), accountStatus: normalizeCell(accountForm.accountStatus), sold: Boolean(accountForm.sold), expireDate: accountForm.expireDate || undefined } }
function buildUpdatePayload() {
  const payload = {}
  const original = originalAccount.value || {}
  const currentEmail = normalizeCell(accountForm.email) || ''
  const currentPassword = normalizeCell(accountForm.password)
  const currentToken = normalizeCell(accountForm.sessionToken) || ''
  const currentTotpSecret = normalizeCell(accountForm.totpSecret) || ''
  const currentSubTier = normalizeCell(accountForm.subTier) || ''
  const currentStatus = normalizeCell(accountForm.accountStatus) || ''
  const currentSold = Boolean(accountForm.sold)
  const currentExpireDate = accountForm.expireDate || ''
  if (currentEmail && currentEmail !== (original.email || '')) payload.email = currentEmail
  if (currentPassword) payload.password = currentPassword
  if (currentToken !== (original.sessionToken || '')) payload.sessionToken = currentToken
  if (currentTotpSecret !== (original.totpSecret || '')) payload.totpSecret = currentTotpSecret
  if (currentSubTier && currentSubTier !== (original.subTier || '')) payload.subTier = currentSubTier
  if (currentStatus && currentStatus !== (original.accountStatus || '')) payload.accountStatus = currentStatus
  if (currentSold !== Boolean(original.sold)) payload.sold = currentSold
  if (currentExpireDate && currentExpireDate !== (original.expireDate || '')) payload.expireDate = currentExpireDate
  return payload
}

async function handleSaveAccount() {
  await accountFormRef.value?.validate()
  savingAccount.value = true
  try {
    if (accountDialogMode.value === 'create') { await createChatgptAccount(buildCreatePayload()); ElMessage.success('ChatGPT 账号新增成功'); pager.current = 1 }
    else {
      const payload = buildUpdatePayload()
      if (!Object.keys(payload).length) return ElMessage.info('未检测到变更内容')
      await updateChatgptAccount(accountForm.id, payload)
      ElMessage.success('ChatGPT 账号更新成功')
    }
    accountDialogVisible.value = false
    await fetchChatgptAccounts()
  } finally { savingAccount.value = false }
}

async function handleQuickSoldToggle(row) {
  if (!row?.id) return
  const nextSold = !Boolean(row.sold)
  try {
    await ElMessageBox.confirm(
      `确认将账号「${row.email || row.id}」改为「${formatSoldStatus(nextSold)}」吗？`,
      '出售状态确认',
      {
        type: nextSold ? 'warning' : 'info',
        confirmButtonText: nextSold ? '确认标记已出售' : '确认撤销售出',
        cancelButtonText: '取消',
      },
    )
  } catch {
    return
  }
  rowSoldUpdatingId.value = row.id
  try {
    await updateChatgptAccount(row.id, { sold: nextSold })
    row.sold = nextSold
    ElMessage.success(nextSold ? '已标记为已出售' : '已改为未出售')
  } finally {
    rowSoldUpdatingId.value = null
  }
}

async function handleDelete(row) {
  if (!row?.id) return
  try { await ElMessageBox.confirm(`确认删除 ChatGPT 账号「${row.email || row.id}」吗？`, '危险操作确认', { type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消', confirmButtonClass: 'el-button--danger' }) } catch { return }
  deletingId.value = row.id
  try { await deleteChatgptAccount(row.id); ElMessage.success('账号已删除'); if (rows.value.length === 1 && pager.current > 1) pager.current -= 1; await fetchChatgptAccounts() } finally { deletingId.value = null }
}

async function handleBatchCreateSubmit() {
  if (!batchRawText.value.trim()) return ElMessage.warning('请先粘贴批量数据')
  let payload = []
  try { payload = parseBatchImportText(batchRawText.value) } catch (error) { return ElMessage.error(error.message || '批量数据格式不正确') }
  batchCreating.value = true
  try { const successCount = await createChatgptAccountsBatch(payload); ElMessage.success(`批量新增完成，成功 ${successCount ?? payload.length} 条`); batchDialogVisible.value = false; batchRawText.value = ''; pager.current = 1; await fetchChatgptAccounts() } finally { batchCreating.value = false }
}

async function handleAutoRegisterSubmit() {
  await autoRegisterFormRef.value?.validate()
  autoRegisterSubmitting.value = true
  try {
    const payload = { signupCount: Number(autoRegisterForm.signupCount) }
    const dispatchResult = await dispatchChatgptBatchRegisterTask(payload)
    setLatestAutoRegisterTaskSnapshot(dispatchResult)
    autoRegisterDialogVisible.value = false
    ElMessage.success(`自动注册任务已投递，数量 ${dispatchResult?.requestedCount || payload.signupCount}`)
    syncPageStateToQuery({ taskRootRunId: dispatchResult?.rootRunId })
    scheduleTaskStatusPoll(dispatchResult?.rootRunId, 1200)
  } finally { autoRegisterSubmitting.value = false }
}

async function handleBatchStatusUpdate() {
  if (!hasSelection.value) return ElMessage.warning('请先选择需要修改状态的账号')
  statusBatchLoading.value = true
  try { const updatedCount = await batchUpdateChatgptAccountStatus({ ids: selectedIds.value, accountStatus: statusBatchValue.value }); ElMessage.success(`批量状态更新成功，共 ${updatedCount ?? selectedIds.value.length} 条`); await fetchChatgptAccounts() } finally { statusBatchLoading.value = false }
}

async function handleBatchSoldUpdate() {
  if (!hasSelection.value) return ElMessage.warning('请先选择需要修改出售状态的账号')
  try {
    await ElMessageBox.confirm(
      `确认将已选 ${selectedIds.value.length} 个账号批量改为「${formatSoldStatus(soldBatchValue.value)}」吗？`,
      '批量出售状态确认',
      {
        type: soldBatchValue.value ? 'warning' : 'info',
        confirmButtonText: '确认执行',
        cancelButtonText: '取消',
      },
    )
  } catch {
    return
  }
  soldBatchLoading.value = true
  try { const updatedCount = await batchUpdateChatgptAccountSold({ ids: selectedIds.value, sold: soldBatchValue.value }); ElMessage.success(`批量出售状态更新成功，共 ${updatedCount ?? selectedIds.value.length} 条`); await fetchChatgptAccounts() } finally { soldBatchLoading.value = false }
}

async function handleBatchDelete() {
  if (!hasSelection.value) return ElMessage.warning('请先选择需要删除的账号')
  try { await ElMessageBox.confirm(`确认批量删除已选 ${selectedIds.value.length} 个 ChatGPT 账号吗？`, '危险操作确认', { type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消', confirmButtonClass: 'el-button--danger' }) } catch { return }
  batchDeleting.value = true
  try { const deletedCount = await batchDeleteChatgptAccounts(selectedIds.value); ElMessage.success(`批量删除成功，共 ${deletedCount ?? selectedIds.value.length} 条`); if (rows.value.length === selectedIds.value.length && pager.current > 1) pager.current -= 1; await fetchChatgptAccounts() } finally { batchDeleting.value = false }
}

async function handleExportAccounts() {
  const exportRows = selectedRows.value.length
    ? [...selectedRows.value]
    : await fetchAllPagedRecords(pageChatgptAccounts, buildFilterParams())

  if (!exportRows.length) {
    ElMessage.warning('没有可导出的 ChatGPT 账号')
    return
  }

  const content = exportRows.map(formatChatgptAccountLine).join('\r\n')
  downloadTextFile({
    filename: buildExportFilename('chatgpt-accounts'),
    content,
  })
  ElMessage.success(`已导出 ${exportRows.length} 条 ChatGPT 账号`)
}

onMounted(() => {
  applyListStateFromRoute()
  fetchChatgptAccounts()
  restoreAutoRegisterTaskState()
})
onBeforeUnmount(stopTaskStatusPolling)
</script>

<template>
  <div class="page-shell">
    <section class="hero-panel">
      <div class="hero-copy">
        <span class="eyebrow">ChatGPT Asset Console</span>
        <h1>账号池控制台</h1>
        <p>把筛选、库存判断、批量改动、自动注册和详情跳转收成一套操作流，让这一页真正承担“控制台”的角色。</p>
        <div class="hero-actions">
          <el-button type="primary" :icon="Plus" @click="openCreateDialog">新增账号</el-button>
          <el-button type="success" :icon="Plus" @click="openAutoRegisterDialog">自动注册</el-button>
          <el-button :icon="Upload" @click="batchDialogVisible = true">批量新增</el-button>
          <el-button text :icon="Refresh" @click="fetchChatgptAccounts">刷新列表</el-button>
        </div>

        <div class="hero-context-grid">
          <article class="hero-context-card">
            <span>当前工作区</span>
            <strong>{{ resultSummary }}</strong>
            <p>筛选条件、页码和进行中的自动注册任务都保持可恢复，刷新页面不会直接丢工作上下文。</p>
          </article>
          <article class="hero-context-card hero-context-card--filters">
            <span>筛选快照</span>
            <div v-if="activeFilterTags.length" class="hero-filter-chips">
              <el-tag v-for="tag in activeFilterTags" :key="tag.key" closable effect="plain" @close="clearSingleFilter(tag.key)">
                {{ tag.label }} · {{ tag.value }}
              </el-tag>
            </div>
            <p v-else>当前未设置筛选条件，处于全量库存视角。</p>
          </article>
        </div>
      </div>
      <div class="stats-grid">
        <article v-for="item in dashboardStats" :key="item.label" class="stat-card">
          <span>{{ item.label }}</span>
          <strong>{{ item.value }}</strong>
          <p>{{ item.note }}</p>
        </article>
      </div>
    </section>

    <section class="ops-grid">
      <section class="surface-card filter-card">
        <div class="panel-head">
          <div>
            <h2>筛选工作台</h2>
            <p>筛选改成提交式动作，再配合快捷视图和 URL 持久化，避免状态切换时列表频繁抖动。</p>
          </div>
          <div class="panel-actions">
            <el-button type="primary" :icon="Search" @click="handleSearch">执行查询</el-button>
            <el-button :icon="Refresh" @click="handleReset">清空条件</el-button>
          </div>
        </div>

        <form class="filter-form" @submit.prevent="handleSearch">
          <div class="filter-grid">
            <div class="filter-field filter-field--wide">
              <label class="field-label" for="chatgpt-filter-email">邮箱关键字</label>
              <el-input id="chatgpt-filter-email" v-model="filterForm.email" name="emailFilter" aria-label="按邮箱关键字筛选 ChatGPT 账号" clearable placeholder="输入邮箱关键字，支持回车查询" @keyup.enter="handleSearch" />
            </div>
            <div class="filter-field">
              <label class="field-label" for="chatgpt-filter-status">账号状态</label>
              <el-select id="chatgpt-filter-status" v-model="filterForm.accountStatus" name="accountStatusFilter" aria-label="按账号状态筛选 ChatGPT 账号" clearable placeholder="全部状态">
                <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
              </el-select>
            </div>
            <div class="filter-field">
              <label class="field-label" for="chatgpt-filter-tier">订阅层级</label>
              <el-select id="chatgpt-filter-tier" v-model="filterForm.subTier" name="subTierFilter" aria-label="按订阅层级筛选 ChatGPT 账号" clearable placeholder="全部层级">
                <el-option v-for="item in subTierOptions" :key="item.value" :label="item.label" :value="item.value" />
              </el-select>
            </div>
            <div class="filter-field">
              <label class="field-label" for="chatgpt-filter-sold">出售状态</label>
              <el-select id="chatgpt-filter-sold" v-model="filterForm.sold" name="soldFilter" aria-label="按出售状态筛选 ChatGPT 账号" clearable placeholder="全部出售状态">
                <el-option v-for="item in soldOptions" :key="String(item.value)" :label="item.label" :value="item.value" />
              </el-select>
            </div>
          </div>
        </form>

        <div class="preset-row">
          <span>快捷视图</span>
          <div class="preset-buttons">
            <el-button :type="isPresetActive('all') ? 'primary' : 'default'" :plain="!isPresetActive('all')" @click="applyFilterPreset('all')">全部库存</el-button>
            <el-button :type="isPresetActive('operable') ? 'primary' : 'default'" :plain="!isPresetActive('operable')" @click="applyFilterPreset('operable')">可运营库存</el-button>
            <el-button :type="isPresetActive('sold') ? 'primary' : 'default'" :plain="!isPresetActive('sold')" @click="applyFilterPreset('sold')">已出售</el-button>
            <el-button :type="isPresetActive('free-stock') ? 'primary' : 'default'" :plain="!isPresetActive('free-stock')" @click="applyFilterPreset('free-stock')">Free 库存</el-button>
          </div>
        </div>

        <div class="filter-summary filter-summary--rich">
          <div>
            <strong>{{ resultSummary }}</strong>
            <span class="subtle-text">支持按邮箱、状态、层级和出售状态组合查询，并保留浏览上下文。</span>
          </div>
          <div v-if="activeFilterTags.length" class="active-filters">
            <span class="active-title">当前筛选</span>
            <el-tag v-for="tag in activeFilterTags" :key="tag.key" closable effect="plain" @close="clearSingleFilter(tag.key)">{{ tag.label }}：{{ tag.value }}</el-tag>
          </div>
        </div>

        <div class="inventory-board">
          <div class="inventory-board__head">
            <strong>库存观察板</strong>
            <span>基于当前页结果快速判断哪些账号更适合接管、补料、排查或标记出库。</span>
          </div>
          <div class="inventory-lane-grid">
            <article v-for="item in inventoryLanes" :key="item.key" class="inventory-lane-card" :class="`inventory-lane-card--${item.tone}`">
              <span>{{ item.label }}</span>
              <strong>{{ item.value }}</strong>
              <p>{{ item.note }}</p>
            </article>
          </div>
        </div>
      </section>

      <div class="ops-side">
        <section class="surface-card batch-card" :class="{ 'batch-card--active': hasSelection }">
          <div class="panel-head">
            <div>
              <h2>批量工作台</h2>
              <p>高频动作改成连续命令条，不需要在表格和弹窗之间反复跳。</p>
            </div>
          </div>

          <div class="batch-state batch-state--compact">
            <strong>{{ hasSelection ? `已选 ${selectedIds.length} 条账号` : '先勾选账号，再启动批量动作' }}</strong>
            <p>{{ hasSelection ? '建议先改状态或出售标记，再做导出或删除。' : '没有勾选时，仍然可以直接导出当前筛选结果。' }}</p>
            <div v-if="selectionInsights.length" class="selection-insights">
              <span v-for="item in selectionInsights" :key="item.label" class="selection-pill">{{ item.label }} {{ item.value }}</span>
            </div>
          </div>

          <div class="batch-toolbar">
            <div class="batch-row">
              <span class="batch-label">批量状态</span>
              <el-select v-model="statusBatchValue" placeholder="批量状态" :disabled="!hasSelection">
                <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
              </el-select>
              <el-button :loading="statusBatchLoading" :disabled="!hasSelection" @click="handleBatchStatusUpdate">应用状态</el-button>
            </div>

            <div class="batch-row">
              <span class="batch-label">批量出售</span>
              <el-select v-model="soldBatchValue" placeholder="批量出售" :disabled="!hasSelection">
                <el-option v-for="item in soldOptions" :key="String(item.value)" :label="item.label" :value="item.value" />
              </el-select>
              <el-button :loading="soldBatchLoading" :disabled="!hasSelection" @click="handleBatchSoldUpdate">应用出售状态</el-button>
            </div>

            <div class="batch-row batch-row--actions">
              <span class="batch-label">其他操作</span>
              <div class="batch-actions">
                <el-button type="success" plain :icon="Download" @click="handleExportAccounts">{{ exportButtonLabel }}</el-button>
                <el-button plain :disabled="!hasSelection" @click="clearCurrentSelection">清空勾选</el-button>
                <el-button type="danger" plain :icon="Delete" :loading="batchDeleting" :disabled="!hasSelection" @click="handleBatchDelete">批量删除</el-button>
              </div>
            </div>
          </div>
        </section>

        <section class="surface-card task-card">
          <div class="panel-head">
            <div>
              <h2>自动注册队列</h2>
              <p>任务反馈被固定在侧轨，窗口缩放时仍然优先保留可见，不再埋到表格下面。</p>
            </div>
            <div class="panel-actions">
              <el-button type="success" :icon="Plus" @click="openAutoRegisterDialog">新建注册任务</el-button>
            </div>
          </div>
          <el-alert v-if="latestAutoRegisterTask" :type="latestAutoRegisterTaskAlertType" :closable="false" class="task-alert" show-icon>
            <template #title>{{ latestAutoRegisterTaskTitle }}</template>
            <template #default>
              <div class="task-meta">
                <span>数量：{{ latestAutoRegisterTask.requestedCount || '-' }}</span>
                <span>状态：{{ latestAutoRegisterTaskStatusLabel }}</span>
                <span v-if="latestAutoRegisterTaskProgressLabel">进度：{{ latestAutoRegisterTaskProgressLabel }}</span>
                <span>TaskRunId：{{ latestAutoRegisterTask.taskRunId || '-' }}</span>
                <span>RootRunId：{{ latestAutoRegisterTask.rootRunId || '-' }}</span>
                <span v-if="latestAutoRegisterTask.lastCheckpoint">检查点：{{ latestAutoRegisterTask.lastCheckpoint }}</span>
                <span v-if="latestAutoRegisterTask.errorMessage">错误信息：{{ latestAutoRegisterTask.errorMessage }}</span>
              </div>
            </template>
          </el-alert>
          <div v-else class="batch-state">
            <strong>当前没有最近任务</strong>
            <p>从这里发起自动注册后，队列状态会固定留在侧轨；刷新页面后也会优先恢复进行中的任务。</p>
          </div>
        </section>

      </div>
    </section>

    <section class="surface-card">
      <div class="panel-head">
        <div>
          <h2>账号矩阵</h2>
          <p>桌面端优先保留高密度扫描效率，窗口继续缩小时再切换成更安全的卡片交互。</p>
        </div>
        <div class="panel-actions table-tools">
          <span class="selection-chip">{{ resultSummary }}</span>
          <span class="subtle-text">当前页 {{ rows.length }} 条</span>
        </div>
      </div>
      <div class="table-shell table-shell--desktop">
        <el-table ref="tableRef" :data="rows" v-loading="loading" stripe @selection-change="handleSelectionChange">
          <el-table-column type="selection" width="50" />
          <el-table-column label="账号" min-width="240">
            <template #default="{ row }">
              <div class="account-cell">
                <el-button link class="cell-link" @click.stop="handleRowClick(row)">{{ row.email }}</el-button>
                <div class="account-meta"><span>ID {{ toNullableText(row.id) }}</span><span>更新于 {{ toNullableText(row.updatedAt) }}</span></div>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="材料完整度" min-width="220">
            <template #default="{ row }">
              <div class="tag-stack">
                <el-tag :type="row.password ? 'success' : 'info'" effect="plain">{{ row.password ? '已录密码' : '缺密码' }}</el-tag>
                <el-tag :type="row.totpSecret ? 'success' : 'warning'" effect="plain">{{ row.totpSecret ? '2FA已配' : '缺2FA' }}</el-tag>
                <el-tag :type="row.sessionToken ? 'primary' : 'info'" effect="plain">{{ row.sessionToken ? 'Session可用' : '缺Session' }}</el-tag>
              </div>
              <div class="account-meta"><span>到期 {{ toNullableText(row.expireDate) }}</span></div>
            </template>
          </el-table-column>
          <el-table-column label="层级 / 状态 / 出售" min-width="200">
            <template #default="{ row }">
              <div class="tag-stack">
                <el-tag :type="resolveTierTag(row.subTier)" effect="plain">{{ formatSubTier(row.subTier) }}</el-tag>
                <el-tag :type="resolveStatusTag(row.accountStatus)" effect="light">{{ formatAccountStatus(row.accountStatus) }}</el-tag>
                <el-tag :type="resolveSoldTag(row.sold)" effect="plain">{{ formatSoldStatus(row.sold) }}</el-tag>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="220" fixed="right">
            <template #default="{ row }">
              <div class="row-actions">
                <el-button link :icon="View" @click.stop="handleRowClick(row)">详情</el-button>
                <el-button link :icon="EditPen" @click.stop="openEditDialog(row)">编辑</el-button>
                <el-button link :loading="rowSoldUpdatingId === row.id" @click.stop="handleQuickSoldToggle(row)">{{ row.sold ? '撤销售出' : '标记售出' }}</el-button>
                <el-button link type="danger" :icon="Delete" :loading="deletingId === row.id" @click.stop="handleDelete(row)">删除</el-button>
              </div>
            </template>
          </el-table-column>
          <template #empty>
            <div class="empty-state"><strong>当前没有匹配账号</strong><p>可以切换快捷视图、清空筛选，或直接新增 / 自动注册账号。</p></div>
          </template>
        </el-table>
      </div>
      <div v-if="rows.length" class="mobile-card-list">
        <article v-for="row in rows" :key="row.id" class="mobile-account-card">
          <div class="mobile-account-card__head">
            <el-checkbox :model-value="isRowSelected(row.id)" @change="(checked) => handleMobileRowSelection(row, checked)" />
            <div class="mobile-account-card__identity">
              <el-button link class="cell-link mobile-account-card__email" @click.stop="handleRowClick(row)">{{ row.email }}</el-button>
              <span>ID {{ toNullableText(row.id) }} · 更新于 {{ toNullableText(row.updatedAt) }}</span>
            </div>
            <el-button link :icon="View" class="mobile-account-card__view" @click.stop="handleRowClick(row)">详情</el-button>
          </div>

          <div class="mobile-account-card__tags">
            <el-tag :type="resolveTierTag(row.subTier)" effect="plain">{{ formatSubTier(row.subTier) }}</el-tag>
            <el-tag :type="resolveStatusTag(row.accountStatus)" effect="light">{{ formatAccountStatus(row.accountStatus) }}</el-tag>
            <el-tag :type="resolveSoldTag(row.sold)" effect="plain">{{ formatSoldStatus(row.sold) }}</el-tag>
          </div>

          <div class="mobile-account-card__materials">
            <span class="material-pill" :class="{ 'material-pill--ready': row.password }">{{ row.password ? '已录密码' : '缺密码' }}</span>
            <span class="material-pill" :class="{ 'material-pill--ready': row.totpSecret }">{{ row.totpSecret ? '2FA已配' : '缺2FA' }}</span>
            <span class="material-pill" :class="{ 'material-pill--ready': row.sessionToken }">{{ row.sessionToken ? 'Session可用' : '缺Session' }}</span>
          </div>

          <div class="mobile-account-card__meta">
            <span>到期 {{ toNullableText(row.expireDate) }}</span>
            <span>{{ row.sold ? '已出库' : '库存中' }}</span>
          </div>

          <div class="mobile-account-card__actions">
            <el-button plain size="small" :icon="EditPen" @click.stop="openEditDialog(row)">编辑</el-button>
            <el-button plain size="small" :loading="rowSoldUpdatingId === row.id" @click.stop="handleQuickSoldToggle(row)">{{ row.sold ? '撤销售出' : '标记售出' }}</el-button>
            <el-button plain size="small" :icon="View" @click.stop="handleRowClick(row)">查看详情</el-button>
            <el-button type="danger" plain size="small" :icon="Delete" :loading="deletingId === row.id" @click.stop="handleDelete(row)">删除</el-button>
          </div>
        </article>
      </div>
      <div v-else class="mobile-card-list">
        <div class="empty-state"><strong>当前没有匹配账号</strong><p>可以切换快捷视图、清空筛选，或直接新增 / 自动注册账号。</p></div>
      </div>
      <div class="table-foot">
        <span class="subtle-text">{{ resultSummary }}，当前页 {{ rows.length }} 条</span>
        <el-pagination v-model:current-page="pager.current" v-model:page-size="pager.size" background layout="total, sizes, prev, pager, next" :page-sizes="[10, 20, 50, 100]" :total="pager.total" @current-change="handleCurrentChange" @size-change="handleSizeChange" />
      </div>
    </section>

    <el-dialog v-model="accountDialogVisible" :title="accountDialogMode === 'create' ? '新增 ChatGPT 账号' : '编辑 ChatGPT 账号'" width="min(760px, calc(100vw - 24px))" destroy-on-close>
        <el-form ref="accountFormRef" :model="accountForm" :rules="accountRules" label-position="top" class="dialog-form">
        <div class="form-grid">
          <el-form-item label="账号邮箱" prop="email"><el-input v-model="accountForm.email" name="chatgptEmail" autocomplete="username" placeholder="name@example.com" /></el-form-item>
          <el-form-item label="登录密码" prop="password"><el-input v-model="accountForm.password" name="chatgptPassword" autocomplete="new-password" type="password" show-password :placeholder="accountDialogMode === 'create' ? '请输入密码' : '留空表示不修改密码'" /></el-form-item>
          <el-form-item label="2FA / TOTP 密钥" prop="totpSecret"><el-input v-model="accountForm.totpSecret" name="chatgptTotpSecret" autocomplete="off" placeholder="可选，绑定后可保存" /></el-form-item>
          <el-form-item label="订阅层级"><el-select v-model="accountForm.subTier"><el-option v-for="item in subTierOptions" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item>
          <el-form-item label="账号状态"><el-select v-model="accountForm.accountStatus"><el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item>
          <el-form-item label="是否已出售"><el-switch v-model="accountForm.sold" inline-prompt active-text="是" inactive-text="否" /></el-form-item>
          <el-form-item label="到期日期"><el-date-picker v-model="accountForm.expireDate" type="date" value-format="YYYY-MM-DD" placeholder="可选" /></el-form-item>
          <el-form-item label="SessionToken" class="span-2"><el-input v-model="accountForm.sessionToken" name="chatgptSessionToken" autocomplete="off" type="textarea" :rows="3" placeholder="可选，支持留空" /></el-form-item>
        </div>
      </el-form>
      <template #footer><div class="dialog-footer"><el-button @click="accountDialogVisible = false">取消</el-button><el-button type="primary" :loading="savingAccount" @click="handleSaveAccount">保存</el-button></div></template>
    </el-dialog>

    <el-dialog v-model="batchDialogVisible" title="批量新增 ChatGPT 账号" width="min(760px, calc(100vw - 24px))" destroy-on-close>
      <div class="dialog-stack">
        <el-alert type="info" show-icon :closable="false"><template #title>每行 1 条，支持 `---- / 逗号 / 竖线 / Tab` 分隔。新格式：`email,password,sessionToken,totpSecret,subTier,accountStatus,expireDate`；旧格式不带 `totpSecret` 也兼容。</template></el-alert>
        <el-input v-model="batchRawText" type="textarea" :rows="10" placeholder="alice@example.com,Pass@123,session_xxx,JBSWY3DPEHPK3PXP,free,active,2026-12-31&#10;bob@example.com,Pass@456,session_xxx,team,active,2026-12-31" />
      </div>
      <template #footer><div class="dialog-footer"><el-button @click="batchDialogVisible = false">取消</el-button><el-button @click="batchRawText = ''">清空</el-button><el-button type="primary" :loading="batchCreating" @click="handleBatchCreateSubmit">开始新增</el-button></div></template>
    </el-dialog>

    <el-dialog v-model="autoRegisterDialogVisible" title="自动注册 ChatGPT 账号" width="min(500px, calc(100vw - 24px))" destroy-on-close>
      <el-form ref="autoRegisterFormRef" :model="autoRegisterForm" :rules="autoRegisterRules" label-position="top">
        <el-form-item label="注册数量" prop="signupCount"><el-input-number v-model="autoRegisterForm.signupCount" :min="1" :step="1" step-strictly /></el-form-item>
        <div class="subtle-text">任务会投递到 worker，由浏览器自动注册账号并写入账号池。投递成功后，页面会自动轮询状态并在结束后刷新列表。</div>
      </el-form>
      <template #footer><div class="dialog-footer"><el-button @click="autoRegisterDialogVisible = false">取消</el-button><el-button type="primary" :loading="autoRegisterSubmitting" @click="handleAutoRegisterSubmit">开始投递</el-button></div></template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page-shell{display:grid;gap:18px;max-width:min(1680px,calc(100vw - 24px));margin:0 auto}
.hero-panel,.surface-card{border-radius:22px}
.hero-panel{display:grid;grid-template-columns:minmax(0,1.12fr) clamp(320px,34vw,460px);gap:20px;padding:28px;background:radial-gradient(circle at top right,rgba(45,212,191,.18),transparent 32%),radial-gradient(circle at 18% 18%,rgba(249,115,22,.18),transparent 28%),linear-gradient(140deg,#111827 0%,#172033 44%,#1f2937 100%);color:#f8fafc;border:1px solid rgba(255,255,255,.08);box-shadow:0 24px 64px rgba(15,23,42,.22)}
.eyebrow{display:inline-flex;padding:6px 10px;border-radius:999px;background:rgba(255,255,255,.09);color:rgba(255,255,255,.72);font-size:.74rem;letter-spacing:.06em;text-transform:uppercase}
.hero-copy h1{margin:12px 0 0;font-family:'Space Grotesk',sans-serif;font-size:2rem;line-height:1.05}
.hero-copy p{margin:12px 0 0;max-width:620px;color:rgba(226,232,240,.84);line-height:1.7}
.hero-actions,.panel-actions,.row-actions,.dialog-footer{display:flex;flex-wrap:wrap;gap:10px}
.hero-actions{margin-top:22px}
.hero-context-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin-top:18px}
.hero-context-card{display:grid;gap:10px;padding:16px 18px;border-radius:20px;background:linear-gradient(180deg,rgba(255,255,255,.12),rgba(255,255,255,.05));border:1px solid rgba(255,255,255,.12)}
.hero-context-card span{color:rgba(226,232,240,.66);font-size:.78rem;letter-spacing:.08em;text-transform:uppercase}
.hero-context-card strong{font-family:'Fira Code','Space Grotesk',monospace;font-size:1.1rem;color:#fff}
.hero-context-card p{margin:0;color:rgba(226,232,240,.74);font-size:.84rem;line-height:1.6}
.hero-filter-chips{display:flex;flex-wrap:wrap;gap:8px}
.hero-filter-chips :deep(.el-tag){border-color:rgba(255,255,255,.18);background:rgba(255,255,255,.08);color:#f8fafc}
.stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px}
.stat-card{padding:16px;border-radius:18px;background:linear-gradient(180deg,rgba(255,255,255,.14),rgba(255,255,255,.06));border:1px solid rgba(255,255,255,.14)}
.stat-card span,.subtle-text{color:#64748b;font-size:.82rem}
.stat-card span{color:rgba(226,232,240,.8)}
.stat-card strong{display:block;margin-top:8px;font-family:'Fira Code','Space Grotesk',monospace;font-size:1.52rem;color:#fff}
.stat-card p{margin:8px 0 0;color:rgba(226,232,240,.72);font-size:.82rem;line-height:1.5}
.surface-card{padding:22px;border:1px solid rgba(148,163,184,.18);background:radial-gradient(circle at top right,rgba(45,212,191,.08),transparent 24%),linear-gradient(180deg,rgba(255,255,255,.96),rgba(248,250,252,.96));box-shadow:0 18px 48px rgba(15,23,42,.08)}
.ops-grid{display:grid;grid-template-columns:minmax(0,1fr) clamp(320px,31vw,420px);gap:18px}
.task-alert{border-radius:18px}
.task-meta{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:8px 16px;margin-top:6px;word-break:break-all;font-size:.84rem}
.panel-head{display:flex;align-items:flex-start;justify-content:space-between;gap:16px;margin-bottom:18px}
.panel-head h2{margin:0;font-family:'Space Grotesk',sans-serif;font-size:1.1rem;color:#0f172a}
.panel-head p{margin:6px 0 0;color:#475569;line-height:1.6}
.filter-card,.batch-card,.task-card{display:grid;align-content:start}
.ops-side{display:grid;gap:18px}
.filter-form,.filter-field{display:grid;gap:10px}
.filter-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}
.filter-field--wide{grid-column:span 2}
.field-label{color:#475569;font-size:.8rem;font-weight:700}
.preset-row{display:grid;grid-template-columns:72px 1fr;gap:12px;align-items:start;margin-top:16px}
.preset-row>span,.active-title{padding-top:8px;color:#475569;font-size:.84rem;font-weight:700}
.preset-buttons,.active-filters,.tag-stack,.account-meta,.table-tools,.batch-actions{display:flex;flex-wrap:wrap;gap:8px}
.filter-summary{display:grid;gap:6px;margin-top:16px}
.filter-summary--rich{grid-template-columns:minmax(0,.9fr) minmax(0,1.1fr);gap:14px;align-items:start;padding-top:14px;border-top:1px solid rgba(148,163,184,.18)}
.filter-summary strong{color:#0f172a;font-size:1rem}
.active-filters{display:grid;gap:8px;align-items:flex-start}
.inventory-board{display:grid;gap:14px;margin-top:18px;padding:16px;border-radius:20px;background:rgba(15,23,42,.03);border:1px solid rgba(148,163,184,.18)}
.inventory-board__head{display:grid;gap:6px}
.inventory-board__head strong{color:#0f172a;font-size:1rem}
.inventory-board__head span{color:#64748b;font-size:.82rem;line-height:1.65}
.inventory-lane-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.inventory-lane-card{display:grid;gap:8px;padding:14px 16px;border-radius:18px;border:1px solid rgba(148,163,184,.18);background:linear-gradient(180deg,#fff,#f8fafc)}
.inventory-lane-card span{color:#64748b;font-size:.76rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase}
.inventory-lane-card strong{color:#0f172a;font-family:'Manrope','Space Grotesk',sans-serif;font-size:1.18rem;letter-spacing:-.03em}
.inventory-lane-card p{margin:0;color:#475569;font-size:.8rem;line-height:1.62}
.inventory-lane-card--success{background:linear-gradient(180deg,rgba(16,185,129,.12),rgba(255,255,255,.96));border-color:rgba(16,185,129,.18)}
.inventory-lane-card--warning{background:linear-gradient(180deg,rgba(245,158,11,.14),rgba(255,255,255,.96));border-color:rgba(245,158,11,.18)}
.inventory-lane-card--danger{background:linear-gradient(180deg,rgba(239,68,68,.12),rgba(255,255,255,.96));border-color:rgba(239,68,68,.18)}
.inventory-lane-card--neutral{background:linear-gradient(180deg,rgba(148,163,184,.12),rgba(255,255,255,.96));border-color:rgba(148,163,184,.22)}
.selection-chip{display:inline-flex;align-items:center;padding:7px 12px;border-radius:999px;background:rgba(249,115,22,.1);color:#9a3412;font-size:.82rem;font-weight:700}
.batch-card--active{border-color:rgba(16,185,129,.28);box-shadow:0 18px 48px rgba(16,185,129,.1)}
.batch-state{display:grid;gap:8px;padding:16px;border-radius:18px;background:rgba(15,23,42,.03);border:1px solid rgba(148,163,184,.18)}
.batch-state--compact{padding:14px 16px}
.batch-state strong{color:#0f172a;font-size:1rem}
.batch-state p{margin:0;color:#64748b;line-height:1.6}
.selection-insights{display:flex;flex-wrap:wrap;gap:8px}
.selection-pill{display:inline-flex;align-items:center;padding:6px 10px;border-radius:999px;background:rgba(15,23,42,.06);color:#334155;font-size:.78rem;font-weight:700}
.batch-toolbar{display:grid;gap:10px;margin-top:14px}
.batch-row{display:grid;grid-template-columns:88px minmax(0,1fr) minmax(116px,auto);gap:10px;align-items:center;padding:12px 14px;border-radius:18px;background:#fff;border:1px solid rgba(148,163,184,.18)}
.batch-row--actions{grid-template-columns:88px 1fr}
.batch-label{color:#475569;font-size:.8rem;font-weight:700}
.table-shell{overflow-x:auto}
.table-shell :deep(.el-table){min-width:820px}.table-shell :deep(.el-table__cell){padding:14px 0}
.mobile-card-list{display:none}
.mobile-account-card{display:grid;gap:12px;padding:16px;border-radius:20px;border:1px solid rgba(148,163,184,.18);background:linear-gradient(180deg,#fff,#f8fafc)}
.mobile-account-card__head{display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:10px;align-items:start}
.mobile-account-card__identity{display:grid;gap:4px;min-width:0}
.mobile-account-card__identity span,.mobile-account-card__meta{color:#64748b;font-size:.78rem}
.mobile-account-card__email{justify-content:flex-start;padding:0;height:auto;font-size:.95rem;font-weight:700;white-space:normal;text-align:left}
.mobile-account-card__view{padding:0;height:auto}
.mobile-account-card__tags,.mobile-account-card__materials,.mobile-account-card__meta{display:flex;flex-wrap:wrap;gap:8px}
.mobile-account-card__materials{gap:6px}
.material-pill{display:inline-flex;align-items:center;padding:6px 10px;border-radius:999px;background:rgba(148,163,184,.12);color:#475569;font-size:.76rem;font-weight:700}
.material-pill--ready{background:rgba(16,185,129,.12);color:#047857}
.mobile-account-card__actions{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
.account-cell,.dialog-stack{display:grid;gap:8px}.cell-link{justify-content:flex-start;padding:0;height:auto;font-weight:700;font-size:.95rem}
.account-meta,.empty-state p{color:#64748b;font-size:.8rem}
.empty-state{padding:42px 0;text-align:center}.empty-state strong{display:block;color:#0f172a;font-size:1rem}
.table-foot{margin-top:18px;display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}
.dialog-form,.dialog-stack{gap:14px}.form-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px 16px}.span-2{grid-column:1/-1}
@media (min-width:1500px){
  .hero-panel{grid-template-columns:minmax(0,1.18fr) clamp(360px,30vw,520px)}
  .ops-grid{grid-template-columns:minmax(0,1.04fr) clamp(340px,28vw,440px)}
}
@media (max-width:1360px){
  .hero-panel{grid-template-columns:minmax(0,1fr) clamp(320px,36vw,420px)}
  .ops-grid{grid-template-columns:minmax(0,1fr) clamp(300px,34vw,380px)}
  .filter-grid{grid-template-columns:repeat(2,minmax(0,1fr))}
  .filter-field--wide{grid-column:1/-1}
  .hero-context-grid,.filter-summary--rich{grid-template-columns:1fr}
}
@media (max-width:1100px){
  .hero-panel,.ops-grid{grid-template-columns:1fr}
  .ops-side{grid-template-columns:repeat(2,minmax(0,1fr));align-items:start}
}
@media (max-width:860px){
  .form-grid,.filter-grid,.batch-row,.inventory-lane-grid{grid-template-columns:1fr}
  .hero-panel,.surface-card{border-radius:20px}
  .hero-panel{padding:22px}
  .hero-copy p{font-size:.92rem;line-height:1.65}
  .hero-actions{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
  .hero-actions :deep(.el-button){width:100%;margin-left:0}
  .hero-context-grid{grid-template-columns:1fr}
  .stats-grid{display:grid;grid-auto-flow:column;grid-auto-columns:minmax(170px,72%);overflow-x:auto;padding-bottom:4px;scroll-snap-type:x proximity}
  .stat-card{scroll-snap-align:start}
  .filter-field--wide{grid-column:auto}
  .preset-row{grid-template-columns:1fr;gap:8px}
  .preset-row>span,.active-title{padding-top:0}
  .preset-buttons{overflow-x:auto;flex-wrap:nowrap;padding-bottom:4px}
  .preset-buttons :deep(.el-button){flex:0 0 auto}
  .ops-side{grid-template-columns:1fr;gap:14px}
  .task-card{order:-1}
  .task-meta{grid-template-columns:1fr}
  .table-shell--desktop{display:none}
  .mobile-card-list{display:grid;gap:12px}
  .table-foot{align-items:stretch}
}
@media (max-width:760px){
  .panel-head,.table-foot{flex-direction:column;align-items:stretch}
  .panel-actions,.table-tools{justify-content:flex-start}
  .panel-actions{display:grid;grid-template-columns:repeat(2,minmax(0,1fr))}
  .panel-actions :deep(.el-button){width:100%;margin-left:0}
  .filter-card,.batch-card,.task-card,.surface-card{padding:18px}
  .batch-row--actions{grid-template-columns:1fr}
  .batch-actions{display:grid;grid-template-columns:1fr 1fr;gap:8px}
  .batch-actions :deep(.el-button){width:100%;margin-left:0}
  .mobile-account-card{padding:14px}
  .mobile-account-card__head{grid-template-columns:auto minmax(0,1fr)}
  .mobile-account-card__view{grid-column:2/3;justify-self:start}
  .mobile-account-card__actions{grid-template-columns:1fr}
}
@media (max-width:520px){
  .page-shell{gap:14px}
  .hero-panel{padding:18px}
  .hero-copy h1{font-size:1.65rem}
  .hero-actions,.panel-actions,.batch-actions{grid-template-columns:1fr}
  .stats-grid{grid-auto-columns:minmax(156px,84%)}
  .selection-chip{justify-content:center}
  .mobile-account-card__tags,.mobile-account-card__materials,.mobile-account-card__meta{gap:6px}
}
</style>
