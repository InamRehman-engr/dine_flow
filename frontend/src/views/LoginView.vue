<template>
  <div class="login">
    <section class="panel">
      <div class="card rise-in">
        <div class="logo" aria-hidden="true">
          <svg viewBox="0 0 48 48" width="44" height="44">
            <circle cx="24" cy="24" r="24" fill="#0f766e" />
            <path
              d="M14 28c4-8 8-10 10-10s6 2 10 10c-3 4-7 6-10 6s-7-2-10-6z"
              fill="none"
              stroke="#fff"
              stroke-width="2.4"
              stroke-linecap="round"
            />
            <path d="M18 22c2-3 4-4 6-4s4 1 6 4" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" />
          </svg>
        </div>

        <h1>Login form</h1>
        <p class="lead">
          Sign in to DineFlow for floor control, live orders, and kitchen tickets.
        </p>

        <div v-if="alreadyIn" class="switch-banner">
          <p>
            Signed in as <strong>{{ staff?.email }}</strong>
            ({{ staff?.role }})
          </p>
          <button class="link-btn" type="button" :disabled="loading" @click="forceLogout">
            Sign out to switch
          </button>
        </div>

        <div class="workspace" role="group" aria-label="Workspace">
          <button type="button" :class="{ active: workspace === 'admin' }" @click="workspace = 'admin'">
            Admin
          </button>
          <button type="button" :class="{ active: workspace === 'kitchen' }" @click="workspace = 'kitchen'">
            Kitchen
          </button>
        </div>

        <form class="form" @submit.prevent="submit">
          <label class="field">
            <span>Username</span>
            <div class="control">
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="#9CA3AF" stroke-width="1.8">
                <circle cx="12" cy="8" r="3.5" />
                <path d="M5 19c1.6-3.2 4.2-4.8 7-4.8S17.4 15.8 19 19" />
              </svg>
              <input
                v-model="email"
                type="email"
                required
                autocomplete="username"
                placeholder="Enter username"
              />
            </div>
          </label>

          <label class="field">
            <span>Password</span>
            <div class="control">
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="#9CA3AF" stroke-width="1.8">
                <rect x="5" y="11" width="14" height="10" rx="2" />
                <path d="M8 11V8a4 4 0 018 0v3" />
              </svg>
              <input
                v-model="password"
                type="password"
                required
                autocomplete="current-password"
                placeholder="Enter password"
              />
            </div>
          </label>

          <div class="row-links">
            <router-link class="forgot" to="/forgot-password">Forgot password?</router-link>
          </div>

          <p v-if="error" class="error">{{ error }}</p>

          <button class="submit" type="submit" :disabled="loading">
            {{ loading ? 'Signing in…' : workspace === 'kitchen' ? 'Open kitchen' : 'Open admin' }}
          </button>
        </form>

        <p class="footer">
          <router-link to="/register">Create restaurant</router-link>
          · End user agreement
        </p>
      </div>
    </section>

    <aside class="hero" aria-hidden="true" />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuth } from '../composables/useAuth'

const router = useRouter()
const route = useRoute()
const { login, logout, fetchMe, staff, tenant } = useAuth()
const email = ref('')
const password = ref('')
const workspace = ref('admin')
const error = ref('')
const loading = ref(false)

const alreadyIn = computed(() => !!tenant.value && !!staff.value)

onMounted(async () => {
  if (!tenant.value) await fetchMe()
  if (route.query.workspace === 'kitchen') workspace.value = 'kitchen'
})

async function forceLogout() {
  loading.value = true
  try {
    await logout()
    error.value = ''
  } finally {
    loading.value = false
  }
}

async function submit() {
  error.value = ''
  loading.value = true
  try {
    if (tenant.value) await logout()
    const data = await login(email.value, password.value, workspace.value)
    if (data.staff?.role === 'kitchen' && workspace.value === 'admin') {
      error.value = 'This account is kitchen-only. Open the Kitchen workspace.'
      workspace.value = 'kitchen'
      await logout()
      return
    }
    const dest =
      route.query.redirect ||
      (workspace.value === 'kitchen' || data.staff?.role === 'kitchen' ? '/kitchen' : '/admin')
    router.replace(String(dest))
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login {
  --brand: #0f766e;
  --brand-dark: #0d5f59;
  --ink: #1c1917;
  --muted: #78716c;
  --line: #e7e5e4;
  min-height: 100vh;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1.05fr);
  font-family: var(--font);
  background: #faf9f7;
}

.panel {
  display: grid;
  place-items: center;
  padding: 2rem 1.5rem;
  background: #fff;
}

.card {
  width: min(380px, 100%);
  text-align: center;
}

.logo {
  display: grid;
  place-items: center;
  margin-bottom: 1rem;
}

h1 {
  margin: 0;
  font-size: 1.85rem;
  font-weight: 700;
  color: var(--ink);
  letter-spacing: -0.02em;
  font-family: inherit;
}

.lead {
  margin: 0.65rem auto 1.35rem;
  max-width: 32ch;
  color: var(--muted);
  font-size: 0.88rem;
  line-height: 1.5;
}

.workspace {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.5rem;
  margin-bottom: 1.25rem;
}
.workspace button {
  border: 1px solid var(--line);
  background: #fff;
  border-radius: 8px;
  min-height: 42px;
  font: inherit;
  font-weight: 650;
  font-size: 0.9rem;
  color: var(--muted);
  cursor: pointer;
  transition: border-color 0.15s ease, color 0.15s ease, background 0.15s ease;
}
.workspace button:active {
  opacity: 0.92;
}
.workspace button.active {
  border-color: var(--brand);
  color: var(--brand);
  background: rgba(15, 118, 110, 0.08);
}

.form {
  text-align: left;
}

.field {
  display: block;
  margin-bottom: 0.95rem;
}
.field > span {
  display: block;
  margin-bottom: 0.4rem;
  font-size: 0.82rem;
  font-weight: 600;
  color: #374151;
}

.control {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  min-height: 48px;
  padding: 0 1rem;
  border: 1.5px solid var(--line);
  border-radius: 8px;
  background: #fff;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
.control:focus-within {
  border-color: var(--brand);
  box-shadow: 0 0 0 3px rgba(255, 106, 0, 0.15);
}
.control input {
  flex: 1;
  border: 0;
  background: transparent;
  font: inherit;
  font-size: 0.95rem;
  color: var(--ink);
  outline: none;
  min-width: 0;
}
.control input::placeholder {
  color: #9ca3af;
}

.row-links {
  margin: -0.15rem 0 1rem;
}
.forgot {
  color: var(--brand);
  font-size: 0.88rem;
  font-weight: 650;
  text-decoration: none;
}
.forgot:hover {
  text-decoration: underline;
}

.submit {
  width: 100%;
  min-height: 48px;
  border: 0;
  border-radius: 8px;
  background: var(--brand);
  color: #fff;
  font: inherit;
  font-size: 0.95rem;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.15s ease, opacity 0.15s ease;
}
.submit:hover:not(:disabled) {
  background: var(--brand-dark);
}
.submit:active:not(:disabled) {
  opacity: 0.92;
}
.submit:disabled {
  opacity: 0.55;
  cursor: not-allowed;
  box-shadow: none;
}

.error {
  margin: 0 0 0.75rem;
  color: #dc2626;
  font-size: 0.88rem;
  font-weight: 600;
}

.footer {
  margin: 1.6rem 0 0;
  font-size: 0.8rem;
  color: #9ca3af;
}
.footer a {
  color: #9ca3af;
  text-decoration: none;
}
.footer a:hover {
  color: var(--brand);
}

.switch-banner {
  text-align: left;
  margin: 0 0 1rem;
  padding: 0.85rem 1rem;
  border-radius: 14px;
  background: #f0fdfa;
  border: 1px solid #fed7aa;
  font-size: 0.88rem;
}
.switch-banner p {
  margin: 0 0 0.45rem;
}
.link-btn {
  border: 0;
  background: transparent;
  color: var(--brand);
  font: inherit;
  font-weight: 700;
  font-size: 0.85rem;
  cursor: pointer;
  padding: 0;
}

.hero {
  background:
    linear-gradient(105deg, rgba(15, 118, 110, 0.35), rgba(15, 118, 110, 0.05) 42%, transparent 62%),
    url('https://images.unsplash.com/photo-1467003909585-2f8a72700288?auto=format&fit=crop&w=1400&q=80')
      center / cover no-repeat;
  min-height: 100vh;
}

@media (max-width: 900px) {
  .login {
    grid-template-columns: 1fr;
  }
  .hero {
    display: none;
  }
  .panel {
    min-height: 100vh;
    background:
      linear-gradient(180deg, rgba(255, 255, 255, 0.92), rgba(255, 255, 255, 0.96)),
      url('https://images.unsplash.com/photo-1467003909585-2f8a72700288?auto=format&fit=crop&w=1000&q=80')
        center / cover no-repeat;
  }
  .card {
    background: #fff;
    border-radius: 22px;
    padding: 1.6rem 1.25rem 1.4rem;
    box-shadow: 0 20px 50px rgba(17, 24, 39, 0.12);
  }
}
</style>
