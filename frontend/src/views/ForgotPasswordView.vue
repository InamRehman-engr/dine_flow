<template>
  <div class="auth-page rise-in">
    <div class="auth-card pencil-border panel">
      <p class="brand">DineFlow</p>
      <h1>Forgot password</h1>
      <p class="muted">Local MVP returns a reset token in the response (no SMTP).</p>
      <form class="stack" @submit.prevent="submit" v-if="!token">
        <div>
          <label class="label">Email</label>
          <input v-model="email" class="input" type="email" required />
        </div>
        <p v-if="error" class="error-text">{{ error }}</p>
        <button class="btn" type="submit" :disabled="loading">Request reset</button>
      </form>
      <div v-else class="stack">
        <p class="muted">Use this token on the reset page:</p>
        <code class="token">{{ token }}</code>
        <router-link class="btn" :to="{ name: 'reset', query: { token } }">Continue to reset</router-link>
      </div>
      <p class="muted links"><router-link to="/login">Back to login</router-link></p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { api } from '../api'

const email = ref('')
const token = ref('')
const error = ref('')
const loading = ref(false)

async function submit() {
  error.value = ''
  loading.value = true
  try {
    const data = await api.post('/api/auth/forgot-password', { email: email.value })
    token.value = data.reset_token || ''
    if (!token.value) error.value = data.message || 'If the email exists, check with your admin.'
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
.token {
  word-break: break-all;
  background: var(--surface);
  border: 1px solid var(--line);
  padding: 0.75rem;
  border-radius: var(--radius);
  font-size: 0.85rem;
}
</style>
