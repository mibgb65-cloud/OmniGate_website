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
  postureItems: {
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
  <article class="surface-card editor-panel" :class="{ 'is-editing': props.editing }">
    <header class="panel-header">
      <div>
        <span class="section-kicker">{{ props.editing ? 'Account Editor' : 'Account Overview' }}</span>
        <h2>{{ props.editing ? '账号资料编辑' : '账号资料概览' }}</h2>
        <p>
          {{
            props.editing
              ? '密码留空表示不修改；SessionToken 和 2FA 密钥支持覆盖或清空。'
              : '默认保持只读，只有在确实需要修改资料时再进入编辑态。'
          }}
        </p>
      </div>
      <el-button
        class="panel-toggle-btn"
        :class="{ 'panel-toggle-btn--accent': !props.editing }"
        @click="emit(props.editing ? 'cancel-edit' : 'start-edit')"
      >
        {{ props.editing ? '取消编辑' : '编辑资料' }}
      </el-button>
    </header>

    <template v-if="props.editing">
      <el-form
        ref="formRef"
        :model="props.form"
        :rules="props.formRules"
        label-position="top"
        class="detail-form"
      >
        <section class="form-section">
          <div class="form-section__header">
            <span class="form-section__index">01</span>
            <div>
              <strong>身份与生命周期</strong>
              <p>用于识别账号和后续运维安排。</p>
            </div>
          </div>

          <div class="form-grid">
            <el-form-item label="账号邮箱" prop="email">
              <el-input v-model.trim="props.form.email" placeholder="name@example.com" />
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
          </div>
        </section>

        <section class="form-section">
          <div class="form-section__header">
            <span class="form-section__index">02</span>
            <div>
              <strong>登录与安全材料</strong>
              <p>集中维护人工接管所需的密码、SessionToken 和 2FA 信息。</p>
            </div>
          </div>

          <div class="form-grid">
            <el-form-item label="登录密码" prop="password">
              <el-input v-model.trim="props.form.password" type="password" show-password placeholder="留空表示不修改" />
            </el-form-item>
            <el-form-item label="2FA / TOTP 密钥" prop="totpSecret">
              <el-input v-model.trim="props.form.totpSecret" placeholder="可选，留空表示不修改" />
            </el-form-item>
            <el-form-item label="SessionToken" prop="sessionToken" class="span-2">
              <el-input
                v-model.trim="props.form.sessionToken"
                type="textarea"
                :rows="5"
                resize="none"
                placeholder="可留空"
              />
            </el-form-item>
          </div>
        </section>
      </el-form>

      <div class="editor-footer">
        <div class="posture-grid">
          <article v-for="item in props.postureItems" :key="item.label" class="posture-card">
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
            <em>{{ item.hint }}</em>
          </article>
        </div>

        <div class="editor-actions">
          <el-button @click="emit('cancel-edit')">取消</el-button>
          <el-button @click="emit('reset')">重置表单</el-button>
          <el-button type="primary" :loading="props.saving" @click="emit('save')">保存修改</el-button>
        </div>
      </div>
    </template>

    <template v-else>
      <div class="overview-stack">
        <section class="overview-section">
          <div class="form-section__header">
            <span class="form-section__index">01</span>
            <div>
              <strong>身份与生命周期</strong>
              <p>先浏览账号关键信息，再决定是否需要进入编辑态。</p>
            </div>
          </div>

          <div class="overview-grid">
            <article class="overview-field">
              <span>账号邮箱</span>
              <strong>{{ toDisplay(props.detail?.email) }}</strong>
            </article>
            <article class="overview-field">
              <span>订阅层级</span>
              <strong>{{ props.formatSubTier(props.detail?.subTier) }}</strong>
            </article>
            <article class="overview-field">
              <span>账号状态</span>
              <strong>{{ props.formatAccountStatus(props.detail?.accountStatus) }}</strong>
            </article>
            <article class="overview-field">
              <span>到期日期</span>
              <strong>{{ props.formatDisplayDate(props.detail?.expireDate, { includeTime: false }) }}</strong>
            </article>
            <article class="overview-field">
              <span>创建时间</span>
              <strong>{{ props.formatDisplayDate(props.detail?.createdAt) }}</strong>
            </article>
            <article class="overview-field">
              <span>更新时间</span>
              <strong>{{ props.formatDisplayDate(props.detail?.updatedAt) }}</strong>
            </article>
          </div>
        </section>

        <section class="overview-section">
          <div class="form-section__header">
            <span class="form-section__index">02</span>
            <div>
              <strong>当前维护姿态</strong>
              <p>把登录材料、安全材料和会话接管能力收成一眼可读的状态摘要。</p>
            </div>
          </div>

          <div class="posture-grid">
            <article v-for="item in props.postureItems" :key="item.label" class="posture-card">
              <span>{{ item.label }}</span>
              <strong>{{ item.value }}</strong>
              <em>{{ item.hint }}</em>
            </article>
          </div>
        </section>

        <section class="overview-note">
          <span>Read-Only First</span>
          <strong>编辑被收敛成一次性动作</strong>
          <p>默认只浏览资料。复制凭据、切换状态仍然在右侧完成，只有修改邮箱、订阅、密码或令牌时才进入编辑。</p>
        </section>
      </div>
    </template>
  </article>
</template>

<style scoped>
.surface-card {
  padding: 24px;
  border-radius: 22px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 22px 48px rgba(15, 23, 42, 0.08);
}

.editor-panel.is-editing {
  border-color: rgba(212, 175, 55, 0.18);
  box-shadow:
    0 26px 54px rgba(15, 23, 42, 0.1),
    0 0 0 1px rgba(212, 175, 55, 0.1);
}

.panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
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

.panel-toggle-btn {
  min-width: 108px;
  border-radius: 999px;
  font-weight: 700;
}

.panel-toggle-btn--accent {
  --el-button-bg-color: rgba(212, 175, 55, 0.12);
  --el-button-border-color: rgba(212, 175, 55, 0.24);
  --el-button-text-color: #171717;
  --el-button-hover-bg-color: rgba(212, 175, 55, 0.22);
  --el-button-hover-border-color: rgba(212, 175, 55, 0.36);
  --el-button-hover-text-color: #171717;
}

.detail-form {
  display: grid;
  gap: 18px;
}

.overview-stack {
  display: grid;
  gap: 18px;
}

.form-section {
  display: grid;
  gap: 16px;
  padding-top: 18px;
  border-top: 1px solid rgba(148, 163, 184, 0.18);
}

.form-section:first-of-type,
.overview-section:first-of-type {
  padding-top: 0;
  border-top: none;
}

.overview-section {
  display: grid;
  gap: 16px;
  padding-top: 18px;
  border-top: 1px solid rgba(148, 163, 184, 0.18);
}

.form-section__header {
  display: flex;
  align-items: flex-start;
  gap: 14px;
}

.form-section__index {
  width: 38px;
  height: 38px;
  display: grid;
  place-items: center;
  flex-shrink: 0;
  border-radius: 12px;
  background: rgba(15, 23, 42, 0.06);
  color: #0f172a;
  font-weight: 700;
}

.form-section__header strong {
  display: block;
  color: #0f172a;
  font-size: 0.98rem;
}

.form-section__header p {
  margin: 6px 0 0;
  color: #64748b;
  font-size: 0.82rem;
  line-height: 1.6;
}

.overview-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.overview-field {
  display: grid;
  gap: 10px;
  min-height: 108px;
  padding: 18px;
  border-radius: 18px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  box-shadow: inset 0 0 0 1px rgba(15, 23, 42, 0.06);
}

.overview-field span {
  color: #64748b;
  font-size: 0.78rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.overview-field strong {
  color: #0f172a;
  font-size: 1rem;
  line-height: 1.5;
  word-break: break-word;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px 16px;
}

.span-2 {
  grid-column: 1 / -1;
}

.editor-footer {
  display: grid;
  gap: 18px;
  margin-top: 22px;
}

.overview-note {
  display: grid;
  gap: 8px;
  padding: 20px;
  border-radius: 20px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background:
    linear-gradient(135deg, rgba(15, 23, 42, 0.03) 0%, rgba(212, 175, 55, 0.08) 100%),
    #ffffff;
}

.overview-note span {
  color: #8a6d1f;
  font-size: 0.76rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.overview-note strong {
  color: #0f172a;
  font-size: 1rem;
}

.overview-note p {
  margin: 0;
  color: #64748b;
  font-size: 0.84rem;
  line-height: 1.7;
}

.posture-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.posture-card {
  display: grid;
  gap: 6px;
  padding: 16px;
  border-radius: 18px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  box-shadow: inset 0 0 0 1px rgba(15, 23, 42, 0.06);
}

.posture-card span,
.posture-card em {
  font-style: normal;
  color: #64748b;
  font-size: 0.78rem;
}

.posture-card strong {
  color: #0f172a;
  font-size: 1rem;
}

.editor-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 10px;
}

:deep(.detail-form .el-form-item__label) {
  color: #0f172a;
  font-weight: 700;
}

:deep(.detail-form .el-input__wrapper),
:deep(.detail-form .el-select__wrapper),
:deep(.detail-form .el-textarea__inner),
:deep(.detail-form .el-date-editor.el-input__wrapper) {
  background: #ffffff;
  box-shadow: 0 0 0 1px rgba(15, 23, 42, 0.12) inset;
}

:deep(.detail-form .el-input__wrapper:hover),
:deep(.detail-form .el-select__wrapper:hover),
:deep(.detail-form .el-textarea__inner:hover),
:deep(.detail-form .el-date-editor.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px rgba(2, 132, 199, 0.22) inset;
}

:deep(.detail-form .el-input__wrapper.is-focus),
:deep(.detail-form .el-select__wrapper.is-focused),
:deep(.detail-form .el-textarea__inner:focus),
:deep(.detail-form .el-date-editor.el-input__wrapper.is-focus) {
  box-shadow:
    0 0 0 1px rgba(2, 132, 199, 0.34) inset,
    0 0 0 4px rgba(2, 132, 199, 0.08);
}

@media (max-width: 760px) {
  .surface-card {
    padding: 20px;
  }

  .overview-grid,
  .form-grid,
  .posture-grid {
    grid-template-columns: 1fr;
  }

  .panel-header,
  .editor-actions,
  .form-section__header {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
