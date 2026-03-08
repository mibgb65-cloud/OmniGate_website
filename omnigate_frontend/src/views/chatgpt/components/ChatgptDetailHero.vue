<script setup>
import { ArrowLeft, CopyDocument, Delete, Download, EditPen, Refresh } from '@element-plus/icons-vue'

const props = defineProps({
  detail: {
    type: Object,
    default: () => ({}),
  },
  commandDeck: {
    type: Array,
    default: () => [],
  },
  copiedField: {
    type: String,
    default: '',
  },
  editing: {
    type: Boolean,
    default: false,
  },
  deleting: {
    type: Boolean,
    default: false,
  },
  formatAccountStatus: {
    type: Function,
    required: true,
  },
  resolveStatusTag: {
    type: Function,
    required: true,
  },
  resolveTierTag: {
    type: Function,
    required: true,
  },
  formatSubTier: {
    type: Function,
    required: true,
  },
  formatDisplayDate: {
    type: Function,
    required: true,
  },
})

const emit = defineEmits(['back', 'refresh', 'export', 'copy-email', 'start-edit', 'cancel-edit', 'delete'])
</script>

<template>
  <section class="hero-panel">
    <div class="hero-main">
      <el-button text :icon="ArrowLeft" class="back-link" @click="emit('back')">返回账号池</el-button>

      <div class="hero-kicker">ChatGPT Asset Profile</div>

      <div class="hero-copy">
        <h1>{{ props.detail?.email || '账号详情' }}</h1>
        <p>围绕身份、会话材料、安全状态和生命周期组织操作入口，让维护动作集中在一个工作台完成。</p>
      </div>

      <div class="hero-badges">
        <el-tag :type="props.resolveStatusTag(props.detail?.accountStatus)" effect="dark">
          {{ props.formatAccountStatus(props.detail?.accountStatus) }}
        </el-tag>
        <el-tag :type="props.resolveTierTag(props.detail?.subTier)" effect="plain">
          {{ props.formatSubTier(props.detail?.subTier) }}
        </el-tag>
        <el-tag effect="plain">到期 {{ props.formatDisplayDate(props.detail?.expireDate, { includeTime: false }) }}</el-tag>
      </div>
    </div>

    <div class="hero-side">
      <div class="hero-side__head">
        <div>
          <span class="section-kicker section-kicker--light">Control Deck</span>
          <strong>运维概况</strong>
        </div>
      </div>

      <div class="command-grid">
        <article
          v-for="item in props.commandDeck"
          :key="item.label"
          class="command-card"
          :class="`tone-${item.tone}`"
        >
          <span>{{ item.label }}</span>
          <strong>{{ item.value }}</strong>
          <em>{{ item.hint }}</em>
        </article>
      </div>

      <div class="hero-actions">
        <el-button
          class="hero-action-btn hero-action-btn--accent"
          :icon="EditPen"
          @click="emit(props.editing ? 'cancel-edit' : 'start-edit')"
        >
          {{ props.editing ? '退出编辑' : '编辑资料' }}
        </el-button>
        <el-button class="hero-action-btn" :icon="Refresh" @click="emit('refresh')">刷新</el-button>
        <el-button class="hero-action-btn" :icon="Download" @click="emit('export')">导出账号</el-button>
        <el-button class="hero-action-btn" :icon="CopyDocument" @click="emit('copy-email')">
          {{ props.copiedField === 'hero-email' ? '已复制邮箱' : '复制邮箱' }}
        </el-button>
        <el-button type="danger" plain :icon="Delete" :loading="props.deleting" @click="emit('delete')">删除账号</el-button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.hero-panel {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(320px, 0.85fr);
  gap: 20px;
  padding: 28px;
  overflow: hidden;
  border-radius: 28px;
  color: #e2e8f0;
  background:
    radial-gradient(circle at 88% 18%, rgba(202, 138, 4, 0.16), transparent 26%),
    radial-gradient(circle at 18% 10%, rgba(56, 189, 248, 0.12), transparent 24%),
    linear-gradient(135deg, rgba(2, 6, 23, 0.98) 0%, rgba(15, 23, 42, 0.96) 60%, rgba(28, 55, 87, 0.92) 100%);
  box-shadow: 0 30px 70px rgba(2, 6, 23, 0.24);
}

.hero-panel::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    linear-gradient(rgba(148, 163, 184, 0.08) 1px, transparent 1px),
    linear-gradient(90deg, rgba(148, 163, 184, 0.08) 1px, transparent 1px);
  background-size: 52px 52px;
  mask-image: linear-gradient(140deg, rgba(0, 0, 0, 0.8), transparent 88%);
  pointer-events: none;
}

.hero-main,
.hero-side {
  position: relative;
  z-index: 1;
}

.hero-main {
  display: grid;
  gap: 16px;
  align-content: start;
}

.back-link {
  width: fit-content;
  padding-left: 0;
  color: rgba(226, 232, 240, 0.9);
}

.hero-kicker {
  width: fit-content;
  display: inline-flex;
  align-items: center;
  padding: 8px 14px;
  border-radius: 999px;
  border: 1px solid rgba(202, 138, 4, 0.2);
  background: rgba(202, 138, 4, 0.12);
  color: #facc15;
  font-size: 0.76rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.hero-copy {
  display: grid;
  gap: 10px;
  max-width: 640px;
}

.hero-copy h1 {
  margin: 0;
  font-family: 'Manrope', 'Segoe UI', sans-serif;
  font-size: clamp(2rem, 4.4vw, 3rem);
  font-weight: 800;
  line-height: 1.04;
  letter-spacing: -0.04em;
  color: #f8fafc;
}

.hero-copy p {
  margin: 0;
  color: rgba(226, 232, 240, 0.78);
  font-size: 0.98rem;
  line-height: 1.75;
}

.hero-badges,
.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.hero-side {
  display: grid;
  gap: 18px;
  align-content: start;
  padding: 18px;
  border-radius: 22px;
  border: 1px solid rgba(226, 232, 240, 0.12);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.1), rgba(255, 255, 255, 0.04));
  backdrop-filter: blur(10px);
}

.hero-side__head strong {
  color: #f8fafc;
  font-size: 1rem;
}

.section-kicker {
  display: block;
  margin-bottom: 8px;
  font-size: 0.72rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #64748b;
}

.section-kicker--light {
  color: rgba(191, 219, 254, 0.72);
}

.command-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.command-card {
  display: grid;
  gap: 6px;
  padding: 14px 16px;
  border-radius: 18px;
  border: 1px solid rgba(226, 232, 240, 0.08);
  background: rgba(2, 6, 23, 0.18);
}

.command-card span,
.command-card em {
  font-style: normal;
  color: rgba(226, 232, 240, 0.66);
  font-size: 0.76rem;
}

.command-card strong {
  color: #f8fafc;
  font-size: 1.16rem;
  line-height: 1.2;
}

.hero-action-btn {
  --el-button-bg-color: rgba(255, 255, 255, 0.08);
  --el-button-border-color: rgba(226, 232, 240, 0.16);
  --el-button-text-color: #f8fafc;
  --el-button-hover-bg-color: rgba(255, 255, 255, 0.14);
  --el-button-hover-border-color: rgba(255, 255, 255, 0.24);
  --el-button-hover-text-color: #ffffff;
  border-radius: 999px;
}

.hero-action-btn--accent {
  --el-button-bg-color: rgba(212, 175, 55, 0.18);
  --el-button-border-color: rgba(212, 175, 55, 0.28);
  --el-button-text-color: #f8fafc;
  --el-button-hover-bg-color: rgba(212, 175, 55, 0.28);
  --el-button-hover-border-color: rgba(212, 175, 55, 0.42);
}

@media (max-width: 1080px) {
  .hero-panel {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .command-grid {
    grid-template-columns: 1fr;
  }

  .hero-panel {
    padding: 20px;
  }
}
</style>
