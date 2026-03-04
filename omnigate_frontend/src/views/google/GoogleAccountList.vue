<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Plus, Refresh, Search, Upload } from '@element-plus/icons-vue'

import { deleteGoogleAccount, importGoogleAccounts, pageGoogleAccounts } from '@/api/google'

const loading = ref(false)
const rows = ref([])
const router = useRouter()
const importDialogVisible = ref(false)
const importing = ref(false)
const importRawText = ref('')
const deletingId = ref(null)

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

function handleRowClick(row) {
  if (!row?.id) return
  try {
    sessionStorage.setItem(`og-google-account-snapshot-${row.id}`, JSON.stringify(row))
  } catch {
    // ignore snapshot persistence failure
  }
  router.push(`/google/accounts/${row.id}`)
}

function resolveRowClass() {
  return 'clickable-row'
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
  if (!importRawText.value.trim()) {
    ElMessage.warning('请先粘贴待导入数据')
    return
  }

  let payload = []
  try {
    payload = parseGoogleImportText(importRawText.value)
  } catch (error) {
    ElMessage.error(error.message || '导入数据格式不正确')
    return
  }

  importing.value = true
  try {
    const successCount = await importGoogleAccounts(payload)
    ElMessage.success(`导入完成，成功 ${successCount ?? payload.length} 条`)
    importDialogVisible.value = false
    importRawText.value = ''
    pager.current = 1
    await fetchGoogleAccounts()
  } finally {
    importing.value = false
  }
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
            <el-button :icon="Plus" @click="importDialogVisible = true">导入账号</el-button>
            <el-button text :icon="Refresh" @click="fetchGoogleAccounts">刷新</el-button>
          </div>
        </div>
      </template>

      <el-table :data="rows" v-loading="loading" stripe :row-class-name="resolveRowClass" @row-click="handleRowClick">
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
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
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

    <el-dialog v-model="importDialogVisible" title="导入 Google 账号" width="760px" destroy-on-close>
      <div class="import-box">
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
      </div>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="importDialogVisible = false">取消</el-button>
          <el-button @click="importRawText = ''">清空</el-button>
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
  background: var(--og-surface);
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
}

.table-header h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: 700;
  color: var(--og-slate-900);
}

.table-card :deep(.el-table__cell) {
  padding: 11px 0;
}

.table-card :deep(.clickable-row > td) {
  cursor: pointer;
}

.cell-link {
  padding: 0;
  height: auto;
  font-weight: 600;
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

.import-input {
  margin-top: 4px;
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

  .pagination-wrap {
    justify-content: center;
  }
}
</style>
