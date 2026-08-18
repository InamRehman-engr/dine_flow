<template>
  <div class="empty-panel">
    <div class="visual" :style="{ backgroundImage: image ? `url(${image})` : 'none' }">
      <div class="shade" />
      <slot name="icon" />
    </div>
    <div class="copy">
      <h3>{{ title }}</h3>
      <p>{{ body }}</p>
      <div v-if="$slots.actions" class="actions">
        <slot name="actions" />
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, required: true },
  body: { type: String, required: true },
  image: { type: String, default: '' },
})
</script>

<style scoped>
.empty-panel {
  display: grid;
  grid-template-columns: minmax(140px, 220px) 1fr;
  gap: 1rem;
  align-items: center;
  padding: 1rem;
  border: 1px dashed var(--border-strong);
  border-radius: var(--radius-lg);
  background: var(--surface-2);
}

.visual {
  position: relative;
  min-height: 120px;
  border-radius: var(--radius);
  overflow: hidden;
  background: var(--bg-subtle) center / cover no-repeat;
  display: grid;
  place-items: center;
  color: var(--muted);
}

.shade {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(31, 26, 23, 0.15), rgba(31, 26, 23, 0.45));
}

.visual :deep(svg) {
  position: relative;
  z-index: 1;
  color: #fff;
  opacity: 0.9;
}

.copy h3 {
  margin: 0;
  font-size: 1.05rem;
  letter-spacing: -0.02em;
}

.copy p {
  margin: 0.35rem 0 0;
  color: var(--muted);
  font-size: 0.9rem;
  line-height: 1.45;
  max-width: 42ch;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
  margin-top: 0.85rem;
}

@media (max-width: 640px) {
  .empty-panel {
    grid-template-columns: 1fr;
  }
  .visual {
    min-height: 100px;
  }
}
</style>
