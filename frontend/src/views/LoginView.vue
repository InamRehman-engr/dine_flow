<template>
  <div class="auth-page">
    <div class="auth-card">
      <p class="brand">DineFlow</p>
      <h1>Sign in</h1>
      <p class="muted">Choose a workspace. Same credentials sync live across devices.</p>

      <div class="seg mode" role="group" aria-label="Sign in as">
        <button type="button" :class="{ active: mode === 'admin' }" @click="mode = 'admin'">Admin</button>
        <button type="button" :class="{ active: mode === 'kitchen' }" @click="mode = 'kitchen'">Kitchen</button>
      </div>

      <form class="stack" @submit.prevent="submit">
        <div>
          <label class="label">Email</label>
          <input v-model="email" class="input" type="email" required autocomplete="username" />
        </div>
        <div>
          <label class="label">Password</label>
          <input v-model="password" class="input" type="password" required autocomplete="current-password" />
        </div>
        <p v-if="error" class="error-text">{{ error }}</p>
        <button class="btn" type="submit" :disabled="loading">
          {{ loading ? 'Signing in…' : 'Continue' }}
        </button>
      </form>
      <p class="muted links">
        <router-link to="/register">Create restaurant</router-link>
        ·
        <router-link to="/forgot-password">Forgot password</router-link>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api'
import { setLoginMode } from '../composables/useLoginMode'

const router = useRouter()
const route = useRoute()
const email = ref('')
const password = ref('')
const mode = ref('admin')
const error = ref('')
const loading = ref(false)

async function submit() {
  error.value = ''
  loading.value = true
  try {
    await api.post('/api/auth/login', { email: email.value, password: password.value })
    setLoginMode(mode.value)
    if (route.query.redirect) router.push(String(route.query.redirect))
    else router.push(mode.value === 'kitchen' ? '/kitchen' : '/admin')
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 1.5rem;
  background: var(--surface);
}
.auth-card {
  width: min(400px, 100%);
  background: #fff;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 1.75rem 1.5rem;
}
.brand {
  margin: 0;
  font-size: 1.05rem;
}
h1 {
  margin: 0.55rem 0 0.35rem;
  font-size: 1.4rem;
}
.mode {
  width: 100%;
  margin: 1.15rem 0 1.25rem;
}
.mode button {
  flex: 1;
}
.links { margin-top: 1rem; }
</style>
