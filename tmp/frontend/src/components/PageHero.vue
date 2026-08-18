<template>
  <section class="page-hero" :style="{ backgroundImage: `url(${image})` }">
    <div class="shade" />
    <div class="copy">
      <p v-if="eyebrow" class="eyebrow">{{ eyebrow }}</p>
      <h2>{{ title }}</h2>
      <p v-if="subtitle" class="sub">{{ subtitle }}</p>
      <div v-if="$slots.actions" class="actions">
        <slot name="actions" />
      </div>
    </div>
    <div v-if="$slots.aside" class="aside">
      <slot name="aside" />
    </div>
  </section>
</template>

<script setup>
defineProps({
  image: { type: String, required: true },
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
  eyebrow: { type: String, default: '' },
})
</script>

<style scoped>
.page-hero {
  position: relative;
  min-height: 168px;
  border-radius: var(--radius-lg);
  overflow: hidden;
  background-size: cover;
  background-position: center;
  border: 1px solid var(--border);
  box-shadow: var(--shadow);
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 1rem;
  padding: 1.25rem 1.35rem;
  color: #fff;
}

.shade {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(105deg, rgba(31, 26, 23, 0.78) 0%, rgba(31, 26, 23, 0.45) 48%, rgba(31, 26, 23, 0.25) 100%);
  pointer-events: none;
}

.copy,
.aside {
  position: relative;
  z-index: 1;
}

.eyebrow {
  margin: 0 0 0.35rem;
  font-size: 0.7rem;
  font-weight: 750;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  opacity: 0.85;
}

h2 {
  margin: 0;
  font-size: clamp(1.35rem, 2.4vw, 1.75rem);
  font-weight: 750;
  letter-spacing: -0.03em;
  color: #fff;
}

.sub {
  margin: 0.4rem 0 0;
  max-width: 42ch;
  font-size: 0.9rem;
  line-height: 1.45;
  color: rgba(255, 255, 255, 0.82);
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
  margin-top: 0.85rem;
}

.aside {
  align-self: center;
}

@media (max-width: 720px) {
  .page-hero {
    min-height: 140px;
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
