<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Check, CopyDocument, Delete, Refresh } from '@element-plus/icons-vue'
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
const copiedField = ref('')
let copyFeedbackTimer = null
const accountId = computed(() => String(route.params.id || '').trim())
const subTierOptions = [{ label: 'Free', value: 'free' }, { label: 'Plus', value: 'plus' }, { label: 'Team', value: 'team' }, { label: 'Go', value: 'go' }]
const statusOptions = [{ label: '可用', value: 'active' }, { label: '锁定', value: 'locked' }, { label: '封禁', value: 'banned' }]
const editForm = reactive({ email: '', password: '', sessionToken: '', totpSecret: '', subTier: 'free', accountStatus: 'active', expireDate: '' })

const formRules = {
  email: [{ required: true, message: '请输入账号邮箱', trigger: 'blur' }, { type: 'email', message: '邮箱格式不正确', trigger: ['blur', 'change'] }],
  password: [{
    trigger: ['blur', 'change'],
    validator: (_rule, value, callback) => {
      const normalized = normalizeCell(value)
      if (normalized && normalized.length > 255) return callback(new Error('密码长度不能超过255'))
      callback()
    },
  }],
  sessionToken: [{
    trigger: ['blur', 'change'],
    validator: (_rule, value, callback) => {
      if (value && String(value).length > 1024) return callback(new Error('SessionToken 长度不能超过1024'))
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

const summaryItems = computed(() => {
  const data = detail.value || {}
  return [
    { label: '账号状态', value: formatAccountStatus(data.accountStatus), tone: resolveStatusTag(data.accountStatus) },
    { label: '订阅层级', value: formatSubTier(data.subTier), tone: resolveTierTag(data.subTier) },
    { label: '到期日期', value: toNullableText(data.expireDate), tone: 'neutral' },
    { label: '更新时间', value: toNullableText(data.updatedAt), tone: 'neutral' },
  ]
})

function normalizeCell(value) { const text = String(value ?? '').trim(); return text || undefined }
function toNullableText(value) { return value || '-' }
function formatAccountStatus(status) { return ({ active: '可用', locked: '锁定', banned: '封禁' }[status]) || status || '-' }
function formatSubTier(subTier) { return ({ free: 'Free', plus: 'Plus', team: 'Team', go: 'Go' }[subTier]) || subTier || '-' }
function resolveStatusTag(status) { return status === 'active' ? 'success' : status === 'locked' ? 'warning' : status === 'banned' ? 'danger' : 'info' }
function resolveTierTag(subTier) { return subTier === 'team' ? 'primary' : subTier === 'plus' ? 'success' : subTier === 'go' ? 'warning' : 'info' }

async function handleCopyValue(value, label) {
  const text = String(value ?? '').trim()
  if (!text) return ElMessage.warning(`${label}为空，无法复制`)
  try { await navigator.clipboard.writeText(text); ElMessage.success(`${label}已复制`) } catch { ElMessage.error('复制失败，请手动复制') }
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

async function handleCopyValueWithState(value, label, fieldKey) {
  const text = String(value ?? '').trim()
  if (!text) return ElMessage.warning(`${label}为空，无法复制`)
  try {
    await navigator.clipboard.writeText(text)
    markCopied(fieldKey)
    ElMessage.success(`${label}已复制`)
  } catch {
    ElMessage.error('复制失败，请手动复制')
  }
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
  } finally { loading.value = false }
}

async function handleSave() {
  await editFormRef.value?.validate()
  const payload = buildUpdatePayload()
  if (!Object.keys(payload).length) return ElMessage.info('未检测到变更内容')
  saving.value = true
  try { await updateChatgptAccount(accountId.value, payload); ElMessage.success('账号信息已更新'); await fetchDetail() } finally { saving.value = false }
}

function handleReset() { fillEditForm(detail.value || {}); editFormRef.value?.clearValidate() }

async function handleQuickStatus(nextStatus) {
  if (!detail.value?.id || !nextStatus || nextStatus === detail.value.accountStatus) return
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

async function handleDelete() {
  if (!detail.value?.id) return
  try { await ElMessageBox.confirm(`确认删除 ChatGPT 账号「${detail.value.email || detail.value.id}」吗？`, '危险操作确认', { type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消', confirmButtonClass: 'el-button--danger' }) } catch { return }
  deleting.value = true
  try { await deleteChatgptAccount(detail.value.id); ElMessage.success('账号已删除'); await router.replace('/chatgpt/accounts') } finally { deleting.value = false }
}

onMounted(fetchDetail)

onBeforeUnmount(() => {
  if (copyFeedbackTimer) {
    clearTimeout(copyFeedbackTimer)
    copyFeedbackTimer = null
  }
})
</script>

<template>
  <div class="detail-page" v-loading="loading">
    <section class="detail-hero">
      <div class="hero-copy">
        <el-button text :icon="ArrowLeft" class="back-link" @click="router.push('/chatgpt/accounts')">返回账号池</el-button>
        <span class="eyebrow">ChatGPT Account Detail</span>
        <h1>{{ detail?.email || '账号详情' }}</h1>
        <div class="hero-tags">
          <el-tag :type="resolveStatusTag(detail?.accountStatus)" effect="dark">{{ formatAccountStatus(detail?.accountStatus) }}</el-tag>
          <el-tag :type="resolveTierTag(detail?.subTier)" effect="plain">{{ formatSubTier(detail?.subTier) }}</el-tag>
          <el-tag effect="plain">到期：{{ toNullableText(detail?.expireDate) }}</el-tag>
        </div>
      </div>
      <div class="hero-actions">
        <el-button :icon="Refresh" @click="fetchDetail">刷新</el-button>
        <el-button :icon="CopyDocument" @click="handleCopyValueWithState(detail?.email, '邮箱', 'hero-email')">复制邮箱</el-button>
        <el-button type="danger" plain :icon="Delete" :loading="deleting" @click="handleDelete">删除账号</el-button>
      </div>
    </section>

    <section class="summary-grid">
      <article v-for="item in summaryItems" :key="item.label" class="summary-card">
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
      </article>
    </section>

    <section class="content-grid">
      <article class="surface-card">
        <div class="panel-head">
          <div>
            <h2>编辑账号信息</h2>
            <p>密码留空表示不修改；SessionToken 支持直接覆盖或清空。</p>
          </div>
        </div>
        <el-form ref="editFormRef" :model="editForm" :rules="formRules" label-position="top" class="dialog-form">
          <div class="form-grid">
            <el-form-item label="账号邮箱" prop="email"><el-input v-model="editForm.email" placeholder="name@example.com" /></el-form-item>
            <el-form-item label="登录密码" prop="password"><el-input v-model="editForm.password" type="password" show-password placeholder="留空表示不修改" /></el-form-item>
            <el-form-item label="2FA / TOTP 密钥" prop="totpSecret"><el-input v-model="editForm.totpSecret" placeholder="可选，留空表示不修改" /></el-form-item>
            <el-form-item label="订阅层级"><el-select v-model="editForm.subTier"><el-option v-for="item in subTierOptions" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item>
            <el-form-item label="账号状态"><el-select v-model="editForm.accountStatus"><el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item>
            <el-form-item label="到期日期"><el-date-picker v-model="editForm.expireDate" type="date" value-format="YYYY-MM-DD" placeholder="可选" /></el-form-item>
            <el-form-item label="SessionToken" prop="sessionToken" class="span-2"><el-input v-model="editForm.sessionToken" type="textarea" :rows="4" placeholder="可留空" /></el-form-item>
          </div>
        </el-form>
        <div class="dialog-footer">
          <el-button @click="handleReset">重置</el-button>
          <el-button type="primary" :loading="saving" @click="handleSave">保存修改</el-button>
        </div>
      </article>

      <aside class="side-stack">
        <article class="surface-card">
          <div class="panel-head compact">
            <div>
              <h2>快速状态切换</h2>
              <p>常用状态直接切，不必先改表单再保存。</p>
            </div>
          </div>
          <div class="status-switch">
            <el-button v-for="item in statusOptions" :key="item.value" :type="editForm.accountStatus === item.value ? 'primary' : 'default'" :plain="editForm.accountStatus !== item.value" :loading="statusUpdating && statusTarget === item.value" @click="handleQuickStatus(item.value)">{{ item.label }}</el-button>
          </div>
        </article>

        <article class="surface-card">
          <div class="panel-head compact">
            <div>
              <h2>复制与凭据</h2>
              <p>把常用字段收拢到一起，减少来回找位置。</p>
            </div>
          </div>
          <div class="copy-block">
            <div class="copy-block-head">
              <span>邮箱</span>
              <el-button
                text
                class="copy-action-btn copy-action-btn--email"
                :class="{ 'is-copied': copiedField === 'email' }"
                :icon="copiedField === 'email' ? Check : CopyDocument"
                @click="handleCopyValueWithState(detail?.email, '邮箱', 'email')"
              >
                {{ copiedField === 'email' ? '已复制' : '复制邮箱' }}
              </el-button>
            </div>
            <strong>{{ toNullableText(detail?.email) }}</strong>
          </div>
          <div class="copy-block">
            <div class="copy-block-head">
              <span>密码</span>
              <el-button
                text
                class="copy-action-btn copy-action-btn--password"
                :class="{ 'is-copied': copiedField === 'password' }"
                :icon="copiedField === 'password' ? Check : CopyDocument"
                @click="handleCopyValueWithState(detail?.password, '密码', 'password')"
              >
                {{ copiedField === 'password' ? '已复制' : '复制密码' }}
              </el-button>
            </div>
            <strong>{{ toNullableText(detail?.password) }}</strong>
          </div>
          <div class="copy-block">
            <div class="copy-block-head">
              <span>2FA / TOTP</span>
              <el-button
                text
                class="copy-action-btn copy-action-btn--totp"
                :class="{ 'is-copied': copiedField === 'totp-secret' }"
                :icon="copiedField === 'totp-secret' ? Check : CopyDocument"
                @click="handleCopyValueWithState(detail?.totpSecret, '2FA 密钥', 'totp-secret')"
              >
                {{ copiedField === 'totp-secret' ? '已复制' : '复制 2FA' }}
              </el-button>
            </div>
            <strong>{{ toNullableText(detail?.totpSecret) }}</strong>
          </div>
          <div class="copy-block">
            <div class="copy-block-head">
              <span>SessionToken</span>
              <el-button
                text
                class="copy-action-btn copy-action-btn--token"
                :class="{ 'is-copied': copiedField === 'session-token' }"
                :icon="copiedField === 'session-token' ? Check : CopyDocument"
                @click="handleCopyValueWithState(detail?.sessionToken, 'SessionToken', 'session-token')"
              >
                {{ copiedField === 'session-token' ? '已复制' : '复制令牌' }}
              </el-button>
            </div>
            <div class="token-box">{{ toNullableText(detail?.sessionToken) }}</div>
          </div>
        </article>

        <article class="surface-card">
          <div class="panel-head compact">
            <div>
              <h2>元数据</h2>
            </div>
          </div>
          <div class="meta-list">
            <div><span>账号 ID</span><strong>{{ toNullableText(detail?.id) }}</strong></div>
            <div><span>创建时间</span><strong>{{ toNullableText(detail?.createdAt) }}</strong></div>
            <div><span>更新时间</span><strong>{{ toNullableText(detail?.updatedAt) }}</strong></div>
          </div>
        </article>
      </aside>
    </section>
  </div>
</template>

<style scoped>
.detail-page{display:grid;gap:18px}
.detail-hero,.surface-card{border-radius:22px}
.detail-hero{display:flex;justify-content:space-between;gap:18px;align-items:flex-start;padding:26px;background:radial-gradient(circle at top right,rgba(45,212,191,.16),transparent 28%),radial-gradient(circle at 14% 20%,rgba(249,115,22,.2),transparent 24%),linear-gradient(140deg,#111827 0%,#172033 44%,#1f2937 100%);color:#f8fafc;border:1px solid rgba(255,255,255,.08);box-shadow:0 24px 64px rgba(15,23,42,.22)}
.eyebrow{display:inline-flex;margin-top:10px;padding:6px 10px;border-radius:999px;background:rgba(255,255,255,.09);color:rgba(255,255,255,.72);font-size:.74rem;letter-spacing:.06em;text-transform:uppercase}
.back-link{padding-left:0;color:rgba(226,232,240,.9)}.hero-copy h1{margin:12px 0 0;font-family:'Space Grotesk',sans-serif;font-size:1.9rem;line-height:1.08}
.hero-tags,.hero-actions,.status-switch,.dialog-footer{display:flex;flex-wrap:wrap;gap:10px}.hero-tags{margin-top:14px}
.surface-card{padding:22px;border:1px solid rgba(148,163,184,.18);background:radial-gradient(circle at top right,rgba(45,212,191,.08),transparent 24%),linear-gradient(180deg,rgba(255,255,255,.96),rgba(248,250,252,.96));box-shadow:0 18px 48px rgba(15,23,42,.08)}
.summary-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}
.summary-card{padding:16px;border-radius:18px;background:#fff;border:1px solid rgba(148,163,184,.16)}
.summary-card span{display:block;color:#64748b;font-size:.8rem}.summary-card strong{display:block;margin-top:8px;font-family:'Fira Code','Space Grotesk',monospace;color:#0f172a;font-size:1.1rem}
.content-grid{display:grid;grid-template-columns:minmax(0,1.2fr) minmax(320px,.8fr);gap:18px}.side-stack,.dialog-form,.meta-list{display:grid;gap:16px}
.panel-head{display:flex;justify-content:space-between;gap:16px;margin-bottom:16px}.panel-head.compact{margin-bottom:14px}.panel-head h2{margin:0;font-family:'Space Grotesk',sans-serif;font-size:1.08rem;color:#0f172a}.panel-head p{margin:6px 0 0;color:#475569;line-height:1.6}
.form-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px 16px}.span-2{grid-column:1/-1}
.copy-block{display:grid;gap:10px;padding:16px;border-radius:18px;background:linear-gradient(180deg,#fff,#f8fafc);border:1px solid rgba(148,163,184,.16);box-shadow:inset 0 1px 0 rgba(255,255,255,.85)}
.copy-block span{color:#64748b;font-size:.8rem}
.copy-block strong{font-family:'Fira Code','Consolas',monospace;color:#0f172a;word-break:break-all;font-size:.94rem;line-height:1.55}
.copy-block-head{display:flex;align-items:center;justify-content:space-between;gap:12px}
.copy-action-btn{height:32px;padding:0 12px;border-radius:999px;color:#334155;background:rgba(15,23,42,.05);border:1px solid rgba(148,163,184,.24);font-weight:700;transition:transform 180ms cubic-bezier(.22,1,.36,1),background-color 180ms ease,color 180ms ease,border-color 180ms ease,box-shadow 180ms ease}
.copy-action-btn:hover{color:#0f172a;background:rgba(15,23,42,.08);border-color:rgba(100,116,139,.34)}
.copy-action-btn:active{transform:translateY(1px) scale(.98)}
.copy-action-btn.is-copied{color:#065f46;background:rgba(16,185,129,.12);border-color:rgba(16,185,129,.28);box-shadow:0 8px 18px rgba(16,185,129,.16)}
.copy-action-btn--email{background:rgba(37,99,235,.08);border-color:rgba(37,99,235,.18);color:#1d4ed8}
.copy-action-btn--email:hover{background:rgba(37,99,235,.12);border-color:rgba(37,99,235,.26)}
.copy-action-btn--password{background:rgba(245,158,11,.1);border-color:rgba(245,158,11,.2);color:#b45309}
.copy-action-btn--password:hover{background:rgba(245,158,11,.14);border-color:rgba(245,158,11,.28)}
.copy-action-btn--totp{background:rgba(8,145,178,.1);border-color:rgba(8,145,178,.2);color:#0f766e}
.copy-action-btn--totp:hover{background:rgba(8,145,178,.14);border-color:rgba(8,145,178,.28)}
.copy-action-btn--token{background:rgba(15,118,110,.1);border-color:rgba(15,118,110,.18);color:#0f766e}
.copy-action-btn--token:hover{background:rgba(15,118,110,.14);border-color:rgba(15,118,110,.26)}
.token-box{max-height:140px;overflow:auto;padding:10px;border-radius:12px;background:#f8fafc;border:1px dashed rgba(148,163,184,.4);font-family:'Fira Code','Consolas',monospace;font-size:.8rem;color:#0f172a;word-break:break-all}
.meta-list>div{display:grid;gap:6px;padding:12px 0;border-bottom:1px solid rgba(148,163,184,.16)}.meta-list>div:last-child{border-bottom:none}.meta-list span{color:#64748b;font-size:.8rem}.meta-list strong{color:#0f172a;font-weight:600;word-break:break-all}
@media (max-width:1080px){.summary-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.content-grid{grid-template-columns:1fr}}
@media (max-width:760px){.detail-hero,.panel-head,.dialog-footer,.copy-block-head{flex-direction:column;align-items:flex-start}.hero-actions{width:100%}.summary-grid,.form-grid{grid-template-columns:1fr}}
@media (prefers-reduced-motion:reduce){.copy-action-btn{transition:none}}
</style>
