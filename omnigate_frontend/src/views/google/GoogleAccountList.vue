<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Plus, Refresh, RefreshRight, Search, Upload } from '@element-plus/icons-vue'

import { deleteGoogleAccount, importGoogleAccounts, pageGoogleAccounts } from '@/api/google'

const loading = ref(false)
const rows = ref([])
const router = useRouter()
const importDialogVisible = ref(false)
const importing = ref(false)
const importRawText = ref('')
const importMode = ref('text')
const deletingId = ref(null)
const importForm = reactive(createGoogleImportForm())
const selectedRowIds = ref([])
const batchRefreshing = ref(false)
const rowRefreshingMap = reactive({})

const filterForm = reactive({
  email: '',
  syncStatus: undefined,
})

const pager = reactive({
  current: 1,
  size: 10,
  total: 0,
})

const syncStatusOptions = [
  { label: '待同步', value: 0 },
  { label: '同步成功', value: 1 },
  { label: '同步失败', value: 2 },
]

const dashboardStats = computed(() => {
  const total = rows.value.length
  const successCount = rows.value.filter((item) => item.syncStatus === 1).length
  const familyOpened = rows.value.filter((item) => item.familyStatus === 1).length
  return [
    { label: '当前页总数', value: total },
    { label: '同步成功', value: successCount },
    { label: '已开通家庭组', value: familyOpened },
  ]
})

function toNullableText(value) {
  return value || '-'
}

function wait(ms) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms)
  })
}

function pickRandom(list) {
  return list[Math.floor(Math.random() * list.length)]
}

function formatDateOnly(date = new Date()) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function formatDateTime(date = new Date()) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hour = String(date.getHours()).padStart(2, '0')
  const minute = String(date.getMinutes()).padStart(2, '0')
  const second = String(date.getSeconds()).padStart(2, '0')
  return `${year}-${month}-${day} ${hour}:${minute}:${second}`
}

function buildMockAccountInfo() {
  const subTier = pickRandom(['none', 'plus', 'pro'])
  const familyStatus = pickRandom([0, 1])
  const inviteLinkStatus = familyStatus === 1 ? pickRandom([0, 1, 1]) : 0
  const expireDate =
    subTier === 'none'
      ? 'none'
      : formatDateOnly(new Date(Date.now() + (45 + Math.floor(Math.random() * 180)) * 24 * 60 * 60 * 1000))

  return {
    syncStatus: pickRandom([1, 1, 1, 0, 2]),
    familyStatus,
    inviteLinkStatus,
    invitedCount: inviteLinkStatus ? Math.floor(Math.random() * 6) : 0,
    subTier,
    expireDate,
    updatedAt: formatDateTime(new Date()),
  }
}

function applyMockInfoForRow(row) {
  if (!row) return
  Object.assign(row, buildMockAccountInfo())
}

function resolveSyncTag(status) {
  if (status === 1) return { type: 'success', text: '同步成功' }
  if (status === 2) return { type: 'danger', text: '同步失败' }
  return { type: 'warning', text: '待同步' }
}

function resolveBinaryTag(status, trueLabel, falseLabel) {
  if (status === 1) return { type: 'success', text: trueLabel }
  return { type: 'info', text: falseLabel }
}

function detectDelimiter(line) {
  if (line.includes('----')) return '----'
  if (line.includes('\t')) return '\t'
  if (line.includes('|')) return '|'
  return ','
}

function normalizeCell(value) {
  const nextValue = String(value || '').trim()
  return nextValue || undefined
}

function createGoogleImportForm() {
  return {
    email: '',
    password: '',
    recoveryEmail: '',
    totpSecret: '',
    region: '',
    remark: '',
  }
}

function resetGoogleImportForm() {
  Object.assign(importForm, createGoogleImportForm())
}

function parseGoogleImportText(rawText) {
  const lines = rawText
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)

  return lines.map((line, index) => {
    const delimiter = detectDelimiter(line)
    const cells = line.split(delimiter).map((cell) => cell.trim())

    let email = ''
    let password = ''
    let recoveryEmail
    let totpSecret = ''
    let region
    let remark

    if (cells.length >= 4) {
      ;[email, password, recoveryEmail, totpSecret, region, remark] = cells
    } else if (cells.length === 3) {
      ;[email, password, totpSecret] = cells
    } else {
      throw new Error(`第 ${index + 1} 行字段不足，至少需要 email,password,totpSecret`)
    }

    if (!email || !password || !totpSecret) {
      throw new Error(`第 ${index + 1} 行存在必填字段为空（email/password/totpSecret）`)
    }

    return {
      email,
      password,
      recoveryEmail: normalizeCell(recoveryEmail),
      totpSecret,
      region: normalizeCell(region),
      remark: normalizeCell(remark),
    }
  })
}

function parseGoogleImportForm(form) {
  const payload = {
    email: normalizeCell(form.email),
    password: normalizeCell(form.password),
    recoveryEmail: normalizeCell(form.recoveryEmail),
    totpSecret: normalizeCell(form.totpSecret),
    region: normalizeCell(form.region),
    remark: normalizeCell(form.remark),
  }

  if (!payload.email || !payload.password || !payload.totpSecret) {
    throw new Error('表单模式必填：email、password、totpSecret')
  }

  return payload
}

async function fetchGoogleAccounts() {
  loading.value = true
  try {
    const pageData = await pageGoogleAccounts({
      current: pager.current,
      size: pager.size,
      email: filterForm.email || undefined,
      syncStatus: filterForm.syncStatus,
    })

    rows.value = pageData?.records || []
    selectedRowIds.value = []
    pager.total = Number(pageData?.total || 0)
    pager.current = Number(pageData?.current || pager.current)
    pager.size = Number(pageData?.size || pager.size)
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  pager.current = 1
  fetchGoogleAccounts()
}

function handleReset() {
  filterForm.email = ''
  filterForm.syncStatus = undefined
  pager.current = 1
  fetchGoogleAccounts()
}

function handleCurrentChange(page) {
  pager.current = page
  fetchGoogleAccounts()
}

function handleSizeChange(size) {
  pager.current = 1
  pager.size = size
  fetchGoogleAccounts()
}

function handleRowClick(row, column) {
  if (column?.type === 'selection' || column?.label === '操作') return
  if (!row?.id) return
  try {
    sessionStorage.setItem(`og-google-account-snapshot-${row.id}`, JSON.stringify(row))
  } catch {
    // ignore snapshot persistence failure
  }
  router.push({
    path: `/google/accounts/${row.id}`,
    query: row?.email ? { email: row.email } : undefined,
  })
}

function resolveRowClass({ row }) {
  if (rowRefreshingMap[row?.id]) {
    return 'clickable-row row-refreshing'
  }
  return 'clickable-row'
}

function handleSelectionChange(selection) {
  selectedRowIds.value = selection.map((item) => item.id).filter((id) => id !== null && id !== undefined)
}

function isRowRefreshing(id) {
  return Boolean(rowRefreshingMap[id])
}

async function handleRefreshInfo(row) {
  if (!row?.id) return

  rowRefreshingMap[row.id] = true
  try {
    await wait(520 + Math.floor(Math.random() * 500))
    applyMockInfoForRow(row)
    ElMessage.success(`已刷新 ${row.email || row.id} 的信息（模拟）`)
  } finally {
    rowRefreshingMap[row.id] = false
  }
}

async function handleBatchRefreshInfo() {
  if (!selectedRowIds.value.length) {
    ElMessage.warning('请先勾选需要获取信息的账号')
    return
  }

  batchRefreshing.value = true
  const idSet = new Set(selectedRowIds.value)
  selectedRowIds.value.forEach((id) => {
    rowRefreshingMap[id] = true
  })

  try {
    await wait(800 + Math.floor(Math.random() * 700))
    let refreshedCount = 0
    rows.value.forEach((row) => {
      if (!idSet.has(row.id)) return
      applyMockInfoForRow(row)
      refreshedCount += 1
    })
    ElMessage.success(`批量获取信息完成（模拟），已刷新 ${refreshedCount} 条`)
  } finally {
    selectedRowIds.value.forEach((id) => {
      rowRefreshingMap[id] = false
    })
    batchRefreshing.value = false
  }
}

async function handleDelete(row) {
  if (!row?.id) return

  try {
    await ElMessageBox.confirm(`确认删除 Google 账号「${row.email || row.id}」吗？`, '危险操作确认', {
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
    await deleteGoogleAccount(row.id)
    ElMessage.success('账号已删除')

    if (rows.value.length === 1 && pager.current > 1) {
      pager.current -= 1
    }
    await fetchGoogleAccounts()
  } finally {
    deletingId.value = null
  }
}

async function handleImportSubmit() {
  let payload = []
  try {
    if (importMode.value === 'text') {
      if (!importRawText.value.trim()) {
        ElMessage.warning('请先粘贴待导入数据')
        return
      }
      payload = parseGoogleImportText(importRawText.value)
    } else {
      payload = [parseGoogleImportForm(importForm)]
    }
  } catch (error) {
    ElMessage.error(error.message || '导入数据格式不正确')
    return
  }

  importing.value = true
  try {
    const successCount = await importGoogleAccounts(payload)
    ElMessage.success(`导入完成，成功 ${successCount ?? payload.length} 条`)
    importDialogVisible.value = false
    pager.current = 1
    await fetchGoogleAccounts()
  } finally {
    importing.value = false
  }
}

function handleImportDialogClosed() {
  importMode.value = 'text'
  importRawText.value = ''
  resetGoogleImportForm()
}

function handleImportClear() {
  if (importMode.value === 'text') {
    importRawText.value = ''
    return
  }
  resetGoogleImportForm()
}

onMounted(fetchGoogleAccounts)
</script>

<template>
  <div class="page-shell">
    <section class="hero-card">
      <div>
        <h1>Google 账号池</h1>
        <p>直连后端分页接口，聚合同步状态、家庭组与邀请链路信息</p>
      </div>
      <div class="hero-right">
        <div class="hero-actions">
          <el-button type="primary" :icon="Upload" @click="importDialogVisible = true">导入 Google 账号</el-button>
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
        <el-form-item label="同步状态">
          <el-select v-model="filterForm.syncStatus" placeholder="全部状态" clearable>
            <el-option v-for="item in syncStatusOptions" :key="item.value" :label="item.label" :value="item.value" />
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
            <el-button
              type="warning"
              plain
              :icon="RefreshRight"
              :loading="batchRefreshing"
              :disabled="!selectedRowIds.length"
              @click="handleBatchRefreshInfo"
            >
              批量获取信息<span v-if="selectedRowIds.length">（{{ selectedRowIds.length }}）</span>
            </el-button>
            <el-button :icon="Plus" @click="importDialogVisible = true">导入账号</el-button>
            <el-button text :icon="Refresh" @click="fetchGoogleAccounts">刷新</el-button>
          </div>
        </div>
      </template>

      <el-table
        :data="rows"
        v-loading="loading"
        class="account-table"
        :row-class-name="resolveRowClass"
        @row-click="handleRowClick"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="48" align="center" />
        <el-table-column prop="id" label="ID" width="96">
          <template #default="{ row }">{{ toNullableText(row.id) }}</template>
        </el-table-column>
        <el-table-column prop="email" label="邮箱" min-width="210" show-overflow-tooltip>
          <template #default="{ row }">
            <el-button link class="cell-link" @click.stop="handleRowClick(row)">{{ row.email }}</el-button>
          </template>
        </el-table-column>
        <el-table-column prop="recoveryEmail" label="辅助邮箱" min-width="170" show-overflow-tooltip>
          <template #default="{ row }">{{ toNullableText(row.recoveryEmail) }}</template>
        </el-table-column>
        <el-table-column prop="region" label="地区" width="120">
          <template #default="{ row }">{{ toNullableText(row.region) }}</template>
        </el-table-column>
        <el-table-column prop="subTier" label="订阅类型" width="120">
          <template #default="{ row }">{{ toNullableText(row.subTier) }}</template>
        </el-table-column>
        <el-table-column label="同步状态" width="120">
          <template #default="{ row }">
            <el-tag :type="resolveSyncTag(row.syncStatus).type" effect="light">{{ resolveSyncTag(row.syncStatus).text }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="家庭组" width="120">
          <template #default="{ row }">
            <el-tag :type="resolveBinaryTag(row.familyStatus, '已开通', '未开通').type" effect="plain">
              {{ resolveBinaryTag(row.familyStatus, '已开通', '未开通').text }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="邀请链接" width="120">
          <template #default="{ row }">
            <el-tag :type="resolveBinaryTag(row.inviteLinkStatus, '已生成', '无链接').type" effect="plain">
              {{ resolveBinaryTag(row.inviteLinkStatus, '已生成', '无链接').text }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="invitedCount" label="已邀请人数" width="120" />
        <el-table-column prop="expireDate" label="到期日期" width="122">
          <template #default="{ row }">{{ toNullableText(row.expireDate) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="110" align="center">
          <template #default="{ row }">
            <div class="row-ops">
              <el-tooltip content="刷新信息" placement="top">
                <el-button
                  circle
                  class="icon-op-btn icon-op-btn--refresh"
                  :icon="RefreshRight"
                  :loading="isRowRefreshing(row.id)"
                  @click.stop="handleRefreshInfo(row)"
                />
              </el-tooltip>
              <el-tooltip content="删除账号" placement="top">
                <el-button
                  circle
                  class="icon-op-btn icon-op-btn--delete"
                  :icon="Delete"
                  :loading="deletingId === row.id"
                  @click.stop="handleDelete(row)"
                />
              </el-tooltip>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="updatedAt" label="更新时间" min-width="170" />
      </el-table>

      <div class="pagination-wrap">
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
      v-model="importDialogVisible"
      title="导入 Google 账号"
      width="980px"
      destroy-on-close
      @closed="handleImportDialogClosed"
    >
      <div class="import-box">
        <div class="import-mode-switch">
          <div class="import-mode-toggle" :class="{ 'is-table': importMode === 'table' }" role="group" aria-label="导入模式切换">
            <span class="mode-indicator" :class="{ 'is-table': importMode === 'table' }"></span>
            <button type="button" class="mode-button" :class="{ active: importMode === 'text' }" @click="importMode = 'text'">
              文本粘贴
            </button>
            <button type="button" class="mode-button" :class="{ active: importMode === 'table' }" @click="importMode = 'table'">
              表单填写
            </button>
          </div>
        </div>

        <template v-if="importMode === 'text'">
          <el-alert type="info" show-icon :closable="false">
            <template #title>
              每行 1 条，支持 `---- / 逗号 / 竖线 / Tab` 分隔。推荐格式：`email,password,recoveryEmail,totpSecret,region,remark`。
              也支持简版：`email,password,totpSecret`。
            </template>
          </el-alert>

          <el-input
            v-model="importRawText"
            type="textarea"
            :rows="10"
            class="import-input"
            placeholder="alice@gmail.com,Pass@123,recovery@gmail.com,JBSWY3DPEHPK3PXP,US,备注"
          />
        </template>

        <template v-else>
          <el-alert type="info" show-icon :closable="false">
            <template #title>表单填写仅支持单账号上传，必填项：邮箱、密码、TOTP 密钥。</template>
          </el-alert>

          <el-form :model="importForm" label-position="top" class="import-form" @submit.prevent>
            <el-form-item label="邮箱*">
              <el-input v-model="importForm.email" placeholder="name@gmail.com" />
            </el-form-item>
            <el-form-item label="密码*">
              <el-input v-model="importForm.password" placeholder="登录密码" />
            </el-form-item>
            <el-form-item label="辅助邮箱">
              <el-input v-model="importForm.recoveryEmail" placeholder="可选" />
            </el-form-item>
            <el-form-item label="TOTP 密钥*">
              <el-input v-model="importForm.totpSecret" placeholder="Base32 密钥" />
            </el-form-item>
            <el-form-item label="地区">
              <el-input v-model="importForm.region" placeholder="可选" />
            </el-form-item>
            <el-form-item label="备注">
              <el-input v-model="importForm.remark" placeholder="可选" />
            </el-form-item>
          </el-form>
        </template>
      </div>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="importDialogVisible = false">取消</el-button>
          <el-button @click="handleImportClear">清空</el-button>
          <el-button type="primary" :loading="importing" @click="handleImportSubmit">开始导入</el-button>
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
  padding: 20px;
  border-radius: 18px;
  border: 1px solid rgba(16, 185, 129, 0.2);
  background:
    radial-gradient(circle at 86% 18%, rgba(34, 197, 94, 0.2), transparent 38%),
    linear-gradient(140deg, rgba(236, 253, 245, 0.92), rgba(244, 252, 248, 0.88));
  backdrop-filter: blur(10px);
}

.hero-card h1 {
  margin: 0;
  font-family: 'Space Grotesk', sans-serif;
  font-size: 1.32rem;
  color: var(--og-slate-900);
}

.hero-card p {
  margin: 8px 0 0;
  color: var(--og-slate-600);
}

.hero-right {
  display: grid;
  gap: 10px;
}

.hero-actions {
  display: flex;
  justify-content: flex-end;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(96px, 1fr));
  gap: 10px;
}

.stat-item {
  border-radius: 12px;
  border: 1px solid rgba(16, 185, 129, 0.16);
  background: rgba(255, 255, 255, 0.86);
  padding: 10px 12px;
}

.stat-item span {
  display: block;
  font-size: 0.75rem;
  color: var(--og-slate-600);
}

.stat-item strong {
  display: block;
  margin-top: 4px;
  font-family: 'Space Grotesk', sans-serif;
  font-size: 1.2rem;
  color: var(--og-slate-900);
}

.query-card,
.table-card {
  border-radius: 16px;
  border: 1px solid rgba(15, 23, 42, 0.06);
  background: var(--og-surface);
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
  backdrop-filter: blur(8px);
}

.query-form {
  display: grid;
  grid-template-columns: repeat(2, minmax(220px, 320px)) auto;
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
}

.table-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.table-header h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: 700;
  color: var(--og-slate-900);
}

.cell-link {
  padding: 0;
  height: auto;
  font-weight: 600;
}

.account-table {
  border-radius: 14px;
  overflow: hidden;
  border: 1px solid rgba(148, 163, 184, 0.22);
}

.table-card :deep(.account-table .el-table__header-wrapper th) {
  background: linear-gradient(180deg, #eef6ff 0%, #e2efff 100%);
  color: #1e3a8a;
  font-weight: 700;
}

.table-card :deep(.account-table .el-table__cell) {
  padding: 12px 0;
  border-bottom-color: rgba(148, 163, 184, 0.18);
}

.table-card :deep(.account-table .el-table__row > td) {
  transition: background-color 0.2s ease;
}

.table-card :deep(.account-table .el-table__row:nth-child(even) > td) {
  background: rgba(248, 250, 252, 0.92);
}

.table-card :deep(.clickable-row > td) {
  cursor: pointer;
}

.table-card :deep(.account-table .clickable-row:hover > td) {
  background: rgba(219, 234, 254, 0.5) !important;
}

.table-card :deep(.account-table .row-refreshing > td) {
  background: rgba(191, 219, 254, 0.58) !important;
}

.row-ops {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.icon-op-btn {
  width: 30px;
  height: 30px;
  border: 0;
  box-shadow: none;
  transition:
    transform 180ms cubic-bezier(0.22, 1, 0.36, 1),
    box-shadow 180ms ease,
    background-color 180ms ease,
    color 180ms ease;
}

.icon-op-btn :deep(.el-icon) {
  font-size: 14px;
}

.icon-op-btn--refresh {
  color: #1d4ed8;
  background: rgba(59, 130, 246, 0.12);
}

.icon-op-btn--refresh:hover {
  color: #1e40af;
  background: rgba(59, 130, 246, 0.2);
  box-shadow: 0 6px 14px rgba(59, 130, 246, 0.22);
}

.icon-op-btn--delete {
  color: #b91c1c;
  background: rgba(239, 68, 68, 0.12);
}

.icon-op-btn--delete:hover {
  color: #991b1b;
  background: rgba(239, 68, 68, 0.2);
  box-shadow: 0 6px 14px rgba(239, 68, 68, 0.2);
}

.icon-op-btn:active {
  transform: scale(0.9);
}

.icon-op-btn.is-loading {
  cursor: wait;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.import-box {
  display: grid;
  gap: 12px;
}

.import-mode-switch {
  display: flex;
  align-items: center;
  justify-content: flex-start;
}

.import-mode-toggle {
  position: relative;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  width: min(100%, 320px);
  padding: 4px;
  border-radius: 14px;
  border: 1px solid rgba(16, 185, 129, 0.2);
  background: linear-gradient(135deg, rgba(209, 250, 229, 0.68), rgba(236, 253, 245, 0.92));
  background-size: 200% 100%;
  background-position: 0 0;
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.12) inset;
  transition:
    background-position 360ms cubic-bezier(0.22, 1, 0.36, 1),
    box-shadow 260ms ease;
  overflow: hidden;
}

.import-mode-toggle.is-table {
  background-position: 100% 0;
  box-shadow: 0 4px 14px rgba(16, 185, 129, 0.16) inset;
}

.mode-indicator {
  position: absolute;
  top: 4px;
  left: 4px;
  width: calc(50% - 4px);
  height: 42px;
  border-radius: 10px;
  background: #ffffff;
  box-shadow:
    0 10px 20px rgba(16, 185, 129, 0.12),
    0 0 0 1px rgba(16, 185, 129, 0.16) inset;
  will-change: transform;
  transition:
    transform 380ms cubic-bezier(0.2, 1.35, 0.32, 1),
    box-shadow 320ms cubic-bezier(0.22, 1, 0.36, 1),
    filter 260ms ease;
}

.mode-indicator.is-table {
  transform: translateX(100%);
  filter: saturate(1.06);
  box-shadow:
    0 12px 24px rgba(16, 185, 129, 0.16),
    0 0 0 1px rgba(16, 185, 129, 0.2) inset;
}

.mode-button {
  position: relative;
  z-index: 1;
  height: 42px;
  border: 0;
  border-radius: 10px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 14px;
  font-size: 0.9rem;
  font-weight: 700;
  line-height: 1;
  color: var(--og-slate-600);
  background: transparent;
  cursor: pointer;
  transition:
    color 180ms ease,
    transform 180ms ease;
}

.mode-button:hover {
  color: #047857;
}

.mode-button.active {
  color: #065f46;
  text-shadow: 0 0 10px rgba(16, 185, 129, 0.12);
}

.mode-button:focus-visible {
  outline: 2px solid rgba(16, 185, 129, 0.45);
  outline-offset: 2px;
}

.mode-button:active {
  transform: translateY(1px) scale(0.985);
}

@media (prefers-reduced-motion: reduce) {
  .import-mode-toggle,
  .mode-indicator,
  .mode-button {
    transition: none !important;
  }
}

.import-input {
  margin-top: 4px;
}

.import-form {
  display: grid;
  grid-template-columns: repeat(2, minmax(220px, 1fr));
  gap: 12px;
}

.import-form :deep(.el-form-item) {
  margin-bottom: 0;
}

.import-form :deep(.el-form-item__label) {
  font-weight: 700;
  color: var(--og-slate-700);
}

.import-form :deep(.el-input__wrapper) {
  border-radius: 10px;
  box-shadow: 0 0 0 1px rgba(16, 185, 129, 0.2) inset;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

@media (max-width: 1080px) {
  .hero-card {
    grid-template-columns: 1fr;
  }

  .stats-grid {
    grid-template-columns: repeat(3, 1fr);
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

  .table-actions {
    width: 100%;
  }

  .row-ops {
    gap: 6px;
  }

  .import-mode-toggle {
    width: 100%;
  }

  .pagination-wrap {
    justify-content: center;
  }

  .import-form {
    grid-template-columns: 1fr;
  }
}
</style>
