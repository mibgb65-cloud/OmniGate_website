<script setup>
import { ref } from 'vue'

const props = defineProps({
  detail: {
    type: Object,
    default: () => ({}),
  },
  form: {
    type: Object,
    required: true,
  },
  formRules: {
    type: Object,
    required: true,
  },
  subTierOptions: {
    type: Array,
    default: () => [],
  },
  statusOptions: {
    type: Array,
    default: () => [],
  },
  soldOptions: {
    type: Array,
    default: () => [],
  },
  postureItems: {
    type: Array,
    default: () => [],
  },
  lifecycleItems: {
    type: Array,
    default: () => [],
  },
  editing: {
    type: Boolean,
    default: false,
  },
  saving: {
    type: Boolean,
    default: false,
  },
  formatAccountStatus: {
    type: Function,
    required: true,
  },
  formatDisplayDate: {
    type: Function,
    required: true,
  },
  formatSubTier: {
    type: Function,
    required: true,
  },
  formatSoldStatus: {
    type: Function,
    required: true,
  },
})

const emit = defineEmits(['start-edit', 'cancel-edit', 'reset', 'save'])
const formRef = ref()

async function validate() {
  if (!formRef.value) return true
  return formRef.value.validate()
}

function clearValidation() {
  formRef.value?.clearValidate()
}

function toDisplay(value) {
  const normalized = String(value ?? '').trim()
  return normalized || '-'
}

defineExpose({
  validate,
  clearValidation,
})
</script>

<template>
  <article class="editor-shell" :class="{ 'is-editing': props.editing }">
    <header class="editor-header">
      <div class="editor-header__copy">
        <span class="editor-kicker">{{ props.editing ? 'Edit Workspace' : 'Asset Dossier' }}</span>
        <h2>{{ props.editing ? '账号资料编辑台' : '账号资料总览' }}</h2>
        <p>
          {{
            props.editing
              ? '编辑被收拢成一次操作：身份、状态、出售登记和安全材料都在同一块里完成。'
              : '默认保持只读，把浏览、判断和接管动作先收成一块“资料总览”，确认后再进入编辑。'
          }}
        </p>
      </div>

      <div class="editor-header__actions">
        <el-button
          class="mode-toggle-btn"
          :class="{ 'mode-toggle-btn--accent': !props.editing }"
          @click="emit(props.editing ? 'cancel-edit' : 'start-edit')"
        >
          {{ props.editing ? '退出编辑' : '进入编辑' }}
        </el-button>
      </div>
    </header>

    <template v-if="props.editing">
      <el-form
        ref="formRef"
        :model="props.form"
        :rules="props.formRules"
        label-position="top"
        class="editor-form"
      >
        <section class="editor-block">
          <div class="block-head">
            <div class="block-index">01</div>
            <div>
              <strong>身份与库存属性</strong>
              <p>这里决定账号怎样被识别、是否可运营，以及后续能否继续流转。</p>
            </div>
          </div>

          <div class="field-grid">
            <el-form-item label="账号邮箱" prop="email">
              <el-input v-model.trim="props.form.email" name="email" autocomplete="username" placeholder="name@example.com" />
            </el-form-item>
            <el-form-item label="到期日期">
              <el-date-picker
                v-model="props.form.expireDate"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="可选"
              />
            </el-form-item>
            <el-form-item label="订阅层级">
              <el-select v-model="props.form.subTier">
                <el-option
                  v-for="item in props.subTierOptions"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="账号状态">
              <el-select v-model="props.form.accountStatus">
                <el-option
                  v-for="item in props.statusOptions"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="出售状态">
              <el-select v-model="props.form.sold">
                <el-option
                  v-for="item in props.soldOptions"
                  :key="String(item.value)"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </el-form-item>
          </div>
        </section>

        <section class="editor-block">
          <div class="block-head">
            <div class="block-index">02</div>
            <div>
              <strong>登录与接管材料</strong>
              <p>密码、2FA 密钥和 SessionToken 会一起影响后续人工接管与自动化任务成功率。</p>
            </div>
          </div>

          <div class="field-grid">
            <el-form-item label="登录密码" prop="password">
              <el-input
                v-model.trim="props.form.password"
                type="password"
                show-password
                name="password"
                autocomplete="new-password"
                placeholder="留空表示不修改"
              />
            </el-form-item>
            <el-form-item label="2FA / TOTP 密钥" prop="totpSecret">
              <el-input
                v-model.trim="props.form.totpSecret"
                name="totpSecret"
                autocomplete="off"
                placeholder="可选，留空表示不修改"
              />
            </el-form-item>
            <el-form-item label="SessionToken" prop="sessionToken" class="span-all">
              <el-input
                v-model.trim="props.form.sessionToken"
                type="textarea"
                :rows="6"
                resize="none"
                name="sessionToken"
                autocomplete="off"
                placeholder="留空表示不修改；支持直接覆盖或清空"
              />
            </el-form-item>
          </div>
        </section>
      </el-form>

      <section class="editor-ops">
        <div class="posture-grid">
          <article v-for="item in props.postureItems" :key="item.label" class="posture-card">
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
            <p>{{ item.hint }}</p>
          </article>
        </div>

        <div class="editor-note">
          <span>Editing Rule</span>
          <strong>密码留空不会覆盖原值</strong>
          <p>只会提交发生变化的字段。邮箱、状态、出售、订阅、过期日和材料内容可以一次性回写。</p>
        </div>
      </section>

      <section class="editor-block">
        <div class="block-head">
          <div class="block-index">03</div>
          <div>
            <strong>生命周期记录</strong>
            <p>保留创建、更新时间和库存属性，编辑时也能继续对照上下文。</p>
          </div>
        </div>

        <div class="lifecycle-grid">
          <article v-for="item in props.lifecycleItems" :key="item.label" class="lifecycle-card">
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
          </article>
        </div>
      </section>

      <footer class="editor-footer">
        <el-button @click="emit('cancel-edit')">取消</el-button>
        <el-button @click="emit('reset')">重置表单</el-button>
        <el-button type="primary" :loading="props.saving" @click="emit('save')">保存修改</el-button>
      </footer>
    </template>

    <template v-else>
      <section class="overview-deck">
        <div class="overview-main">
          <section class="overview-block">
            <div class="block-head">
              <div class="block-index">01</div>
              <div>
                <strong>基础身份</strong>
                <p>先确认这个账号是谁、是否还在库存、以及生命周期是否需要介入。</p>
              </div>
            </div>

            <div class="overview-grid">
              <article class="overview-card overview-card--hero">
                <span>账号邮箱</span>
                <strong>{{ toDisplay(props.detail?.email) }}</strong>
                <p>详情页唯一识别项</p>
              </article>
              <article class="overview-card">
                <span>订阅层级</span>
                <strong>{{ props.formatSubTier(props.detail?.subTier) }}</strong>
                <p>决定可用能力范围</p>
              </article>
              <article class="overview-card">
                <span>账号状态</span>
                <strong>{{ props.formatAccountStatus(props.detail?.accountStatus) }}</strong>
                <p>决定能否继续运营</p>
              </article>
              <article class="overview-card">
                <span>出售状态</span>
                <strong>{{ props.formatSoldStatus(props.detail?.sold) }}</strong>
                <p>是否已出库登记</p>
              </article>
              <article class="overview-card">
                <span>到期日期</span>
                <strong>{{ props.formatDisplayDate(props.detail?.expireDate, { includeTime: false }) }}</strong>
                <p>用于追踪续期窗口</p>
              </article>
            </div>
          </section>

          <section class="overview-block">
            <div class="block-head">
              <div class="block-index">02</div>
              <div>
                <strong>维护姿态</strong>
                <p>把登录材料、安全材料、会话接管能力和出售登记汇总成一眼能判断的姿态板。</p>
              </div>
            </div>

            <div class="posture-grid">
              <article v-for="item in props.postureItems" :key="item.label" class="posture-card">
                <span>{{ item.label }}</span>
                <strong>{{ item.value }}</strong>
                <p>{{ item.hint }}</p>
              </article>
            </div>
          </section>

          <section class="overview-block">
            <div class="block-head">
              <div class="block-index">03</div>
              <div>
                <strong>生命周期记录</strong>
                <p>把创建、更新和库存属性集中放在左侧，避免在运维轨里来回找静态信息。</p>
              </div>
            </div>

            <div class="lifecycle-grid">
              <article v-for="item in props.lifecycleItems" :key="item.label" class="lifecycle-card">
                <span>{{ item.label }}</span>
                <strong>{{ item.value }}</strong>
              </article>
            </div>
          </section>
        </div>

        <aside class="overview-rail">
          <article class="readiness-card">
            <span>Read-Only First</span>
            <strong>先判断，再编辑</strong>
            <p>复制凭据、更新状态、触发 Session 抓取都在右侧运维轨完成。只有字段本身需要更改时，才进入编辑模式。</p>
          </article>
        </aside>
      </section>
    </template>
  </article>
</template>

<style scoped>
.editor-shell {
  display: grid;
  gap: 20px;
  padding: 24px;
  border-radius: 28px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  background:
    radial-gradient(circle at top right, rgba(45, 212, 191, 0.08), transparent 22%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.98));
  box-shadow: 0 24px 56px rgba(15, 23, 42, 0.08);
}

.editor-shell.is-editing {
  border-color: rgba(20, 184, 166, 0.24);
  box-shadow:
    0 28px 60px rgba(15, 23, 42, 0.1),
    0 0 0 1px rgba(20, 184, 166, 0.08);
}

.editor-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
}

.editor-header__copy {
  display: grid;
  gap: 8px;
  max-width: 680px;
}

.editor-kicker {
  color: #0f766e;
  font-size: 0.74rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.editor-header h2 {
  margin: 0;
  color: #0f172a;
  font-family: 'Manrope', 'Segoe UI', sans-serif;
  font-size: 1.4rem;
  font-weight: 800;
  letter-spacing: -0.03em;
}

.editor-header p {
  margin: 0;
  color: #475569;
  font-size: 0.92rem;
  line-height: 1.72;
}

.mode-toggle-btn {
  min-width: 116px;
  border-radius: 999px;
  font-weight: 700;
}

.mode-toggle-btn--accent {
  --el-button-bg-color: rgba(15, 118, 110, 0.1);
  --el-button-border-color: rgba(15, 118, 110, 0.2);
  --el-button-text-color: #134e4a;
  --el-button-hover-bg-color: rgba(15, 118, 110, 0.18);
  --el-button-hover-border-color: rgba(15, 118, 110, 0.3);
  --el-button-hover-text-color: #0f172a;
}

.editor-form,
.overview-main {
  display: grid;
  gap: 18px;
}

.editor-block,
.overview-block {
  display: grid;
  gap: 16px;
  padding: 18px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.86);
  box-shadow: inset 0 0 0 1px rgba(148, 163, 184, 0.16);
}

.block-head {
  display: flex;
  align-items: flex-start;
  gap: 14px;
}

.block-index {
  width: 40px;
  height: 40px;
  display: grid;
  place-items: center;
  flex-shrink: 0;
  border-radius: 14px;
  background: rgba(15, 23, 42, 0.06);
  color: #0f172a;
  font-family: 'Fira Code', 'Space Grotesk', monospace;
  font-size: 0.82rem;
  font-weight: 700;
}

.block-head strong {
  display: block;
  color: #0f172a;
  font-size: 1rem;
}

.block-head p {
  margin: 6px 0 0;
  color: #64748b;
  font-size: 0.84rem;
  line-height: 1.68;
}

.field-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px 16px;
}

.span-all {
  grid-column: 1 / -1;
}

.editor-ops {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 260px;
  gap: 16px;
}

.overview-deck {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(260px, 0.8fr);
  gap: 18px;
}

.overview-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.lifecycle-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.overview-card,
.posture-card,
.lifecycle-card,
.readiness-card,
.editor-note {
  display: grid;
  gap: 8px;
  padding: 16px;
  border-radius: 20px;
  border: 1px solid rgba(148, 163, 184, 0.16);
  background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
}

.overview-card--hero {
  grid-column: 1 / -1;
  background:
    radial-gradient(circle at top right, rgba(45, 212, 191, 0.16), transparent 30%),
    linear-gradient(180deg, #ffffff 0%, #f7fffd 100%);
}

.overview-card span,
.posture-card span,
.lifecycle-card span,
.readiness-card span,
.editor-note span {
  color: #64748b;
  font-size: 0.76rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.overview-card strong,
.posture-card strong,
.lifecycle-card strong,
.readiness-card strong,
.editor-note strong {
  color: #0f172a;
  font-size: 1rem;
  line-height: 1.5;
  word-break: break-word;
}

.overview-card p,
.posture-card p,
.readiness-card p,
.editor-note p {
  margin: 0;
  color: #475569;
  font-size: 0.82rem;
  line-height: 1.68;
}

.posture-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.overview-rail {
  display: grid;
  align-content: start;
  gap: 14px;
}

.editor-footer {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 10px;
}

:deep(.editor-form .el-form-item__label) {
  color: #0f172a;
  font-weight: 700;
}

:deep(.editor-form .el-input__wrapper),
:deep(.editor-form .el-select__wrapper),
:deep(.editor-form .el-textarea__inner),
:deep(.editor-form .el-date-editor.el-input__wrapper) {
  background: #ffffff;
  box-shadow: 0 0 0 1px rgba(15, 23, 42, 0.12) inset;
}

:deep(.editor-form .el-input__wrapper:hover),
:deep(.editor-form .el-select__wrapper:hover),
:deep(.editor-form .el-textarea__inner:hover),
:deep(.editor-form .el-date-editor.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px rgba(20, 184, 166, 0.22) inset;
}

:deep(.editor-form .el-input__wrapper.is-focus),
:deep(.editor-form .el-select__wrapper.is-focused),
:deep(.editor-form .el-textarea__inner:focus),
:deep(.editor-form .el-date-editor.el-input__wrapper.is-focus) {
  box-shadow:
    0 0 0 1px rgba(20, 184, 166, 0.32) inset,
    0 0 0 4px rgba(45, 212, 191, 0.12);
}

@media (max-width: 1180px) {
  .editor-ops,
  .overview-deck {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 820px) {
  .editor-shell {
    padding: 20px;
  }

  .field-grid,
  .overview-grid,
  .posture-grid,
  .lifecycle-grid {
    grid-template-columns: 1fr;
  }

  .editor-header,
  .editor-footer,
  .block-head {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
