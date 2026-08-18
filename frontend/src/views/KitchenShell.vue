<template>
  <div class="shell">
    <header class="hero">
      <div class="hero-bg" aria-hidden="true" />
      <div class="hero-shade" aria-hidden="true" />
      <div class="hero-inner">
        <div>
          <p class="brand">DineFlow</p>
          <p class="sub" v-if="tenant">{{ tenant.name }} · Kitchen display</p>
        </div>
        <div class="tools">
          <span class="live"><span class="status-dot" :class="{ on: connected }" /> {{ connected ? 'Live' : 'Offline' }}</span>
          <button class="btn btn-ghost btn-sm light" type="button" @click="logout">Sign out</button>
        </div>
      </div>
    </header>
    <main class="content">
      <KitchenDisplay :tenant="tenant" />
    </main>
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'
import { useSocket } from '../composables/useSocket'
import { clearLoginMode } from '../composables/useLoginMode'
import KitchenDisplay from '../components/KitchenDisplay.vue'

const router = useRouter()
const tenant = ref(null)
const { connected, socket } = useSocket(null)

async function loadMe() {
  const data = await api.get('/api/auth/me')
  tenant.value = data.tenant
}
async function logout() {
  await api.post('/api/auth/logout')
  clearLoginMode()
  router.push('/login')
}
watch(() => tenant.value?.id, (id) => { if (id) socket.emit('join_session', { tenant_id: id }) })
onMounted(loadMe)
</script>

<style scoped>
.shell {
  min-height: 100vh;
  background:
    radial-gradient(800px 360px at 100% 0%, rgba(47, 107, 79, 0.08), transparent 50%),
    #f3f4f2;
}
.hero {
  position: relative;
  min-height: 150px;
  overflow: hidden;
  color: #fff;
}
.hero-bg {
  position: absolute;
  inset: 0;
  background:
    url('https://images.unsplash.com/photo-1556910103-1c02745aae4d?auto=format&fit=crop&w=1800&q=80')
    center/cover no-repeat;
}
.hero-shade {
  position: absolute;
  inset: 0;
  background: linear-gradient(115deg, rgba(10, 14, 12, 0.9) 15%, rgba(10, 14, 12, 0.45) 100%);
}
.hero-inner {
  position: relative;
  z-index: 1;
  max-width: 1240px;
  margin: 0 auto;
  padding: 1.4rem 1.25rem 1.2rem;
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 1rem;
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
.tools {
  display: flex;
  align-items: center;
  gap: 0.65rem;
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
  max-width: 1240px;
  margin: 0 auto;
  padding: 1.35rem 1.25rem 2.5rem;
}
</style>
