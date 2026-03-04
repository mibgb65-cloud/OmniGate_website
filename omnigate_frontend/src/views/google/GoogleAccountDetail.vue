<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Check, CopyDocument, Delete, Plus, Refresh } from '@element-plus/icons-vue'

import { deleteGoogleAccount, getGoogleAccountDetail, listGoogleFamilyMembers, listGoogleInviteLinks } from '@/api/google'
import TotpCodeTool from '@/components/security/TotpCodeTool.vue'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const detail = ref(null)
const familyMembers = ref([])
const inviteLinks = ref([])
const deleting = ref(false)
const copiedField = ref('')
const addMemberPanelOpen = ref(false)
const addingMember = ref(false)
const newMemberEmail = ref('')
let copyFeedbackTimer = null

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

const summaryItems = computed(() => {
  const data = detail.value || {}
  return [
    { label: '同步状态', value: resolveSyncText(data.syncStatus) },
    { label: '家庭组状态', value: resolveBinaryText(data.familyStatus, '已开通', '未开通') },
    { label: '邀请链接状态', value: resolveBinaryText(data.inviteLinkStatus, '已生成', '无链接') },
    { label: '已邀请人数', value: data.invitedCount ?? 0 },
  ]
})

function toNullableText(value) {
  return value || '-'
}

function resolveSyncText(status) {
  if (status === 1) return '同步成功'
  if (status === 2) return '同步失败'
  return '待同步'
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

function wait(ms) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms)
  })
}

function formatDateOnly(date = new Date()) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
}

function deriveMemberNameFromEmail(email) {
  const localPart = String(email || '').split('@')[0]?.trim()
  return localPart || 'member'
}

function resetAddMemberForm() {
  newMemberEmail.value = ''
}

function openAddMemberPanel() {
  addMemberPanelOpen.value = true
}

function closeAddMemberPanel() {
  addMemberPanelOpen.value = false
  resetAddMemberForm()
}

function resolveFamilyRowClass({ row }) {
  if (row?.__mock) return 'family-row-mock'
  return ''
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

  addingMember.value = true
  try {
    await wait(580 + Math.floor(Math.random() * 520))

    familyMembers.value = [
      {
        id: Date.now(),
        memberName: deriveMemberNameFromEmail(email),
        memberEmail: email,
        inviteDate: formatDateOnly(new Date()),
        memberRole: 2,
        __mock: true,
      },
      ...familyMembers.value,
    ]

    if (detail.value) {
      detail.value.familyStatus = 1
      detail.value.invitedCount = Number(detail.value.invitedCount || 0) + 1
    }

    closeAddMemberPanel()
    ElMessage.success('成员已添加（前端模拟）')
  } finally {
    addingMember.value = false
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

async function fetchDetail() {
  if (!accountId.value) {
    ElMessage.error('账号 ID 无效')
    router.replace('/google/accounts')
    return
  }

  const snapshot = getSnapshotById(accountId.value)
  if (snapshot) {
    detail.value = {
      ...(detail.value || {}),
      ...snapshot,
    }
  }

  loading.value = true
  try {
    const [detailData, familyData, inviteData] = await Promise.all([
      getGoogleAccountDetail(accountId.value),
      listGoogleFamilyMembers(accountId.value).catch(() => []),
      listGoogleInviteLinks(accountId.value).catch(() => []),
    ])

    detail.value = detailData || {}
    familyMembers.value = Array.isArray(familyData) ? familyData : []
    inviteLinks.value = Array.isArray(inviteData) ? inviteData : []
  } catch {
    familyMembers.value = []
    inviteLinks.value = []
    if (detail.value && Object.keys(detail.value).length > 0) {
      ElMessage.warning('详情接口异常，已展示列表页快照数据')
      return
    }
    detail.value = {}
    ElMessage.warning('暂无可展示的详情数据')
  } finally {
    loading.value = false
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

onMounted(fetchDetail)
watch(accountId, (nextId, prevId) => {
  if (nextId && nextId !== prevId) {
    fetchDetail()
  }
})

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
      <div>
        <h1>Google 账号详情</h1>
        <p>{{ detail?.email || '-' }}</p>
      </div>
      <div class="hero-actions">
        <el-button type="danger" plain :icon="Delete" :loading="deleting" @click="handleDelete">删除账号</el-button>
        <el-button :icon="Refresh" @click="fetchDetail">刷新</el-button>
        <el-button type="primary" :icon="ArrowLeft" @click="router.push('/google/accounts')">返回列表</el-button>
      </div>
    </section>

    <section class="summary-grid">
      <article v-for="item in summaryItems" :key="item.label" class="summary-card">
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
      </article>
    </section>

    <section class="card-block">
      <header><h3>基础信息</h3></header>
      <el-descriptions :column="2" class="detail-descriptions">
        <el-descriptions-item label="账号ID">{{ toNullableText(detail?.id) }}</el-descriptions-item>
        <el-descriptions-item label="辅助邮箱">{{ toNullableText(detail?.recoveryEmail) }}</el-descriptions-item>
        <el-descriptions-item :span="2" class-name="credential-focus-content">
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
          </div>
        </el-descriptions-item>
        <el-descriptions-item label="TOTP 密钥">{{ toNullableText(detail?.totpSecret) }}</el-descriptions-item>
        <el-descriptions-item label="地区">{{ toNullableText(detail?.region) }}</el-descriptions-item>
      </el-descriptions>
    </section>

    <section class="card-block">
      <TotpCodeTool :secret="detail?.totpSecret" :allow-manual-input="false" />
    </section>

    <section class="card-block">
      <header><h3>其他信息</h3></header>
      <el-descriptions :column="2" class="detail-descriptions">
        <el-descriptions-item label="订阅类型">{{ toNullableText(detail?.subTier) }}</el-descriptions-item>
        <el-descriptions-item label="到期日期">{{ toNullableText(detail?.expireDate) }}</el-descriptions-item>
        <el-descriptions-item label="学生认证链接">
          <a v-if="detail?.studentLink" :href="detail.studentLink" target="_blank" rel="noopener noreferrer" class="text-link">
            打开链接
          </a>
          <span v-else>-</span>
        </el-descriptions-item>
        <el-descriptions-item label="备注">{{ toNullableText(detail?.remark) }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ toNullableText(detail?.createdAt) }}</el-descriptions-item>
        <el-descriptions-item label="更新时间">{{ toNullableText(detail?.updatedAt) }}</el-descriptions-item>
      </el-descriptions>
    </section>

    <section class="card-block">
      <header class="section-header">
        <h3>家庭组成员</h3>
        <div class="section-actions">
          <el-button type="primary" plain size="small" :icon="Plus" @click="openAddMemberPanel">添加成员</el-button>
        </div>
      </header>
      <transition name="expand-fade">
        <div v-if="addMemberPanelOpen" class="member-composer">
          <div class="member-composer-main">
            <el-input
              v-model="newMemberEmail"
              clearable
              class="composer-input"
              placeholder="输入成员邮箱，例如 member@gmail.com"
              @keyup.enter="handleAddFamilyMember"
            />
            <el-button :loading="addingMember" :disabled="!canSubmitMember" type="primary" @click="handleAddFamilyMember">
              确认添加
            </el-button>
            <el-button @click="closeAddMemberPanel">取消</el-button>
          </div>
          <p class="composer-hint">当前为前端模拟流程，后续接入接口后可直接替换提交逻辑。</p>
          <p v-if="memberEmailError" class="composer-error">{{ memberEmailError }}</p>
        </div>
      </transition>

      <el-empty v-if="!familyMembers.length" description="暂无家庭组成员数据" />
      <div v-else class="table-wrap">
        <el-table class="adaptive-table" :data="familyMembers" stripe :row-class-name="resolveFamilyRowClass">
          <el-table-column prop="id" label="ID" width="86" />
          <el-table-column prop="memberName" label="成员名称" min-width="140" />
          <el-table-column prop="memberEmail" label="成员邮箱" min-width="220">
            <template #default="{ row }">
              <div class="member-email-cell">
                <span>{{ row.memberEmail }}</span>
                <el-tag v-if="row.__mock" size="small" type="warning" effect="plain" class="mock-flag">模拟</el-tag>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="inviteDate" label="邀请日期" width="140" />
          <el-table-column label="成员角色" width="120">
            <template #default="{ row }">{{ resolveFamilyRoleText(row.memberRole) }}</template>
          </el-table-column>
        </el-table>
      </div>
    </section>

    <section class="card-block">
      <header><h3>邀请链接</h3></header>
      <el-empty v-if="!inviteLinks.length" description="暂无邀请链接数据" />
      <div v-else class="table-wrap">
        <el-table class="adaptive-table" :data="inviteLinks" stripe>
          <el-table-column prop="id" label="ID" width="86" />
          <el-table-column prop="inviteUrl" label="邀请链接" min-width="360">
            <template #default="{ row }">
              <div class="invite-url-cell">
                <a :href="row.inviteUrl" target="_blank" rel="noopener noreferrer" class="text-link">
                  {{ row.inviteUrl }}
                </a>
                <el-button
                  text
                  size="small"
                  class="invite-copy-btn"
                  :class="{ 'is-copied': copiedField === `invite-${row.id}` }"
                  :icon="copiedField === `invite-${row.id}` ? Check : CopyDocument"
                  @click.stop="handleCopyValue(row.inviteUrl, '邀请链接', `invite-${row.id}`)"
                >
                  {{ copiedField === `invite-${row.id}` ? '已复制' : '复制链接' }}
                </el-button>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="usedCount" label="已使用次数" width="120" />
        </el-table>
      </div>
    </section>
  </div>
</template>

<style scoped>
.detail-page {
  display: grid;
  gap: 16px;
  width: 100%;
  min-width: 0;
}

.detail-hero {
  border-radius: 12px;
  padding: 20px;
  background:
    radial-gradient(circle at 86% 20%, rgba(18, 161, 115, 0.2), transparent 34%),
    linear-gradient(136deg, #1a2a35 0%, #213540 100%);
  color: #f5faf8;
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
}

.detail-hero h1 {
  margin: 0;
  font-size: 1.3rem;
}

.detail-hero p {
  margin: 6px 0 0;
  color: rgba(245, 250, 248, 0.82);
  font-size: 0.92rem;
}

.hero-actions {
  display: flex;
  gap: 8px;
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
  font-size: 1.08rem;
}

.card-block {
  border-radius: 12px;
  border: 1px solid rgba(23, 37, 48, 0.08);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
  background: #ffffff;
  padding: 18px;
}

.card-block header {
  margin-bottom: 12px;
}

.card-block header h3 {
  margin: 0;
  color: var(--og-slate-900);
  font-size: 1rem;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.section-actions {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.member-composer {
  margin-bottom: 12px;
  padding: 12px;
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

.composer-hint {
  margin: 0;
  color: var(--og-slate-500);
  font-size: 0.78rem;
}

.composer-error {
  margin: 0;
  color: #b91c1c;
  font-size: 0.78rem;
  font-weight: 600;
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
  gap: 10px;
}

.credential-item {
  flex: 1 1 0;
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

@media (prefers-reduced-motion: reduce) {
  .credential-copy-btn {
    transition: none !important;
  }
}

.text-link {
  color: var(--og-emerald-700);
  text-decoration: none;
}

.text-link:hover {
  text-decoration: underline;
}

.table-wrap {
  width: 100%;
  overflow-x: auto;
}

.adaptive-table {
  width: 100%;
  min-width: 680px;
}

.invite-url-cell {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  max-width: 100%;
}

.invite-copy-btn {
  flex-shrink: 0;
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

.member-email-cell {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.mock-flag {
  flex-shrink: 0;
}

:deep(.el-table .family-row-mock > td) {
  background: rgba(251, 191, 36, 0.1) !important;
}

.expand-fade-enter-active,
.expand-fade-leave-active {
  transition: all 220ms ease;
}

.expand-fade-enter-from,
.expand-fade-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

@media (max-width: 980px) {
  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .detail-hero {
    flex-direction: column;
    align-items: flex-start;
  }
}

@media (max-width: 640px) {
  .summary-grid {
    grid-template-columns: 1fr;
  }

  .section-header {
    flex-wrap: wrap;
  }

  .member-composer-main {
    grid-template-columns: 1fr;
  }

  .adaptive-table {
    min-width: 620px;
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

  .hero-actions {
    width: 100%;
    flex-wrap: wrap;
  }

  .hero-actions :deep(.el-button) {
    flex: 1 1 auto;
  }
}
</style>
