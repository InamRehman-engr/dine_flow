<template>
  <div class="shell">
    <header class="hero">
      <div class="hero-bg" aria-hidden="true" />
      <div class="hero-shade" aria-hidden="true" />
      <div class="hero-inner">
        <div class="brand-block">
          <p class="brand">DineFlow</p>
          <p class="sub" v-if="tenant">{{ tenant.name }} · Operations</p>
        </div>
        <nav class="tabs">
          <router-link to="/admin">Floor</router-link>
          <router-link to="/admin/menu">Menu</router-link>
        </nav>
        <div class="tools">
          <span class="live"><span class="status-dot" :class="{ on: connected }" /> {{ connected ? 'Live' : 'Offline' }}</span>
          <button class="btn btn-ghost btn-sm light" type="button" @click="logout">Sign out</button>
        </div>
      </div>
    </header>

    <div class="content">
      <section v-if="waiterCalls.length" class="alerts">
        <div class="alerts-head">
          <h2>Waiter calls</h2>
          <span>{{ waiterCalls.length }} open</span>
        </div>
        <div v-for="call in waiterCalls" :key="call.id" class="alert-row">
          <div>
            <strong>Table {{ call.table_number }}</strong>
            <span class="muted"> · {{ formatTime(call.created_at) }}</span>
          </div>
          <button class="btn btn-sm" type="button" @click="ack(call)">Acknowledge</button>
        </div>
      </section>

      <main class="main">
        <router-view v-slot="{ Component }">
          <component :is="Component" :tenant="tenant" @refresh-alerts="loadAlerts" />
        </router-view>
      </main>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'
import { useSocket } from '../composables/useSocket'
import { clearLoginMode } from '../composables/useLoginMode'

const router = useRouter()
const tenant = ref(null)
const waiterCalls = ref([])
const { connected, on, socket } = useSocket(null)

async function loadMe() {
  const data = await api.get('/api/auth/me')
  tenant.value = data.tenant
}
async function loadAlerts() {
  const data = await api.get('/api/orders/waiter-calls?status=open')
  waiterCalls.value = data.calls || []
}
async function ack(call) {
  await api.post(`/api/orders/waiter-call/${call.id}/ack`)
  await loadAlerts()
}
async function logout() {
  await api.post('/api/auth/logout')
  clearLoginMode()
  router.push('/login')
}
function formatTime(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

watch(() => tenant.value?.id, (id) => { if (id) socket.emit('join_session', { tenant_id: id }) })

onMounted(async () => {
  await loadMe()
  await loadAlerts()
  on('waiter_call', () => loadAlerts())
  on('waiter_acked', () => loadAlerts())
  on('floor_refresh', () => loadAlerts())
})
</script>

<style scoped>
.shell {
  min-height: 100vh;
  background:
    radial-gradient(900px 420px at 0% 0%, rgba(138, 112, 72, 0.08), transparent 55%),
    #f4f2ef;
}
.hero {
  position: relative;
  min-height: 168px;
  overflow: hidden;
  color: #fff;
}
.hero-bg {
  position: absolute;
  inset: 0;
  background:
    url('https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?auto=format&fit=crop&w=1800&q=80')
    center/cover no-repeat;
  transform: scale(1.02);
}
.hero-shade {
  position: absolute;
  inset: 0;
  background: linear-gradient(110deg, rgba(12, 14, 16, 0.88) 10%, rgba(12, 14, 16, 0.55) 55%, rgba(12, 14, 16, 0.35) 100%);
}
.hero-inner {
  position: relative;
  z-index: 1;
  max-width: 1180px;
  margin: 0 auto;
  padding: 1.4rem 1.25rem 1.1rem;
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  gap: 1rem;
  align-items: end;
}
.brand {
  margin: 0;
  font-size: 1.35rem;
  color: #fff;
}
.sub {
  margin: 0.25rem 0 0;
  color: rgba(255, 255, 255, 0.72);
  font-size: 0.85rem;
}
.tabs {
  justify-self: center;
  border-bottom: 0;
  gap: 0.25rem;
}
.tabs :deep(a),
.tabs a {
  color: rgba(255, 255, 255, 0.7);
  padding: 0.55rem 0.9rem;
}
.tabs a.router-link-active {
  color: #fff;
}
.tabs a.router-link-active::after {
  background: #fff;
  bottom: 0;
}
.tools {
  justify-self: end;
  display: flex;
  align-items: center;
  gap: 0.65rem;
  padding-bottom: 0.35rem;
}
.live {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.75rem;
  color: rgba(255, 255, 255, 0.75);
}
.btn.light {
  color: #fff;
  border-color: rgba(255, 255, 255, 0.45);
  background: transparent;
}
.btn.light:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
}
.content {
  max-width: 1180px;
  margin: 0 auto;
  padding: 1.35rem 1.25rem 3rem;
}
.alerts {
  margin-bottom: 1.25rem;
  border: 1px solid #e7d5b3;
  background: #fffaf1;
  border-radius: 12px;
  padding: 0.9rem 1rem;
  box-shadow: 0 10px 28px rgba(20, 16, 10, 0.05);
}
.alerts-head {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.45rem;
  color: var(--accent);
}
.alerts h2 {
  margin: 0;
  font-size: 0.75rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  font-family: var(--font-body);
  font-weight: 600;
}
.alert-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
  padding: 0.55rem 0;
  border-top: 1px solid #f0e2c8;
}
@media (max-width: 800px) {
  .hero-inner {
    grid-template-columns: 1fr;
    align-items: start;
  }
  .tabs, .tools { justify-self: start; }
}
</style>
