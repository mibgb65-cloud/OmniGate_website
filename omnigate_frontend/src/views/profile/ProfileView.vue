<script setup>
import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()

const roleLabel = computed(() => {
  const roleMap = {
    ADMIN: '超级管理员',
    OPERATOR: '运营管理员',
    VIEWER: '只读观察者',
  }
  return roleMap[authStore.role] || authStore.role || '管理员'
})

const accessExpireText = computed(() => {
  if (!authStore.accessExpireSeconds) return '未设置'
  return `${authStore.accessExpireSeconds} 秒`
})

const refreshExpireText = computed(() => {
  if (!authStore.refreshExpireSeconds) return '未设置'
  return `${authStore.refreshExpireSeconds} 秒`
})

const avatarLetter = computed(() => authStore.username?.charAt(0)?.toUpperCase() || 'A')
</script>

<template>
  <div class="profile-page">
    <section class="profile-hero">
      <div class="hero-left">
        <el-avatar :size="74" class="hero-avatar">{{ avatarLetter }}</el-avatar>
        <div class="hero-copy">
          <h1>{{ authStore.username || 'Admin' }}</h1>
          <p>{{ roleLabel }} · OmniGate 控制台账号</p>
        </div>
      </div>
      <div class="hero-status">在线状态：安全会话中</div>
    </section>

    <section class="profile-grid">
      <article class="profile-card">
        <header><h3>基础信息</h3></header>
        <div class="info-list">
          <div class="info-item">
            <span>用户名</span>
            <strong>{{ authStore.username || '未设置' }}</strong>
          </div>
          <div class="info-item">
            <span>角色权限</span>
            <strong>{{ roleLabel }}</strong>
          </div>
          <div class="info-item">
            <span>Token 类型</span>
            <strong>{{ authStore.tokenType || 'Bearer' }}</strong>
          </div>
        </div>
      </article>

      <article class="profile-card">
        <header><h3>会话安全</h3></header>
        <div class="info-list">
          <div class="info-item">
            <span>Access Token 过期</span>
            <strong>{{ accessExpireText }}</strong>
          </div>
          <div class="info-item">
            <span>Refresh Token 过期</span>
            <strong>{{ refreshExpireText }}</strong>
          </div>
          <div class="info-item">
            <span>登录状态</span>
            <strong>有效</strong>
          </div>
        </div>
      </article>
    </section>

    <section class="profile-card security-hint">
      <header><h3>安全建议</h3></header>
      <ul>
        <li>建议每 30 天轮换一次核心账号口令。</li>
        <li>高权限账号请启用设备级访问审计。</li>
        <li>异常登录请立即执行会话失效与令牌刷新。</li>
      </ul>
    </section>
  </div>
</template>

<style scoped>
.profile-page {
  display: grid;
  gap: 16px;
}

.profile-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 24px;
  border-radius: 12px;
  background:
    radial-gradient(circle at 84% 24%, rgba(18, 161, 115, 0.3), transparent 38%),
    linear-gradient(132deg, #17242e 0%, #1f303b 58%, #253843 100%);
  color: #f5fbf8;
  box-shadow: 0 10px 28px rgba(14, 24, 34, 0.18);
}

.hero-left {
  display: flex;
  align-items: center;
  gap: 14px;
}

.hero-avatar {
  background: linear-gradient(140deg, #0f8d65 0%, #2a9c79 100%);
  color: #ffffff;
  font-size: 1.6rem;
  font-weight: 700;
  border: 2px solid rgba(255, 255, 255, 0.65);
}

.hero-copy h1 {
  margin: 0;
  font-size: 1.32rem;
}

.hero-copy p {
  margin: 4px 0 0;
  color: rgba(243, 252, 248, 0.78);
  font-size: 0.88rem;
}

.hero-status {
  padding: 6px 12px;
  border-radius: 999px;
  font-size: 0.78rem;
  border: 1px solid rgba(138, 245, 206, 0.32);
  background: rgba(138, 245, 206, 0.16);
  color: #8af5ce;
}

.profile-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.profile-card {
  background: #ffffff;
  border-radius: 12px;
  border: 1px solid rgba(22, 39, 50, 0.09);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
  padding: 20px;
}

.profile-card header h3 {
  margin: 0;
  font-size: 1rem;
  color: var(--og-slate-900);
}

.info-list {
  margin-top: 14px;
  display: grid;
  gap: 10px;
}

.info-item {
  border-radius: 10px;
  border: 1px solid rgba(22, 39, 50, 0.08);
  background: #f7faf9;
  padding: 10px 12px;
  display: flex;
  justify-content: space-between;
  gap: 12px;
  transition: all 0.3s ease;
}

.info-item:hover {
  border-color: rgba(18, 161, 115, 0.35);
  transform: translateY(-1px);
}

.info-item span {
  color: var(--og-slate-600);
  font-size: 0.84rem;
}

.info-item strong {
  color: var(--og-slate-900);
  font-size: 0.88rem;
}

.security-hint ul {
  margin: 12px 0 0;
  padding-left: 18px;
  color: var(--og-slate-700);
  line-height: 1.75;
}

@media (max-width: 900px) {
  .profile-grid {
    grid-template-columns: 1fr;
  }

  .profile-hero {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
