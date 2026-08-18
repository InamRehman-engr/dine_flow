<template>
  <div class="app-shell">
    <router-view />
  </div>
</template>

<script setup>
import { useTheme } from './composables/useTheme'
useTheme()
</script>

<style scoped>
.app-shell {
  min-height: 100vh;
}
</style>
