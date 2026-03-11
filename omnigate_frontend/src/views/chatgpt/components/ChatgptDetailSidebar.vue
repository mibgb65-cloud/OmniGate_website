<script setup>
import { Check, CopyDocument } from '@element-plus/icons-vue'
import TotpCodeTool from '@/components/security/TotpCodeTool.vue'

const props = defineProps({
  statusActionCards: {
    type: Array,
    default: () => [],
  },
  statusUpdating: {
    type: Boolean,
    default: false,
  },
  credentialVaultItems: {
    type: Array,
    default: () => [],
  },
  copiedField: {
    type: String,
    default: '',
  },
  totpSecret: {
    type: String,
    default: '',
  },
  sessionSyncLoading: {
    type: Boolean,
    default: false,
  },
  sessionSyncDisabled: {
    type: Boolean,
    default: false,
  },
  sessionTask: {
    type: Object,
    default: null,
  },
  sessionTaskStatusText: {
    type: String,
    default: '未开始',
  },
  sessionTaskTagType: {
    type: String,
    default: 'info',
  },
  sessionTaskAlertType: {
    type: String,
    default: 'info',
  },
  sessionTaskActionText: {
    type: String,
    default: '-',
  },
})

const emit = defineEmits(['quick-status', 'copy', 'sync-session'])

function resolveCredentialVariant(key) {
  const normalized = String(key || '').trim().toLowerCase()
  if (normalized === 'email') return 'email'
  if (normalized === 'password') return 'password'
  if (normalized === 'totp-secret') return 'totp'
  return 'token'
}
</script>

<template>
  <aside class="ops-rail">
    <article class="surface-card rail-card rail-card--status">
      <header class="rail-head">
        <div>
          <span class="rail-kicker">Status Routing</span>
          <h2>状态命令台</h2>
          <p>把高频状态改动放在右侧独立命令区，不需要先进入编辑态。</p>
        </div>
      </header>

      <div class="status-command-grid">
        <button
          v-for="item in props.statusActionCards"
          :key="item.value"
          type="button"
          class="status-command-card"
          :class="[`tone-${item.tone}`, { 'is-active': item.active }]"
          :disabled="props.statusUpdating"
          @click="emit('quick-status', item.value)"
        >
          <div class="status-command-card__top">
            <strong>{{ item.loading ? '处理中...' : item.label }}</strong>
            <span>{{ item.note }}</span>
          </div>
          <p>{{ item.description }}</p>
        </button>
      </div>
    </article>

    <article class="surface-card rail-card">
      <header class="rail-head">
        <div>
          <span class="rail-kicker">Credential Vault</span>
          <h2>凭据保险库</h2>
          <p>复制动作、字段强弱和长文本令牌都统一在这一块处理。</p>
        </div>
      </header>

      <div class="vault-grid">
        <article
          v-for="item in props.credentialVaultItems"
          :key="item.key"
          class="vault-card"
          :class="[
            `vault-card--${resolveCredentialVariant(item.key)}`,
            { 'is-empty': !item.rawValue, 'is-wide': item.multiline },
          ]"
        >
          <div class="vault-card__head">
            <span>{{ item.label }}</span>
            <el-button
              text
              class="vault-copy-btn"
              :class="{ 'is-copied': props.copiedField === item.key }"
              :icon="props.copiedField === item.key ? Check : CopyDocument"
              :disabled="!item.rawValue"
              @click="emit('copy', item)"
            >
              {{ props.copiedField === item.key ? '已复制' : '复制' }}
            </el-button>
          </div>
          <strong>{{ item.value }}</strong>
          <p>{{ item.note }}</p>
        </article>
      </div>
    </article>

    <article class="surface-card rail-card rail-card--session">
      <header class="rail-head">
        <div>
          <span class="rail-kicker">Session Automation</span>
          <h2>Session 抓取</h2>
          <p>直接调起 worker 登录 ChatGPT，重新抓取并回写当前账号的 SessionToken。</p>
        </div>
        <el-button
          type="primary"
          class="session-sync-btn"
          :loading="props.sessionSyncLoading"
          :disabled="props.sessionSyncDisabled"
          @click="emit('sync-session')"
        >
          更新 Session
        </el-button>
      </header>

      <div v-if="props.sessionTask" class="session-feedback">
        <div class="session-feedback__summary">
          <span>最近任务</span>
          <strong>{{ props.sessionTaskActionText }}</strong>
          <el-tag :type="props.sessionTaskTagType" effect="light">
            {{ props.sessionTaskStatusText }}
          </el-tag>
        </div>

        <div class="session-meta-grid">
          <div class="session-meta-item">
            <span>TaskRunId</span>
            <strong>{{ props.sessionTask.taskRunId || '-' }}</strong>
          </div>
          <div class="session-meta-item">
            <span>RootRunId</span>
            <strong>{{ props.sessionTask.rootRunId || '-' }}</strong>
          </div>
          <div class="session-meta-item">
            <span>重试</span>
            <strong>{{ props.sessionTask.attemptNo || '-' }} / {{ props.sessionTask.maxAttempts || '-' }}</strong>
          </div>
          <div class="session-meta-item">
            <span>检查点</span>
            <strong>{{ props.sessionTask.lastCheckpoint || '-' }}</strong>
          </div>
        </div>

        <el-alert
          :type="props.sessionTaskAlertType"
          :closable="false"
          class="session-alert"
          show-icon
        >
          <template #title>任务状态已同步到详情页侧轨</template>
          <div v-if="props.sessionTask.errorMessage" class="session-error-text">
            {{ props.sessionTask.errorMessage }}
          </div>
        </el-alert>
      </div>
      <div v-else class="session-placeholder">
        <strong>暂未发起 Session 更新任务</strong>
        <p>发起后状态会持续留在详情页侧轨里，直到任务结束。</p>
      </div>
    </article>

    <div class="support-grid">
      <article class="surface-card rail-card">
        <header class="rail-head rail-head--compact">
          <div>
            <span class="rail-kicker">Live 2FA Code</span>
            <h2>动态验证码</h2>
            <p>从当前账号密钥直接生成验证码，适合临时人工接管。</p>
          </div>
        </header>

        <TotpCodeTool :secret="props.totpSecret" :allow-manual-input="false" />
      </article>
    </div>
  </aside>
</template>

<style scoped>
.ops-rail {
  display: grid;
  gap: 16px;
  align-content: start;
}

.surface-card {
  padding: 22px;
  border-radius: 26px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  background:
    radial-gradient(circle at top right, rgba(249, 115, 22, 0.08), transparent 22%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.98));
  box-shadow: 0 22px 50px rgba(15, 23, 42, 0.08);
}

.rail-card {
  display: grid;
  gap: 18px;
}

.rail-card--status,
.rail-card--session {
  background:
    radial-gradient(circle at top right, rgba(45, 212, 191, 0.08), transparent 24%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.98));
}

.rail-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.rail-head--compact {
  margin-bottom: -2px;
}

.rail-kicker {
  display: block;
  margin-bottom: 8px;
  color: #0f766e;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.rail-head h2 {
  margin: 0;
  color: #0f172a;
  font-family: 'Manrope', 'Segoe UI', sans-serif;
  font-size: 1.12rem;
  font-weight: 800;
  letter-spacing: -0.02em;
}

.rail-head p {
  margin: 6px 0 0;
  color: #475569;
  font-size: 0.84rem;
  line-height: 1.68;
}

.status-command-grid {
  display: grid;
  gap: 12px;
}

.status-command-card {
  display: grid;
  gap: 10px;
  width: 100%;
  padding: 16px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 20px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
  text-align: left;
  cursor: pointer;
  transition:
    transform 180ms ease,
    box-shadow 180ms ease,
    border-color 180ms ease;
}

.status-command-card:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 18px 38px rgba(15, 23, 42, 0.08);
}

.status-command-card:disabled {
  cursor: wait;
  opacity: 0.76;
}

.status-command-card__top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.status-command-card__top strong {
  color: #0f172a;
  font-size: 0.98rem;
}

.status-command-card__top span {
  color: #64748b;
  font-size: 0.76rem;
}

.status-command-card p {
  margin: 0;
  color: #475569;
  font-size: 0.82rem;
  line-height: 1.66;
}

.status-command-card.is-active {
  border-color: rgba(15, 23, 42, 0.16);
  box-shadow: 0 18px 38px rgba(15, 23, 42, 0.08);
}

.status-command-card.tone-success.is-active {
  background: linear-gradient(180deg, rgba(16, 185, 129, 0.12), rgba(255, 255, 255, 0.96));
}

.status-command-card.tone-warning.is-active {
  background: linear-gradient(180deg, rgba(245, 158, 11, 0.14), rgba(255, 255, 255, 0.96));
}

.status-command-card.tone-danger.is-active {
  background: linear-gradient(180deg, rgba(239, 68, 68, 0.12), rgba(255, 255, 255, 0.96));
}

.vault-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.vault-card {
  display: grid;
  gap: 10px;
  min-height: 154px;
  padding: 16px;
  border-radius: 20px;
  border: 1px solid transparent;
}

.vault-card.is-wide {
  grid-column: 1 / -1;
}

.vault-card--email {
  background: rgba(37, 99, 235, 0.08);
  border-color: rgba(37, 99, 235, 0.22);
}

.vault-card--password {
  background: rgba(245, 158, 11, 0.12);
  border-color: rgba(245, 158, 11, 0.22);
}

.vault-card--totp {
  background: rgba(16, 185, 129, 0.1);
  border-color: rgba(16, 185, 129, 0.22);
}

.vault-card--token {
  background: rgba(15, 23, 42, 0.06);
  border-color: rgba(15, 23, 42, 0.12);
}

.vault-card.is-empty {
  background: rgba(148, 163, 184, 0.08);
  border-color: rgba(148, 163, 184, 0.18);
}

.vault-card__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.vault-card__head span {
  color: #334155;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.vault-card strong {
  color: #0f172a;
  font-size: 0.96rem;
  line-height: 1.58;
  word-break: break-word;
}

.vault-card p {
  margin: 0;
  color: #475569;
  font-size: 0.8rem;
  line-height: 1.64;
}

.vault-copy-btn {
  height: 30px;
  padding: 0 10px;
  border-radius: 999px;
  color: #475569;
  background: rgba(255, 255, 255, 0.42);
}

.vault-copy-btn.is-copied {
  color: #047857;
  background: rgba(16, 185, 129, 0.18);
}

.session-sync-btn {
  border-radius: 999px;
}

.session-feedback {
  display: grid;
  gap: 14px;
}

.session-feedback__summary {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  padding: 14px 16px;
  border-radius: 18px;
  background: rgba(15, 23, 42, 0.04);
}

.session-feedback__summary span {
  color: #64748b;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.session-feedback__summary strong {
  color: #0f172a;
  font-size: 0.96rem;
}

.session-meta-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.session-meta-item {
  display: grid;
  gap: 8px;
  padding: 14px;
  border-radius: 18px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
  border: 1px solid rgba(148, 163, 184, 0.16);
}

.session-meta-item span {
  color: #64748b;
  font-size: 0.76rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.session-meta-item strong {
  color: #0f172a;
  font-size: 0.9rem;
  line-height: 1.54;
  word-break: break-all;
}

.session-alert {
  border-radius: 18px;
}

.session-error-text {
  color: #991b1b;
  word-break: break-word;
}

.session-placeholder {
  display: grid;
  gap: 8px;
  padding: 16px;
  border-radius: 20px;
  background: rgba(15, 23, 42, 0.04);
}

.session-placeholder strong {
  color: #0f172a;
  font-size: 0.96rem;
}

.session-placeholder p {
  margin: 0;
  color: #475569;
  font-size: 0.84rem;
  line-height: 1.7;
}

.support-grid {
  display: grid;
  gap: 16px;
}

@media (max-width: 960px) {
  .vault-grid,
  .session-meta-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .surface-card {
    padding: 20px;
  }

  .rail-head,
  .status-command-card__top {
    flex-direction: column;
    align-items: flex-start;
  }
}

@media (prefers-reduced-motion: reduce) {
  .status-command-card {
    transition: none;
  }

  .status-command-card:hover:not(:disabled) {
    transform: none;
  }
}
</style>
