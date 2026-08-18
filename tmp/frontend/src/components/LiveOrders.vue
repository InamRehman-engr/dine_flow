<template>
  <div class="orders">
    <PageHero
      :image="ORDERS_PHOTO"
      eyebrow="Service"
      title="Active orders"
      subtitle="Track every ticket from the floor to the pass — filter by kitchen status."
    >
      <template #aside>
        <div class="hero-metrics">
          <div><strong>{{ orders.length }}</strong><span>Open</span></div>
          <div><strong>{{ count('pending') }}</strong><span>Pending</span></div>
          <div><strong>{{ count('preparing') }}</strong><span>Cooking</span></div>
          <div><strong>{{ count('ready') }}</strong><span>Ready</span></div>
        </div>
      </template>
    </PageHero>

    <div class="split">
      <section class="feed">
        <header class="feed-head">
          <div>
            <h2>Ticket feed</h2>
            <p class="feed-sub">{{ filtered.length }} shown</p>
          </div>
          <div class="filters" role="tablist">
            <button type="button" role="tab" :aria-selected="filter === 'all'" :class="{ on: filter === 'all' }" @click="filter = 'all'">All</button>
            <button type="button" role="tab" :aria-selected="filter === 'pending'" :class="{ on: filter === 'pending' }" @click="filter = 'pending'">Pending</button>
            <button type="button" role="tab" :aria-selected="filter === 'preparing'" :class="{ on: filter === 'preparing' }" @click="filter = 'preparing'">Preparing</button>
            <button type="button" role="tab" :aria-selected="filter === 'ready'" :class="{ on: filter === 'ready' }" @click="filter = 'ready'">Ready</button>
          </div>
        </header>

        <div v-if="!filtered.length" class="empty-wrap">
          <EmptyPanel
            :image="EMPTY_ORDERS_PHOTO"
            title="Everything is quiet"
            body="No tickets match this filter. New guest orders will appear here instantly."
          >
            <template #icon>
              <ClipboardList :size="32" :stroke-width="1.6" />
            </template>
          </EmptyPanel>
        </div>

        <button
          v-for="(o, i) in filtered"
          :key="o.id"
          type="button"
          class="row"
          :class="{ selected: selected?.id === o.id }"
          :style="{ animationDelay: `${Math.min(i, 8) * 35}ms` }"
          @click="select(o)"
        >
          <div class="table-cell">
            <strong>T{{ o.table_number }}</strong>
            <small>{{ formatTime(o.created_at) }}</small>
          </div>
          <div class="items-cell">
            <p>{{ summary(o) }}</p>
            <em v-if="o.notes">{{ o.notes }}</em>
          </div>
          <span class="badge" :data-status="o.status">{{ o.status }}</span>
        </button>
      </section>

      <aside class="detail" v-if="selected">
        <header>
          <div>
            <p class="eyebrow">Order detail</p>
            <h2>Table {{ selected.table_number }}</h2>
          </div>
          <span class="badge" :data-status="selected.status">{{ selected.status }}</span>
        </header>
        <ul class="lines">
          <li v-for="item in selected.items" :key="item.id">
            <b>{{ item.quantity }}×</b>
            <div>
              <strong>{{ item.name }}</strong>
              <span v-if="item.modifiers?.length">{{ item.modifiers.map((m) => m.name).join(', ') }}</span>
            </div>
          </li>
        </ul>
        <p v-if="selected.notes" class="note">{{ selected.notes }}</p>
        <h3>Audit trail</h3>
        <ul class="audit" v-if="audits.length">
          <li v-for="a in audits" :key="a.id">
            <span>{{ a.from_status || '—' }} → <strong>{{ a.to_status }}</strong></span>
            <small>{{ a.actor_label }} · {{ formatTime(a.created_at) }}</small>
          </li>
        </ul>
        <p v-else class="muted-line">Loading audit…</p>
      </aside>

      <aside v-else class="detail empty-detail">
        <EmptyPanel
          :image="ORDERS_PHOTO"
          title="Select a ticket"
          body="Pick an order from the feed to inspect dishes and status history."
        >
          <template #icon>
            <ClipboardList :size="32" :stroke-width="1.6" />
          </template>
        </EmptyPanel>
      </aside>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ClipboardList } from '@lucide/vue'
import { api } from '../api'
import { EMPTY_ORDERS_PHOTO, ORDERS_PHOTO } from '../composables/useFoodImage'
import { useSocket } from '../composables/useSocket'
import EmptyPanel from './EmptyPanel.vue'
import PageHero from './PageHero.vue'

const orders = ref([])
const selected = ref(null)
const audits = ref([])
const filter = ref('all')
const { on, joinStaff } = useSocket()

const filtered = computed(() => {
  if (filter.value === 'all') return orders.value
  return orders.value.filter((o) => o.status === filter.value)
})

function count(status) {
  return orders.value.filter((o) => o.status === status).length
}
function summary(o) {
  return (o.items || []).map((i) => `${i.quantity}× ${i.name}`).join(' · ')
}
async function load() {
  const data = await api.get('/api/orders/live')
  orders.value = data.orders || []
}
async function select(o) {
  selected.value = o
  audits.value = []
  try {
    const data = await api.get(`/api/orders/${o.id}`)
    selected.value = data.order
    audits.value = data.order.audits || []
  } catch {
    audits.value = []
  }
}
function formatTime(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

onMounted(async () => {
  joinStaff()
  await load()
  on('new_order', load)
  on('status_update', load)
  on('floor_refresh', load)
})
</script>

<style scoped>
.orders {
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
  animation: rise 0.35s var(--ease-out, cubic-bezier(0.22, 1, 0.36, 1));
}

.hero-metrics {
  display: grid;
  grid-template-columns: repeat(4, auto);
  gap: 0.5rem;
}

.hero-metrics div {
  min-width: 62px;
  padding: 0.45rem 0.6rem;
  border-radius: var(--radius);
  background: rgba(31, 26, 23, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.14);
  text-align: center;
}

.hero-metrics strong {
  display: block;
  font-size: 1.15rem;
  font-weight: 800;
  line-height: 1.1;
}

.hero-metrics span {
  font-size: 0.62rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  opacity: 0.85;
}

.split {
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(280px, 360px);
  gap: 0.9rem;
  align-items: start;
  min-height: 520px;
}

.feed,
.detail {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow);
}

.feed {
  overflow: hidden;
  padding-bottom: 0.35rem;
}

.feed-head {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 0.85rem;
  align-items: center;
  padding: 0.9rem 1rem;
  border-bottom: 1px solid var(--border);
  background: var(--surface-2);
}

.feed-head h2 {
  margin: 0;
  font-size: 1.1rem;
  letter-spacing: -0.02em;
}

.feed-sub {
  margin: 0.2rem 0 0;
  font-size: 0.78rem;
  color: #94a3b8;
  font-weight: 550;
}

.filters {
  display: flex;
  gap: 0.3rem;
  flex-wrap: wrap;
  padding: 0.2rem;
  background: rgba(15, 23, 42, 0.04);
  border-radius: 999px;
}

.filters button {
  border: 0;
  background: transparent;
  border-radius: 999px;
  padding: 0.4rem 0.8rem;
  font: inherit;
  font-size: 0.78rem;
  font-weight: 650;
  color: #64748b;
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease, transform 0.15s ease;
}

.filters button:hover {
  color: #0b1220;
}

.filters button.on {
  background: #0b1220;
  color: #fff;
  box-shadow: 0 6px 14px rgba(11, 18, 32, 0.2);
}

.filters button:active {
  transform: scale(0.97);
}

.row {
  width: 100%;
  display: grid;
  grid-template-columns: 76px 1fr auto;
  gap: 0.9rem;
  align-items: center;
  text-align: left;
  border: 0;
  border-bottom: 1px solid rgba(15, 23, 42, 0.05);
  background: transparent;
  padding: 1rem 1.2rem;
  cursor: pointer;
  font: inherit;
  animation: ticketIn 0.35s var(--ease-out, cubic-bezier(0.22, 1, 0.36, 1)) both;
  transition: background 0.18s ease, box-shadow 0.18s ease;
}

.row:hover {
  background: rgba(13, 148, 136, 0.04);
}

.row:focus-visible {
  outline: 2px solid #0d9488;
  outline-offset: -2px;
}

.row.selected {
  background: rgba(13, 148, 136, 0.08);
  box-shadow: inset 3px 0 0 #14b8a6;
}

.table-cell strong {
  display: block;
  font-size: 1.2rem;
  letter-spacing: -0.03em;
  font-weight: 750;
}

.table-cell small {
  color: #94a3b8;
  font-weight: 600;
  font-size: 0.75rem;
  font-variant-numeric: tabular-nums;
}

.items-cell p {
  margin: 0;
  font-weight: 600;
  font-size: 0.92rem;
  color: #0b1220;
  line-height: 1.35;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.items-cell em {
  display: block;
  margin-top: 0.25rem;
  font-style: normal;
  color: #94a3b8;
  font-size: 0.8rem;
}

.badge {
  font-size: 0.68rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-weight: 800;
  padding: 0.3rem 0.6rem;
  border-radius: 999px;
  background: #f1f5f9;
  color: #475569;
  white-space: nowrap;
}

.badge[data-status='pending'] { background: #ffedd5; color: #9a3412; }
.badge[data-status='preparing'] { background: #dbeafe; color: #1d4ed8; }
.badge[data-status='ready'] { background: #ccfbf1; color: #0f766e; }

.detail {
  padding: 1.3rem 1.35rem 1.5rem;
  position: sticky;
  top: 5.75rem;
}

.detail header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 0.75rem;
  margin-bottom: 1.1rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid rgba(15, 23, 42, 0.06);
}

.eyebrow {
  margin: 0;
  font-size: 0.68rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #64748b;
  font-weight: 750;
}

.detail h2 {
  margin: 0.3rem 0 0;
  font-size: 1.45rem;
  letter-spacing: -0.03em;
}

.lines {
  list-style: none;
  margin: 0;
  padding: 0;
}

.lines li {
  display: grid;
  grid-template-columns: 40px 1fr;
  gap: 0.55rem;
  padding: 0.7rem 0;
  border-bottom: 1px solid rgba(15, 23, 42, 0.05);
}

.lines b {
  color: #0d9488;
  font-size: 1.05rem;
  font-weight: 800;
}

.lines strong {
  display: block;
  font-size: 0.95rem;
}

.lines span {
  display: block;
  color: #64748b;
  font-size: 0.85rem;
  margin-top: 0.15rem;
}

.note {
  margin: 0.95rem 0 0;
  padding: 0.75rem 0.85rem;
  border-radius: 14px;
  background: #fffbeb;
  color: #92400e;
  font-weight: 600;
  font-size: 0.9rem;
  line-height: 1.4;
}

.detail h3 {
  margin: 1.25rem 0 0.5rem;
  font-size: 0.7rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #64748b;
  font-weight: 750;
}

.audit {
  list-style: none;
  margin: 0;
  padding: 0;
}

.audit li {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  padding: 0.6rem 0;
  border-bottom: 1px solid rgba(15, 23, 42, 0.05);
  font-size: 0.9rem;
}

.audit small {
  color: #94a3b8;
  font-size: 0.78rem;
}

.empty-wrap {
  padding: 1rem;
}

.empty-detail {
  padding: 1rem;
  display: grid;
  place-items: center;
  min-height: 360px;
}

.muted-line {
  color: var(--muted);
  font-size: 0.9rem;
  margin: 0.5rem 0 0;
}

@keyframes rise {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: none; }
}

@keyframes ticketIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: none; }
}

@media (max-width: 900px) {
  .split {
    grid-template-columns: 1fr;
  }
  .detail {
    position: static;
  }
  .row {
    grid-template-columns: 64px 1fr;
  }
  .badge {
    grid-column: 2;
    justify-self: start;
  }
  .hero-metrics {
    grid-template-columns: repeat(2, auto);
  }
}
</style>
