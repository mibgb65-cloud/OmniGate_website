<script setup>
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, EditPen, Plus, Refresh, Search, Upload } from '@element-plus/icons-vue'

import {
  batchDeleteChatgptAccounts,
  batchUpdateChatgptAccountStatus,
  createChatgptAccount,
  createChatgptAccountsBatch,
  deleteChatgptAccount,
  pageChatgptAccounts,
  updateChatgptAccount,
} from '@/api/chatgpt'

const router = useRouter()

const loading = ref(false)
const rows = ref([])
const selectedRows = ref([])
const deletingId = ref(null)

const filterForm = reactive({
  email: '',
  subTier: undefined,
  accountStatus: undefined,
})

const pager = reactive({
  current: 1,
  size: 10,
  total: 0,
})

const subTierOptions = [
  { label: 'free', value: 'free' },
  { label: 'plus', value: 'plus' },
  { label: 'team', value: 'team' },
  { label: 'go', value: 'go' },
]

const statusOptions = [
  { label: 'active', value: 'active' },
  { label: 'locked', value: 'locked' },
  { label: 'banned', value: 'banned' },
]

const accountDialogVisible = ref(false)
const accountDialogMode = ref('create')
const accountFormRef = ref()
const savingAccount = ref(false)
const originalAccount = ref(null)
const accountForm = reactive({
  id: null,
  email: '',
  password: '',
  sessionToken: '',
  subTier: 'free',
  accountStatus: 'active',
  expireDate: '',
})

const batchDialogVisible = ref(false)
const batchRawText = ref('')
const batchCreating = ref(false)

const statusBatchValue = ref('active')
const statusBatchLoading = ref(false)
const batchDeleting = ref(false)

const dashboardStats = computed(() => {
  const total = rows.value.length
  const activeCount = rows.value.filter((row) => row.accountStatus === 'active').length
  const teamCount = rows.value.filter((row) => row.subTier === 'team').length
  return [
    { label: '当前页总数', value: total },
    { label: 'Active 账号', value: activeCount },
    { label: 'Team 订阅', value: teamCount },
  ]
})

const selectedIds = computed(() => selectedRows.value.map((row) => row.id).filter(Boolean))
const hasSelection = computed(() => selectedIds.value.length > 0)

const accountRules = {
  email: [
    { required: true, message: '请输入账号邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: ['blur', 'change'] },
  ],
  password: [
    {
      trigger: ['blur', 'change'],
      validator: (_rule, value, callback) => {
        const normalized = normalizeCell(value)
        if (accountDialogMode.value === 'create' && !normalized) {
          callback(new Error('新增时密码不能为空'))
          return
        }
        if (normalized && normalized.length > 255) {
          callback(new Error('密码长度不能超过255'))
          return
        }
        callback()
      },
    },
  ],
}

function normalizeCell(value) {
  const text = String(value ?? '').trim()
  return text || undefined
}

function detectDelimiter(line) {
  if (line.includes('----')) return '----'
  if (line.includes('\t')) return '\t'
  if (line.includes('|')) return '|'
  return ','
}

function toNullableText(value) {
  return value || '-'
}

function maskToken(token) {
  if (!token) return '-'
  if (token.length <= 14) return token
  return `${token.slice(0, 8)}...${token.slice(-4)}`
}

function resolveStatusTag(status) {
  if (status === 'active') return 'success'
  if (status === 'locked') return 'warning'
  if (status === 'banned') return 'danger'
  return 'info'
}

function resolveTierTag(subTier) {
  if (subTier === 'team') return 'primary'
  if (subTier === 'plus') return 'success'
  if (subTier === 'go') return 'warning'
  if (subTier === 'free') return 'info'
  return ''
}

function resolveRowClass() {
  return 'clickable-row'
}

function validateStatus(status, lineIndex) {
  const normalized = normalizeCell(status)
  if (!normalized) return undefined
  if (!statusOptions.some((item) => item.value === normalized)) {
    throw new Error(`第 ${lineIndex + 1} 行账号状态仅支持 active/locked/banned`)
  }
  return normalized
}

function validateSubTier(subTier, lineIndex) {
  const normalized = normalizeCell(subTier)
  if (!normalized) return undefined
  if (!subTierOptions.some((item) => item.value === normalized)) {
    throw new Error(`第 ${lineIndex + 1} 行订阅层级仅支持 free/plus/team/go`)
  }
  return normalized
}

function validateExpireDate(expireDate, lineIndex) {
  const normalized = normalizeCell(expireDate)
  if (!normalized) return undefined
  if (!/^\d{4}-\d{2}-\d{2}$/.test(normalized)) {
    throw new Error(`第 ${lineIndex + 1} 行到期日期必须是 yyyy-MM-dd`)
  }
  return normalized
}

function parseBatchImportText(rawText) {
  const lines = rawText
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)

  return lines.map((line, index) => {
    const delimiter = detectDelimiter(line)
    const cells = line.split(delimiter).map((cell) => cell.trim())

    if (cells.length < 2) {
      throw new Error(`第 ${index + 1} 行字段不足，至少需要 email,password`)
    }

    const [email, password, sessionToken, subTier, accountStatus, expireDate] = cells
    if (!normalizeCell(email) || !normalizeCell(password)) {
      throw new Error(`第 ${index + 1} 行存在必填字段为空（email/password）`)
    }

    return {
      email,
      password,
      sessionToken: normalizeCell(sessionToken),
      subTier: validateSubTier(subTier, index),
      accountStatus: validateStatus(accountStatus, index),
      expireDate: validateExpireDate(expireDate, index),
    }
  })
}

async function fetchChatgptAccounts() {
  loading.value = true
  try {
    const pageData = await pageChatgptAccounts({
      current: pager.current,
      size: pager.size,
      email: filterForm.email || undefined,
      subTier: filterForm.subTier,
      accountStatus: filterForm.accountStatus,
    })

    rows.value = pageData?.records || []
    pager.total = Number(pageData?.total || 0)
    pager.current = Number(pageData?.current || pager.current)
    pager.size = Number(pageData?.size || pager.size)
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  pager.current = 1
  fetchChatgptAccounts()
}

function handleReset() {
  filterForm.email = ''
  filterForm.subTier = undefined
  filterForm.accountStatus = undefined
  pager.current = 1
  fetchChatgptAccounts()
}

function handleCurrentChange(page) {
  pager.current = page
  fetchChatgptAccounts()
}

function handleSizeChange(size) {
  pager.current = 1
  pager.size = size
  fetchChatgptAccounts()
}

function handleSelectionChange(selection) {
  selectedRows.value = selection || []
}

function handleRowClick(row, column) {
  if (column?.type === 'selection') return
  if (!row?.id) return
  router.push(`/chatgpt/accounts/${row.id}`)
}

function resetAccountForm() {
  accountForm.id = null
  accountForm.email = ''
  accountForm.password = ''
  accountForm.sessionToken = ''
  accountForm.subTier = 'free'
  accountForm.accountStatus = 'active'
  accountForm.expireDate = ''
  originalAccount.value = null
}

function openCreateDialog() {
  accountDialogMode.value = 'create'
  resetAccountForm()
  accountDialogVisible.value = true
  nextTick(() => accountFormRef.value?.clearValidate())
}

function openEditDialog(row) {
  if (!row?.id) return
  accountDialogMode.value = 'edit'
  accountForm.id = row.id
  accountForm.email = row.email || ''
  accountForm.password = ''
  accountForm.sessionToken = row.sessionToken || ''
  accountForm.subTier = row.subTier || 'free'
  accountForm.accountStatus = row.accountStatus || 'active'
  accountForm.expireDate = row.expireDate || ''
  originalAccount.value = {
    email: row.email || '',
    sessionToken: row.sessionToken || '',
    subTier: row.subTier || '',
    accountStatus: row.accountStatus || '',
    expireDate: row.expireDate || '',
  }
  accountDialogVisible.value = true
  nextTick(() => accountFormRef.value?.clearValidate())
}

function buildCreatePayload() {
  return {
    email: normalizeCell(accountForm.email),
    password: normalizeCell(accountForm.password),
    sessionToken: normalizeCell(accountForm.sessionToken),
    subTier: normalizeCell(accountForm.subTier),
    accountStatus: normalizeCell(accountForm.accountStatus),
    expireDate: accountForm.expireDate || undefined,
  }
}

function buildUpdatePayload() {
  const payload = {}
  const original = originalAccount.value || {}

  const currentEmail = normalizeCell(accountForm.email) || ''
  if (currentEmail && currentEmail !== (original.email || '')) {
    payload.email = currentEmail
  }

  const currentPassword = normalizeCell(accountForm.password)
  if (currentPassword) {
    payload.password = currentPassword
  }

  const currentToken = normalizeCell(accountForm.sessionToken) || ''
  if (currentToken !== (original.sessionToken || '')) {
    payload.sessionToken = currentToken
  }

  const currentSubTier = normalizeCell(accountForm.subTier) || ''
  if (currentSubTier && currentSubTier !== (original.subTier || '')) {
    payload.subTier = currentSubTier
  }

  const currentStatus = normalizeCell(accountForm.accountStatus) || ''
  if (currentStatus && currentStatus !== (original.accountStatus || '')) {
    payload.accountStatus = currentStatus
  }

  const currentExpireDate = accountForm.expireDate || ''
  if (currentExpireDate && currentExpireDate !== (original.expireDate || '')) {
    payload.expireDate = currentExpireDate
  }

  return payload
}

async function handleSaveAccount() {
  await accountFormRef.value?.validate()
  savingAccount.value = true
  try {
    if (accountDialogMode.value === 'create') {
      await createChatgptAccount(buildCreatePayload())
      ElMessage.success('ChatGPT 账号新增成功')
      pager.current = 1
    } else {
      const payload = buildUpdatePayload()
      if (!Object.keys(payload).length) {
        ElMessage.info('未检测到变更内容')
        return
      }
      await updateChatgptAccount(accountForm.id, payload)
      ElMessage.success('ChatGPT 账号更新成功')
    }

    accountDialogVisible.value = false
    await fetchChatgptAccounts()
  } finally {
    savingAccount.value = false
  }
}

async function handleDelete(row) {
  if (!row?.id) return

  try {
    await ElMessageBox.confirm(`确认删除 ChatGPT 账号「${row.email || row.id}」吗？`, '危险操作确认', {
      type: 'warning',
      confirmButtonText: '确认删除',
      cancelButtonText: '取消',
      confirmButtonClass: 'el-button--danger',
    })
  } catch {
    return
  }

  deletingId.value = row.id
  try {
    await deleteChatgptAccount(row.id)
    ElMessage.success('账号已删除')

    if (rows.value.length === 1 && pager.current > 1) {
      pager.current -= 1
    }
    await fetchChatgptAccounts()
  } finally {
    deletingId.value = null
  }
}

async function handleBatchCreateSubmit() {
  if (!batchRawText.value.trim()) {
    ElMessage.warning('请先粘贴批量数据')
    return
  }

  let payload = []
  try {
    payload = parseBatchImportText(batchRawText.value)
  } catch (error) {
    ElMessage.error(error.message || '批量数据格式不正确')
    return
  }

  batchCreating.value = true
  try {
    const successCount = await createChatgptAccountsBatch(payload)
    ElMessage.success(`批量新增完成，成功 ${successCount ?? payload.length} 条`)
    batchDialogVisible.value = false
    batchRawText.value = ''
    pager.current = 1
    await fetchChatgptAccounts()
  } finally {
    batchCreating.value = false
  }
}

async function handleBatchStatusUpdate() {
  if (!hasSelection.value) {
    ElMessage.warning('请先选择需要修改状态的账号')
    return
  }

  statusBatchLoading.value = true
  try {
    const updatedCount = await batchUpdateChatgptAccountStatus({
      ids: selectedIds.value,
      accountStatus: statusBatchValue.value,
    })
    ElMessage.success(`批量状态更新成功，共 ${updatedCount ?? selectedIds.value.length} 条`)
    await fetchChatgptAccounts()
  } finally {
    statusBatchLoading.value = false
  }
}

async function handleBatchDelete() {
  if (!hasSelection.value) {
    ElMessage.warning('请先选择需要删除的账号')
    return
  }

  try {
    await ElMessageBox.confirm(`确认批量删除已选 ${selectedIds.value.length} 个 ChatGPT 账号吗？`, '危险操作确认', {
      type: 'warning',
      confirmButtonText: '确认删除',
      cancelButtonText: '取消',
      confirmButtonClass: 'el-button--danger',
    })
  } catch {
    return
  }

  batchDeleting.value = true
  try {
    const deletedCount = await batchDeleteChatgptAccounts(selectedIds.value)
    ElMessage.success(`批量删除成功，共 ${deletedCount ?? selectedIds.value.length} 条`)
    if (rows.value.length === selectedIds.value.length && pager.current > 1) {
      pager.current -= 1
    }
    await fetchChatgptAccounts()
  } finally {
    batchDeleting.value = false
  }
}

onMounted(fetchChatgptAccounts)
</script>

<template>
  <div class="page-shell">
    <section class="hero-card">
      <div>
        <h1>ChatGPT 账号池</h1>
        <p>覆盖单条 CRUD 与批量操作，适配高密度账号管理场景</p>
      </div>
      <div class="hero-right">
        <div class="hero-actions">
          <el-button type="primary" :icon="Plus" @click="openCreateDialog">新增账号</el-button>
          <el-button :icon="Upload" @click="batchDialogVisible = true">批量新增</el-button>
        </div>
        <div class="stats-grid">
          <article v-for="item in dashboardStats" :key="item.label" class="stat-item">
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
          </article>
        </div>
      </div>
    </section>

    <el-card class="query-card" shadow="never">
      <el-form :model="filterForm" class="query-form" @submit.prevent>
        <el-form-item label="邮箱关键字">
          <el-input v-model="filterForm.email" clearable placeholder="输入邮箱模糊匹配" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="订阅层级">
          <el-select v-model="filterForm.subTier" clearable placeholder="全部层级">
            <el-option v-for="item in subTierOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="账号状态">
          <el-select v-model="filterForm.accountStatus" clearable placeholder="全部状态">
            <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item class="actions">
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="table-card" shadow="never">
      <template #header>
        <div class="table-header">
          <h3>账号清单</h3>
          <div class="table-actions">
            <el-select v-model="statusBatchValue" placeholder="批量状态" class="status-select" :disabled="!hasSelection">
              <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
            <el-button
              :loading="statusBatchLoading"
              :disabled="!hasSelection"
              @click="handleBatchStatusUpdate"
            >
              批量改状态
            </el-button>
            <el-button
              type="danger"
              plain
              :icon="Delete"
              :loading="batchDeleting"
              :disabled="!hasSelection"
              @click="handleBatchDelete"
            >
              批量删除
            </el-button>
            <el-button :icon="Plus" @click="openCreateDialog">新增账号</el-button>
            <el-button :icon="Upload" @click="batchDialogVisible = true">批量新增</el-button>
            <el-button text :icon="Refresh" @click="fetchChatgptAccounts">刷新</el-button>
          </div>
        </div>
      </template>

      <el-table
        :data="rows"
        v-loading="loading"
        stripe
        :row-class-name="resolveRowClass"
        @row-click="handleRowClick"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="50" />
        <el-table-column prop="id" label="ID" width="84" />
        <el-table-column prop="email" label="邮箱" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">
            <el-button link class="cell-link" @click.stop="handleRowClick(row)">{{ row.email }}</el-button>
          </template>
        </el-table-column>
        <el-table-column prop="subTier" label="订阅层级" width="120">
          <template #default="{ row }">
            <el-tag :type="resolveTierTag(row.subTier)" effect="plain">{{ toNullableText(row.subTier) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="accountStatus" label="账号状态" width="120">
          <template #default="{ row }">
            <el-tag :type="resolveStatusTag(row.accountStatus)" effect="light">{{ toNullableText(row.accountStatus) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="sessionToken" label="Session Token" min-width="190" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="mono-text">{{ maskToken(row.sessionToken) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="expireDate" label="到期日期" width="124">
          <template #default="{ row }">{{ toNullableText(row.expireDate) }}</template>
        </el-table-column>
        <el-table-column prop="updatedAt" label="更新时间" min-width="172" />
        <el-table-column label="操作" width="142" fixed="right">
          <template #default="{ row }">
            <el-button link :icon="EditPen" @click.stop="openEditDialog(row)">编辑</el-button>
            <el-button
              link
              type="danger"
              :icon="Delete"
              :loading="deletingId === row.id"
              @click.stop="handleDelete(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="table-foot">
        <span class="selection-text">已选 {{ selectedIds.length }} 条</span>
        <el-pagination
          v-model:current-page="pager.current"
          v-model:page-size="pager.size"
          background
          layout="total, sizes, prev, pager, next"
          :page-sizes="[10, 20, 50, 100]"
          :total="pager.total"
          @current-change="handleCurrentChange"
          @size-change="handleSizeChange"
        />
      </div>
    </el-card>

    <el-dialog
      v-model="accountDialogVisible"
      :title="accountDialogMode === 'create' ? '新增 ChatGPT 账号' : '编辑 ChatGPT 账号'"
      width="680px"
      destroy-on-close
    >
      <el-form ref="accountFormRef" :model="accountForm" :rules="accountRules" label-width="110px">
        <el-form-item label="账号邮箱" prop="email">
          <el-input v-model="accountForm.email" placeholder="name@example.com" />
        </el-form-item>
        <el-form-item label="登录密码" prop="password">
          <el-input
            v-model="accountForm.password"
            type="password"
            show-password
            :placeholder="accountDialogMode === 'create' ? '请输入密码' : '留空表示不修改密码'"
          />
        </el-form-item>
        <el-form-item label="SessionToken">
          <el-input v-model="accountForm.sessionToken" type="textarea" :rows="2" placeholder="可选，支持留空" />
        </el-form-item>
        <el-form-item label="订阅层级">
          <el-select v-model="accountForm.subTier" placeholder="选择订阅层级">
            <el-option v-for="item in subTierOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="账号状态">
          <el-select v-model="accountForm.accountStatus" placeholder="选择账号状态">
            <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="到期日期">
          <el-date-picker
            v-model="accountForm.expireDate"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="可选"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="accountDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="savingAccount" @click="handleSaveAccount">保存</el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog v-model="batchDialogVisible" title="批量新增 ChatGPT 账号" width="760px" destroy-on-close>
      <div class="import-box">
        <el-alert type="info" show-icon :closable="false">
          <template #title>
            每行 1 条，支持 `---- / 逗号 / 竖线 / Tab` 分隔。
            格式：`email,password,sessionToken,subTier,accountStatus,expireDate`，其中后 4 项可留空。
          </template>
        </el-alert>

        <el-input
          v-model="batchRawText"
          type="textarea"
          :rows="10"
          class="import-input"
          placeholder="alice@example.com,Pass@123,session_xxx,team,active,2026-12-31"
        />
      </div>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="batchDialogVisible = false">取消</el-button>
          <el-button @click="batchRawText = ''">清空</el-button>
          <el-button type="primary" :loading="batchCreating" @click="handleBatchCreateSubmit">开始新增</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page-shell {
  display: grid;
  gap: 16px;
}

.hero-card {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 20px;
  padding: 22px;
  border-radius: 18px;
  border: 1px solid rgba(251, 146, 60, 0.24);
  background:
    radial-gradient(circle at 87% 18%, rgba(251, 146, 60, 0.3), transparent 36%),
    linear-gradient(140deg, #7c2d12 0%, #9a3412 54%, #b45309 100%);
  color: #f8fbff;
}

.hero-card h1 {
  margin: 0;
  font-family: 'Space Grotesk', sans-serif;
  font-size: 1.34rem;
}

.hero-card p {
  margin: 8px 0 0;
  color: rgba(247, 251, 255, 0.84);
}

.hero-right {
  display: grid;
  gap: 10px;
}

.hero-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(104px, 1fr));
  gap: 10px;
}

.stat-item {
  border-radius: 12px;
  border: 1px solid rgba(248, 251, 255, 0.28);
  background: rgba(248, 251, 255, 0.12);
  padding: 10px 12px;
}

.stat-item span {
  display: block;
  font-size: 0.75rem;
  color: rgba(248, 251, 255, 0.78);
}

.stat-item strong {
  display: block;
  margin-top: 4px;
  font-family: 'Fira Code', 'Space Grotesk', monospace;
  font-size: 1.18rem;
  color: #ffffff;
}

.query-card,
.table-card {
  border-radius: 16px;
  background: var(--og-surface);
  backdrop-filter: blur(8px);
}

.query-form {
  display: grid;
  grid-template-columns: repeat(3, minmax(180px, 1fr)) auto;
  gap: 12px;
  align-items: end;
}

.query-form .actions {
  margin-bottom: 18px;
}

.table-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.table-header h3 {
  margin: 0;
  color: var(--og-slate-900);
  font-size: 1rem;
  font-weight: 700;
}

.table-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.status-select {
  width: 120px;
}

.table-card :deep(.el-table__cell) {
  padding: 10px 0;
}

.table-card :deep(.clickable-row > td) {
  cursor: pointer;
}

.table-card :deep(.clickable-row:hover > td) {
  background-color: rgba(30, 64, 175, 0.06);
}

.cell-link {
  padding: 0;
  height: auto;
  font-weight: 600;
}

.mono-text {
  font-family: 'Fira Code', 'Consolas', monospace;
  font-size: 0.82rem;
}

.table-foot {
  margin-top: 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.selection-text {
  color: var(--og-slate-600);
  font-size: 0.84rem;
}

.import-box {
  display: grid;
  gap: 12px;
}

.import-input {
  margin-top: 4px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

@media (max-width: 1180px) {
  .hero-card {
    grid-template-columns: 1fr;
  }

  .query-form {
    grid-template-columns: repeat(2, minmax(180px, 1fr));
  }
}

@media (max-width: 760px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }

  .query-form {
    grid-template-columns: 1fr;
  }

  .table-foot {
    flex-direction: column;
    align-items: flex-start;
  }
}

@media (prefers-reduced-motion: reduce) {
  .table-card :deep(.clickable-row:hover > td) {
    transition: none;
  }
}
</style>
