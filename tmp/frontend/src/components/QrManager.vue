<template>
  <div class="hub">
    <PageHero
      :image="QR_PHOTO"
      eyebrow="Guest ordering"
      title="QR codes"
      subtitle="Print branded table cards so guests can open the menu and order from their seat."
    >
      <template #actions>
        <button class="hero-btn" type="button" @click="refreshUrl">Refresh detection</button>
      </template>
      <template #aside>
        <div class="url-chip">
          <small>{{ sourceLabel }}</small>
          <code>{{ publicUrl || 'Detecting…' }}</code>
        </div>
      </template>
    </PageHero>

    <p v-if="hint" class="hint">{{ hint }}</p>

    <div class="grid">
      <section class="card">
        <h2>Print all tables</h2>
        <p class="muted">Choose density for A4. Larger codes scan more reliably.</p>
        <div class="controls">
          <div class="seg">
            <button type="button" :class="{ active: perPage === 1 }" @click="perPage = 1">1 / page</button>
            <button type="button" :class="{ active: perPage === 2 }" @click="perPage = 2">2 / page</button>
            <button type="button" :class="{ active: perPage === 4 }" @click="perPage = 4">4 / page</button>
          </div>
          <button class="btn" type="button" :disabled="loading || !tables.length" @click="exportAll">
            {{ loading ? 'Preparing…' : 'Download PDF' }}
          </button>
        </div>
        <p v-if="error" class="error-text">{{ error }}</p>
      </section>

      <section class="card wide">
        <h2>Per-table reprint</h2>
        <div v-if="tables.length" class="table-list">
          <article v-for="t in tables" :key="t.id">
            <div class="thumb" :style="{ backgroundImage: `url(${FLOOR_PHOTO})` }" />
            <div>
              <strong>Table {{ t.number }}</strong>
              <span class="muted">{{ t.capacity }} seats</span>
            </div>
            <div class="actions">
              <button class="btn btn-ghost btn-sm" type="button" @click="reprint(t, false)">Reprint</button>
              <button class="btn btn-ghost btn-sm" type="button" @click="reprint(t, true)">Rotate</button>
            </div>
          </article>
        </div>
        <EmptyPanel
          v-else
          :image="EMPTY_FLOOR_PHOTO"
          title="No tables yet"
          body="Add tables on Live Floor first, then return here to print QR cards."
        >
          <template #icon>
            <QrCode :size="32" :stroke-width="1.6" />
          </template>
          <template #actions>
            <router-link class="btn" to="/admin">Open floor</router-link>
          </template>
        </EmptyPanel>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { QrCode } from '@lucide/vue'
import { api } from '../api'
import { EMPTY_FLOOR_PHOTO, FLOOR_PHOTO, QR_PHOTO } from '../composables/useFoodImage'
import EmptyPanel from './EmptyPanel.vue'
import PageHero from './PageHero.vue'

const tables = ref([])
const perPage = ref(2)
const loading = ref(false)
const error = ref('')
const publicUrl = ref('')
const source = ref('')
const hint = ref('')

const sourceLabel = computed(() => {
  return (
    {
      ngrok: 'ngrok tunnel',
      request: 'this browser session',
      env: 'env fallback',
      local: 'localhost',
      localhost: 'localhost',
    }[source.value] || source.value || 'auto'
  )
})

async function refreshUrl() {
  try {
    const data = await api.get('/api/public/config')
    publicUrl.value = data.public_base_url || ''
    source.value = data.public_url_source || ''
    hint.value = data.public_url_hint || ''
  } catch {
    publicUrl.value = ''
  }
}

async function load() {
  const data = await api.get('/api/tenant/tables')
  tables.value = data.tables || []
  await refreshUrl()
}

async function exportAll() {
  error.value = ''
  loading.value = true
  try {
    await refreshUrl()
    await api.download(`/api/tenant/export-qrs?per_page=${perPage.value}`, 'dineflow-table-qrs.pdf')
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

async function reprint(t, rotate) {
  const q = rotate ? '?rotate=1' : ''
  await api.download(`/api/tenant/tables/${t.id}/qr${q}`, `dineflow-table-${t.number}-qr.pdf`)
  if (rotate) await load()
}

onMounted(load)
</script>

<style scoped>
.hub {
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
  animation: rise 0.35s ease;
}
.hero-btn {
  border: 1px solid rgba(255, 255, 255, 0.35);
  background: rgba(255, 255, 255, 0.12);
  color: #fff;
  border-radius: var(--radius);
  min-height: 36px;
  padding: 0.35rem 0.85rem;
  font: inherit;
  font-weight: 650;
  font-size: 0.82rem;
  cursor: pointer;
}
.url-chip {
  max-width: 280px;
  padding: 0.65rem 0.8rem;
  border-radius: var(--radius);
  background: rgba(31, 26, 23, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.14);
}
.url-chip small {
  display: block;
  font-size: 0.65rem;
  font-weight: 750;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  opacity: 0.8;
  margin-bottom: 0.25rem;
}
.url-chip code {
  display: block;
  font-size: 0.78rem;
  word-break: break-all;
  color: #fff;
}
.hint {
  color: var(--warn);
  font-weight: 650;
  margin: 0;
}
.grid {
  display: grid;
  grid-template-columns: minmax(280px, 380px) 1fr;
  gap: 0.9rem;
}
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 1.15rem 1.25rem;
  box-shadow: var(--shadow);
}
h2 {
  margin: 0 0 0.35rem;
  font-size: 1.1rem;
}
.muted {
  margin: 0;
  color: var(--muted);
  font-size: 0.88rem;
}
.controls {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  align-items: center;
  margin-top: 1rem;
}
.table-list {
  margin-top: 0.75rem;
}
.table-list article {
  display: grid;
  grid-template-columns: 52px 1fr auto;
  gap: 0.75rem;
  align-items: center;
  padding: 0.75rem 0;
  border-bottom: 1px solid var(--border);
}
.thumb {
  width: 52px;
  height: 52px;
  border-radius: var(--radius);
  background-size: cover;
  background-position: center;
}
.table-list strong {
  display: block;
}
.actions {
  display: flex;
  gap: 0.4rem;
  flex-wrap: wrap;
}
@keyframes rise {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: none; }
}
@media (max-width: 900px) {
  .grid { grid-template-columns: 1fr; }
}
</style>
