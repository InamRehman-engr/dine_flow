<template>
  <div class="settings">
    <PageHero
      :image="SETTINGS_PHOTO"
      eyebrow="System"
      title="Settings"
      subtitle="Restaurant profile, staff access, and device preferences."
    />

    <div class="grid">
      <section class="card">
        <h2>Appearance</h2>
        <p class="muted">Theme for Admin & Kitchen on this device.</p>
        <div class="seg">
          <button type="button" :class="{ active: theme === 'light' }" @click="setTheme('light')">Light</button>
          <button type="button" :class="{ active: theme === 'dark' }" @click="setTheme('dark')">Dark</button>
        </div>
      </section>

      <section class="card">
        <h2>Locale & payments</h2>
        <dl>
          <div><dt>Currency</dt><dd>{{ currency }}</dd></div>
          <div><dt>Language</dt><dd>{{ language }}</dd></div>
          <div>
            <dt>Payments</dt>
            <dd>{{ paymentsEnabled ? 'Enabled' : 'Stub only' }}</dd>
          </div>
        </dl>
      </section>
    </div>

    <section class="card">
      <h2>Restaurant profile</h2>
      <form class="stack" @submit.prevent="saveProfile">
        <div class="row2">
          <div>
            <label class="label">Name</label>
            <input v-model="name" class="input" />
          </div>
          <div>
            <label class="label">New password (optional)</label>
            <input v-model="password" class="input" type="password" minlength="8" />
          </div>
        </div>
        <p v-if="msg" class="ok">{{ msg }}</p>
        <p v-if="error" class="error-text">{{ error }}</p>
        <button class="btn" type="submit">Save profile</button>
      </form>
    </section>

    <section class="card">
      <header class="head">
        <div>
          <h2>Staff accounts</h2>
          <p class="muted">Managers run Admin. Kitchen staff open the KDS only.</p>
        </div>
      </header>
      <div v-if="staffList.length" class="staff">
        <article v-for="s in staffList" :key="s.id">
          <div class="avatar">{{ (s.display_name || s.email || '?').slice(0, 1).toUpperCase() }}</div>
          <div>
            <strong>{{ s.display_name || s.email }}</strong>
            <span>{{ s.role }} · {{ s.email }}</span>
          </div>
          <button
            v-if="s.id !== currentStaff?.id"
            class="btn btn-ghost btn-sm"
            type="button"
            @click="removeStaff(s)"
          >
            Remove
          </button>
        </article>
      </div>
      <EmptyPanel
        v-else
        :image="SETTINGS_PHOTO"
        title="No staff listed yet"
        body="Invite kitchen or manager accounts so your team can sign in."
      />
      <form class="stack add" @submit.prevent="addStaff">
        <h3>Invite staff</h3>
        <div class="row2">
          <input v-model="newEmail" class="input" type="email" placeholder="Email" required />
          <select v-model="newRole" class="select">
            <option value="kitchen">Kitchen</option>
            <option value="manager">Manager</option>
          </select>
        </div>
        <input v-model="newPassword" class="input" type="password" placeholder="Password (8+)" minlength="8" required />
        <button class="btn btn-ghost" type="submit">Add staff</button>
      </form>
    </section>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api'
import { SETTINGS_PHOTO } from '../composables/useFoodImage'
import { useAuth } from '../composables/useAuth'
import { useMoney } from '../composables/useMoney'
import { useTheme } from '../composables/useTheme'
import EmptyPanel from './EmptyPanel.vue'
import PageHero from './PageHero.vue'

const { theme, setTheme } = useTheme()
const { staff: currentStaff, tenant, fetchMe } = useAuth()
const { currency, language, loadConfig } = useMoney()

const name = ref('')
const password = ref('')
const msg = ref('')
const error = ref('')
const staffList = ref([])
const newEmail = ref('')
const newPassword = ref('')
const newRole = ref('kitchen')
const paymentsEnabled = ref(false)

async function loadStaff() {
  const data = await api.get('/api/auth/staff')
  staffList.value = data.staff || []
}

async function saveProfile() {
  msg.value = ''
  error.value = ''
  try {
    const body = { name: name.value }
    if (password.value) body.password = password.value
    await api.put('/api/auth/profile', body)
    password.value = ''
    msg.value = 'Saved'
    await fetchMe()
  } catch (e) {
    error.value = e.message
  }
}

async function addStaff() {
  await api.post('/api/auth/staff', {
    email: newEmail.value,
    password: newPassword.value,
    role: newRole.value,
  })
  newEmail.value = ''
  newPassword.value = ''
  await loadStaff()
}

async function removeStaff(s) {
  if (!confirm(`Remove ${s.email}?`)) return
  await api.delete(`/api/auth/staff/${s.id}`)
  await loadStaff()
}

onMounted(async () => {
  await fetchMe()
  name.value = tenant.value?.name || ''
  await loadStaff()
  await loadConfig()
  try {
    const cfg = await api.get('/api/public/config')
    paymentsEnabled.value = !!cfg.payments?.enabled
  } catch {
    /* ignore */
  }
})
</script>

<style scoped>
.settings {
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
  max-width: 960px;
  animation: rise 0.35s ease;
}
.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
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
  font-size: 1.15rem;
}
h3 {
  margin: 0 0 0.65rem;
  font-size: 0.95rem;
}
.muted {
  margin: 0 0 0.85rem;
  color: #64748b;
  font-size: 0.88rem;
}
dl {
  margin: 0;
}
dl > div {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.55rem 0;
  border-bottom: 1px solid #eef2f6;
}
dt {
  color: #64748b;
  font-weight: 650;
  font-size: 0.88rem;
}
dd {
  margin: 0;
  font-weight: 750;
}
.stack {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}
.row2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.65rem;
}
.ok {
  margin: 0;
  color: #0f766e;
  font-weight: 700;
}
.staff {
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
  margin: 0.75rem 0 1.15rem;
}
.staff article {
  display: grid;
  grid-template-columns: 40px 1fr auto;
  gap: 0.75rem;
  align-items: center;
  padding: 0.7rem 0.75rem;
  border-radius: 14px;
  background: #f8fafc;
  border: 1px solid #eef2f6;
}
.avatar {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  background: #ccfbf1;
  color: #0f766e;
  font-weight: 800;
}
.staff strong {
  display: block;
  font-size: 0.92rem;
}
.staff span {
  color: #64748b;
  font-size: 0.8rem;
}
.add {
  padding-top: 0.85rem;
  border-top: 1px solid #eef2f6;
}
@keyframes rise {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: none; }
}
@media (max-width: 800px) {
  .grid,
  .row2 {
    grid-template-columns: 1fr;
  }
}
</style>
