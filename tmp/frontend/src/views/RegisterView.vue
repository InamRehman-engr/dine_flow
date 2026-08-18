<template>
  <div class="auth-page">
    <div class="auth-card rise-in">
      <p class="brand">DineFlow</p>
      <h1>Register your restaurant</h1>
      <p class="muted">Creates a manager account. Add kitchen staff later in Settings.</p>
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
import { useAuth } from '../composables/useAuth'

const router = useRouter()
const { register } = useAuth()
const name = ref('')
const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function submit() {
  error.value = ''
  loading.value = true
  try {
    await register({ name: name.value, email: email.value, password: password.value })
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
}
.auth-card {
  width: min(420px, 100%);
  background: var(--surface-raised);
  border: 1px solid var(--line);
  border-radius: var(--radius-lg);
  padding: 1.75rem 1.5rem;
  box-shadow: var(--shadow);
}
.brand { margin: 0; font-size: 1.35rem; }
h1 { margin: 0.55rem 0 0.5rem; font-size: 1.55rem; }
.links { margin-top: 1rem; }
</style>
