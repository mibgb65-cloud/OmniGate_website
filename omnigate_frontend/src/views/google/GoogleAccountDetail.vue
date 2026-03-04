<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Delete, Refresh } from '@element-plus/icons-vue'

import { deleteGoogleAccount, getGoogleAccountDetail, listGoogleFamilyMembers, listGoogleInviteLinks } from '@/api/google'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const detail = ref(null)
const familyMembers = ref([])
const inviteLinks = ref([])
const deleting = ref(false)

const accountId = computed(() => String(route.params.id || '').trim())

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
      <el-descriptions :column="2" border>
        <el-descriptions-item label="账号ID">{{ toNullableText(detail?.id) }}</el-descriptions-item>
        <el-descriptions-item label="邮箱">{{ toNullableText(detail?.email) }}</el-descriptions-item>
        <el-descriptions-item label="密码">{{ toNullableText(detail?.password) }}</el-descriptions-item>
        <el-descriptions-item label="辅助邮箱">{{ toNullableText(detail?.recoveryEmail) }}</el-descriptions-item>
        <el-descriptions-item label="TOTP 密钥">{{ toNullableText(detail?.totpSecret) }}</el-descriptions-item>
        <el-descriptions-item label="地区">{{ toNullableText(detail?.region) }}</el-descriptions-item>
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
      <header><h3>家庭组成员</h3></header>
      <el-empty v-if="!familyMembers.length" description="暂无家庭组成员数据" />
      <el-table v-else :data="familyMembers" stripe>
        <el-table-column prop="id" label="ID" width="86" />
        <el-table-column prop="memberName" label="成员名称" min-width="140" />
        <el-table-column prop="memberEmail" label="成员邮箱" min-width="200" />
        <el-table-column prop="inviteDate" label="邀请日期" width="140" />
        <el-table-column label="成员角色" width="120">
          <template #default="{ row }">{{ resolveFamilyRoleText(row.memberRole) }}</template>
        </el-table-column>
      </el-table>
    </section>

    <section class="card-block">
      <header><h3>邀请链接</h3></header>
      <el-empty v-if="!inviteLinks.length" description="暂无邀请链接数据" />
      <el-table v-else :data="inviteLinks" stripe>
        <el-table-column prop="id" label="ID" width="86" />
        <el-table-column prop="inviteUrl" label="邀请链接" min-width="300">
          <template #default="{ row }">
            <a :href="row.inviteUrl" target="_blank" rel="noopener noreferrer" class="text-link">
              {{ row.inviteUrl }}
            </a>
          </template>
        </el-table-column>
        <el-table-column prop="usedCount" label="已使用次数" width="120" />
      </el-table>
    </section>
  </div>
</template>

<style scoped>
.detail-page {
  display: grid;
  gap: 16px;
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

.text-link {
  color: var(--og-emerald-700);
  text-decoration: none;
}

.text-link:hover {
  text-decoration: underline;
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

  .hero-actions {
    width: 100%;
  }
}
</style>
