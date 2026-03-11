<script setup>
const props = defineProps({
  items: {
    type: Array,
    default: () => [],
  },
})
</script>

<template>
  <section class="summary-grid">
    <article
      v-for="(item, index) in props.items"
      :key="item.label"
      class="summary-card"
      :class="`tone-${item.tone || 'neutral'}`"
    >
      <div class="summary-card__head">
        <span class="summary-label">{{ item.label }}</span>
        <span class="summary-index">{{ String(index + 1).padStart(2, '0') }}</span>
      </div>
      <strong class="summary-value">{{ item.value }}</strong>
      <p class="summary-note">{{ item.note }}</p>
    </article>
  </section>
</template>

<style scoped>
.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 14px;
}

.summary-card {
  position: relative;
  display: grid;
  gap: 12px;
  min-height: 168px;
  padding: 18px;
  border-radius: 24px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  background:
    radial-gradient(circle at top right, rgba(255, 255, 255, 0.92), rgba(255, 255, 255, 0.66)),
    linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
  box-shadow:
    0 20px 44px rgba(15, 23, 42, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.72);
  overflow: hidden;
}

.summary-card::before {
  content: '';
  position: absolute;
  inset: auto 16px 16px 16px;
  height: 4px;
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.18);
}

.summary-card__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.summary-label {
  color: #475569;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.summary-index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 38px;
  min-height: 30px;
  padding: 0 10px;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.06);
  color: #334155;
  font-family: 'Fira Code', 'Space Grotesk', monospace;
  font-size: 0.78rem;
}

.summary-value {
  color: #0f172a;
  font-family: 'Manrope', 'Segoe UI', sans-serif;
  font-size: 1.4rem;
  font-weight: 800;
  line-height: 1.15;
  letter-spacing: -0.04em;
}

.summary-note {
  margin: 0;
  color: #475569;
  font-size: 0.84rem;
  line-height: 1.72;
}

.tone-success::before {
  background: linear-gradient(90deg, rgba(16, 185, 129, 0.88), rgba(52, 211, 153, 0.44));
}

.tone-warning::before {
  background: linear-gradient(90deg, rgba(245, 158, 11, 0.88), rgba(251, 191, 36, 0.44));
}

.tone-primary::before {
  background: linear-gradient(90deg, rgba(59, 130, 246, 0.88), rgba(56, 189, 248, 0.44));
}

.tone-danger::before {
  background: linear-gradient(90deg, rgba(239, 68, 68, 0.88), rgba(248, 113, 113, 0.44));
}

.tone-neutral::before,
.tone-info::before {
  background: linear-gradient(90deg, rgba(100, 116, 139, 0.88), rgba(148, 163, 184, 0.44));
}

@media (max-width: 760px) {
  .summary-card {
    min-height: 0;
  }
}
</style>
