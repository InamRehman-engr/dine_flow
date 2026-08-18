<template>
  <div class="menu-page">
    <header class="top">
      <div>
        <p class="eyebrow">{{ restaurantName || 'Menu' }}</p>
        <h1>Table {{ tableNumber || '—' }}</h1>
      </div>
      <div class="meta">
        <span class="status-dot" :class="{ on: connected }" />
        {{ connected ? 'Live' : 'Offline' }}
      </div>
    </header>

    <p v-if="error" class="notice bad">{{ error }}</p>
    <p v-if="notify" class="notice good" role="status">{{ notify }}</p>

    <p v-if="!guestToken && !loading" class="notice bad">
      Invalid QR link. Scan the table QR again (secure link uses <code>?t=…</code>).
    </p>

    <template v-else-if="sessionReady">
      <div class="sticky-bar">
        <button class="btn btn-ghost btn-sm" type="button" :disabled="calling || callOpen" @click="callWaiter">
          {{ calling ? 'Calling…' : callOpen ? 'Waiter notified' : 'Call waiter' }}
        </button>
        <button class="btn btn-sm" type="button" :disabled="!cartCount || submitting || !items.length" @click="submitOrder">
          {{ submitting ? 'Sending…' : `Place order · ${cartCount}` }}
        </button>
      </div>

      <section class="orders">
        <div class="orders-head">
          <h2>Your orders</h2>
          <span class="muted">{{ orders.length ? `${orders.length} open` : 'None yet' }}</span>
        </div>
        <p v-if="!orders.length" class="muted empty-orders">No open tickets for this table.</p>
        <div v-else class="order-stack">
          <article v-for="order in orders" :key="order.id" class="order">
            <div class="order-top">
              <span class="badge" :class="'badge-' + order.status">{{ order.status }}</span>
              <span class="muted">{{ formatTime(order.created_at) }}</span>
            </div>
            <ul>
              <li v-for="line in order.items" :key="line.id">{{ line.quantity }}× {{ line.name }}</li>
            </ul>
          </article>
        </div>
      </section>

      <p v-if="loading" class="muted pad">Loading menu…</p>

      <div v-else-if="!items.length" class="empty">
        <h2>Menu unavailable</h2>
        <p class="muted">No dishes are published yet. Please ask your server.</p>
      </div>

      <template v-else>
        <nav v-if="grouped.length > 1" class="cats" aria-label="Categories">
          <button
            v-for="group in grouped"
            :key="group.key"
            type="button"
            class="cat"
            @click="scrollTo(group.key)"
          >
            {{ group.name }}
          </button>
        </nav>

        <section
          v-for="group in grouped"
          :id="'cat-' + group.key"
          :key="group.key"
          class="section"
        >
          <h2>{{ group.name }}</h2>
          <div class="cards">
            <article
              v-for="item in group.items"
              :key="item.id"
              class="card"
              :class="{ selected: !!cart[item.id] }"
            >
              <div class="media">
                <img v-if="item.image_url" :src="item.image_url" :alt="item.name" loading="lazy" />
                <span v-else class="fallback">{{ initials(item.name) }}</span>
                <span v-if="cart[item.id]" class="qty-badge">{{ cart[item.id] }}</span>
              </div>
              <div class="body">
                <div class="title-line">
                  <h3>{{ item.name }}</h3>
                  <span class="price">{{ money(item.price) }}</span>
                </div>
                <p class="desc">{{ item.description || 'Prepared fresh to order.' }}</p>
                <div class="qty">
                  <button type="button" @click="dec(item)" :disabled="!(cart[item.id])">−</button>
                  <span>{{ cart[item.id] || 0 }}</span>
                  <button type="button" @click="inc(item)">+</button>
                </div>
              </div>
            </article>
          </div>
        </section>
      </template>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api'
import { useSocket } from '../composables/useSocket'

const route = useRoute()
/** Opaque QR token only — never trust a client-editable table number for actions. */
const guestToken = computed(() => String(route.query.t || route.query.token || '').trim())

const tenantId = ref('')
const tableNumber = ref('')
const restaurantName = ref('')
const sessionReady = ref(false)
const items = ref([])
const categories = ref([])
const orders = ref([])
const cart = reactive({})
const error = ref('')
const notify = ref('')
const loading = ref(false)
const submitting = ref(false)
const calling = ref(false)
const callOpen = ref(false)
let notifyTimer = null

const { connected, on } = useSocket(tenantId)

const cartCount = computed(() => Object.values(cart).reduce((s, n) => s + (n || 0), 0))

const grouped = computed(() => {
  const byId = Object.fromEntries(categories.value.map((c) => [c.id, c.name]))
  const map = new Map()
  for (const item of items.value) {
    const key = item.category_id || 'other'
    const name = byId[item.category_id] || 'Menu'
    if (!map.has(key)) map.set(key, { key, name, items: [] })
    map.get(key).items.push(item)
  }
  return [...map.values()]
})

function money(v) {
  const n = Number(v)
  return Number.isNaN(n) ? '$0.00' : `$${n.toFixed(2)}`
}
function initials(name) {
  return (name || '?').split(/\s+/).slice(0, 2).map((w) => w[0]?.toUpperCase() || '').join('')
}
function showNotify(message) {
  notify.value = message
  if (notifyTimer) clearTimeout(notifyTimer)
  notifyTimer = setTimeout(() => { notify.value = '' }, 7000)
}
function scrollTo(key) {
  document.getElementById(`cat-${key}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}
function inc(item) { cart[item.id] = (cart[item.id] || 0) + 1 }
function dec(item) {
  const n = (cart[item.id] || 0) - 1
  if (n <= 0) delete cart[item.id]
  else cart[item.id] = n
}

async function resolveSession() {
  const data = await api.get(`/api/public/session?token=${encodeURIComponent(guestToken.value)}`)
  tenantId.value = data.tenant_id
  tableNumber.value = String(data.table_number)
  restaurantName.value = data.restaurant?.name || ''
  sessionReady.value = true
}

async function loadMenu() {
  const data = await api.get(`/api/menu/${tenantId.value}`)
  if (data.restaurant?.name) restaurantName.value = data.restaurant.name
  items.value = data.items || []
  categories.value = data.categories || []
}

async function loadOrders() {
  const data = await api.get(
    `/api/public/orders?token=${encodeURIComponent(guestToken.value)}&status=open`
  )
  orders.value = data.orders || []
}

async function submitOrder() {
  if (!cartCount.value) return
  submitting.value = true
  error.value = ''
  try {
    await api.post('/api/orders/create', {
      token: guestToken.value,
      items: Object.entries(cart).map(([menu_item_id, quantity]) => ({ menu_item_id, quantity })),
    })
    Object.keys(cart).forEach((k) => delete cart[k])
    showNotify('Order sent to the kitchen.')
    await loadOrders()
  } catch (e) {
    error.value = e.message
  } finally {
    submitting.value = false
  }
}

async function callWaiter() {
  calling.value = true
  error.value = ''
  try {
    await api.post('/api/orders/waiter-call', { token: guestToken.value })
    callOpen.value = true
    showNotify('Waiter notified. You’ll be updated when staff acknowledges.')
  } catch (e) {
    error.value = e.message
  } finally {
    calling.value = false
  }
}

function formatTime(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}
function sameTable(payload) {
  return Number(payload?.table_number) === Number(tableNumber.value)
}

const offs = [
  on('status_update', (p) => { if (sameTable(p)) loadOrders() }),
  on('new_order', (p) => { if (sameTable(p)) loadOrders() }),
  on('waiter_acked', (p) => {
    if (!sameTable(p)) return
    callOpen.value = false
    showNotify('A waiter is on the way to your table.')
  }),
  on('waiter_call', (p) => { if (sameTable(p)) callOpen.value = true }),
]

async function bootstrap() {
  sessionReady.value = false
  tenantId.value = ''
  tableNumber.value = ''
  if (!guestToken.value) return
  loading.value = true
  error.value = ''
  try {
    await resolveSession()
    await loadMenu()
    await loadOrders()
  } catch (e) {
    sessionReady.value = false
    error.value = e.message
  } finally {
    loading.value = false
  }
}

watch(guestToken, bootstrap)
onMounted(bootstrap)
onUnmounted(() => {
  offs.forEach((off) => off && off())
  if (notifyTimer) clearTimeout(notifyTimer)
})
</script>

<style scoped>
.menu-page {
  max-width: 880px;
  margin: 0 auto;
  padding: 1.25rem 1rem 5.5rem;
}
.top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  margin-bottom: 1rem;
}
.eyebrow {
  margin: 0;
  font-size: 0.72rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--muted);
  font-weight: 600;
}
h1 {
  margin: 0.3rem 0 0;
  font-size: 1.55rem;
}
.meta {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.75rem;
  color: var(--muted);
  padding-top: 0.35rem;
}
.notice {
  margin: 0 0 0.85rem;
  padding: 0.7rem 0.85rem;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  font-size: 0.875rem;
}
.notice.bad { border-color: #e2bdbd; color: var(--danger); background: #fcf6f6; }
.notice.good { border-color: #c5d8cc; color: var(--ok); background: #f5faf7; }
.sticky-bar {
  position: sticky;
  top: 0;
  z-index: 6;
  display: flex;
  justify-content: space-between;
  gap: 0.65rem;
  padding: 0.7rem 0;
  margin-bottom: 1rem;
  background: rgba(255, 255, 255, 0.94);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid var(--line);
}
.orders {
  margin-bottom: 1.35rem;
  padding: 0.9rem 1rem;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--surface);
}
.orders-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 0.75rem;
  margin-bottom: 0.55rem;
}
.orders h2,
.section h2 {
  margin: 0;
  font-size: 0.72rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--muted);
  font-family: var(--font-body);
  font-weight: 600;
}
.empty-orders { margin: 0; }
.order-stack { display: flex; flex-direction: column; gap: 0.55rem; }
.order {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 0.7rem 0.8rem;
}
.order-top {
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
}
.order ul {
  margin: 0.35rem 0 0;
  padding-left: 1.1rem;
  color: var(--ink-2);
  font-size: 0.88rem;
}
.pad { padding: 2rem 0; text-align: center; }
.empty {
  padding: 2rem 0;
  text-align: center;
}
.empty h2 { margin: 0 0 0.4rem; font-size: 1.1rem; }
.cats {
  display: flex;
  gap: 0.35rem;
  overflow-x: auto;
  padding: 0.15rem 0 1rem;
}
.cat {
  border: 1px solid var(--line-strong);
  background: #fff;
  border-radius: 999px;
  padding: 0.35rem 0.75rem;
  font: inherit;
  font-size: 0.8rem;
  font-weight: 500;
  color: var(--ink-2);
  white-space: nowrap;
  cursor: pointer;
}
.cat:hover { border-color: var(--ink); }
.section {
  margin-bottom: 1.75rem;
}
.section h2 {
  margin-bottom: 0.85rem;
}
.cards {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.85rem;
}
.card {
  display: flex;
  flex-direction: column;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 12px;
  overflow: hidden;
  transition: border-color 0.15s ease, transform 0.15s ease;
}
.card:hover {
  border-color: var(--line-strong);
  transform: translateY(-2px);
}
.card.selected {
  border-color: var(--ink);
}
.media {
  position: relative;
  aspect-ratio: 4 / 3;
  background: linear-gradient(145deg, #ececec, #f7f7f7);
  overflow: hidden;
}
.media img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.fallback {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  font-family: var(--font-display);
  font-size: 1.4rem;
  font-weight: 600;
  color: var(--muted);
}
.qty-badge {
  position: absolute;
  top: 0.55rem;
  right: 0.55rem;
  min-width: 1.45rem;
  height: 1.45rem;
  padding: 0 0.35rem;
  border-radius: 999px;
  background: var(--ink);
  color: #fff;
  font-size: 0.75rem;
  font-weight: 700;
  display: grid;
  place-items: center;
}
.body {
  padding: 0.8rem 0.85rem 0.9rem;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  flex: 1;
}
.title-line {
  display: flex;
  justify-content: space-between;
  gap: 0.55rem;
  align-items: flex-start;
}
.body h3 {
  margin: 0;
  font-size: 0.98rem;
  font-family: var(--font-body);
  font-weight: 600;
  letter-spacing: -0.01em;
  line-height: 1.25;
}
.price {
  color: var(--accent);
  font-weight: 600;
  font-size: 0.9rem;
  white-space: nowrap;
}
.desc {
  margin: 0;
  color: var(--muted);
  font-size: 0.8rem;
  line-height: 1.35;
  flex: 1;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.qty {
  display: inline-flex;
  align-items: center;
  align-self: flex-end;
  gap: 0.35rem;
  margin-top: 0.25rem;
  border: 1px solid var(--line-strong);
  border-radius: var(--radius);
  padding: 0.15rem;
  background: #fff;
}
.qty button {
  width: 30px;
  height: 30px;
  border: 0;
  background: transparent;
  font-size: 1.05rem;
  cursor: pointer;
  color: var(--ink);
}
.qty button:disabled { opacity: 0.3; }
.qty span {
  min-width: 1.15rem;
  text-align: center;
  font-size: 0.88rem;
  font-weight: 600;
}
@media (max-width: 560px) {
  .cards {
    grid-template-columns: 1fr;
  }
}
</style>
