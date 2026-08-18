<template>
  <div class="kds" :class="{ flash: flashing }" @pointerdown="unlock">
    <div class="toolbar">
      <div class="stats" aria-label="Order counts">
        <div class="stat">
          <span class="stat-val">{{ orders.length }}</span>
          <span class="stat-lbl">Open</span>
        </div>
        <div class="stat pending">
          <span class="stat-val">{{ byStatus('pending').length }}</span>
          <span class="stat-lbl">New</span>
        </div>
        <div class="stat preparing">
          <span class="stat-val">{{ byStatus('preparing').length }}</span>
          <span class="stat-lbl">Cooking</span>
        </div>
        <div class="stat ready">
          <span class="stat-val">{{ byStatus('ready').length }}</span>
          <span class="stat-lbl">Ready</span>
        </div>
      </div>

      <div class="filters" role="tablist" aria-label="Station filter">
        <button type="button" class="chip" :class="{ active: !stationId }" @click="stationId = ''">
          All stations
        </button>
        <button
          v-for="s in stations"
          :key="s.id"
          type="button"
          class="chip"
          :class="{ active: stationId === s.id }"
          @click="stationId = s.id"
        >
          {{ s.name }}
        </button>
      </div>

      <button
        class="sound"
        type="button"
        :class="{ on: soundEnabled }"
        :aria-pressed="soundEnabled"
        @click="toggleSound"
      >
        <Volume2 v-if="soundEnabled" :size="18" :stroke-width="2" />
        <VolumeX v-else :size="18" :stroke-width="2" />
        {{ soundEnabled ? 'Sound on' : 'Sound off' }}
      </button>
    </div>

    <p v-if="error" class="error" role="alert">{{ error }}</p>

    <div class="board">
      <section v-for="col in columns" :key="col.key" class="lane" :data-lane="col.key">
        <header class="lane-head">
          <div class="lane-title">
            <span class="lane-dot" aria-hidden="true" />
            <h2>{{ col.label }}</h2>
          </div>
          <span class="lane-count">{{ byStatus(col.key).length }}</span>
        </header>

        <div class="lane-body">
          <article
            v-for="order in byStatus(col.key)"
            :key="order.id"
            class="ticket"
            :class="{ 'flash-new': justArrived.has(order.id) }"
            :data-age="ageBand(order)"
            :data-status="order.status"
          >
            <div class="ticket-head">
              <div>
                <span class="order-id">#{{ shortId(order.id) }}</span>
                <span class="meta">
                  <UtensilsCrossed :size="13" :stroke-width="2.25" />
                  Table {{ order.table_number }}
                  <span class="sep">·</span>
                  Dine in
                </span>
              </div>
              <div class="timer" :data-age="ageBand(order)">
                <Clock :size="16" :stroke-width="2.25" />
                {{ elapsed(order.created_at) }}
              </div>
            </div>

            <ul class="items">
              <li v-for="item in order.items" :key="item.id">
                <span class="qty">{{ item.quantity }}</span>
                <div class="item-body">
                  <strong>{{ item.name }}</strong>
                  <span v-if="item.modifiers?.length" class="mods">
                    + {{ item.modifiers.map((m) => m.name).join(', ') }}
                  </span>
                </div>
              </li>
            </ul>

            <p v-if="order.notes" class="note">
              <AlertTriangle :size="15" :stroke-width="2.25" />
              {{ order.notes }}
            </p>

            <div class="ticket-foot">
              <span class="status-label">{{ statusLabel(order.status) }}</span>
              <div class="bumps">
                <button
                  v-if="order.status === 'pending'"
                  class="bump primary"
                  type="button"
                  @click="setStatus(order, 'preparing')"
                >
                  <Play :size="17" :stroke-width="2.4" />
                  Start cooking
                </button>
                <button
                  v-if="order.status === 'preparing'"
                  class="bump primary"
                  type="button"
                  @click="setStatus(order, 'ready')"
                >
                  <Check :size="17" :stroke-width="2.6" />
                  Mark ready
                </button>
                <button
                  v-if="order.status === 'ready'"
                  class="bump success"
                  type="button"
                  @click="setStatus(order, 'served')"
                >
                  <Check :size="17" :stroke-width="2.6" />
                  Bump served
                </button>
                <button
                  v-if="order.status !== 'served' && order.status !== 'cancelled'"
                  class="bump ghost"
                  type="button"
                  @click="setStatus(order, 'cancelled')"
                >
                  Cancel
                </button>
              </div>
            </div>
          </article>

          <div v-if="!byStatus(col.key).length" class="empty">
            <ClipboardList :size="36" :stroke-width="1.5" />
            <p>Kitchen is clear</p>
            <span>No {{ col.label.toLowerCase() }} tickets</span>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref, watch } from 'vue'
import {
  AlertTriangle,
  Check,
  ClipboardList,
  Clock,
  Play,
  UtensilsCrossed,
  Volume2,
  VolumeX,
} from '@lucide/vue'
import { api } from '../api'
import { useAuth } from '../composables/useAuth'
import { useKdsSound } from '../composables/useKdsSound'
import { useSocket } from '../composables/useSocket'

const emit = defineEmits(['open-count'])

const { fetchMe } = useAuth()
const { soundEnabled, setEnabled, playChime, unlock } = useKdsSound()
const { on, joinStaff } = useSocket()

const orders = ref([])
const stations = ref([])
const stationId = ref('')
const error = ref('')
const flashing = ref(false)
const justArrived = ref(new Set())
const now = ref(Date.now())
let tickTimer = null

const columns = [
  { key: 'pending', label: 'New' },
  { key: 'preparing', label: 'Preparing' },
  { key: 'ready', label: 'Ready' },
]

function byStatus(status) {
  return orders.value.filter((o) => o.status === status)
}

function shortId(id) {
  const s = String(id || '')
  return s.length > 4 ? s.slice(-4) : s
}

function statusLabel(status) {
  return (
    {
      pending: 'Waiting',
      preparing: 'In progress',
      ready: 'Ready to serve',
    }[status] || status
  )
}

async function load() {
  error.value = ''
  try {
    const q = stationId.value ? `?station_id=${stationId.value}` : ''
    const data = await api.get(`/api/orders/kitchen${q}`)
    orders.value = data.orders || []
    emit('open-count', orders.value.length)
  } catch (e) {
    error.value = e.message
  }
}

async function loadStations() {
  try {
    const data = await api.get('/api/stations')
    stations.value = data.stations || []
  } catch {
    stations.value = []
  }
}

async function setStatus(order, status) {
  unlock()
  try {
    await api.patch(`/api/orders/${order.id}/status`, { status, version: order.version })
    await load()
  } catch (e) {
    error.value = e.message
    await load()
  }
}

function elapsed(iso) {
  if (!iso) return ''
  const sec = Math.max(0, Math.floor((now.value - new Date(iso).getTime()) / 1000))
  const m = Math.floor(sec / 60)
  const s = sec % 60
  return `${m}:${String(s).padStart(2, '0')}`
}

function ageBand(order) {
  const min = (now.value - new Date(order.created_at).getTime()) / 60000
  if (min > 15) return 'hot'
  if (min > 8) return 'warm'
  return 'fresh'
}

function onNewOrder(payload) {
  flashing.value = true
  playChime()
  if (payload?.id) {
    const next = new Set(justArrived.value)
    next.add(payload.id)
    justArrived.value = next
    setTimeout(() => {
      const n = new Set(justArrived.value)
      n.delete(payload.id)
      justArrived.value = n
    }, 2500)
  }
  setTimeout(() => (flashing.value = false), 900)
  load()
}

function toggleSound() {
  unlock()
  setEnabled(!soundEnabled.value)
}

watch(stationId, () => load())

onMounted(async () => {
  await fetchMe()
  joinStaff()
  await loadStations()
  await load()
  tickTimer = setInterval(() => {
    now.value = Date.now()
  }, 1000)
  on('new_order', onNewOrder)
  on('status_update', () => load())
  on('connect', () => joinStaff())
})

onUnmounted(() => {
  if (tickTimer) clearInterval(tickTimer)
})
</script>

<style scoped>
.kds {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding: 0.85rem 1rem 1rem;
  background: var(--bg);
  color: var(--ink);
  font-family: var(--font);
}

.kds.flash {
  animation: flashPulse 0.45s ease 2;
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.65rem 0.85rem;
  padding: 0.65rem 0.75rem;
  margin-bottom: 0.75rem;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow);
  flex-shrink: 0;
}

.stats {
  display: flex;
  gap: 0.4rem;
}

.stat {
  min-width: 64px;
  padding: 0.4rem 0.6rem;
  border-radius: var(--radius);
  border: 1px solid var(--border);
  background: var(--surface-2);
  text-align: center;
}

.stat-val {
  display: block;
  font-size: 1.25rem;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
  line-height: 1.1;
}

.stat-lbl {
  font-size: 0.62rem;
  font-weight: 750;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--muted);
}

.stat.pending .stat-val { color: var(--st-pending); }
.stat.preparing .stat-val { color: var(--st-preparing); }
.stat.ready .stat-val { color: var(--st-ready); }

.filters {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  flex: 1;
  justify-content: center;
}

.chip {
  border: 1px solid var(--border-strong);
  background: var(--surface);
  color: var(--muted);
  border-radius: 999px;
  min-height: 34px;
  padding: 0.25rem 0.75rem;
  font: inherit;
  font-weight: 650;
  font-size: 0.78rem;
  cursor: pointer;
}

.chip:hover { color: var(--ink); }
.chip.active {
  background: var(--ink);
  color: #fff;
  border-color: var(--ink);
}

.sound {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  border: 1px solid var(--border-strong);
  background: var(--surface);
  color: var(--muted);
  border-radius: var(--radius);
  min-height: 36px;
  padding: 0.3rem 0.75rem;
  font: inherit;
  font-weight: 650;
  font-size: 0.78rem;
  cursor: pointer;
}

.sound.on {
  color: var(--ok);
  border-color: var(--ok-border);
  background: var(--ok-bg);
}

.error {
  color: var(--danger);
  margin: 0 0 0.55rem;
  font-weight: 650;
  font-size: 0.85rem;
}

.board {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.75rem;
  flex: 1;
  min-height: 0;
}

.lane {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
  box-shadow: var(--shadow);
}

.lane-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  padding: 0.75rem 0.9rem;
  border-bottom: 1px solid var(--border);
  background: var(--surface-2);
}

.lane-title {
  display: flex;
  align-items: center;
  gap: 0.45rem;
}

.lane-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  flex-shrink: 0;
}

.lane[data-lane='pending'] .lane-dot { background: var(--st-pending); }
.lane[data-lane='preparing'] .lane-dot { background: var(--st-preparing); }
.lane[data-lane='ready'] .lane-dot { background: var(--st-ready); }

.lane-head h2 {
  margin: 0;
  font-size: 0.78rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--muted);
  font-weight: 750;
}

.lane-count {
  font-variant-numeric: tabular-nums;
  font-weight: 800;
  min-width: 26px;
  height: 26px;
  padding: 0 0.4rem;
  border-radius: 999px;
  display: grid;
  place-items: center;
  font-size: 0.8rem;
  background: var(--bg-subtle);
  color: var(--ink);
}

.lane-body {
  padding: 0.65rem;
  overflow: auto;
  flex: 1;
  min-height: 0;
}

.ticket {
  background: var(--surface);
  border: 1px solid var(--border-strong);
  border-left: 4px solid var(--st-pending);
  border-radius: var(--radius);
  padding: 0.9rem;
  margin-bottom: 0.6rem;
  animation: ticketIn 0.28s var(--ease) both;
  box-shadow: var(--shadow);
}

.ticket[data-status='preparing'] { border-left-color: var(--st-preparing); }
.ticket[data-status='ready'] { border-left-color: var(--st-ready); }
.ticket[data-age='warm'] { border-left-color: var(--st-delayed); }
.ticket[data-age='hot'] {
  border-left-color: var(--st-urgent);
  background: #fff8f7;
}

.ticket.flash-new {
  outline: 2px solid var(--accent);
  outline-offset: 1px;
}

.ticket-head {
  display: flex;
  justify-content: space-between;
  gap: 0.55rem;
  margin-bottom: 0.75rem;
}

.order-id {
  display: block;
  font-size: 1.55rem;
  font-weight: 800;
  letter-spacing: -0.04em;
  line-height: 1;
}

.meta {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  margin-top: 0.35rem;
  font-size: 0.78rem;
  font-weight: 700;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.sep { opacity: 0.5; }

.timer {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  height: fit-content;
  font-variant-numeric: tabular-nums;
  font-weight: 800;
  font-size: 1.1rem;
  color: var(--ok);
  padding: 0.3rem 0.5rem;
  border-radius: var(--radius);
  background: var(--ok-bg);
  border: 1px solid var(--ok-border);
}

.timer[data-age='warm'] {
  color: var(--warn);
  background: var(--warn-bg);
  border-color: var(--warn-border);
}
.timer[data-age='hot'] {
  color: var(--danger);
  background: var(--danger-bg);
  border-color: var(--danger-border);
}

.items {
  list-style: none;
  margin: 0;
  padding: 0;
}

.items li {
  display: grid;
  grid-template-columns: 40px 1fr;
  gap: 0.5rem;
  padding: 0.5rem 0;
  border-top: 1px solid var(--border);
}

.qty {
  font-weight: 800;
  font-size: 1.05rem;
  color: var(--ink);
  background: var(--bg-subtle);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  display: grid;
  place-items: center;
  min-height: 40px;
  font-variant-numeric: tabular-nums;
}

.item-body strong {
  display: block;
  font-size: 1.05rem;
  font-weight: 700;
  line-height: 1.25;
}

.mods {
  display: block;
  margin-top: 0.15rem;
  font-size: 0.82rem;
  color: var(--muted);
}

.note {
  margin: 0.55rem 0 0;
  padding: 0.55rem 0.65rem;
  border-radius: var(--radius);
  background: var(--warn-bg);
  border: 1px solid var(--warn-border);
  color: var(--warn);
  font-weight: 650;
  font-size: 0.88rem;
  display: flex;
  gap: 0.4rem;
  align-items: flex-start;
}

.ticket-foot {
  margin-top: 0.8rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.status-label {
  font-size: 0.68rem;
  font-weight: 750;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--muted);
}

.bumps {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 0.4rem;
}

.bump {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
  border: 0;
  border-radius: var(--radius);
  min-height: 50px;
  font: inherit;
  font-weight: 750;
  font-size: 0.92rem;
  cursor: pointer;
}

.bump.primary {
  background: var(--st-pending);
  color: #fff;
}
.ticket[data-status='preparing'] .bump.primary {
  background: var(--st-preparing);
  color: #1f1a17;
}
.bump.success {
  background: var(--st-ready);
  color: #fff;
  grid-column: 1 / -1;
}
.bump.ghost {
  background: var(--surface);
  color: var(--muted);
  border: 1px solid var(--border-strong);
  min-width: 76px;
  font-size: 0.8rem;
}
.bump.ghost:hover {
  color: var(--danger);
  border-color: var(--danger-border);
  background: var(--danger-bg);
}
.bump:active { opacity: 0.92; }

.empty {
  text-align: center;
  padding: 2.75rem 0.75rem;
  color: var(--muted);
  display: grid;
  place-items: center;
  gap: 0.3rem;
}
.empty p {
  margin: 0.4rem 0 0;
  font-weight: 750;
  color: var(--ink);
}
.empty span { font-size: 0.8rem; }

@keyframes ticketIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: none; }
}

@keyframes flashPulse {
  0%, 100% { filter: none; }
  50% { filter: brightness(0.98); }
}

@media (max-width: 1100px) {
  .board { grid-template-columns: 1fr 1fr; }
  .lane[data-lane='ready'] { grid-column: 1 / -1; }
}

@media (max-width: 900px) {
  .toolbar { flex-direction: column; align-items: stretch; }
  .filters { justify-content: flex-start; }
  .sound { align-self: flex-start; }
}

@media (max-width: 720px) {
  .board { grid-template-columns: 1fr; }
  .lane[data-lane='ready'] { grid-column: auto; }
  .lane { min-height: 240px; }
  .kds { padding: 0.65rem; }
}
</style>
