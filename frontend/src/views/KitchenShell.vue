<template>
  <div class="kds-shell" @pointerdown="unlockAudio">
    <header class="topbar">
      <div class="brand">
        <div class="mark" aria-hidden="true">
          <CookingPot :size="20" :stroke-width="2.25" />
        </div>
        <div class="brand-text">
          <strong>Kitchen</strong>
          <span>{{ tenantName }}</span>
        </div>
        <span class="live">
          <span class="live-dot" />
          Live
        </span>
      </div>

      <time class="clock" :datetime="clockIso">{{ clockLabel }}</time>

      <div class="actions">
        <span class="count-pill">{{ openCount }} open tickets</span>
        <button v-if="isManager" class="btn-tool" type="button" @click="goAdmin">
          <LayoutGrid :size="16" :stroke-width="2" />
          Floor
        </button>
        <button class="btn-tool danger" type="button" @click="doLogout">
          <LogOut :size="16" :stroke-width="2" />
          Sign out
        </button>
      </div>
    </header>

    <KitchenDisplay @open-count="openCount = $event" />
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { CookingPot, LayoutGrid, LogOut } from '@lucide/vue'
import KitchenDisplay from '../components/KitchenDisplay.vue'
import { setWorkspace, useAuth } from '../composables/useAuth'
import { useKdsSound } from '../composables/useKdsSound'
import { useTheme } from '../composables/useTheme'

useTheme()
const router = useRouter()
const { unlock } = useKdsSound()
const { isManager, logout, fetchMe, tenant } = useAuth()

const now = ref(Date.now())
const openCount = ref(0)
let clockTimer = null

const tenantName = computed(() => tenant.value?.name || 'Restaurant')
const clockIso = computed(() => new Date(now.value).toISOString())
const clockLabel = computed(() =>
  new Date(now.value).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }),
)

function unlockAudio() {
  unlock()
}
function goAdmin() {
  setWorkspace('admin')
  router.push('/admin')
}
async function doLogout() {
  await logout()
  router.replace('/login?workspace=kitchen')
}

onMounted(async () => {
  await fetchMe()
  setWorkspace('kitchen')
  clockTimer = setInterval(() => {
    now.value = Date.now()
  }, 1000)
})

onUnmounted(() => {
  if (clockTimer) clearInterval(clockTimer)
})
</script>

<style scoped>
.kds-shell {
  min-height: 100vh;
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--bg);
  color: var(--ink);
  font-family: var(--font);
}

.topbar {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 0.75rem;
  padding: 0.7rem 1.1rem;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.brand {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  min-width: 0;
}

.mark {
  width: 38px;
  height: 38px;
  border-radius: var(--radius);
  display: grid;
  place-items: center;
  background: var(--accent);
  color: #fff;
  flex-shrink: 0;
}

.brand-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
  line-height: 1.15;
}

.brand-text strong {
  font-size: 1rem;
  font-weight: 750;
  letter-spacing: -0.02em;
}

.brand-text span {
  font-size: 0.72rem;
  color: var(--muted);
  font-weight: 550;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.live {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.68rem;
  font-weight: 750;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  padding: 0.28rem 0.55rem;
  border-radius: 999px;
  border: 1px solid var(--ok-border);
  color: var(--ok);
  background: var(--ok-bg);
}

.live-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--ok);
  animation: pulse 1.6s ease infinite;
}

.clock {
  font-variant-numeric: tabular-nums;
  font-weight: 750;
  font-size: 1.35rem;
  letter-spacing: 0.04em;
  color: var(--ink);
}

.actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.45rem;
  flex-wrap: wrap;
}

.count-pill {
  min-height: 36px;
  display: inline-flex;
  align-items: center;
  padding: 0.3rem 0.75rem;
  border-radius: var(--radius);
  border: 1px solid var(--border-strong);
  background: var(--surface-2);
  color: var(--muted);
  font-size: 0.8rem;
  font-weight: 650;
}

.btn-tool {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  min-height: 36px;
  padding: 0.3rem 0.75rem;
  border-radius: var(--radius);
  border: 1px solid var(--border-strong);
  background: var(--surface);
  color: var(--ink);
  font: inherit;
  font-size: 0.8rem;
  font-weight: 650;
  cursor: pointer;
}

.btn-tool:hover {
  background: var(--bg-subtle);
}

.btn-tool.danger {
  color: var(--danger);
  border-color: var(--danger-border);
}

@keyframes pulse {
  0%,
  100% {
    box-shadow: 0 0 0 0 rgba(47, 107, 79, 0.35);
  }
  50% {
    box-shadow: 0 0 0 5px transparent;
  }
}

@media (max-width: 800px) {
  .topbar {
    grid-template-columns: 1fr auto;
  }
  .clock {
    display: none;
  }
  .brand-text span,
  .live {
    display: none;
  }
}
</style>
