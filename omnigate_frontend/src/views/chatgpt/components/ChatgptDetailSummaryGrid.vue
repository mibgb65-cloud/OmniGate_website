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
      v-for="item in props.items"
      :key="item.label"
      class="summary-card"
      :class="`tone-${item.tone}`"
    >
      <span>{{ item.label }}</span>
      <strong>{{ item.value }}</strong>
      <em>{{ item.note }}</em>
    </article>
  </section>
</template>

<style scoped>
.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.summary-card {
  display: grid;
  gap: 8px;
  padding: 18px 20px;
  border-radius: 22px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 22px 48px rgba(15, 23, 42, 0.08);
}

.summary-card span,
.summary-card em {
  font-style: normal;
}

.summary-card span {
  color: #64748b;
  font-size: 0.8rem;
}

.summary-card strong {
  color: #0f172a;
  font-size: 1.16rem;
  letter-spacing: -0.03em;
}

.summary-card em {
  color: #475569;
  font-size: 0.78rem;
  line-height: 1.55;
}

.tone-success {
  box-shadow:
    inset 0 0 0 1px rgba(16, 185, 129, 0.1),
    0 16px 34px rgba(15, 23, 42, 0.06);
}

.tone-warning {
  box-shadow:
    inset 0 0 0 1px rgba(245, 158, 11, 0.12),
    0 16px 34px rgba(15, 23, 42, 0.06);
}

.tone-primary {
  box-shadow:
    inset 0 0 0 1px rgba(2, 132, 199, 0.12),
    0 16px 34px rgba(15, 23, 42, 0.06);
}

@media (max-width: 1080px) {
  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .summary-grid {
    grid-template-columns: 1fr;
  }
}
</style>
