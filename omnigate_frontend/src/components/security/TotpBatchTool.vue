<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Check, CopyDocument, Refresh, WarningFilled } from '@element-plus/icons-vue'

import { generateTotpCode, getTotpRemainingSeconds } from '@/utils/totp'

const props = defineProps({
  period: {
    type: Number,
    default: 30,
  },
  digits: {
    type: Number,
    default: 6,
  },
})

const secretsInput = ref('')
const secondsLeft = ref(props.period)
const loading = ref(false)
const results = ref([])
const copiedRowKey = ref('')

let ticker = null
let inputRefreshTimer = null
let copyFeedbackTimer = null

const parsedSecrets = computed(() =>
  String(secretsInput.value || '')
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((secret, index) => ({
      rowKey: `${index + 1}-${secret}`,
      lineNo: index + 1,
      secret,
    })),
)

const progressPercentage = computed(() => Math.round((secondsLeft.value / props.period) * 100))
const validCount = computed(() => results.value.filter((item) => !item.error && /^\d+$/.test(item.code)).length)
const invalidCount = computed(() => results.value.filter((item) => item.error).length)
const hasResults = computed(() => results.value.length > 0)
const hasValidCodes = computed(() => validCount.value > 0)

function maskSecret(secret) {
  const normalized = String(secret || '').trim()
  if (!normalized) return '-'
  if (normalized.length <= 10) return normalized
  return `${normalized.slice(0, 6)}...${normalized.slice(-4)}`
}

async function refreshCodes() {
  secondsLeft.value = getTotpRemainingSeconds(props.period)

  if (!parsedSecrets.value.length) {
    results.value = []
    return
  }

  loading.value = true
  try {
    const nextResults = await Promise.all(
      parsedSecrets.value.map(async (item) => {
        try {
          const code = await generateTotpCode(item.secret, {
            period: props.period,
            digits: props.digits,
          })
          return {
            ...item,
            code,
            error: '',
          }
        } catch (error) {
          return {
            ...item,
            code: '------',
            error: error?.message || '验证码生成失败',
          }
        }
      }),
    )
    results.value = nextResults
  } finally {
    loading.value = false
  }
}

function scheduleRefresh(delay = 180) {
  if (inputRefreshTimer) {
    clearTimeout(inputRefreshTimer)
  }
  inputRefreshTimer = setTimeout(() => {
    refreshCodes()
    inputRefreshTimer = null
  }, delay)
}

function startTicker() {
  stopTicker()
  let previous = getTotpRemainingSeconds(props.period)
  secondsLeft.value = previous

  ticker = setInterval(() => {
    const current = getTotpRemainingSeconds(props.period)
    secondsLeft.value = current
    if (current > previous) {
      refreshCodes()
    }
    previous = current
  }, 1000)
}

function stopTicker() {
  if (ticker) {
    clearInterval(ticker)
    ticker = null
  }
}

function markCopied(rowKey) {
  copiedRowKey.value = rowKey
  if (copyFeedbackTimer) {
    clearTimeout(copyFeedbackTimer)
  }
  copyFeedbackTimer = setTimeout(() => {
    copiedRowKey.value = ''
    copyFeedbackTimer = null
  }, 1200)
}

async function handleCopyCode(item) {
  if (!item || item.error || !/^\d+$/.test(item.code)) {
    ElMessage.warning('当前这行没有可复制的验证码')
    return
  }
  try {
    await navigator.clipboard.writeText(item.code)
    markCopied(item.rowKey)
    ElMessage.success(`第 ${item.lineNo} 行验证码已复制`)
  } catch {
    ElMessage.error('复制失败，请手动复制')
  }
}

async function handleCopyAllCodes() {
  const lines = results.value
    .filter((item) => !item.error && /^\d+$/.test(item.code))
    .map((item) => `${item.lineNo}. ${item.code}`)

  if (!lines.length) {
    ElMessage.warning('当前没有可复制的批量验证码')
    return
  }

  try {
    await navigator.clipboard.writeText(lines.join('\n'))
    ElMessage.success(`已复制 ${lines.length} 条验证码`)
  } catch {
    ElMessage.error('复制失败，请手动复制')
  }
}

watch(secretsInput, () => {
  scheduleRefresh()
})

onMounted(() => {
  refreshCodes()
  startTicker()
})

onBeforeUnmount(() => {
  stopTicker()
  if (inputRefreshTimer) {
    clearTimeout(inputRefreshTimer)
    inputRefreshTimer = null
  }
  if (copyFeedbackTimer) {
    clearTimeout(copyFeedbackTimer)
    copyFeedbackTimer = null
  }
})
</script>

<template>
  <section class="totp-batch-tool">
    <header class="tool-header">
      <div>
        <h3>批量验证码解析</h3>
        <p>每行一个 TOTP 密钥，自动生成并跟随 30 秒窗口刷新。</p>
      </div>
      <div class="header-actions">
        <el-button text :icon="Refresh" @click="refreshCodes">重新解析</el-button>
        <el-button type="primary" plain :icon="CopyDocument" :disabled="!hasValidCodes" @click="handleCopyAllCodes">
          复制全部
        </el-button>
      </div>
    </header>

    <div class="batch-grid">
      <div class="input-panel">
        <el-input
          v-model="secretsInput"
          type="textarea"
          :rows="12"
          resize="vertical"
          autocomplete="off"
          placeholder="每行一个 Base32 格式密钥，例如&#10;JBSWY3DPEHPK3PXP&#10;MFRGGZDFMZTWQ2LK"
        />

        <div class="input-summary">
          <span>共 {{ parsedSecrets.length }} 条</span>
          <span>成功 {{ validCount }} 条</span>
          <span v-if="invalidCount">异常 {{ invalidCount }} 条</span>
          <span>{{ secondsLeft }} 秒后自动更新</span>
        </div>

        <el-progress :percentage="progressPercentage" :show-text="false" :stroke-width="8" />
      </div>

      <div class="result-panel">
        <div v-if="!hasResults" class="empty-state">
          <strong>还没有待解析的密钥</strong>
          <p>把多个 2FA 密钥按“一行一个”粘贴进左侧输入框后，这里会显示批量结果。</p>
        </div>

        <ul v-else class="result-list">
          <li v-for="item in results" :key="item.rowKey" class="result-item" :class="{ invalid: item.error }">
            <div class="result-meta">
              <span class="result-line">第 {{ item.lineNo }} 行</span>
              <span class="result-secret">{{ maskSecret(item.secret) }}</span>
            </div>

            <div class="result-main">
              <strong>{{ item.code }}</strong>
              <el-button
                text
                class="copy-btn"
                :class="{ 'is-copied': copiedRowKey === item.rowKey }"
                :icon="copiedRowKey === item.rowKey ? Check : CopyDocument"
                :disabled="Boolean(item.error)"
                @click="handleCopyCode(item)"
              >
                {{ copiedRowKey === item.rowKey ? '已复制' : '复制' }}
              </el-button>
            </div>

            <p v-if="item.error" class="result-error">
              <el-icon><WarningFilled /></el-icon>
              <span>{{ item.error }}</span>
            </p>
          </li>
        </ul>
      </div>
    </div>
  </section>
</template>

<style scoped>
.totp-batch-tool {
  display: grid;
  gap: 14px;
}

.tool-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.tool-header h3 {
  margin: 0;
  color: var(--og-slate-900);
  font-size: 1rem;
}

.tool-header p {
  margin: 6px 0 0;
  color: var(--og-slate-600);
  font-size: 0.84rem;
  line-height: 1.6;
}

.header-actions {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.batch-grid {
  display: grid;
  grid-template-columns: minmax(280px, 0.92fr) minmax(320px, 1.08fr);
  gap: 14px;
}

.input-panel,
.result-panel {
  border-radius: 16px;
  border: 1px solid rgba(148, 163, 184, 0.16);
  background: linear-gradient(180deg, #ffffff, #f8fafc);
  padding: 14px;
}

.input-summary {
  margin: 12px 0 10px;
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  color: var(--og-slate-600);
  font-size: 0.8rem;
}

.result-list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 10px;
  max-height: 476px;
  overflow: auto;
}

.result-item {
  border-radius: 14px;
  border: 1px solid rgba(16, 185, 129, 0.18);
  background: linear-gradient(145deg, rgba(16, 185, 129, 0.08), rgba(5, 150, 105, 0.04));
  padding: 12px 14px;
  display: grid;
  gap: 8px;
}

.result-item.invalid {
  border-color: rgba(239, 68, 68, 0.2);
  background: linear-gradient(145deg, rgba(239, 68, 68, 0.08), rgba(248, 113, 113, 0.04));
}

.result-meta,
.result-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.result-line {
  color: var(--og-slate-700);
  font-weight: 700;
  font-size: 0.82rem;
}

.result-secret {
  color: var(--og-slate-500);
  font-family: 'Fira Code', 'Consolas', monospace;
  font-size: 0.78rem;
}

.result-main strong {
  font-family: 'Space Grotesk', sans-serif;
  font-size: 1.44rem;
  letter-spacing: 0.12em;
  color: #065f46;
}

.result-item.invalid .result-main strong {
  color: #b91c1c;
}

.copy-btn {
  flex-shrink: 0;
  height: 30px;
  padding: 0 10px;
  border-radius: 999px;
  color: var(--og-slate-600);
  background: rgba(148, 163, 184, 0.12);
}

.copy-btn.is-copied {
  color: #047857;
  background: rgba(16, 185, 129, 0.18);
}

.result-error {
  margin: 0;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #b45309;
  font-size: 0.8rem;
  line-height: 1.5;
}

.empty-state {
  min-height: 220px;
  display: grid;
  place-content: center;
  gap: 8px;
  text-align: center;
}

.empty-state strong {
  color: var(--og-slate-900);
  font-size: 1rem;
}

.empty-state p {
  margin: 0;
  color: var(--og-slate-600);
  line-height: 1.6;
}

@media (max-width: 980px) {
  .batch-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 680px) {
  .tool-header,
  .result-meta,
  .result-main {
    flex-direction: column;
    align-items: flex-start;
  }

  .result-main strong {
    letter-spacing: 0.08em;
  }
}
</style>
