<template>
  <div class="ops" :class="{ 'nav-open': navOpen }">
    <aside class="rail">
      <div class="rail-top">
        <div class="logo">
          <span class="logo-mark" aria-hidden="true">
            <UtensilsCrossed :size="18" :stroke-width="2.25" />
          </span>
          <div class="logo-text">
            <strong>DineFlow</strong>
            <small>{{ tenant?.name || 'Restaurant' }}</small>
          </div>
        </div>
      </div>

      <nav class="rail-nav">
        <p class="rail-section">Operations</p>
        <router-link to="/admin" end @click="navOpen = false">
          <LayoutGrid :size="18" :stroke-width="2" class="ico" />
          Floor
        </router-link>
        <router-link to="/admin/orders" @click="navOpen = false">
          <ClipboardList :size="18" :stroke-width="2" class="ico" />
          Orders
          <em v-if="openHint" class="count">{{ openHint }}</em>
        </router-link>
        <router-link to="/kitchen" @click="goKitchen">
          <CookingPot :size="18" :stroke-width="2" class="ico" />
          Kitchen
        </router-link>

        <p class="rail-section">Management</p>
        <router-link to="/admin/menu" @click="navOpen = false">
          <BookOpen :size="18" :stroke-width="2" class="ico" />
          Menu
        </router-link>
        <router-link to="/admin/stations" @click="navOpen = false">
          <PanelsTopLeft :size="18" :stroke-width="2" class="ico" />
          Stations
        </router-link>
        <router-link to="/admin/qrs" @click="navOpen = false">
          <QrCode :size="18" :stroke-width="2" class="ico" />
          QR codes
        </router-link>

        <p class="rail-section">System</p>
        <router-link to="/admin/settings" @click="navOpen = false">
          <Settings :size="18" :stroke-width="2" class="ico" />
          Settings
        </router-link>
      </nav>

      <div class="rail-foot">
        <div class="who-rail">
          <div class="avatar">{{ initials }}</div>
          <div>
            <strong>{{ staff?.display_name || staff?.email || 'Manager' }}</strong>
            <small>Manager</small>
          </div>
        </div>
        <button class="signout" type="button" @click="doLogout">
          <LogOut :size="16" :stroke-width="2" />
          Sign out
        </button>
      </div>
    </aside>

    <div class="workspace">
      <header class="command">
        <button class="burger" type="button" aria-label="Open navigation" @click="navOpen = !navOpen">
          <Menu :size="20" :stroke-width="2" />
        </button>
        <div class="command-title">
          <h1>{{ page.title }}</h1>
          <p>{{ page.subtitle }}</p>
        </div>
        <div class="command-actions">
          <div class="live-chip" :data-on="connected">
            <Wifi v-if="connected" :size="14" :stroke-width="2.25" />
            <WifiOff v-else :size="14" :stroke-width="2.25" />
            {{ connected ? 'Realtime' : 'Reconnecting' }}
          </div>
        </div>
      </header>

      <div v-if="waiterCalls.length" class="alert-rail">
        <article v-for="call in waiterCalls" :key="call.id" class="alert-card">
          <AlertTriangle :size="18" :stroke-width="2.25" />
          <div>
            <strong>Table {{ call.table_number }}</strong>
            <span>{{ reasonLabel(call.reason) }}</span>
            <small v-if="call.note">{{ call.note }}</small>
          </div>
          <button type="button" @click="ack(call)">Acknowledge</button>
        </article>
      </div>

      <main class="stage">
        <router-view v-slot="{ Component }">
          <Transition name="stage" mode="out-in">
            <component :is="Component" :tenant="tenant" @refresh-alerts="loadAlerts" />
          </Transition>
        </router-view>
      </main>
    </div>

    <div v-if="navOpen" class="scrim" @click="navOpen = false" />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  AlertTriangle,
  BookOpen,
  ClipboardList,
  CookingPot,
  LayoutGrid,
  LogOut,
  Menu,
  PanelsTopLeft,
  QrCode,
  Settings,
  UtensilsCrossed,
  Wifi,
  WifiOff,
} from '@lucide/vue'
import { api } from '../api'
import { setWorkspace, useAuth } from '../composables/useAuth'
import { useSocket } from '../composables/useSocket'
import { useTheme } from '../composables/useTheme'

useTheme()

const router = useRouter()
const route = useRoute()
const { tenant, staff, fetchMe, logout } = useAuth()
const waiterCalls = ref([])
const openHint = ref(0)
const navOpen = ref(false)
const { connected, on, joinStaff } = useSocket()

const page = computed(() => {
  const map = {
    'admin-floor': { title: 'Live Floor', subtitle: 'Tables, orders, and attention — at a glance' },
    'admin-orders': { title: 'Active Orders', subtitle: 'Live tickets and kitchen status' },
    'admin-menu': { title: 'Menu', subtitle: 'Categories, dishes, and availability' },
    'admin-stations': { title: 'Stations', subtitle: 'Route tickets to the right line' },
    'admin-qrs': { title: 'QR Codes', subtitle: 'Table links for guest ordering' },
    'admin-settings': { title: 'Settings', subtitle: 'Restaurant, staff, and preferences' },
  }
  return map[route.name] || { title: 'Admin', subtitle: 'Operations' }
})

const initials = computed(() => {
  const n = staff.value?.display_name || staff.value?.email || 'M'
  return String(n).slice(0, 1).toUpperCase()
})

function reasonLabel(r) {
  return ({ water: 'Water', bill: 'Bill', help: 'Help', other: 'Other' })[r] || 'Help'
}

async function loadAlerts() {
  const data = await api.get('/api/orders/waiter-calls?status=open')
  waiterCalls.value = data.calls || []
}

async function loadOpenHint() {
  try {
    const data = await api.get('/api/orders/live')
    openHint.value = (data.orders || []).length
  } catch {
    openHint.value = 0
  }
}

async function ack(call) {
  await api.post(`/api/orders/waiter-call/${call.id}/ack`)
  await loadAlerts()
}

function goKitchen() {
  setWorkspace('kitchen')
  navOpen.value = false
}

async function doLogout() {
  await logout()
  router.replace('/login')
}

onMounted(async () => {
  await fetchMe()
  setWorkspace('admin')
  joinStaff()
  await Promise.all([loadAlerts(), loadOpenHint()])
  on('waiter_call', () => loadAlerts())
  on('waiter_acked', () => loadAlerts())
  on('floor_refresh', () => loadAlerts())
  on('new_order', () => loadOpenHint())
  on('status_update', () => loadOpenHint())
  on('connect', () => joinStaff())
})
</script>

<style scoped>
.ops {
  min-height: 100vh;
  display: grid;
  grid-template-columns: var(--sidebar-w) 1fr;
  color: var(--ink);
  font-family: var(--font);
  background: var(--bg);
}

.rail {
  position: sticky;
  top: 0;
  height: 100vh;
  background: #241f1c;
  color: #f2ebe3;
  display: flex;
  flex-direction: column;
  z-index: 40;
  border-right: 1px solid #322c28;
}

.rail-top {
  padding: 1.15rem 1rem;
  border-bottom: 1px solid #322c28;
}

.logo {
  display: flex;
  align-items: center;
  gap: 0.7rem;
}

.logo-mark {
  width: 36px;
  height: 36px;
  border-radius: var(--radius);
  display: grid;
  place-items: center;
  background: var(--accent);
  color: #fff;
  flex-shrink: 0;
}

.logo-text {
  min-width: 0;
  line-height: 1.15;
}

.logo-text strong {
  display: block;
  font-size: 0.95rem;
  font-weight: 700;
  color: #fafaf9;
}

.logo-text small {
  color: #a8a29e;
  font-size: 0.72rem;
}

.rail-nav {
  flex: 1;
  overflow: auto;
  padding: 0.75rem 0.65rem;
}

.rail-section {
  margin: 0.85rem 0.55rem 0.4rem;
  font-size: 0.65rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: #78716c;
  font-weight: 700;
}

.rail-nav a {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  padding: 0.65rem 0.7rem;
  border-radius: var(--radius);
  color: #a8a29e;
  font-weight: 550;
  font-size: 0.9rem;
  margin-bottom: 0.15rem;
}

.rail-nav a:hover {
  background: #292524;
  color: #fafaf9;
}

.rail-nav a.router-link-active,
.rail-nav a.router-link-exact-active {
  background: rgba(31, 107, 92, 0.22);
  color: #9fd5c8;
  font-weight: 650;
}

.ico {
  flex-shrink: 0;
  opacity: 0.95;
}

.count {
  margin-left: auto;
  min-width: 1.25rem;
  height: 1.25rem;
  padding: 0 0.35rem;
  border-radius: 999px;
  background: var(--accent);
  color: #fff;
  font-size: 0.7rem;
  font-weight: 750;
  font-style: normal;
  display: grid;
  place-items: center;
}

.rail-foot {
  padding: 0.85rem;
  border-top: 1px solid #292524;
  display: grid;
  gap: 0.65rem;
}

.who-rail {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.avatar {
  width: 32px;
  height: 32px;
  border-radius: var(--radius);
  background: #292524;
  color: #e7e5e4;
  display: grid;
  place-items: center;
  font-weight: 700;
  font-size: 0.85rem;
}

.who-rail strong {
  display: block;
  font-size: 0.8rem;
  color: #fafaf9;
}

.who-rail small {
  color: #78716c;
  font-size: 0.7rem;
}

.signout {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
  min-height: 36px;
  border: 1px solid #3f3a36;
  background: transparent;
  color: #a8a29e;
  border-radius: var(--radius);
  font: inherit;
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
}

.signout:hover {
  color: #fecaca;
  border-color: rgba(248, 113, 113, 0.4);
}

.workspace {
  min-width: 0;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.command {
  position: sticky;
  top: 0;
  z-index: 30;
  display: flex;
  align-items: center;
  gap: 0.85rem;
  padding: 1rem 1.5rem;
  background: rgba(247, 243, 238, 0.94);
  border-bottom: 1px solid var(--border);
}

.burger {
  display: none;
  border: 1px solid var(--border-strong);
  background: var(--surface);
  border-radius: var(--radius);
  width: 40px;
  height: 40px;
  place-items: center;
  cursor: pointer;
  color: var(--ink);
}

.command-title {
  flex: 1;
  min-width: 0;
}

.command-title h1 {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 700;
  letter-spacing: -0.03em;
}

.command-title p {
  margin: 0.2rem 0 0;
  color: var(--muted);
  font-size: 0.85rem;
}

.command-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.live-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  min-height: 34px;
  padding: 0.3rem 0.7rem;
  border-radius: 999px;
  border: 1px solid var(--border-strong);
  background: var(--surface);
  color: var(--muted);
  font-size: 0.75rem;
  font-weight: 650;
}

.live-chip[data-on='true'] {
  color: var(--ok);
  border-color: var(--ok-border);
  background: var(--ok-bg);
}

.alert-rail {
  display: grid;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem 0;
}

.alert-card {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 0.9rem;
  border-radius: var(--radius);
  border: 1px solid var(--attention-border);
  background: var(--attention-bg);
  color: var(--attention);
}

.alert-card strong {
  display: block;
  color: var(--ink);
  font-size: 0.9rem;
}

.alert-card span,
.alert-card small {
  display: block;
  font-size: 0.8rem;
}

.alert-card button {
  margin-left: auto;
  border: 0;
  background: var(--ink);
  color: #fff;
  border-radius: var(--radius);
  min-height: 34px;
  padding: 0.35rem 0.75rem;
  font: inherit;
  font-weight: 650;
  font-size: 0.8rem;
  cursor: pointer;
}

.stage {
  padding: 1.15rem 1.5rem 1.75rem;
  flex: 1;
}

.stage-enter-active,
.stage-leave-active {
  transition: opacity var(--dur-med) var(--ease), transform var(--dur-med) var(--ease);
}
.stage-enter-from,
.stage-leave-to {
  opacity: 0;
  transform: translateY(6px);
}

.scrim {
  display: none;
}

@media (max-width: 960px) {
  .ops {
    grid-template-columns: 1fr;
  }
  .rail {
    position: fixed;
    left: 0;
    top: 0;
    width: min(280px, 86vw);
    transform: translateX(-105%);
    transition: transform var(--dur-med) var(--ease);
  }
  .ops.nav-open .rail {
    transform: none;
  }
  .burger {
    display: grid;
  }
  .scrim {
    display: block;
    position: fixed;
    inset: 0;
    background: rgba(28, 25, 23, 0.45);
    z-index: 35;
  }
  .command {
    padding: 0.85rem 1rem;
  }
  .stage {
    padding: 1rem;
  }
}
</style>
