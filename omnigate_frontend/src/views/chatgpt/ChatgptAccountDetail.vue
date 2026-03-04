<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, CopyDocument, Delete, Refresh } from '@element-plus/icons-vue'

import {
  deleteChatgptAccount,
  getChatgptAccount,
  updateChatgptAccount,
  updateChatgptAccountStatus,
} from '@/api/chatgpt'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const saving = ref(false)
const deleting = ref(false)
const statusUpdating = ref(false)
const statusTarget = ref('')
const detail = ref(null)
const editFormRef = ref()

const accountId = computed(() => String(route.params.id || '').trim())

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

const editForm = reactive({
  email: '',
  password: '',
  sessionToken: '',
  subTier: 'free',
  accountStatus: 'active',
  expireDate: '',
})

const formRules = {
  email: [
    { required: true, message: '请输入账号邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: ['blur', 'change'] },
  ],
  password: [
    {
      trigger: ['blur', 'change'],
      validator: (_rule, value, callback) => {
        const normalized = normalizeCell(value)
        if (normalized && normalized.length > 255) {
          callback(new Error('密码长度不能超过255'))
          return
        }
        callback()
      },
    },
  ],
  sessionToken: [
    {
      trigger: ['blur', 'change'],
      validator: (_rule, value, callback) => {
        if (value && String(value).length > 1024) {
          callback(new Error('SessionToken 长度不能超过1024'))
          return
        }
        callback()
      },
    },
  ],
}

const summaryItems = computed(() => {
  const data = detail.value || {}
  return [
    { label: '账号状态', value: toNullableText(data.accountStatus) },
    { label: '订阅层级', value: toNullableText(data.subTier) },
    { label: '到期日期', value: toNullableText(data.expireDate) },
    { label: '更新时间', value: toNullableText(data.updatedAt) },
  ]
})

function normalizeCell(value) {
  const text = String(value ?? '').trim()
  return text || undefined
}

function toNullableText(value) {
  return value || '-'
}

async function handleCopyValue(value, label) {
  const text = String(value ?? '').trim()
  if (!text) {
    ElMessage.warning(`${label}为空，无法复制`)
    return
  }
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success(`${label}已复制`)
  } catch {
    ElMessage.error('复制失败，请手动复制')
  }
}

function fillEditForm(data) {
  editForm.email = data?.email || ''
  editForm.password = ''
  editForm.sessionToken = data?.sessionToken || ''
  editForm.subTier = data?.subTier || 'free'
  editForm.accountStatus = data?.accountStatus || 'active'
  editForm.expireDate = data?.expireDate || ''
}

function buildUpdatePayload() {
  const payload = {}
  const source = detail.value || {}

  const currentEmail = normalizeCell(editForm.email) || ''
  if (currentEmail && currentEmail !== (source.email || '')) {
    payload.email = currentEmail
  }

  const currentPassword = normalizeCell(editForm.password)
  if (currentPassword) {
    payload.password = currentPassword
  }

  const currentToken = normalizeCell(editForm.sessionToken) || ''
  if (currentToken !== (source.sessionToken || '')) {
    payload.sessionToken = currentToken
  }

  const currentSubTier = normalizeCell(editForm.subTier) || ''
  if (currentSubTier && currentSubTier !== (source.subTier || '')) {
    payload.subTier = currentSubTier
  }

  const currentStatus = normalizeCell(editForm.accountStatus) || ''
  if (currentStatus && currentStatus !== (source.accountStatus || '')) {
    payload.accountStatus = currentStatus
  }

  const currentExpireDate = editForm.expireDate || ''
  if (currentExpireDate && currentExpireDate !== (source.expireDate || '')) {
    payload.expireDate = currentExpireDate
  }

  return payload
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
    fillEditForm(detail.value)
  } catch {
    ElMessage.error('获取 ChatGPT 账号详情失败')
    router.replace('/chatgpt/accounts')
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  await editFormRef.value?.validate()

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
  } finally {
    saving.value = false
  }
}

function handleReset() {
  fillEditForm(detail.value || {})
  editFormRef.value?.clearValidate()
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
    ElMessage.success(`状态已切换为 ${nextStatus}`)
  } finally {
    statusUpdating.value = false
    statusTarget.value = ''
  }
}

async function handleDelete() {
  if (!detail.value?.id) return

  try {
    await ElMessageBox.confirm(`确认删除 ChatGPT 账号「${detail.value.email || detail.value.id}」吗？`, '危险操作确认', {
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
    await deleteChatgptAccount(detail.value.id)
    ElMessage.success('账号已删除')
    await router.replace('/chatgpt/accounts')
  } finally {
    deleting.value = false
  }
}

onMounted(fetchDetail)
</script>

<template>
  <div class="detail-page" v-loading="loading">
    <section class="detail-hero">
      <div>
        <h1>ChatGPT 账号详情</h1>
        <p>{{ detail?.email || '-' }}</p>
      </div>
      <div class="hero-actions">
        <div class="status-switch">
          <el-button
            v-for="item in statusOptions"
            :key="item.value"
            :type="editForm.accountStatus === item.value ? 'primary' : 'default'"
            :plain="editForm.accountStatus !== item.value"
            size="small"
            :loading="statusUpdating && statusTarget === item.value"
            @click="handleQuickStatus(item.value)"
          >
            {{ item.label }}
          </el-button>
        </div>
        <div class="control-buttons">
          <el-button :icon="Refresh" @click="fetchDetail">刷新</el-button>
          <el-button type="danger" plain :icon="Delete" :loading="deleting" @click="handleDelete">删除账号</el-button>
          <el-button type="primary" :icon="ArrowLeft" @click="router.push('/chatgpt/accounts')">返回列表</el-button>
        </div>
      </div>
    </section>

    <section class="summary-grid">
      <article v-for="item in summaryItems" :key="item.label" class="summary-card">
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
      </article>
    </section>

    <section class="content-grid">
      <article class="panel-card">
        <header class="panel-header">
          <h3>编辑账号信息</h3>
          <p>密码留空即保持原值；SessionToken 支持清空后保存。</p>
        </header>

        <el-form ref="editFormRef" :model="editForm" :rules="formRules" label-width="110px">
          <el-form-item label="账号邮箱" prop="email">
            <el-input v-model="editForm.email" placeholder="name@example.com" />
          </el-form-item>
          <el-form-item label="登录密码" prop="password">
            <el-input v-model="editForm.password" type="password" show-password placeholder="留空表示不修改" />
          </el-form-item>
          <el-form-item label="SessionToken" prop="sessionToken">
            <el-input v-model="editForm.sessionToken" type="textarea" :rows="3" placeholder="可留空" />
          </el-form-item>
          <el-form-item label="订阅层级">
            <el-select v-model="editForm.subTier" placeholder="选择订阅层级">
              <el-option v-for="item in subTierOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="账号状态">
            <el-select v-model="editForm.accountStatus" placeholder="选择账号状态">
              <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="到期日期">
            <el-date-picker v-model="editForm.expireDate" type="date" value-format="YYYY-MM-DD" placeholder="可选" />
          </el-form-item>
        </el-form>

        <div class="form-footer">
          <el-button @click="handleReset">重置</el-button>
          <el-button type="primary" :loading="saving" @click="handleSave">保存修改</el-button>
        </div>
      </article>

      <article class="panel-card">
        <header class="panel-header">
          <h3>元数据</h3>
        </header>

        <el-descriptions :column="1" class="detail-descriptions">
          <el-descriptions-item label="账号 ID">{{ toNullableText(detail?.id) }}</el-descriptions-item>
          <el-descriptions-item label="邮箱">
            <div class="copyable-field">
              <span class="copy-text">{{ toNullableText(detail?.email) }}</span>
              <el-button
                text
                class="copy-btn"
                :icon="CopyDocument"
                :disabled="!detail?.email"
                @click="handleCopyValue(detail?.email, '邮箱')"
              >
                复制
              </el-button>
            </div>
          </el-descriptions-item>
          <el-descriptions-item label="密码">
            <div class="copyable-field">
              <span class="copy-text">{{ toNullableText(detail?.password) }}</span>
              <el-button
                text
                class="copy-btn"
                :icon="CopyDocument"
                :disabled="!detail?.password"
                @click="handleCopyValue(detail?.password, '密码')"
              >
                复制
              </el-button>
            </div>
          </el-descriptions-item>
          <el-descriptions-item label="订阅层级">{{ toNullableText(detail?.subTier) }}</el-descriptions-item>
          <el-descriptions-item label="账号状态">{{ toNullableText(detail?.accountStatus) }}</el-descriptions-item>
          <el-descriptions-item label="到期日期">{{ toNullableText(detail?.expireDate) }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ toNullableText(detail?.createdAt) }}</el-descriptions-item>
          <el-descriptions-item label="更新时间">{{ toNullableText(detail?.updatedAt) }}</el-descriptions-item>
        </el-descriptions>

        <div class="token-viewer">
          <div class="token-viewer-header">
            <p>SessionToken 预览</p>
            <el-button
              text
              class="copy-btn"
              :icon="CopyDocument"
              :disabled="!detail?.sessionToken"
              @click="handleCopyValue(detail?.sessionToken, 'SessionToken')"
            >
              复制
            </el-button>
          </div>
          <div class="token-content">{{ toNullableText(detail?.sessionToken) }}</div>
        </div>
      </article>
    </section>
  </div>
</template>

<style scoped>
.detail-page {
  display: grid;
  gap: 16px;
}

.detail-hero {
  border-radius: 14px;
  padding: 20px;
  background:
    radial-gradient(circle at 86% 18%, rgba(251, 146, 60, 0.34), transparent 34%),
    linear-gradient(136deg, #7c2d12 0%, #9a3412 54%, #b45309 100%);
  color: #f8fbff;
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: center;
}

.detail-hero h1 {
  margin: 0;
  font-size: 1.3rem;
}

.detail-hero p {
  margin: 6px 0 0;
  color: rgba(248, 251, 255, 0.84);
  font-size: 0.92rem;
}

.hero-actions {
  display: grid;
  gap: 8px;
  justify-items: end;
}

.status-switch,
.control-buttons {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
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
  font-family: 'Fira Code', 'Space Grotesk', monospace;
  font-size: 1.04rem;
}

.content-grid {
  display: grid;
  grid-template-columns: 1.2fr 0.8fr;
  gap: 16px;
}

.panel-card {
  border-radius: 12px;
  border: 1px solid rgba(23, 37, 48, 0.08);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
  background: #ffffff;
  padding: 18px;
}

.panel-header {
  margin-bottom: 12px;
}

.panel-header h3 {
  margin: 0;
  color: var(--og-slate-900);
  font-size: 1rem;
}

.panel-header p {
  margin: 6px 0 0;
  color: var(--og-slate-600);
  font-size: 0.82rem;
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
  width: 108px;
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

.copyable-field {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.copy-text {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.copy-btn {
  flex-shrink: 0;
  padding: 0;
}

.form-footer {
  margin-top: 10px;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.token-viewer {
  margin-top: 12px;
}

.token-viewer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.token-viewer p {
  margin: 0 0 8px;
  color: var(--og-slate-600);
  font-size: 0.82rem;
}

.token-content {
  border-radius: 10px;
  border: 1px dashed rgba(23, 37, 48, 0.2);
  background: #f8fafc;
  color: var(--og-slate-800);
  font-family: 'Fira Code', 'Consolas', monospace;
  font-size: 0.8rem;
  line-height: 1.6;
  padding: 10px;
  word-break: break-all;
}

@media (max-width: 1080px) {
  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .content-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 780px) {
  .detail-hero {
    flex-direction: column;
    align-items: flex-start;
  }

  .hero-actions {
    width: 100%;
    justify-items: start;
  }

  .status-switch,
  .control-buttons {
    width: 100%;
    justify-content: flex-start;
  }
}

@media (max-width: 640px) {
  .summary-grid {
    grid-template-columns: 1fr;
  }
}
</style>
