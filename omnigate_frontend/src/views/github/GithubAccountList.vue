<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Plus, Refresh, Search, Upload } from '@element-plus/icons-vue'

import { deleteGithubAccount, importGithubAccounts, pageGithubAccounts } from '@/api/github'

const loading = ref(false)
const rows = ref([])
const router = useRouter()
const importDialogVisible = ref(false)
const importing = ref(false)
const importRawText = ref('')
const deletingId = ref(null)

const filterForm = reactive({
  username: '',
  accountStatus: undefined,
  proxyIp: '',
})

const pager = reactive({
  current: 1,
  size: 10,
  total: 0,
})

const statusOptions = [
  { label: 'active', value: 'active' },
  { label: 'locked', value: 'locked' },
  { label: 'banned', value: 'banned' },
]

const dashboardStats = computed(() => {
  const total = rows.value.length
  const activeCount = rows.value.filter((item) => item.accountStatus === 'active').length
  const proxyCount = rows.value.filter((item) => item.proxyIp).length
  return [
    { label: '当前页总数', value: total },
    { label: 'Active 账号', value: activeCount },
    { label: '已配置代理', value: proxyCount },
  ]
})

function resolveStatusTag(status) {
  if (status === 'active') return 'success'
  if (status === 'locked') return 'warning'
  if (status === 'banned') return 'danger'
  return 'info'
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

function parseGithubImportText(rawText) {
  const lines = rawText
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)

  return lines.map((line, index) => {
    const delimiter = detectDelimiter(line)
    const cells = line.split(delimiter).map((cell) => cell.trim())

    if (cells.length < 4) {
      throw new Error(`第 ${index + 1} 行字段不足，至少需要 username,email,password,totpSecret`)
    }

    const [username, email, password, totpSecret, proxyIp, accountStatus] = cells

    if (!username || !email || !password || !totpSecret) {
      throw new Error(`第 ${index + 1} 行存在必填字段为空（username/email/password/totpSecret）`)
    }

    const normalizedStatus = normalizeCell(accountStatus)
    if (normalizedStatus && !['active', 'locked', 'banned'].includes(normalizedStatus)) {
      throw new Error(`第 ${index + 1} 行账号状态仅支持 active/locked/banned`)
    }

    return {
      username,
      email,
      password,
      totpSecret,
      proxyIp: normalizeCell(proxyIp),
      accountStatus: normalizedStatus,
    }
  })
}

async function fetchGithubAccounts() {
  loading.value = true
  try {
    const pageData = await pageGithubAccounts({
      current: pager.current,
      size: pager.size,
      username: filterForm.username || undefined,
      accountStatus: filterForm.accountStatus,
      proxyIp: filterForm.proxyIp || undefined,
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
  fetchGithubAccounts()
}

function handleReset() {
  filterForm.username = ''
  filterForm.accountStatus = undefined
  filterForm.proxyIp = ''
  pager.current = 1
  fetchGithubAccounts()
}

function handleRowClick(row) {
  if (!row?.id) return
  router.push(`/github/accounts/${row.id}`)
}

function resolveRowClass() {
  return 'clickable-row'
}

async function handleDelete(row) {
  if (!row?.id) return

  try {
    await ElMessageBox.confirm(`确认删除 GitHub 账号「${row.username || row.id}」吗？`, '危险操作确认', {
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
    await deleteGithubAccount(row.id)
    ElMessage.success('账号已删除')

    if (rows.value.length === 1 && pager.current > 1) {
      pager.current -= 1
    }
    await fetchGithubAccounts()
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
    payload = parseGithubImportText(importRawText.value)
  } catch (error) {
    ElMessage.error(error.message || '导入数据格式不正确')
    return
  }

  importing.value = true
  try {
    const successCount = await importGithubAccounts(payload)
    ElMessage.success(`导入完成，成功 ${successCount ?? payload.length} 条`)
    importDialogVisible.value = false
    importRawText.value = ''
    pager.current = 1
    await fetchGithubAccounts()
  } finally {
    importing.value = false
  }
}

onMounted(fetchGithubAccounts)
</script>

<template>
  <div class="page-shell">
    <section class="hero-card">
      <div>
        <h1>GitHub 账号池</h1>
        <p>统一管理账号状态、代理配置与批量导入任务</p>
      </div>
      <div class="hero-right">
        <div class="hero-actions">
          <el-button type="primary" :icon="Upload" @click="importDialogVisible = true">导入 GitHub 账号</el-button>
        </div>
        <div class="stats-grid">
          <article v-for="item in dashboardStats" :key="item.label" class="stat-item">
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
          </article>
        </div>
      </div>
    </section>

    <el-card shadow="never" class="query-card">
      <el-form :model="filterForm" class="query-form" @submit.prevent>
        <el-form-item label="用户名">
          <el-input v-model="filterForm.username" clearable placeholder="输入用户名关键字" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="账号状态">
          <el-select v-model="filterForm.accountStatus" placeholder="全部状态" clearable>
            <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="代理 IP">
          <el-input v-model="filterForm.proxyIp" clearable placeholder="精确过滤代理 IP" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item class="actions">
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
          <el-button :icon="Upload" @click="importDialogVisible = true">导入账号</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="table-card">
      <template #header>
        <div class="table-header">
          <h3>GitHub 账号清单</h3>
          <div class="table-actions">
            <el-button :icon="Plus" @click="importDialogVisible = true">导入账号</el-button>
            <el-button text :icon="Refresh" @click="fetchGithubAccounts">刷新</el-button>
          </div>
        </div>
      </template>

      <el-table :data="rows" v-loading="loading" stripe :row-class-name="resolveRowClass" @row-click="handleRowClick">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="username" label="用户名" min-width="160">
          <template #default="{ row }">
            <el-button link class="cell-link" @click.stop="handleRowClick(row)">{{ row.username }}</el-button>
          </template>
        </el-table-column>
        <el-table-column prop="email" label="邮箱" min-width="220" />
        <el-table-column prop="proxyIp" label="代理 IP" min-width="150">
          <template #default="{ row }">{{ row.proxyIp || '-' }}</template>
        </el-table-column>
        <el-table-column prop="accountStatus" label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="resolveStatusTag(row.accountStatus)" effect="light">{{ row.accountStatus || '-' }}</el-tag>
          </template>
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
        <el-table-column prop="updatedAt" label="更新时间" min-width="180" />
      </el-table>

      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="pager.current"
          v-model:page-size="pager.size"
          background
          layout="total, sizes, prev, pager, next"
          :page-sizes="[10, 20, 50]"
          :total="pager.total"
          @current-change="fetchGithubAccounts"
          @size-change="fetchGithubAccounts"
        />
      </div>
    </el-card>

    <el-dialog v-model="importDialogVisible" title="导入 GitHub 账号" width="760px" destroy-on-close>
      <div class="import-box">
        <el-alert type="info" show-icon :closable="false">
          <template #title>
            每行 1 条，支持 `---- / 逗号 / 竖线 / Tab` 分隔。格式：`username,email,password,totpSecret,proxyIp,accountStatus`。
            其中 `accountStatus` 仅支持 `active/locked/banned`，可留空。
          </template>
        </el-alert>

        <el-input
          v-model="importRawText"
          type="textarea"
          :rows="10"
          class="import-input"
          placeholder="octocat,octo@example.com,Pass@123,JBSWY3DPEHPK3PXP,127.0.0.1:1080,active"
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
  border: 1px solid rgba(148, 163, 184, 0.24);
  background:
    radial-gradient(circle at 86% 18%, rgba(99, 102, 241, 0.24), transparent 36%),
    linear-gradient(140deg, #1f2937 0%, #1e293b 54%, #111827 100%);
  backdrop-filter: blur(10px);
}

.hero-card h1 {
  margin: 0;
  font-family: 'Space Grotesk', sans-serif;
  font-size: 1.32rem;
  color: #f8fafc;
}

.hero-card p {
  margin: 8px 0 0;
  color: rgba(241, 245, 249, 0.84);
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
  border: 1px solid rgba(241, 245, 249, 0.18);
  background: rgba(255, 255, 255, 0.08);
  padding: 10px 12px;
}

.stat-item span {
  display: block;
  font-size: 0.75rem;
  color: rgba(241, 245, 249, 0.74);
}

.stat-item strong {
  display: block;
  margin-top: 4px;
  font-family: 'Space Grotesk', sans-serif;
  font-size: 1.2rem;
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
}

.pagination-wrap {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.table-card :deep(.clickable-row > td) {
  cursor: pointer;
}

.cell-link {
  padding: 0;
  height: auto;
  font-weight: 600;
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

@media (max-width: 980px) {
  .hero-card {
    grid-template-columns: 1fr;
  }

  .stats-grid {
    grid-template-columns: repeat(3, 1fr);
  }

  .query-form {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 640px) {
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
