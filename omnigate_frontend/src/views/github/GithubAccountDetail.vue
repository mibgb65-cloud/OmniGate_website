<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Delete, Refresh } from '@element-plus/icons-vue'

import { deleteGithubAccount, getGithubAccount } from '@/api/github'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const detail = ref(null)
const deleting = ref(false)

const accountId = computed(() => String(route.params.id || '').trim())

function resolveStatusText(status) {
  if (status === 'active') return '正常'
  if (status === 'locked') return '锁定'
  if (status === 'banned') return '封禁'
  return '-'
}

function toNullableText(value) {
  return value || '-'
}

async function fetchDetail() {
  if (!accountId.value) {
    ElMessage.error('账号 ID 无效')
    router.replace('/github/accounts')
    return
  }

  loading.value = true
  try {
    const detailData = await getGithubAccount(accountId.value)
    detail.value = detailData || {}
  } catch {
    ElMessage.error('获取 GitHub 账号详情失败')
    router.replace('/github/accounts')
  } finally {
    loading.value = false
  }
}

async function handleDelete() {
  if (!detail.value?.id) return

  try {
    await ElMessageBox.confirm(`确认删除 GitHub 账号「${detail.value.username || detail.value.id}」吗？`, '危险操作确认', {
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
    await deleteGithubAccount(detail.value.id)
    ElMessage.success('账号已删除')
    await router.replace('/github/accounts')
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
        <h1>GitHub 账号详情</h1>
        <p>{{ detail?.username || '-' }} · {{ detail?.email || '-' }}</p>
      </div>
      <div class="hero-actions">
        <el-button type="danger" plain :icon="Delete" :loading="deleting" @click="handleDelete">删除账号</el-button>
        <el-button :icon="Refresh" @click="fetchDetail">刷新</el-button>
        <el-button type="primary" :icon="ArrowLeft" @click="router.push('/github/accounts')">返回列表</el-button>
      </div>
    </section>

    <section class="summary-grid">
      <article class="summary-card">
        <span>账号状态</span>
        <strong>{{ resolveStatusText(detail?.accountStatus) }}</strong>
      </article>
      <article class="summary-card">
        <span>代理 IP</span>
        <strong>{{ toNullableText(detail?.proxyIp) }}</strong>
      </article>
      <article class="summary-card">
        <span>创建时间</span>
        <strong>{{ toNullableText(detail?.createdAt) }}</strong>
      </article>
      <article class="summary-card">
        <span>更新时间</span>
        <strong>{{ toNullableText(detail?.updatedAt) }}</strong>
      </article>
    </section>

    <section class="card-block">
      <header><h3>基础信息</h3></header>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="账号 ID">{{ toNullableText(detail?.id) }}</el-descriptions-item>
        <el-descriptions-item label="用户名">{{ toNullableText(detail?.username) }}</el-descriptions-item>
        <el-descriptions-item label="绑定邮箱">{{ toNullableText(detail?.email) }}</el-descriptions-item>
        <el-descriptions-item label="账号状态">{{ resolveStatusText(detail?.accountStatus) }}</el-descriptions-item>
        <el-descriptions-item label="密码">{{ toNullableText(detail?.password) }}</el-descriptions-item>
        <el-descriptions-item label="TOTP 密钥">{{ toNullableText(detail?.totpSecret) }}</el-descriptions-item>
        <el-descriptions-item label="代理 IP">{{ toNullableText(detail?.proxyIp) }}</el-descriptions-item>
        <el-descriptions-item label="更新时间">{{ toNullableText(detail?.updatedAt) }}</el-descriptions-item>
      </el-descriptions>
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
    radial-gradient(circle at 86% 20%, rgba(99, 102, 241, 0.26), transparent 34%),
    linear-gradient(136deg, #1f2937 0%, #1e293b 56%, #111827 100%);
  color: #f8fafc;
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
  color: rgba(241, 245, 249, 0.82);
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
