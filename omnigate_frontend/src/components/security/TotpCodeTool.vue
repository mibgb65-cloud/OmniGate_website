<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { CopyDocument, Refresh, WarningFilled } from '@element-plus/icons-vue'

import { generateTotpCode, getTotpRemainingSeconds } from '@/utils/totp'

const props = defineProps({
  secret: {
    type: String,
    default: '',
  },
  allowManualInput: {
    type: Boolean,
    default: true,
  },
  showUseAccountSecretButton: {
    type: Boolean,
    default: true,
  },
  period: {
    type: Number,
    default: 30,
  },
  digits: {
    type: Number,
    default: 6,
  },
})

const secretInput = ref('')
const code = ref('------')
const secondsLeft = ref(props.period)
const loading = ref(false)
const errorMessage = ref('')
const lastSyncedSecret = ref('')

const activeSecret = computed(() =>
  props.allowManualInput ? String(secretInput.value || '').trim() : String(props.secret || '').trim(),
)
const hasValidCode = computed(() => /^\d+$/.test(code.value))
const progressPercentage = computed(() => Math.round((secondsLeft.value / props.period) * 100))

let ticker = null

function syncSecretFromProps(force = false) {
  const incoming = String(props.secret || '').trim()
  if (!props.allowManualInput) {
    secretInput.value = incoming
    lastSyncedSecret.value = incoming
    return
  }

  const current = String(secretInput.value || '').trim()
  const canOverwrite = force || !current || current === lastSyncedSecret.value

  if (canOverwrite) {
    secretInput.value = incoming
    lastSyncedSecret.value = incoming
  }
}

async function refreshCode() {
  secondsLeft.value = getTotpRemainingSeconds(props.period)

  if (!activeSecret.value) {
    code.value = '------'
    errorMessage.value = '暂无 TOTP 密钥，无法生成验证码'
    return
  }

  loading.value = true
  try {
    code.value = await generateTotpCode(activeSecret.value, {
      period: props.period,
      digits: props.digits,
    })
    errorMessage.value = ''
  } catch (error) {
    code.value = '------'
    errorMessage.value = error?.message || '验证码生成失败'
  } finally {
    loading.value = false
  }
}

function startTicker() {
  stopTicker()
  let previous = getTotpRemainingSeconds(props.period)
  secondsLeft.value = previous

  ticker = setInterval(() => {
    const current = getTotpRemainingSeconds(props.period)
    secondsLeft.value = current

    if (current > previous) {
      refreshCode()
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

async function handleCopyCode() {
  if (!hasValidCode.value) {
    ElMessage.warning('当前没有可复制的验证码')
    return
  }
  try {
    await navigator.clipboard.writeText(code.value)
    ElMessage.success('验证码已复制')
  } catch {
    ElMessage.error('复制失败，请手动复制')
  }
}

function handleUseAccountSecret() {
  if (!props.allowManualInput) {
    return
  }
  syncSecretFromProps(true)
  refreshCode()
}

watch(
  () => props.secret,
  () => {
    syncSecretFromProps()
    refreshCode()
  },
)

watch(secretInput, () => {
  if (!props.allowManualInput) {
    return
  }
  refreshCode()
})

onMounted(() => {
  syncSecretFromProps(true)
  refreshCode()
  startTicker()
})

onBeforeUnmount(() => {
  stopTicker()
})
</script>

<template>
  <section class="totp-tool">
    <header class="tool-header">
      <h3>2FA 验证码工具</h3>
      <div class="header-actions">
        <el-button v-if="props.allowManualInput && props.showUseAccountSecretButton" text @click="handleUseAccountSecret">
          使用账号密钥
        </el-button>
        <el-button text :icon="Refresh" @click="refreshCode">重新获取</el-button>
      </div>
    </header>

    <el-input
      v-model="secretInput"
      clearable
      :disabled="!props.allowManualInput"
      autocomplete="off"
      :placeholder="
        props.allowManualInput ? '输入 Base32 格式 TOTP 密钥，或直接使用账号密钥' : '使用当前账号绑定的 TOTP 密钥'
      "
    />

    <article class="code-board" :class="{ invalid: !!errorMessage }">
      <span>当前验证码</span>
      <strong>{{ code }}</strong>
      <p>{{ secondsLeft }} 秒后自动更新</p>
      <el-progress :percentage="progressPercentage" :show-text="false" :stroke-width="8" />
    </article>

    <div class="tool-actions">
      <div v-if="errorMessage" class="inline-error">
        <el-icon><WarningFilled /></el-icon>
        <span>{{ errorMessage }}</span>
      </div>
      <el-button type="primary" :icon="CopyDocument" :disabled="!hasValidCode || loading" @click="handleCopyCode">
        复制验证码
      </el-button>
    </div>
  </section>
</template>

<style scoped>
.totp-tool {
  display: grid;
  gap: 12px;
}

.tool-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.header-actions {
  display: inline-flex;
  align-items: center;
  gap: 2px;
}

.tool-header h3 {
  margin: 0;
  color: var(--og-slate-900);
  font-size: 1rem;
}

.code-board {
  border-radius: 12px;
  border: 1px solid rgba(16, 185, 129, 0.24);
  background: linear-gradient(142deg, rgba(16, 185, 129, 0.08), rgba(5, 150, 105, 0.05));
  padding: 14px;
}

.code-board span {
  display: block;
  color: var(--og-slate-600);
  font-size: 0.8rem;
}

.code-board strong {
  display: block;
  margin-top: 8px;
  font-family: 'Space Grotesk', sans-serif;
  font-size: 2rem;
  letter-spacing: 0.12em;
  color: #065f46;
}

.code-board p {
  margin: 8px 0 12px;
  color: var(--og-slate-600);
  font-size: 0.82rem;
}

.code-board.invalid {
  border-color: rgba(239, 68, 68, 0.28);
  background: linear-gradient(142deg, rgba(239, 68, 68, 0.08), rgba(248, 113, 113, 0.04));
}

.code-board.invalid strong {
  color: #b91c1c;
}

.tool-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  justify-content: flex-end;
}

.tool-actions :deep(.el-button) {
  margin-left: auto;
}

.inline-error {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 32px;
  padding: 6px 10px;
  border-radius: 8px;
  border: 1px solid rgba(245, 158, 11, 0.32);
  background: rgba(254, 243, 199, 0.65);
  color: #92400e;
  font-size: 0.8rem;
}

.inline-error :deep(svg) {
  font-size: 14px;
}

@media (max-width: 640px) {
  .code-board strong {
    font-size: 1.6rem;
    letter-spacing: 0.08em;
  }

  .tool-actions {
    flex-wrap: wrap;
  }

  .tool-actions :deep(.el-button) {
    margin-left: 0;
  }
}
</style>
