<script setup>
import { Check, CopyDocument } from '@element-plus/icons-vue'

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
  lifecycleItems: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['quick-status', 'copy'])

function resolveCredentialVariant(key) {
  const normalized = String(key || '').trim().toLowerCase()
  if (normalized === 'email') return 'email'
  if (normalized === 'password') return 'password'
  if (normalized === 'totp-secret') return 'totp'
  return 'token'
}
</script>

<template>
  <aside class="side-stack">
    <article class="surface-card">
      <header class="panel-header panel-header--compact">
        <div>
          <span class="section-kicker">Status Routing</span>
          <h2>快速状态切换</h2>
          <p>把高频状态动作前置，不需要先进入表单区再保存。</p>
        </div>
      </header>

      <div class="status-action-grid">
        <button
          v-for="item in props.statusActionCards"
          :key="item.value"
          type="button"
          class="status-action-card"
          :class="[`tone-${item.tone}`, { 'is-active': item.active }]"
          :disabled="props.statusUpdating"
          @click="emit('quick-status', item.value)"
        >
          <div class="status-action-card__top">
            <strong>{{ item.loading ? '处理中...' : item.label }}</strong>
            <span>{{ item.note }}</span>
          </div>
          <p>{{ item.description }}</p>
        </button>
      </div>
    </article>

    <article class="surface-card">
      <header class="panel-header panel-header--compact">
        <div>
          <span class="section-kicker">Credential Vault</span>
          <h2>凭据保险库</h2>
          <p>收拢复制动作和关键材料，保持和其他账号系统一致的查看方式。</p>
        </div>
      </header>

      <div class="credential-focus-row">
        <div
          v-for="item in props.credentialVaultItems"
          :key="item.key"
          class="credential-item"
          :class="[
            `credential-item--${resolveCredentialVariant(item.key)}`,
            { 'is-empty': !item.rawValue, 'is-wide': item.multiline },
          ]"
          :title="item.note || ''"
        >
          <span class="credential-key">{{ item.label }}</span>
          <span class="credential-value">{{ item.value }}</span>
          <el-button
            text
            class="credential-copy-btn"
            :class="{ 'is-copied': props.copiedField === item.key }"
            :icon="props.copiedField === item.key ? Check : CopyDocument"
            :disabled="!item.rawValue"
            @click="emit('copy', item)"
          >
            {{ props.copiedField === item.key ? '已复制' : '复制' }}
          </el-button>
        </div>
      </div>

      <p class="vault-panel-hint">长字段默认折叠展示，复制后可直接用于人工接管或任务执行。</p>
    </article>

    <article class="surface-card">
      <header class="panel-header panel-header--compact">
        <div>
          <span class="section-kicker">Lifecycle Record</span>
          <h2>生命周期记录</h2>
          <p>用于确认资产何时创建、何时更新以及当前所属状态。</p>
        </div>
      </header>

      <div class="meta-list">
        <div v-for="item in props.lifecycleItems" :key="item.label" class="meta-row">
          <span>{{ item.label }}</span>
          <strong>{{ item.value }}</strong>
        </div>
      </div>
    </article>
  </aside>
</template>

<style scoped>
.side-stack {
  display: grid;
  gap: 16px;
}

.surface-card {
  padding: 24px;
  border-radius: 22px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 22px 48px rgba(15, 23, 42, 0.08);
}

.panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.panel-header--compact {
  margin-bottom: 16px;
}

.section-kicker {
  display: block;
  margin-bottom: 8px;
  font-size: 0.72rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #64748b;
}

.panel-header h2 {
  margin: 0;
  color: #0f172a;
  font-size: 1.08rem;
}

.panel-header p {
  margin: 6px 0 0;
  color: #64748b;
  font-size: 0.85rem;
  line-height: 1.6;
}

.status-action-grid {
  display: grid;
  gap: 12px;
}

.status-action-card {
  width: 100%;
  display: grid;
  gap: 8px;
  padding: 16px;
  border: none;
  border-radius: 18px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  box-shadow: inset 0 0 0 1px rgba(15, 23, 42, 0.06);
  text-align: left;
  cursor: pointer;
  transition:
    transform 180ms ease,
    box-shadow 180ms ease,
    background 180ms ease;
}

.status-action-card:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow:
    inset 0 0 0 1px rgba(15, 23, 42, 0.08),
    0 16px 34px rgba(15, 23, 42, 0.06);
}

.status-action-card:disabled {
  cursor: wait;
  opacity: 0.78;
}

.status-action-card__top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.status-action-card__top strong {
  color: #0f172a;
  font-size: 0.96rem;
}

.status-action-card__top span {
  color: #475569;
  font-size: 0.76rem;
}

.status-action-card p {
  margin: 0;
  color: #64748b;
  font-size: 0.82rem;
  line-height: 1.6;
}

.status-action-card.is-active {
  box-shadow:
    inset 0 0 0 1px rgba(15, 23, 42, 0.1),
    0 16px 34px rgba(15, 23, 42, 0.06);
}

.status-action-card.tone-success.is-active {
  background: linear-gradient(180deg, rgba(16, 185, 129, 0.12) 0%, rgba(255, 255, 255, 0.96) 100%);
}

.status-action-card.tone-warning.is-active {
  background: linear-gradient(180deg, rgba(245, 158, 11, 0.14) 0%, rgba(255, 255, 255, 0.96) 100%);
}

.status-action-card.tone-danger.is-active {
  background: linear-gradient(180deg, rgba(239, 68, 68, 0.12) 0%, rgba(255, 255, 255, 0.96) 100%);
}

.credential-focus-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

.credential-item {
  flex: 1 1 220px;
  min-width: 0;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  border-radius: 10px;
  padding: 8px 10px;
  border: 1px solid transparent;
}

.credential-item.is-wide {
  flex-basis: 100%;
}

.credential-item--email {
  background: rgba(37, 99, 235, 0.08);
  border-color: rgba(37, 99, 235, 0.26);
}

.credential-item--password {
  background: rgba(245, 158, 11, 0.12);
  border-color: rgba(245, 158, 11, 0.3);
}

.credential-item--totp {
  background: rgba(16, 185, 129, 0.1);
  border-color: rgba(16, 185, 129, 0.24);
}

.credential-item--token {
  background: rgba(15, 23, 42, 0.06);
  border-color: rgba(15, 23, 42, 0.14);
}

.credential-item.is-empty {
  background: rgba(148, 163, 184, 0.08);
  border-color: rgba(148, 163, 184, 0.18);
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

.credential-item--totp .credential-key {
  color: #047857;
}

.credential-item--token .credential-key {
  color: #0f172a;
}

.credential-item.is-empty .credential-key {
  color: #64748b;
}

.credential-value {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: 'Space Grotesk', sans-serif;
  color: #0f172a;
}

.credential-item.is-empty .credential-value {
  color: #64748b;
}

.credential-copy-btn {
  flex-shrink: 0;
  height: 28px;
  padding: 0 10px;
  border-radius: 999px;
  color: #475569;
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

.credential-copy-btn:focus-visible {
  outline: 2px solid #2563eb;
  outline-offset: 2px;
}

.vault-panel-hint {
  margin: 12px 0 0;
  color: #64748b;
  font-size: 0.78rem;
  line-height: 1.6;
}

.meta-list {
  display: grid;
}

.meta-row {
  display: grid;
  gap: 6px;
  padding: 14px 0;
  border-bottom: 1px solid rgba(148, 163, 184, 0.16);
}

.meta-row:last-child {
  border-bottom: none;
}

.meta-row span {
  color: #64748b;
  font-size: 0.78rem;
}

.meta-row strong {
  color: #0f172a;
  font-size: 0.92rem;
  font-weight: 600;
  word-break: break-all;
}

@media (max-width: 760px) {
  .surface-card {
    padding: 20px;
  }

  .panel-header,
  .status-action-card__top {
    flex-direction: column;
    align-items: flex-start;
  }

  .credential-focus-row {
    gap: 8px;
  }

  .credential-item {
    gap: 6px;
    padding: 8px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .status-action-card,
  .credential-copy-btn {
    transition: none;
  }

  .status-action-card:hover:not(:disabled) {
    transform: none;
  }
}
</style>
