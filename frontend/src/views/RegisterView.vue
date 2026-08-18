<template>
  <div class="auth-page rise-in">
    <div class="auth-card panel">
      <p class="brand">DineFlow</p>
      <h1>Register your restaurant</h1>
      <p class="muted">One restaurant account. Sign in as Admin or Kitchen later — both share the same live data.</p>
      <form class="stack" @submit.prevent="submit">
        <div>
          <label class="label">Restaurant name</label>
          <input v-model="name" class="input" required />
        </div>
        <div>
          <label class="label">Email</label>
          <input v-model="email" class="input" type="email" required />
        </div>
        <div>
          <label class="label">Password (8+ characters)</label>
          <input v-model="password" class="input" type="password" minlength="8" required />
        </div>
        <p v-if="error" class="error-text">{{ error }}</p>
        <button class="btn" type="submit" :disabled="loading">{{ loading ? 'Creating…' : 'Create account' }}</button>
      </form>
      <p class="muted links"><router-link to="/login">Already have an account?</router-link></p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'
import { setLoginMode } from '../composables/useLoginMode'

const router = useRouter()
const name = ref('')
const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function submit() {
  error.value = ''
  loading.value = true
  try {
    await api.post('/api/auth/register', {
      name: name.value,
      email: email.value,
      password: password.value,
    })
    setLoginMode('admin')
    router.push('/admin')
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
  width: min(420px, 100%);
  background: #fff;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 1.75rem 1.5rem;
}
.brand { margin: 0; font-size: 1.05rem; }
h1 { margin: 0.55rem 0 0.5rem; font-size: 1.4rem; }
.links { margin-top: 1rem; }
</style>
