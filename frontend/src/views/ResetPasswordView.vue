<template>
  <div class="auth-page rise-in">
    <div class="auth-card pencil-border panel">
      <p class="brand">DineFlow</p>
      <h1>Reset password</h1>
      <form class="stack" @submit.prevent="submit">
        <div>
          <label class="label">Reset token</label>
          <input v-model="token" class="input" required />
        </div>
        <div>
          <label class="label">New password</label>
          <input v-model="password" class="input" type="password" minlength="8" required />
        </div>
        <p v-if="message" class="muted">{{ message }}</p>
        <p v-if="error" class="error-text">{{ error }}</p>
        <button class="btn" type="submit" :disabled="loading">Update password</button>
      </form>
      <p class="muted links"><router-link to="/login">Back to login</router-link></p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api'

const route = useRoute()
const router = useRouter()
const token = ref(route.query.token || '')
const password = ref('')
const error = ref('')
const message = ref('')
const loading = ref(false)

async function submit() {
  error.value = ''
  message.value = ''
  loading.value = true
  try {
    const data = await api.post('/api/auth/reset-password', {
      token: token.value,
      password: password.value,
    })
    message.value = data.message
    setTimeout(() => router.push('/login'), 1200)
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
  width: min(440px, 100%);
  background: #fff;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 1.75rem 1.5rem;
}
.brand { margin: 0; font-size: 1.05rem; }
h1 { margin: 0.55rem 0 0.5rem; font-size: 1.4rem; }
.links { margin-top: 1rem; }
</style>
