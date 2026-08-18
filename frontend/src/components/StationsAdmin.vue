<template>
  <div class="stations">
    <PageHero
      :image="STATIONS_PHOTO"
      eyebrow="Kitchen"
      title="Stations"
      subtitle="Route tickets on the KDS — grill, bar, pastry, expo, and more."
    />

    <section class="card">
      <form class="add" @submit.prevent="add">
        <input v-model="name" class="input" placeholder="Station name" required />
        <button class="btn" type="submit">Add station</button>
      </form>

      <div v-if="stations.length" class="list">
        <article v-for="(s, i) in stations" :key="s.id">
          <span class="idx">{{ i + 1 }}</span>
          <input v-model="s.name" class="input" @change="save(s)" />
          <button class="btn btn-ghost btn-sm" type="button" @click="remove(s)">Archive</button>
        </article>
      </div>

      <EmptyPanel
        v-else
        :image="STATIONS_PHOTO"
        title="No stations yet"
        body="Without stations, the kitchen board shows every ticket in one stream. Add lines to route work."
      >
        <template #icon>
          <PanelsTopLeft :size="32" :stroke-width="1.6" />
        </template>
      </EmptyPanel>
    </section>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { PanelsTopLeft } from '@lucide/vue'
import { api } from '../api'
import { STATIONS_PHOTO } from '../composables/useFoodImage'
import EmptyPanel from './EmptyPanel.vue'
import PageHero from './PageHero.vue'

const stations = ref([])
const name = ref('')

async function load() {
  const data = await api.get('/api/stations')
  stations.value = data.stations || []
}
async function add() {
  await api.post('/api/stations', { name: name.value })
  name.value = ''
  await load()
}
async function save(s) {
  await api.put(`/api/stations/${s.id}`, { name: s.name })
}
async function remove(s) {
  if (!confirm(`Archive ${s.name}?`)) return
  await api.delete(`/api/stations/${s.id}`)
  await load()
}
onMounted(load)
</script>

<style scoped>
.stations {
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
  max-width: 880px;
  animation: rise 0.35s ease;
}
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 1.15rem 1.2rem;
  box-shadow: var(--shadow);
}
.add {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 0.55rem;
  margin-bottom: 1rem;
}
.list {
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
}
article {
  display: grid;
  grid-template-columns: 36px 1fr auto;
  gap: 0.55rem;
  align-items: center;
}
.idx {
  width: 36px;
  height: 36px;
  border-radius: var(--radius);
  display: grid;
  place-items: center;
  background: var(--accent-muted);
  color: var(--accent);
  font-weight: 800;
  font-size: 0.85rem;
}
@keyframes rise {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: none; }
}
</style>
