<template>
  <div class="kds">
    <div class="section-head">
      <div>
        <h2 class="page-title">Kitchen</h2>
        <p class="page-sub">Tickets move left to right: pending → preparing → ready.</p>
      </div>
      <div class="row">
        <span class="count">{{ orders.length }} open</span>
        <button class="btn btn-ghost btn-sm" type="button" @click="load">Refresh</button>
      </div>
    </div>

    <p v-if="error" class="error-text">{{ error }}</p>

    <div v-if="!orders.length" class="empty">No open tickets.</div>

    <div v-else class="board">
      <section v-for="col in columns" :key="col.key" class="lane">
        <header>
          <h3>{{ col.label }}</h3>
          <span>{{ byStatus(col.key).length }}</span>
        </header>
        <div class="lane-body">
          <article v-for="order in byStatus(col.key)" :key="order.id" class="ticket">
            <div class="ticket-top">
              <strong>Table {{ order.table_number }}</strong>
              <span class="muted">{{ formatTime(order.created_at) }}</span>
            </div>
            <ul>
              <li v-for="item in order.items" :key="item.id">
                <b>{{ item.quantity }}</b> {{ item.name }}
              </li>
            </ul>
            <p v-if="order.notes" class="note">{{ order.notes }}</p>
            <div class="actions">
              <button
                v-if="order.status === 'pending'"
                class="btn btn-sm"
                type="button"
                @click="setStatus(order, 'preparing')"
              >Start</button>
              <button
                v-if="order.status === 'preparing'"
                class="btn btn-sm"
                type="button"
                @click="setStatus(order, 'ready')"
              >Ready</button>
              <button
                v-if="order.status === 'ready'"
                class="btn btn-sm"
                type="button"
                @click="setStatus(order, 'served')"
              >Served</button>
              <button
                v-if="order.status !== 'served' && order.status !== 'cancelled'"
                class="btn btn-ghost btn-sm"
                type="button"
                @click="setStatus(order, 'cancelled')"
              >Cancel</button>
            </div>
          </article>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { api } from '../api'
import { useSocket } from '../composables/useSocket'

const props = defineProps({
  tenant: { type: Object, default: null },
})

const orders = ref([])
const error = ref('')
const tenantId = computed(() => props.tenant?.id || null)
const { on } = useSocket(tenantId)

const columns = [
  { key: 'pending', label: 'Pending' },
  { key: 'preparing', label: 'Preparing' },
  { key: 'ready', label: 'Ready' },
]

function byStatus(status) {
  return orders.value.filter((o) => o.status === status)
}

async function load() {
  error.value = ''
  try {
    const data = await api.get('/api/orders/kitchen')
    orders.value = data.orders || []
  } catch (e) {
    error.value = e.message
  }
}

async function setStatus(order, status) {
  try {
    await api.patch(`/api/orders/${order.id}/status`, {
      status,
      version: order.version,
    })
    await load()
  } catch (e) {
    error.value = e.message
    await load()
  }
}

function formatTime(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

const offs = [
  on('new_order', () => load()),
  on('status_update', () => load()),
]

watch(tenantId, (id) => { if (id) load() })
onMounted(load)
onUnmounted(() => offs.forEach((off) => off && off()))
</script>

<style scoped>
.count {
  font-size: 0.8rem;
  color: var(--muted);
  font-weight: 500;
}
.empty {
  padding: 2.75rem 1rem;
  text-align: center;
  color: var(--muted);
  border: 1px solid var(--line);
  border-radius: 14px;
  background:
    linear-gradient(180deg, rgba(255,255,255,0.88), rgba(255,255,255,0.92)),
    url('https://images.unsplash.com/photo-1414235077428-338989a2e8c0?auto=format&fit=crop&w=1200&q=60')
      center/cover;
}
.board {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.85rem;
  align-items: start;
}
.lane {
  border: 1px solid #d9ddd8;
  border-radius: 14px;
  min-height: 300px;
  background: rgba(255, 255, 255, 0.86);
  overflow: hidden;
  box-shadow: 0 12px 28px rgba(16, 20, 18, 0.06);
}
.lane:nth-child(1) { border-top: 3px solid #8a8f96; }
.lane:nth-child(2) { border-top: 3px solid #8a7048; }
.lane:nth-child(3) { border-top: 3px solid #2f6b4f; }
.lane header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.8rem 0.95rem;
  border-bottom: 1px solid var(--line);
  background: linear-gradient(180deg, #fafaf8, #f3f4f2);
}
.lane h3 {
  margin: 0;
  font-size: 0.72rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  font-family: var(--font-body);
  font-weight: 600;
  color: var(--muted);
}
.lane header span {
  font-size: 0.75rem;
  color: var(--ink);
  font-weight: 600;
  min-width: 1.4rem;
  height: 1.4rem;
  border-radius: 999px;
  display: grid;
  place-items: center;
  background: #ececea;
}
.lane-body {
  padding: 0.7rem;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}
.ticket {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 0.85rem;
  box-shadow: 0 4px 12px rgba(16, 20, 18, 0.04);
}
.ticket-top {
  display: flex;
  justify-content: space-between;
  gap: 0.5rem;
  margin-bottom: 0.45rem;
}
.ticket-top strong {
  font-size: 0.98rem;
}
.ticket ul {
  margin: 0;
  padding: 0;
  list-style: none;
}
.ticket li {
  font-size: 0.9rem;
  padding: 0.18rem 0;
  color: var(--ink-2);
  border-bottom: 1px dashed #ececec;
}
.ticket li:last-child { border-bottom: 0; }
.ticket li b {
  display: inline-block;
  min-width: 1.1rem;
  color: var(--accent);
}
.note {
  margin: 0.45rem 0 0;
  font-size: 0.8rem;
  color: var(--muted);
}
.actions {
  display: flex;
  gap: 0.4rem;
  flex-wrap: wrap;
  margin-top: 0.75rem;
}
@media (max-width: 900px) {
  .board { grid-template-columns: 1fr; }
}
</style>
