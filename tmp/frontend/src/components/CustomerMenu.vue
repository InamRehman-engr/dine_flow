<template>
  <div class="guest" :class="{ 'detail-open': !!activeItem }">
    <p v-if="error" class="notice bad">{{ error }}</p>
    <p v-if="notify" class="notice good">{{ notify }}</p>
    <p v-if="!guestToken && !loading" class="notice bad">Invalid QR link. Scan the table QR again.</p>

    <template v-else-if="sessionReady">
      <!-- LIST / ORDERS / FAVS -->
      <div v-show="!activeItem" class="shell">
        <header class="top">
          <div>
            <h1>{{ viewTitle }}</h1>
            <p class="table-line">Table {{ tableNumber || '—' }} · {{ restaurantName || 'DineFlow' }}</p>
          </div>
          <button type="button" class="icon-btn" aria-label="Cart" @click="checkoutOpen = true">
            <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M6 7h15l-1.5 9h-12z" />
              <path d="M6 7l-1-3H2" />
              <circle cx="9" cy="20" r="1.2" fill="currentColor" stroke="none" />
              <circle cx="17" cy="20" r="1.2" fill="currentColor" stroke="none" />
            </svg>
            <span v-if="cartCount" class="cart-dot">{{ cartCount }}</span>
          </button>
        </header>

        <template v-if="view === 'menu' || view === 'favorites'">
          <div class="search-wrap">
            <svg class="search-ico" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="#9CA3AF" stroke-width="2">
              <circle cx="11" cy="11" r="7" />
              <path d="M20 20l-3.5-3.5" />
            </svg>
            <input v-model="search" class="search" type="search" placeholder="Search" />
          </div>

          <div class="mint-panel">
            <nav v-if="view === 'menu'" class="cats">
              <button
                type="button"
                class="cat"
                :class="{ active: activeCat === 'all' }"
                @click="activeCat = 'all'"
              >All</button>
              <button
                v-for="c in categories"
                :key="c.id"
                type="button"
                class="cat"
                :class="{ active: activeCat === c.id }"
                @click="activeCat = c.id"
              >{{ c.name }}</button>
            </nav>

            <p v-if="loading" class="empty">Loading menu…</p>
            <p v-else-if="!displayItems.length" class="empty">
              {{ view === 'favorites' ? 'No favorites yet — tap the heart on a dish.' : 'No matches.' }}
            </p>
            <div v-else class="grid">
              <article
                v-for="(item, idx) in displayItems"
                :key="item.id"
                class="card"
                :style="{ animationDelay: `${Math.min(idx, 10) * 40}ms` }"
                @click="openItem(item)"
              >
                <div class="thumb">
                  <img :src="foodImage(item)" :alt="item.name" loading="lazy" />
                  <span v-if="cartQty(item.id)" class="qty-pill">{{ cartQty(item.id) }}</span>
                </div>
                <div class="card-body">
                  <h3>{{ item.name }}</h3>
                  <div class="meta">
                    <span>
                      <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>
                      {{ itemMins(item) }} min
                    </span>
                    <span class="rating">
                      <svg viewBox="0 0 24 24" width="12" height="12" fill="#F5A623" stroke="none"><path d="M12 2l2.9 6.4L22 9.3l-5 4.6 1.4 7.1L12 17.8 5.6 21l1.4-7.1-5-4.6 7.1-.9z"/></svg>
                      {{ itemRating(item) }}
                    </span>
                  </div>
                  <p class="price">{{ formatMoney(item.price) }}</p>
                </div>
              </article>
            </div>
          </div>
        </template>

        <section v-else-if="view === 'orders'" class="orders-panel">
          <p v-if="!orders.length" class="empty">Nothing yet — pick something delicious.</p>
          <article v-for="order in orders" :key="order.id" class="order-card">
            <div class="order-top">
              <span class="status" :data-status="order.status">{{ order.status }}</span>
              <span class="muted">{{ formatTime(order.created_at) }}</span>
            </div>
            <ul>
              <li v-for="line in order.items" :key="line.id">
                <span>
                  <b>{{ line.quantity }}×</b> {{ line.name }}
                  <em v-if="line.modifiers?.length">{{ line.modifiers.map((m) => m.name).join(', ') }}</em>
                </span>
                <strong>{{ formatMoney(line.line_total) }}</strong>
              </li>
            </ul>
          </article>
          <button class="btn-teal full" type="button" @click="view = 'menu'">Add more</button>
        </section>

        <section v-else-if="view === 'profile'" class="profile-panel">
          <div class="profile-card">
            <p class="muted">You're dining at</p>
            <h2>{{ restaurantName || 'Restaurant' }}</h2>
            <p class="table-big">Table {{ tableNumber || '—' }}</p>
            <p class="live-line"><span class="status-dot" :class="{ on: connected }" /> {{ connected ? 'Live' : 'Offline' }}</p>
          </div>
          <button class="btn-teal full" type="button" :disabled="calling || callOpen" @click="openWaiter">
            {{ callOpen ? 'Waiter notified' : 'Call waiter' }}
          </button>
        </section>

        <nav class="bottom-nav">
          <button type="button" :class="{ active: view === 'menu' }" @click="view = 'menu'">
            <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 6h16M4 12h16M4 18h10"/></svg>
            <span>Menu</span>
            <i v-if="view === 'menu'" class="dot" />
          </button>
          <button type="button" :class="{ active: view === 'favorites' }" @click="view = 'favorites'">
            <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 21s-7-4.5-7-10a4 4 0 017-2.5A4 4 0 0119 11c0 5.5-7 10-7 10z"/></svg>
            <span>Favorites</span>
            <i v-if="view === 'favorites'" class="dot" />
          </button>
          <button type="button" :class="{ active: view === 'orders' }" @click="view = 'orders'">
            <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/></svg>
            <span>Orders</span>
            <i v-if="view === 'orders'" class="dot" />
            <em v-if="orders.length" class="nav-badge">{{ orders.length }}</em>
          </button>
          <button type="button" :class="{ active: view === 'profile' }" @click="view = 'profile'">
            <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="8" r="4"/><path d="M4 20c1.5-3.5 4.5-5 8-5s6.5 1.5 8 5"/></svg>
            <span>Profile</span>
            <i v-if="view === 'profile'" class="dot" />
          </button>
        </nav>
      </div>

      <!-- PRODUCT DETAIL -->
      <Transition name="detail">
        <div v-if="activeItem" class="detail">
          <div class="detail-hero">
            <img :src="foodImage(activeItem)" :alt="activeItem.name" />
            <button type="button" class="float-btn back" aria-label="Back" @click="activeItem = null">
              <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M15 18l-6-6 6-6"/></svg>
            </button>
            <button type="button" class="float-btn bag" aria-label="Cart" @click="checkoutOpen = true">
              <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M6 7h15l-1.5 9h-12z" />
                <path d="M6 7l-1-3H2" />
                <circle cx="9" cy="20" r="1.2" fill="currentColor" stroke="none" />
                <circle cx="17" cy="20" r="1.2" fill="currentColor" stroke="none" />
              </svg>
              <span v-if="cartCount" class="cart-dot sm">{{ cartCount }}</span>
            </button>
          </div>

          <div class="detail-sheet">
            <div class="detail-head">
              <div>
                <h2>{{ activeItem.name }}</h2>
                <p class="price-lg">{{ formatMoney(activeItem.price) }}</p>
              </div>
              <div class="detail-meta">
                <span>
                  <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>
                  {{ itemMins(activeItem) }} min
                </span>
                <span class="rating">
                  <svg viewBox="0 0 24 24" width="14" height="14" fill="#F5A623" stroke="none"><path d="M12 2l2.9 6.4L22 9.3l-5 4.6 1.4 7.1L12 17.8 5.6 21l1.4-7.1-5-4.6 7.1-.9z"/></svg>
                  {{ itemRating(activeItem) }}
                </span>
              </div>
            </div>

            <p class="desc">
              {{ activeItem.description || 'A beautifully prepared dish made with fresh ingredients. Soft textures, balanced flavors, and plated to order.' }}
            </p>

            <div v-for="g in activeItem.modifier_groups || []" :key="g.id" class="mod-group">
              <p class="mod-label">{{ g.name }} {{ g.required ? '(required)' : '' }}</p>
              <label v-for="m in g.modifiers" :key="m.id" class="mod-opt">
                <input type="checkbox" :checked="isModSelected(g.id, m.id)" @change="toggleMod(g, m)" />
                <span>{{ m.name }}</span>
                <span v-if="m.price_delta" class="muted">+{{ formatMoney(m.price_delta) }}</span>
              </label>
            </div>

            <div class="qty-row">
              <button type="button" class="qty-btn" @click="sheetQty = Math.max(1, sheetQty - 1)">−</button>
              <span>{{ sheetQty }}</span>
              <button type="button" class="qty-btn" @click="sheetQty += 1">+</button>
            </div>

            <div v-if="recentItems.length" class="recent">
              <h3>Recently Viewed</h3>
              <div class="recent-row">
                <button
                  v-for="r in recentItems"
                  :key="r.id"
                  type="button"
                  class="recent-thumb"
                  @click="openItem(r)"
                >
                  <img :src="foodImage(r)" :alt="r.name" />
                </button>
              </div>
            </div>

            <div class="detail-actions">
              <button
                type="button"
                class="fav-btn"
                :class="{ on: isFavorite(activeItem.id) }"
                aria-label="Favorite"
                @click="toggleFavorite(activeItem.id)"
              >
                <svg viewBox="0 0 24 24" width="22" height="22" :fill="isFavorite(activeItem.id) ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="2">
                  <path d="M12 21s-7-4.5-7-10a4 4 0 017-2.5A4 4 0 0119 11c0 5.5-7 10-7 10z"/>
                </svg>
              </button>
              <button type="button" class="btn-teal add-cart" @click="addToCart">Add to cart</button>
            </div>
          </div>

          <nav class="bottom-nav inset">
            <button type="button" :class="{ active: view === 'menu' }" @click="closeTo('menu')">
              <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 6h16M4 12h16M4 18h10"/></svg>
              <span>Menu</span>
              <i class="dot" />
            </button>
            <button type="button" @click="closeTo('favorites')">
              <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 21s-7-4.5-7-10a4 4 0 017-2.5A4 4 0 0119 11c0 5.5-7 10-7 10z"/></svg>
              <span>Favorites</span>
            </button>
            <button type="button" @click="closeTo('orders')">
              <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/></svg>
              <span>Orders</span>
            </button>
            <button type="button" @click="closeTo('profile')">
              <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="8" r="4"/><path d="M4 20c1.5-3.5 4.5-5 8-5s6.5 1.5 8 5"/></svg>
              <span>Profile</span>
            </button>
          </nav>
        </div>
      </Transition>
    </template>

    <!-- Cart checkout -->
    <div v-if="checkoutOpen" class="sheet-scrim" @click.self="checkoutOpen = false">
      <div class="sheet">
        <div class="handle" />
        <h3>Your cart</h3>
        <p v-if="!cartLines.length" class="empty">Cart is empty</p>
        <ul v-else class="cart-list">
          <li v-for="(line, idx) in cartLines" :key="idx">
            <div>
              <strong>{{ line.quantity }}× {{ line.name }}</strong>
              <p v-if="line.modifiers.length" class="mods">{{ line.modifiers.map((m) => m.name).join(', ') }}</p>
            </div>
            <span>{{ formatMoney(line.unit_price * line.quantity) }}</span>
          </li>
        </ul>
        <label class="label">Notes</label>
        <textarea v-model="notes" class="textarea" placeholder="Allergies, preferences…" />
        <button
          class="btn-teal full"
          type="button"
          :disabled="submitting || !cartLines.length"
          @click="submitOrder"
        >
          {{ submitting ? 'Sending…' : `Place order · ${formatMoney(cartTotal)}` }}
        </button>
      </div>
    </div>

    <!-- Waiter -->
    <div v-if="waiterOpen" class="sheet-scrim" @click.self="waiterOpen = false">
      <div class="sheet">
        <div class="handle" />
        <h3>Call waiter</h3>
        <div class="reason-grid">
          <button
            v-for="r in reasons"
            :key="r.id"
            type="button"
            class="chip"
            :class="{ active: waiterReason === r.id }"
            @click="waiterReason = r.id"
          >{{ r.label }}</button>
        </div>
        <textarea v-if="waiterReason === 'other'" v-model="waiterNote" class="textarea" placeholder="Tell us more…" />
        <button class="btn-teal full" type="button" :disabled="calling" @click="callWaiter">
          {{ calling ? 'Calling…' : 'Send request' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api'
import { foodImage } from '../composables/useFoodImage'
import { useMoney } from '../composables/useMoney'
import { useSocket } from '../composables/useSocket'

const route = useRoute()
const { formatMoney, loadConfig } = useMoney()
const { connected, on, joinGuest } = useSocket()

const guestToken = ref((route.query.t || route.query.token || '').toString())
const tenantId = ref('')
const guestTicket = ref('')
const tableNumber = ref(null)
const restaurantName = ref('')
const sessionReady = ref(false)
const loading = ref(true)
const error = ref('')
const notify = ref('')
const items = ref([])
const categories = ref([])
const orders = ref([])
const view = ref('menu')
const activeCat = ref('all')
const search = ref('')
const cart = ref([])
const notes = ref('')
const submitting = ref(false)
const calling = ref(false)
const callOpen = ref(false)
const checkoutOpen = ref(false)
const activeItem = ref(null)
const sheetQty = ref(1)
const sheetMods = ref({})
const waiterOpen = ref(false)
const waiterReason = ref('help')
const waiterNote = ref('')
const favorites = ref(new Set())
const recentIds = ref([])

const reasons = [
  { id: 'water', label: 'Water' },
  { id: 'bill', label: 'Bill' },
  { id: 'help', label: 'Help' },
  { id: 'other', label: 'Other' },
]

const FAV_KEY = 'dineflow_favs'
const REC_KEY = 'dineflow_recent'

const viewTitle = computed(() => {
  if (view.value === 'favorites') return 'Favorites'
  if (view.value === 'orders') return 'Orders'
  if (view.value === 'profile') return 'Profile'
  return 'Menu'
})

const cartCount = computed(() => cart.value.reduce((n, l) => n + l.quantity, 0))
const cartTotal = computed(() => cart.value.reduce((n, l) => n + l.unit_price * l.quantity, 0))
const cartLines = computed(() => cart.value)
const cartQty = (id) => cart.value.filter((l) => l.menu_item_id === id).reduce((n, l) => n + l.quantity, 0)

function hash(str) {
  let h = 0
  const s = String(str || '')
  for (let i = 0; i < s.length; i += 1) h = (h * 31 + s.charCodeAt(i)) >>> 0
  return h
}

function itemMins(item) {
  return 12 + (hash(item?.id || item?.name) % 20)
}

function itemRating(item) {
  const n = 45 + (hash(item?.id || item?.name) % 6)
  return (n / 10).toFixed(1)
}

const displayItems = computed(() => {
  let list = items.value
  if (view.value === 'favorites') {
    list = list.filter((i) => favorites.value.has(i.id))
  } else if (activeCat.value !== 'all') {
    list = list.filter((i) => i.category_id === activeCat.value)
  }
  const q = search.value.trim().toLowerCase()
  if (q) list = list.filter((i) => i.name.toLowerCase().includes(q) || (i.description || '').toLowerCase().includes(q))
  return list
})

const recentItems = computed(() => {
  const map = new Map(items.value.map((i) => [i.id, i]))
  return recentIds.value.map((id) => map.get(id)).filter(Boolean).filter((i) => i.id !== activeItem.value?.id).slice(0, 8)
})

function formatTime(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function openItem(item) {
  activeItem.value = item
  sheetQty.value = 1
  sheetMods.value = {}
  const next = [item.id, ...recentIds.value.filter((id) => id !== item.id)].slice(0, 12)
  recentIds.value = next
  try {
    localStorage.setItem(REC_KEY, JSON.stringify(next))
  } catch {
    /* ignore */
  }
}

function closeTo(tab) {
  activeItem.value = null
  view.value = tab
}

function isFavorite(id) {
  return favorites.value.has(id)
}

function toggleFavorite(id) {
  const next = new Set(favorites.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  favorites.value = next
  try {
    localStorage.setItem(FAV_KEY, JSON.stringify([...next]))
  } catch {
    /* ignore */
  }
}

function isModSelected(gid, mid) {
  return (sheetMods.value[gid] || []).some((m) => m.id === mid)
}

function toggleMod(group, mod) {
  const cur = [...(sheetMods.value[group.id] || [])]
  const idx = cur.findIndex((m) => m.id === mod.id)
  if (idx >= 0) cur.splice(idx, 1)
  else {
    if (group.max_select <= 1) cur.splice(0, cur.length)
    else if (cur.length >= group.max_select) return
    cur.push(mod)
  }
  sheetMods.value = { ...sheetMods.value, [group.id]: cur }
}

function addToCart() {
  const item = activeItem.value
  if (!item) return
  for (const g of item.modifier_groups || []) {
    if (g.required && !(sheetMods.value[g.id] || []).length) {
      error.value = `Select ${g.name}`
      return
    }
  }
  const modifiers = Object.values(sheetMods.value).flat()
  let unit = Number(item.price)
  for (const m of modifiers) unit += Number(m.price_delta || 0)
  cart.value = [
    ...cart.value,
    {
      menu_item_id: item.id,
      name: item.name,
      quantity: sheetQty.value,
      unit_price: unit,
      modifiers: modifiers.map((m) => ({ id: m.id, name: m.name, price_delta: m.price_delta })),
    },
  ]
  activeItem.value = null
  error.value = ''
  notify.value = 'Added to cart'
  setTimeout(() => (notify.value = ''), 1800)
}

async function loadSession() {
  const data = await api.get(`/api/public/session?token=${encodeURIComponent(guestToken.value)}`)
  tenantId.value = data.tenant_id
  tableNumber.value = data.table_number
  restaurantName.value = data.restaurant?.name || ''
  guestTicket.value = data.guest_ticket
  guestToken.value = data.token
  sessionReady.value = true
  joinGuest(data.guest_ticket)
}

async function loadMenu() {
  const data = await api.get(`/api/menu/${tenantId.value}`)
  items.value = data.items || []
  categories.value = data.categories || []
}

async function loadOrders() {
  const data = await api.get(`/api/public/orders?token=${encodeURIComponent(guestToken.value)}&status=open`)
  orders.value = data.orders || []
}

async function submitOrder() {
  if (!cart.value.length) return
  submitting.value = true
  error.value = ''
  try {
    await api.post('/api/orders/create', {
      token: guestToken.value,
      notes: notes.value || null,
      items: cart.value.map((l) => ({
        menu_item_id: l.menu_item_id,
        quantity: l.quantity,
        modifiers: l.modifiers,
      })),
    })
    cart.value = []
    notes.value = ''
    checkoutOpen.value = false
    notify.value = 'Order sent to the kitchen'
    view.value = 'orders'
    await loadOrders()
    setTimeout(() => (notify.value = ''), 2800)
  } catch (e) {
    error.value = e.message
  } finally {
    submitting.value = false
  }
}

function openWaiter() {
  waiterOpen.value = true
  waiterReason.value = 'help'
  waiterNote.value = ''
}

async function callWaiter() {
  calling.value = true
  try {
    await api.post('/api/orders/waiter-call', {
      token: guestToken.value,
      reason: waiterReason.value,
      note: waiterReason.value === 'other' ? waiterNote.value : null,
    })
    callOpen.value = true
    waiterOpen.value = false
    notify.value = 'Waiter notified'
    setTimeout(() => (notify.value = ''), 2800)
  } catch (e) {
    error.value = e.message
  } finally {
    calling.value = false
  }
}

watch(view, () => {
  search.value = ''
  if (view.value === 'menu') activeCat.value = 'all'
})

onMounted(async () => {
  try {
    const fav = JSON.parse(localStorage.getItem(FAV_KEY) || '[]')
    favorites.value = new Set(fav)
  } catch {
    favorites.value = new Set()
  }
  try {
    recentIds.value = JSON.parse(localStorage.getItem(REC_KEY) || '[]')
  } catch {
    recentIds.value = []
  }

  await loadConfig()
  if (!guestToken.value) {
    loading.value = false
    return
  }
  try {
    await loadSession()
    await Promise.all([loadMenu(), loadOrders()])
    on('status_update', loadOrders)
    on('new_order', loadOrders)
    on('waiter_acked', () => {
      callOpen.value = false
      notify.value = 'A waiter is on the way'
    })
    on('connect', () => joinGuest(guestTicket.value))
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.guest {
  --teal: #0f766e;
  --teal-dark: #115e59;
  --mint: #ccfbf1;
  --mint-soft: #f0fdfa;
  --bg: #f3f7f6;
  --ink: #0f172a;
  --muted: #64748b;
  --star: #f59e0b;
  --radius: 18px;
  max-width: 480px;
  margin: 0 auto;
  min-height: 100vh;
  background: var(--bg);
  color: var(--ink);
  font-family: 'Plus Jakarta Sans', system-ui, sans-serif;
  position: relative;
}

.shell {
  padding: 1.15rem 1.05rem 6.5rem;
  animation: riseIn 0.4s var(--ease-out, cubic-bezier(0.22, 1, 0.36, 1));
}

.top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 0.75rem;
  margin-bottom: 1rem;
}
.top h1 {
  margin: 0;
  font-size: 2rem;
  font-weight: 700;
  letter-spacing: -0.03em;
  font-family: inherit;
  color: var(--ink);
}
.table-line {
  margin: 0.2rem 0 0;
  font-size: 0.78rem;
  color: var(--muted);
  font-weight: 500;
}

.icon-btn {
  position: relative;
  width: 46px;
  height: 46px;
  border: 0;
  border-radius: 14px;
  background: var(--teal);
  color: #fff;
  display: grid;
  place-items: center;
  cursor: pointer;
  box-shadow: 0 8px 18px rgba(26, 92, 80, 0.28);
  flex-shrink: 0;
  transition: transform 0.15s ease;
}
.icon-btn:active {
  transform: scale(0.94);
}
.cart-dot {
  position: absolute;
  top: -5px;
  right: -5px;
  min-width: 18px;
  height: 18px;
  padding: 0 4px;
  border-radius: 999px;
  background: #fff;
  color: var(--teal);
  font-size: 0.68rem;
  font-weight: 800;
  display: grid;
  place-items: center;
  border: 2px solid var(--teal);
}
.cart-dot.sm {
  top: -4px;
  right: -4px;
  min-width: 16px;
  height: 16px;
  font-size: 0.62rem;
}

.search-wrap {
  position: relative;
  margin-bottom: 1rem;
}
.search-ico {
  position: absolute;
  left: 14px;
  top: 50%;
  transform: translateY(-50%);
  pointer-events: none;
}
.search {
  width: 100%;
  min-height: 48px;
  border: 0;
  border-radius: 14px;
  background: #eceff3;
  padding: 0.7rem 1rem 0.7rem 2.55rem;
  font: inherit;
  font-size: 0.95rem;
  color: var(--ink);
}
.search::placeholder {
  color: #9ca3af;
}
.search:focus {
  outline: none;
  box-shadow: 0 0 0 3px rgba(26, 92, 80, 0.18);
}

.mint-panel {
  background: var(--mint);
  border-radius: 28px 28px 24px 24px;
  padding: 1rem 0.85rem 1.25rem;
  min-height: 50vh;
}

.cats {
  display: flex;
  gap: 0.85rem;
  overflow-x: auto;
  padding: 0.15rem 0.35rem 0.95rem;
  scrollbar-width: none;
}
.cats::-webkit-scrollbar {
  display: none;
}
.cat {
  border: 0;
  background: transparent;
  font: inherit;
  font-size: 0.95rem;
  font-weight: 500;
  color: rgba(17, 24, 39, 0.55);
  cursor: pointer;
  white-space: nowrap;
  padding: 0.15rem 0;
  transition: color 0.15s ease, transform 0.15s ease;
}
.cat.active {
  color: var(--ink);
  font-weight: 700;
  transform: scale(1.04);
}

.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.85rem;
}
@media (min-width: 520px) {
  .grid {
    gap: 1rem;
  }
}

.card {
  background: #fff;
  border-radius: 20px;
  overflow: hidden;
  cursor: pointer;
  box-shadow: 0 6px 18px rgba(17, 24, 39, 0.06);
  animation: riseIn 0.4s var(--ease-out, cubic-bezier(0.22, 1, 0.36, 1)) both;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.card:active {
  transform: scale(0.97);
}
.thumb {
  position: relative;
  aspect-ratio: 1 / 1;
  overflow: hidden;
  background: #e5e7eb;
}
.thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.45s ease;
}
.card:hover .thumb img {
  transform: scale(1.05);
}
.qty-pill {
  position: absolute;
  top: 8px;
  left: 8px;
  min-width: 24px;
  height: 24px;
  border-radius: 999px;
  background: var(--teal);
  color: #fff;
  font-size: 0.72rem;
  font-weight: 800;
  display: grid;
  place-items: center;
}
.card-body {
  padding: 0.7rem 0.75rem 0.85rem;
}
.card-body h3 {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 700;
  font-family: inherit;
  line-height: 1.25;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.meta {
  display: flex;
  gap: 0.65rem;
  margin: 0.4rem 0 0.45rem;
  font-size: 0.72rem;
  color: var(--muted);
  font-weight: 500;
}
.meta span {
  display: inline-flex;
  align-items: center;
  gap: 0.22rem;
}
.rating {
  color: var(--ink);
}
.price {
  margin: 0;
  font-weight: 700;
  font-size: 0.95rem;
}

.bottom-nav {
  position: fixed;
  left: 50%;
  transform: translateX(-50%);
  bottom: 0;
  width: min(480px, 100%);
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.15rem;
  padding: 0.55rem 0.4rem calc(0.65rem + env(safe-area-inset-bottom));
  background: #fff;
  border-top: 1px solid #eceff3;
  z-index: 25;
}
.bottom-nav.inset {
  position: sticky;
  left: auto;
  transform: none;
  width: 100%;
  margin-top: auto;
}
.bottom-nav button {
  position: relative;
  border: 0;
  background: transparent;
  color: #9ca3af;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.15rem;
  font: inherit;
  font-size: 0.68rem;
  font-weight: 600;
  cursor: pointer;
  padding: 0.25rem;
}
.bottom-nav button.active {
  color: var(--teal);
}
.bottom-nav .dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--teal);
  display: block;
}
.nav-badge {
  position: absolute;
  top: 0;
  right: 18%;
  min-width: 16px;
  height: 16px;
  border-radius: 999px;
  background: var(--teal);
  color: #fff;
  font-size: 0.62rem;
  font-style: normal;
  font-weight: 800;
  display: grid;
  place-items: center;
}

/* Detail */
.detail {
  position: fixed;
  inset: 0;
  z-index: 30;
  max-width: 480px;
  margin: 0 auto;
  background: #fff;
  display: flex;
  flex-direction: column;
  overflow: auto;
  animation: riseIn 0.35s var(--ease-out, cubic-bezier(0.22, 1, 0.36, 1));
}
.detail-hero {
  position: relative;
  height: min(42vh, 340px);
  flex-shrink: 0;
  background: #ddd;
}
.detail-hero img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.float-btn {
  position: absolute;
  top: 1rem;
  width: 44px;
  height: 44px;
  border: 0;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.92);
  color: var(--teal);
  display: grid;
  place-items: center;
  cursor: pointer;
  backdrop-filter: blur(8px);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.12);
}
.float-btn.back {
  left: 1rem;
}
.float-btn.bag {
  right: 1rem;
  background: var(--teal);
  color: #fff;
}
.detail-sheet {
  margin-top: -28px;
  background: #fff;
  border-radius: 28px 28px 0 0;
  padding: 1.35rem 1.2rem 1rem;
  position: relative;
  flex: 1;
}
.detail-head {
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
  align-items: flex-start;
}
.detail-head h2 {
  margin: 0;
  font-size: 1.45rem;
  font-weight: 700;
  font-family: inherit;
  letter-spacing: -0.02em;
}
.price-lg {
  margin: 0.35rem 0 0;
  font-size: 1.15rem;
  font-weight: 700;
}
.detail-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.35rem;
  font-size: 0.82rem;
  color: var(--muted);
  font-weight: 500;
  padding-top: 0.2rem;
}
.detail-meta span {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
}
.desc {
  margin: 1rem 0 0;
  color: #6b7280;
  font-size: 0.92rem;
  line-height: 1.55;
}
.mod-group {
  margin: 1rem 0 0;
}
.mod-label {
  margin: 0 0 0.35rem;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--muted);
}
.mod-opt {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 0.55rem;
  padding: 0.55rem 0;
  border-bottom: 1px solid #f0f0f0;
  align-items: center;
  font-size: 0.92rem;
}
.qty-row {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 1.1rem;
  margin: 1.1rem 0 0.5rem;
  font-size: 1.25rem;
  font-weight: 700;
}
.qty-btn {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  background: #f9fafb;
  font-size: 1.25rem;
  cursor: pointer;
  color: var(--teal);
}
.recent {
  margin-top: 1.15rem;
}
.recent h3 {
  margin: 0 0 0.7rem;
  font-size: 1rem;
  font-weight: 700;
  font-family: inherit;
}
.recent-row {
  display: flex;
  gap: 0.65rem;
  overflow-x: auto;
  padding-bottom: 0.35rem;
  scrollbar-width: none;
}
.recent-row::-webkit-scrollbar {
  display: none;
}
.recent-thumb {
  border: 0;
  padding: 0;
  width: 72px;
  height: 72px;
  border-radius: 16px;
  overflow: hidden;
  flex-shrink: 0;
  cursor: pointer;
  background: #eee;
}
.recent-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.detail-actions {
  display: flex;
  gap: 0.75rem;
  margin-top: 1.25rem;
  margin-bottom: 0.5rem;
}
.fav-btn {
  width: 54px;
  height: 54px;
  border-radius: 16px;
  border: 1.5px solid var(--teal);
  background: #fff;
  color: var(--teal);
  display: grid;
  place-items: center;
  cursor: pointer;
  flex-shrink: 0;
}
.fav-btn.on {
  background: rgba(26, 92, 80, 0.08);
}
.add-cart {
  flex: 1;
  min-height: 54px;
}

.btn-teal {
  border: 0;
  border-radius: 16px;
  background: var(--teal);
  color: #fff;
  font: inherit;
  font-weight: 700;
  font-size: 1rem;
  cursor: pointer;
  box-shadow: 0 10px 24px rgba(26, 92, 80, 0.28);
  transition: transform 0.15s ease, background 0.15s ease;
}
.btn-teal:active {
  transform: scale(0.98);
}
.btn-teal:disabled {
  opacity: 0.45;
  cursor: not-allowed;
  box-shadow: none;
}
.btn-teal:hover:not(:disabled) {
  background: var(--teal-dark);
}
.full {
  width: 100%;
  min-height: 52px;
}

.orders-panel,
.profile-panel {
  padding: 0.25rem 0 1rem;
}
.order-card {
  background: #fff;
  border-radius: 18px;
  padding: 1rem;
  margin-bottom: 0.75rem;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.04);
}
.order-top {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.45rem;
}
.status {
  text-transform: uppercase;
  font-size: 0.68rem;
  font-weight: 800;
  letter-spacing: 0.05em;
  padding: 0.25rem 0.5rem;
  border-radius: 999px;
  background: #f3f4f6;
}
.status[data-status='pending'] {
  background: #fff4e5;
  color: #b54708;
}
.status[data-status='preparing'] {
  background: #e8f0ff;
  color: #175cd3;
}
.status[data-status='ready'] {
  background: #e8faf0;
  color: #048a4a;
}
.order-card ul {
  list-style: none;
  margin: 0;
  padding: 0;
}
.order-card li {
  display: flex;
  justify-content: space-between;
  gap: 0.5rem;
  padding: 0.35rem 0;
}
.order-card em {
  display: block;
  font-style: normal;
  color: var(--muted);
  font-size: 0.85rem;
}
.profile-card {
  background: var(--mint);
  border-radius: 22px;
  padding: 1.35rem 1.2rem;
  margin-bottom: 1rem;
}
.profile-card h2 {
  margin: 0.2rem 0;
  font-size: 1.4rem;
  font-family: inherit;
}
.table-big {
  margin: 0.35rem 0;
  font-size: 1.6rem;
  font-weight: 700;
}
.live-line {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  margin: 0.5rem 0 0;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--teal);
}

.sheet-scrim {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: grid;
  align-items: end;
  z-index: 50;
  justify-items: center;
}
.sheet {
  width: min(480px, 100%);
  background: #fff;
  border-radius: 24px 24px 0 0;
  max-height: 88vh;
  overflow: auto;
  padding: 0.85rem 1.15rem 1.5rem;
  animation: slideUp 0.35s var(--ease-out, cubic-bezier(0.22, 1, 0.36, 1));
}
.handle {
  width: 42px;
  height: 4px;
  border-radius: 999px;
  background: #ddd;
  margin: 0.15rem auto 0.85rem;
}
.sheet h3 {
  margin: 0 0 0.75rem;
  font-size: 1.25rem;
  font-family: inherit;
}
.cart-list {
  list-style: none;
  margin: 0 0 1rem;
  padding: 0;
}
.cart-list li {
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.7rem 0;
  border-bottom: 1px solid #eee;
}
.mods {
  margin: 0.2rem 0 0;
  color: var(--muted);
  font-size: 0.85rem;
}
.reason-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
  margin: 0.85rem 0 1rem;
}
.chip {
  border: 1px solid #e5e7eb;
  background: #f9fafb;
  border-radius: 999px;
  padding: 0.5rem 0.9rem;
  font: inherit;
  font-weight: 650;
  cursor: pointer;
}
.chip.active {
  background: var(--teal);
  border-color: var(--teal);
  color: #fff;
}
.label {
  display: block;
  margin-bottom: 0.35rem;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--muted);
}
.textarea {
  width: 100%;
  min-height: 88px;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  padding: 0.75rem;
  font: inherit;
  margin-bottom: 0.85rem;
  resize: vertical;
}
.textarea:focus {
  outline: none;
  border-color: var(--teal);
  box-shadow: 0 0 0 3px rgba(26, 92, 80, 0.15);
}

.notice {
  margin: 0.75rem 1rem;
  padding: 0.8rem 0.95rem;
  border-radius: 14px;
  font-weight: 700;
  position: relative;
  z-index: 60;
}
.notice.bad {
  background: #ffe8e6;
  color: #eb1700;
}
.notice.good {
  background: #e8faf0;
  color: #048a4a;
}
.empty {
  padding: 2rem 0.75rem;
  text-align: center;
  color: var(--muted);
  font-weight: 500;
}
.muted {
  color: var(--muted);
}

.detail-enter-active,
.detail-leave-active {
  transition: opacity 0.28s ease, transform 0.28s var(--ease-out, cubic-bezier(0.22, 1, 0.36, 1));
}
.detail-enter-from,
.detail-leave-to {
  opacity: 0;
  transform: translateY(18px);
}

@keyframes riseIn {
  from {
    opacity: 0;
    transform: translateY(12px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}
@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(100%);
  }
  to {
    opacity: 1;
    transform: none;
  }
}
</style>
