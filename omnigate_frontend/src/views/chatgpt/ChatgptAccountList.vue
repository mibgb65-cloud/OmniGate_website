<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Download, EditPen, Plus, Refresh, Search, Upload } from '@element-plus/icons-vue'
import {
  batchDeleteChatgptAccounts,
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

const router = useRouter()
const loading = ref(false)
const rows = ref([])
const selectedRows = ref([])
const deletingId = ref(null)
const filterForm = reactive({ email: '', subTier: undefined, accountStatus: undefined })
const pager = reactive({ current: 1, size: 10, total: 0 })
const subTierOptions = [{ label: 'Free', value: 'free' }, { label: 'Plus', value: 'plus' }, { label: 'Team', value: 'team' }, { label: 'Go', value: 'go' }]
const statusOptions = [{ label: '可用', value: 'active' }, { label: '锁定', value: 'locked' }, { label: '封禁', value: 'banned' }]
const accountDialogVisible = ref(false)
const accountDialogMode = ref('create')
const accountFormRef = ref()
const savingAccount = ref(false)
const originalAccount = ref(null)
const accountForm = reactive({ id: null, email: '', password: '', sessionToken: '', totpSecret: '', subTier: 'free', accountStatus: 'active', expireDate: '' })
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
const batchDeleting = ref(false)
const TASK_STATUS_POLL_INTERVAL_MS = 3000
const TASK_STATUS_RETRY_INTERVAL_MS = 5000
const TERMINAL_TASK_STATUSES = new Set(['success', 'failed', 'cancelled', 'timeout'])
let taskStatusPollTimer = null

const selectedIds = computed(() => selectedRows.value.map((row) => row.id).filter(Boolean))
const hasSelection = computed(() => selectedIds.value.length > 0)
const dashboardStats = computed(() => [
  { label: '筛选结果', value: pager.total, note: '当前过滤后的总数' },
  { label: '当前页可用', value: rows.value.filter((row) => row.accountStatus === 'active').length, note: '适合直接使用' },
  { label: '付费层级', value: rows.value.filter((row) => ['plus', 'team', 'go'].includes(row.subTier)).length, note: 'Plus / Team / Go' },
  { label: '已勾选', value: selectedIds.value.length, note: '可直接批量处理' },
])
const activeFilterTags = computed(() => {
  const tags = []
  if (normalizeCell(filterForm.email)) tags.push({ key: 'email', label: '邮箱', value: filterForm.email.trim() })
  if (filterForm.subTier) tags.push({ key: 'subTier', label: '层级', value: formatSubTier(filterForm.subTier) })
  if (filterForm.accountStatus) tags.push({ key: 'accountStatus', label: '状态', value: formatAccountStatus(filterForm.accountStatus) })
  return tags
})
const latestAutoRegisterTaskStatusLabel = computed(() => formatTaskStatus(latestAutoRegisterTask.value?.status))
const latestAutoRegisterTaskAlertType = computed(() => resolveTaskAlertType(latestAutoRegisterTask.value?.status))
const latestAutoRegisterTaskTitle = computed(() => {
  const status = normalizeTaskStatus(latestAutoRegisterTask.value?.status)
  if (!status) return '最近一次自动注册任务'
  return isTerminalTaskStatus(status) ? `最近一次自动注册任务已结束（${formatTaskStatus(status)}）` : `最近一次自动注册任务进行中（${formatTaskStatus(status)}）`
})
const exportButtonLabel = computed(() => (
  selectedRows.value.length
    ? `导出已选（${selectedRows.value.length}）`
    : '导出全部'
))

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
function detectDelimiter(line) { if (line.includes('----')) return '----'; if (line.includes('\t')) return '\t'; if (line.includes('|')) return '|'; return ',' }
function toNullableText(value) { return value || '-' }
function maskToken(token) { if (!token) return '-'; if (token.length <= 18) return token; return `${token.slice(0, 8)}...${token.slice(-6)}` }
function formatAccountStatus(status) { return ({ active: '可用', locked: '锁定', banned: '封禁' }[status]) || status || '-' }
function formatSubTier(subTier) { return ({ free: 'Free', plus: 'Plus', team: 'Team', go: 'Go' }[subTier]) || subTier || '-' }
function resolveStatusTag(status) { return status === 'active' ? 'success' : status === 'locked' ? 'warning' : status === 'banned' ? 'danger' : 'info' }
function resolveTierTag(subTier) { return subTier === 'team' ? 'primary' : subTier === 'plus' ? 'success' : subTier === 'go' ? 'warning' : 'info' }
function resolveRowClass() { return 'clickable-row' }
function normalizeTaskStatus(status) { return String(status ?? '').trim().toLowerCase() }
function isTerminalTaskStatus(status) { return TERMINAL_TASK_STATUSES.has(normalizeTaskStatus(status)) }
function formatTaskStatus(status) { return ({ queued: '排队中', running: '执行中', success: '成功', failed: '失败', cancelled: '已取消', timeout: '超时' }[normalizeTaskStatus(status)]) || status || '-' }
function resolveTaskAlertType(status) { const s = normalizeTaskStatus(status); return s === 'success' ? 'success' : ['failed', 'cancelled', 'timeout'].includes(s) ? 'error' : s === 'running' ? 'warning' : 'info' }
function stopTaskStatusPolling() { if (taskStatusPollTimer) { clearTimeout(taskStatusPollTimer); taskStatusPollTimer = null } }
function scheduleTaskStatusPoll(rootRunId, delay = TASK_STATUS_POLL_INTERVAL_MS) { stopTaskStatusPolling(); if (rootRunId) taskStatusPollTimer = setTimeout(() => pollTaskStatus(rootRunId), delay) }

async function pollTaskStatus(rootRunId) {
  if (!rootRunId) return
  try {
    const statusResult = await getChatgptTaskStatusByRootRunId(rootRunId, { skipErrorMessage: true })
    if (!statusResult) return scheduleTaskStatusPoll(rootRunId, TASK_STATUS_RETRY_INTERVAL_MS)
    if (latestAutoRegisterTask.value?.rootRunId !== rootRunId) return
    latestAutoRegisterTask.value = { ...latestAutoRegisterTask.value, ...statusResult, requestedCount: latestAutoRegisterTask.value?.requestedCount }
    const normalizedStatus = normalizeTaskStatus(statusResult.status)
    if (!isTerminalTaskStatus(normalizedStatus)) return scheduleTaskStatusPoll(rootRunId)
    stopTaskStatusPolling()
    await fetchChatgptAccounts()
    if (normalizedStatus === 'success') return ElMessage.success('自动注册任务已完成，账号池列表已自动刷新')
    const errorText = statusResult.errorMessage ? `：${statusResult.errorMessage}` : ''
    ElMessage.warning(`自动注册任务已结束，状态 ${formatTaskStatus(normalizedStatus)}${errorText}，列表已自动刷新`)
  } catch {
    if (latestAutoRegisterTask.value?.rootRunId === rootRunId) scheduleTaskStatusPoll(rootRunId, TASK_STATUS_RETRY_INTERVAL_MS)
  }
}

function toggleQuickFilter(field, value) { filterForm[field] = filterForm[field] === value ? undefined : value; pager.current = 1; fetchChatgptAccounts() }
function clearSingleFilter(key) { if (key === 'email') filterForm.email = ''; else filterForm[key] = undefined; pager.current = 1; fetchChatgptAccounts() }
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
    const pageData = await pageChatgptAccounts({ current: pager.current, size: pager.size, email: filterForm.email || undefined, subTier: filterForm.subTier, accountStatus: filterForm.accountStatus })
    rows.value = pageData?.records || []
    selectedRows.value = []
    pager.total = Number(pageData?.total || 0)
    pager.current = Number(pageData?.current || pager.current)
    pager.size = Number(pageData?.size || pager.size)
  } finally { loading.value = false }
}

function handleSearch() { pager.current = 1; fetchChatgptAccounts() }
function handleReset() { filterForm.email = ''; filterForm.subTier = undefined; filterForm.accountStatus = undefined; pager.current = 1; fetchChatgptAccounts() }
function handleCurrentChange(page) { pager.current = page; fetchChatgptAccounts() }
function handleSizeChange(size) { pager.current = 1; pager.size = size; fetchChatgptAccounts() }
function handleSelectionChange(selection) { selectedRows.value = selection || [] }
function handleRowClick(row, column) { if (column?.type !== 'selection' && row?.id) router.push(`/chatgpt/accounts/${row.id}`) }
function resetAccountForm() { Object.assign(accountForm, { id: null, email: '', password: '', sessionToken: '', totpSecret: '', subTier: 'free', accountStatus: 'active', expireDate: '' }); originalAccount.value = null }
function openCreateDialog() { accountDialogMode.value = 'create'; resetAccountForm(); accountDialogVisible.value = true; nextTick(() => accountFormRef.value?.clearValidate()) }
function openAutoRegisterDialog() { autoRegisterForm.signupCount = 1; autoRegisterDialogVisible.value = true; nextTick(() => autoRegisterFormRef.value?.clearValidate()) }
function openEditDialog(row) {
  if (!row?.id) return
  accountDialogMode.value = 'edit'
  Object.assign(accountForm, { id: row.id, email: row.email || '', password: '', sessionToken: row.sessionToken || '', totpSecret: row.totpSecret || '', subTier: row.subTier || 'free', accountStatus: row.accountStatus || 'active', expireDate: row.expireDate || '' })
  originalAccount.value = { email: row.email || '', sessionToken: row.sessionToken || '', totpSecret: row.totpSecret || '', subTier: row.subTier || '', accountStatus: row.accountStatus || '', expireDate: row.expireDate || '' }
  accountDialogVisible.value = true
  nextTick(() => accountFormRef.value?.clearValidate())
}

function buildCreatePayload() { return { email: normalizeCell(accountForm.email), password: normalizeCell(accountForm.password), sessionToken: normalizeCell(accountForm.sessionToken), totpSecret: normalizeCell(accountForm.totpSecret), subTier: normalizeCell(accountForm.subTier), accountStatus: normalizeCell(accountForm.accountStatus), expireDate: accountForm.expireDate || undefined } }
function buildUpdatePayload() {
  const payload = {}
  const original = originalAccount.value || {}
  const currentEmail = normalizeCell(accountForm.email) || ''
  const currentPassword = normalizeCell(accountForm.password)
  const currentToken = normalizeCell(accountForm.sessionToken) || ''
  const currentTotpSecret = normalizeCell(accountForm.totpSecret) || ''
  const currentSubTier = normalizeCell(accountForm.subTier) || ''
  const currentStatus = normalizeCell(accountForm.accountStatus) || ''
  const currentExpireDate = accountForm.expireDate || ''
  if (currentEmail && currentEmail !== (original.email || '')) payload.email = currentEmail
  if (currentPassword) payload.password = currentPassword
  if (currentToken !== (original.sessionToken || '')) payload.sessionToken = currentToken
  if (currentTotpSecret !== (original.totpSecret || '')) payload.totpSecret = currentTotpSecret
  if (currentSubTier && currentSubTier !== (original.subTier || '')) payload.subTier = currentSubTier
  if (currentStatus && currentStatus !== (original.accountStatus || '')) payload.accountStatus = currentStatus
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
    latestAutoRegisterTask.value = dispatchResult
    autoRegisterDialogVisible.value = false
    ElMessage.success(`自动注册任务已投递，数量 ${dispatchResult?.requestedCount || payload.signupCount}`)
    scheduleTaskStatusPoll(dispatchResult?.rootRunId, 1200)
  } finally { autoRegisterSubmitting.value = false }
}

async function handleBatchStatusUpdate() {
  if (!hasSelection.value) return ElMessage.warning('请先选择需要修改状态的账号')
  statusBatchLoading.value = true
  try { const updatedCount = await batchUpdateChatgptAccountStatus({ ids: selectedIds.value, accountStatus: statusBatchValue.value }); ElMessage.success(`批量状态更新成功，共 ${updatedCount ?? selectedIds.value.length} 条`); await fetchChatgptAccounts() } finally { statusBatchLoading.value = false }
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
    : await fetchAllPagedRecords(pageChatgptAccounts, {
      email: filterForm.email || undefined,
      subTier: filterForm.subTier,
      accountStatus: filterForm.accountStatus,
    })

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

onMounted(fetchChatgptAccounts)
onBeforeUnmount(stopTaskStatusPolling)
</script>

<template>
  <div class="page-shell">
    <section class="hero-panel">
      <div class="hero-copy">
        <span class="eyebrow">Workspace / ChatGPT Accounts</span>
        <h1>ChatGPT 账号池</h1>
        <p>把筛选、批量处理、自动注册和详情查看收拢到一屏，减少重复跳转。</p>
        <div class="hero-actions">
          <el-button type="success" :icon="Plus" @click="openAutoRegisterDialog">自动注册</el-button>
          <el-button type="primary" :icon="Plus" @click="openCreateDialog">新增账号</el-button>
          <el-button :icon="Upload" @click="batchDialogVisible = true">批量新增</el-button>
          <el-button text :icon="Refresh" @click="fetchChatgptAccounts">刷新列表</el-button>
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

    <el-alert v-if="latestAutoRegisterTask" :type="latestAutoRegisterTaskAlertType" :closable="false" class="task-alert" show-icon>
      <template #title>{{ latestAutoRegisterTaskTitle }}</template>
      <template #default>
        <div class="task-meta">
          <span>数量：{{ latestAutoRegisterTask.requestedCount || '-' }}</span>
          <span>状态：{{ latestAutoRegisterTaskStatusLabel }}</span>
          <span>TaskRunId：{{ latestAutoRegisterTask.taskRunId || '-' }}</span>
          <span>RootRunId：{{ latestAutoRegisterTask.rootRunId || '-' }}</span>
          <span v-if="latestAutoRegisterTask.lastCheckpoint">检查点：{{ latestAutoRegisterTask.lastCheckpoint }}</span>
          <span v-if="latestAutoRegisterTask.errorMessage">错误信息：{{ latestAutoRegisterTask.errorMessage }}</span>
        </div>
      </template>
    </el-alert>

    <section class="surface-card">
      <div class="panel-head">
        <div>
          <h2>快速筛选</h2>
          <p>先用状态和层级按钮缩小范围，再按邮箱关键字精确定位。</p>
        </div>
        <div class="panel-actions">
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <el-button :icon="Refresh" @click="handleReset">清空筛选</el-button>
        </div>
      </div>
      <div class="filter-box">
        <el-input v-model="filterForm.email" clearable placeholder="输入邮箱关键字，支持回车查询" @keyup.enter="handleSearch" />
        <div class="quick-row">
          <span>状态</span>
          <div class="quick-buttons">
            <el-button :type="!filterForm.accountStatus ? 'primary' : 'default'" :plain="Boolean(filterForm.accountStatus)" @click="toggleQuickFilter('accountStatus', filterForm.accountStatus)">全部</el-button>
            <el-button v-for="item in statusOptions" :key="item.value" :type="filterForm.accountStatus === item.value ? 'primary' : 'default'" :plain="filterForm.accountStatus !== item.value" @click="toggleQuickFilter('accountStatus', item.value)">{{ item.label }}</el-button>
          </div>
        </div>
        <div class="quick-row">
          <span>层级</span>
          <div class="quick-buttons">
            <el-button :type="!filterForm.subTier ? 'primary' : 'default'" :plain="Boolean(filterForm.subTier)" @click="toggleQuickFilter('subTier', filterForm.subTier)">全部</el-button>
            <el-button v-for="item in subTierOptions" :key="item.value" :type="filterForm.subTier === item.value ? 'primary' : 'default'" :plain="filterForm.subTier !== item.value" @click="toggleQuickFilter('subTier', item.value)">{{ item.label }}</el-button>
          </div>
        </div>
      </div>
      <div v-if="activeFilterTags.length" class="active-filters">
        <span class="active-title">当前筛选</span>
        <el-tag v-for="tag in activeFilterTags" :key="tag.key" closable effect="plain" @close="clearSingleFilter(tag.key)">{{ tag.label }}：{{ tag.value }}</el-tag>
      </div>
    </section>

    <section class="surface-card">
      <div class="panel-head">
        <div>
          <h2>账号清单</h2>
          <p>点击行进入详情页；勾选后可直接批量改状态或删除。</p>
        </div>
        <div class="panel-actions bulk-actions">
          <span class="selection-chip">已选 {{ selectedIds.length }} 条</span>
          <el-button type="success" plain :icon="Download" @click="handleExportAccounts">
            {{ exportButtonLabel }}
          </el-button>
          <el-select v-model="statusBatchValue" placeholder="批量状态" class="status-select" :disabled="!hasSelection">
            <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
          <el-button :loading="statusBatchLoading" :disabled="!hasSelection" @click="handleBatchStatusUpdate">批量改状态</el-button>
          <el-button type="danger" plain :icon="Delete" :loading="batchDeleting" :disabled="!hasSelection" @click="handleBatchDelete">批量删除</el-button>
        </div>
      </div>
      <div class="table-shell">
        <el-table :data="rows" v-loading="loading" stripe :row-class-name="resolveRowClass" @row-click="handleRowClick" @selection-change="handleSelectionChange">
          <el-table-column type="selection" width="50" />
          <el-table-column label="账号" min-width="280">
            <template #default="{ row }">
              <div class="account-cell">
                <el-button link class="cell-link" @click.stop="handleRowClick(row)">{{ row.email }}</el-button>
                <div class="account-meta"><span>ID {{ toNullableText(row.id) }}</span><span>更新于 {{ toNullableText(row.updatedAt) }}</span></div>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="层级 / 状态" min-width="170">
            <template #default="{ row }">
              <div class="tag-stack">
                <el-tag :type="resolveTierTag(row.subTier)" effect="plain">{{ formatSubTier(row.subTier) }}</el-tag>
                <el-tag :type="resolveStatusTag(row.accountStatus)" effect="light">{{ formatAccountStatus(row.accountStatus) }}</el-tag>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="凭据概览" min-width="220" show-overflow-tooltip>
            <template #default="{ row }">
              <div class="credential-cell">
                <span class="mono-text">{{ maskToken(row.sessionToken) }}</span>
                <span class="subtle-text">到期：{{ toNullableText(row.expireDate) }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="180" fixed="right">
            <template #default="{ row }">
              <div class="row-actions">
                <el-button link @click.stop="handleRowClick(row)">详情</el-button>
                <el-button link :icon="EditPen" @click.stop="openEditDialog(row)">编辑</el-button>
                <el-button link type="danger" :icon="Delete" :loading="deletingId === row.id" @click.stop="handleDelete(row)">删除</el-button>
              </div>
            </template>
          </el-table-column>
          <template #empty>
            <div class="empty-state"><strong>当前没有匹配账号</strong><p>可以先清空筛选，或直接新增 / 自动注册账号。</p></div>
          </template>
        </el-table>
      </div>
      <div class="table-foot">
        <span class="subtle-text">当前页 {{ rows.length }} 条，筛选结果共 {{ pager.total }} 条</span>
        <el-pagination v-model:current-page="pager.current" v-model:page-size="pager.size" background layout="total, sizes, prev, pager, next" :page-sizes="[10, 20, 50, 100]" :total="pager.total" @current-change="handleCurrentChange" @size-change="handleSizeChange" />
      </div>
    </section>

    <el-dialog v-model="accountDialogVisible" :title="accountDialogMode === 'create' ? '新增 ChatGPT 账号' : '编辑 ChatGPT 账号'" width="760px" destroy-on-close>
      <el-form ref="accountFormRef" :model="accountForm" :rules="accountRules" label-position="top" class="dialog-form">
        <div class="form-grid">
          <el-form-item label="账号邮箱" prop="email"><el-input v-model="accountForm.email" placeholder="name@example.com" /></el-form-item>
          <el-form-item label="登录密码" prop="password"><el-input v-model="accountForm.password" type="password" show-password :placeholder="accountDialogMode === 'create' ? '请输入密码' : '留空表示不修改密码'" /></el-form-item>
          <el-form-item label="2FA / TOTP 密钥" prop="totpSecret"><el-input v-model="accountForm.totpSecret" placeholder="可选，绑定后可保存" /></el-form-item>
          <el-form-item label="订阅层级"><el-select v-model="accountForm.subTier"><el-option v-for="item in subTierOptions" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item>
          <el-form-item label="账号状态"><el-select v-model="accountForm.accountStatus"><el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item>
          <el-form-item label="到期日期"><el-date-picker v-model="accountForm.expireDate" type="date" value-format="YYYY-MM-DD" placeholder="可选" /></el-form-item>
          <el-form-item label="SessionToken" class="span-2"><el-input v-model="accountForm.sessionToken" type="textarea" :rows="3" placeholder="可选，支持留空" /></el-form-item>
        </div>
      </el-form>
      <template #footer><div class="dialog-footer"><el-button @click="accountDialogVisible = false">取消</el-button><el-button type="primary" :loading="savingAccount" @click="handleSaveAccount">保存</el-button></div></template>
    </el-dialog>

    <el-dialog v-model="batchDialogVisible" title="批量新增 ChatGPT 账号" width="760px" destroy-on-close>
      <div class="dialog-stack">
        <el-alert type="info" show-icon :closable="false"><template #title>每行 1 条，支持 `---- / 逗号 / 竖线 / Tab` 分隔。新格式：`email,password,sessionToken,totpSecret,subTier,accountStatus,expireDate`；旧格式不带 `totpSecret` 也兼容。</template></el-alert>
        <el-input v-model="batchRawText" type="textarea" :rows="10" placeholder="alice@example.com,Pass@123,session_xxx,JBSWY3DPEHPK3PXP,free,active,2026-12-31&#10;bob@example.com,Pass@456,session_xxx,team,active,2026-12-31" />
      </div>
      <template #footer><div class="dialog-footer"><el-button @click="batchDialogVisible = false">取消</el-button><el-button @click="batchRawText = ''">清空</el-button><el-button type="primary" :loading="batchCreating" @click="handleBatchCreateSubmit">开始新增</el-button></div></template>
    </el-dialog>

    <el-dialog v-model="autoRegisterDialogVisible" title="自动注册 ChatGPT 账号" width="500px" destroy-on-close>
      <el-form ref="autoRegisterFormRef" :model="autoRegisterForm" :rules="autoRegisterRules" label-position="top">
        <el-form-item label="注册数量" prop="signupCount"><el-input-number v-model="autoRegisterForm.signupCount" :min="1" :step="1" step-strictly /></el-form-item>
        <div class="subtle-text">任务会投递到 worker，由浏览器自动注册账号并写入账号池。投递成功后，页面会自动轮询状态并在结束后刷新列表。</div>
      </el-form>
      <template #footer><div class="dialog-footer"><el-button @click="autoRegisterDialogVisible = false">取消</el-button><el-button type="primary" :loading="autoRegisterSubmitting" @click="handleAutoRegisterSubmit">开始投递</el-button></div></template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page-shell{display:grid;gap:18px}
.hero-panel,.surface-card{border-radius:22px}
.hero-panel{display:grid;grid-template-columns:minmax(0,1.15fr) minmax(320px,.85fr);gap:20px;padding:28px;background:radial-gradient(circle at top right,rgba(45,212,191,.18),transparent 32%),radial-gradient(circle at 18% 18%,rgba(249,115,22,.18),transparent 28%),linear-gradient(140deg,#111827 0%,#172033 44%,#1f2937 100%);color:#f8fafc;border:1px solid rgba(255,255,255,.08);box-shadow:0 24px 64px rgba(15,23,42,.22)}
.eyebrow{display:inline-flex;padding:6px 10px;border-radius:999px;background:rgba(255,255,255,.09);color:rgba(255,255,255,.72);font-size:.74rem;letter-spacing:.06em;text-transform:uppercase}
.hero-copy h1{margin:12px 0 0;font-family:'Space Grotesk',sans-serif;font-size:2rem;line-height:1.05}
.hero-copy p{margin:12px 0 0;max-width:620px;color:rgba(226,232,240,.84);line-height:1.7}
.hero-actions,.panel-actions,.row-actions,.dialog-footer{display:flex;flex-wrap:wrap;gap:10px}
.hero-actions{margin-top:22px}
.stats-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.stat-card{padding:16px;border-radius:18px;background:linear-gradient(180deg,rgba(255,255,255,.14),rgba(255,255,255,.06));border:1px solid rgba(255,255,255,.14)}
.stat-card span,.subtle-text{color:#64748b;font-size:.82rem}
.stat-card span{color:rgba(226,232,240,.8)}
.stat-card strong{display:block;margin-top:8px;font-family:'Fira Code','Space Grotesk',monospace;font-size:1.52rem;color:#fff}
.stat-card p{margin:8px 0 0;color:rgba(226,232,240,.72);font-size:.82rem;line-height:1.5}
.surface-card{padding:22px;border:1px solid rgba(148,163,184,.18);background:radial-gradient(circle at top right,rgba(45,212,191,.08),transparent 24%),linear-gradient(180deg,rgba(255,255,255,.96),rgba(248,250,252,.96));box-shadow:0 18px 48px rgba(15,23,42,.08)}
.task-alert{border-radius:18px}
.task-meta{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:8px 16px;margin-top:6px;word-break:break-all;font-size:.84rem}
.panel-head{display:flex;align-items:flex-start;justify-content:space-between;gap:16px;margin-bottom:18px}
.panel-head h2{margin:0;font-family:'Space Grotesk',sans-serif;font-size:1.1rem;color:#0f172a}
.panel-head p{margin:6px 0 0;color:#475569;line-height:1.6}
.filter-box{display:grid;gap:14px}
.quick-row{display:grid;grid-template-columns:56px 1fr;gap:12px;align-items:start}
.quick-row>span,.active-title{padding-top:8px;color:#475569;font-size:.84rem;font-weight:700}
.quick-buttons,.active-filters,.tag-stack,.account-meta,.credential-cell{display:flex;flex-wrap:wrap;gap:8px}
.active-filters{margin-top:14px;padding-top:14px;border-top:1px solid rgba(148,163,184,.18);align-items:flex-start}
.selection-chip{display:inline-flex;align-items:center;padding:7px 12px;border-radius:999px;background:rgba(249,115,22,.1);color:#9a3412;font-size:.82rem;font-weight:700}
.bulk-actions{justify-content:flex-end}.status-select{width:140px}.table-shell{overflow-x:auto}
.table-shell :deep(.el-table){min-width:760px}.table-shell :deep(.el-table__cell){padding:14px 0}
.table-shell :deep(.clickable-row>td){cursor:pointer;transition:background-color 180ms ease}
.table-shell :deep(.clickable-row:hover>td){background-color:rgba(15,118,110,.05)}
.account-cell,.dialog-stack{display:grid;gap:8px}.cell-link{justify-content:flex-start;padding:0;height:auto;font-weight:700;font-size:.95rem}
.account-meta,.credential-cell,.empty-state p{color:#64748b;font-size:.8rem}
.mono-text{font-family:'Fira Code','Consolas',monospace;font-size:.8rem;color:#0f172a;word-break:break-all}
.empty-state{padding:42px 0;text-align:center}.empty-state strong{display:block;color:#0f172a;font-size:1rem}
.table-foot{margin-top:18px;display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}
.dialog-form,.dialog-stack{gap:14px}.form-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px 16px}.span-2{grid-column:1/-1}
@media (max-width:1180px){.hero-panel{grid-template-columns:1fr}}
@media (max-width:860px){.form-grid,.stats-grid{grid-template-columns:1fr}.quick-row{grid-template-columns:1fr;gap:8px}.quick-row>span,.active-title{padding-top:0}}
@media (max-width:760px){.panel-head,.table-foot{flex-direction:column;align-items:stretch}.bulk-actions,.panel-actions{justify-content:flex-start}}
@media (prefers-reduced-motion:reduce){.table-shell :deep(.clickable-row>td){transition:none}}
</style>
