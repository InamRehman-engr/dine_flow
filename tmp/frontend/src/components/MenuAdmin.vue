<template>
  <div class="menu-page">
    <PageHero
      :image="MENU_PHOTO"
      eyebrow="Catalog"
      title="Menu"
      subtitle="Photo-first dishes for the guest QR experience — categories, prices, and availability."
    >
      <template #actions>
        <button class="hero-btn" type="button" @click="startNew">+ New item</button>
      </template>
    </PageHero>

    <div class="catalog">
    <aside class="side">
      <header>
        <h2>Categories</h2>
      </header>
      <form class="add-cat" @submit.prevent="addCategory">
        <input v-model="catName" class="input" placeholder="New category" required />
        <button class="btn" type="submit">Add</button>
      </form>
      <ul>
        <li v-for="c in categories" :key="c.id">
          <span>{{ c.name }}</span>
          <button type="button" class="x" @click="removeCategory(c)">Remove</button>
        </li>
      </ul>
      <p v-if="!categories.length" class="muted">No categories yet.</p>
    </aside>

    <section class="main">
      <header class="main-head">
        <div>
          <h2>Items · {{ items.length }}</h2>
          <p class="muted">Guest-facing catalog</p>
        </div>
        <button class="btn" type="button" @click="startNew">+ New item</button>
      </header>

      <div v-if="items.length" class="grid">
        <article v-for="item in items" :key="item.id" class="card">
          <div class="thumb">
            <img :src="foodImage(item)" :alt="item.name" loading="lazy" />
            <span class="avail" :data-on="item.available">{{ item.available ? 'Live' : '86’d' }}</span>
          </div>
          <div class="body">
            <h3>{{ item.name }}</h3>
            <p>{{ formatMoney(item.price) }}</p>
            <div class="actions">
              <button type="button" @click="edit(item)">Edit</button>
              <button type="button" @click="toggleAvail(item)">{{ item.available ? '86' : 'Restore' }}</button>
              <button type="button" class="danger" @click="archive(item)">Archive</button>
            </div>
          </div>
        </article>
      </div>
      <EmptyPanel
        v-else
        :image="MENU_PHOTO"
        title="No menu items yet"
        body="Add your first dish with a photo, price, and kitchen station."
      >
        <template #actions>
          <button class="btn" type="button" @click="startNew">Create first dish</button>
        </template>
      </EmptyPanel>
    </section>
    </div>

    <div v-if="editing" class="sheet-scrim" @click.self="editing = false">
      <div class="sheet">
        <header>
          <h2>{{ form.id ? 'Edit item' : 'New item' }}</h2>
          <button type="button" class="x" @click="editing = false">Close</button>
        </header>
        <form class="stack" @submit.prevent="saveItem">
          <div class="row2">
            <div>
              <label class="label">Name</label>
              <input v-model="form.name" class="input" required />
            </div>
            <div>
              <label class="label">Price ({{ currency }})</label>
              <input v-model.number="form.price" class="input" type="number" min="0" step="1" required />
            </div>
          </div>
          <div>
            <label class="label">Description</label>
            <textarea v-model="form.description" class="textarea" />
          </div>
          <div class="row2">
            <div>
              <label class="label">Category</label>
              <select v-model="form.category_id" class="select">
                <option value="">None</option>
                <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.name }}</option>
              </select>
            </div>
            <div>
              <label class="label">Station</label>
              <select v-model="form.station_id" class="select">
                <option value="">Any</option>
                <option v-for="s in stations" :key="s.id" :value="s.id">{{ s.name }}</option>
              </select>
            </div>
          </div>
          <div>
            <label class="label">Image URL</label>
            <input v-model="form.image_url" class="input" placeholder="https://…" />
          </div>
          <div>
            <label class="label">Or upload</label>
            <input type="file" accept="image/*" @change="onUpload" />
          </div>
          <label class="check"><input v-model="form.available" type="checkbox" /> Available</label>

          <div v-if="form.id" class="mods">
            <h3>Modifiers</h3>
            <div v-for="g in form.modifier_groups || []" :key="g.id" class="mod-block">
              <div class="mod-head">
                <strong>{{ g.name }}</strong>
                <button type="button" class="x" @click="deleteGroup(g)">Remove group</button>
              </div>
              <ul>
                <li v-for="m in g.modifiers" :key="m.id">
                  {{ m.name }} (+{{ formatMoney(m.price_delta) }})
                  <button type="button" class="x" @click="deleteMod(m)">×</button>
                </li>
              </ul>
              <form class="row" @submit.prevent="addMod(g)">
                <input v-model="modDraft[g.id].name" class="input" placeholder="Option" required />
                <input v-model.number="modDraft[g.id].price_delta" class="input" type="number" placeholder="+price" />
                <button class="btn btn-ghost btn-sm" type="submit">Add</button>
              </form>
            </div>
            <form class="row" @submit.prevent="addGroup">
              <input v-model="groupName" class="input" placeholder="New group e.g. Size" required />
              <label class="check"><input v-model="groupRequired" type="checkbox" /> Required</label>
              <button class="btn btn-ghost btn-sm" type="submit">Add group</button>
            </form>
          </div>

          <p v-if="error" class="error-text">{{ error }}</p>
          <div class="row">
            <button class="btn" type="submit">{{ form.id ? 'Save changes' : 'Create item' }}</button>
            <button class="btn btn-ghost" type="button" @click="editing = false">Cancel</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { api } from '../api'
import { foodImage, MENU_PHOTO } from '../composables/useFoodImage'
import { useMoney } from '../composables/useMoney'
import EmptyPanel from './EmptyPanel.vue'
import PageHero from './PageHero.vue'

const { currency, formatMoney, loadConfig } = useMoney()
const categories = ref([])
const items = ref([])
const stations = ref([])
const catName = ref('')
const editing = ref(false)
const error = ref('')
const groupName = ref('')
const groupRequired = ref(false)
const modDraft = reactive({})

const form = reactive({
  id: null,
  name: '',
  price: 0,
  description: '',
  category_id: '',
  station_id: '',
  image_url: '',
  available: true,
  version: 1,
  modifier_groups: [],
})

async function load() {
  const [menu, st] = await Promise.all([api.get('/api/menu/admin'), api.get('/api/stations')])
  categories.value = menu.categories || []
  items.value = menu.items || []
  stations.value = st.stations || []
}

function startNew() {
  Object.assign(form, {
    id: null,
    name: '',
    price: 0,
    description: '',
    category_id: '',
    station_id: '',
    image_url: '',
    available: true,
    version: 1,
    modifier_groups: [],
  })
  editing.value = true
  error.value = ''
}

function edit(item) {
  Object.assign(form, {
    id: item.id,
    name: item.name,
    price: item.price,
    description: item.description || '',
    category_id: item.category_id || '',
    station_id: item.station_id || '',
    image_url: item.image_url || '',
    available: item.available,
    version: item.version,
    modifier_groups: item.modifier_groups || [],
  })
  for (const g of form.modifier_groups) {
    modDraft[g.id] = { name: '', price_delta: 0 }
  }
  editing.value = true
  error.value = ''
}

async function saveItem() {
  error.value = ''
  const body = {
    name: form.name,
    price: form.price,
    description: form.description,
    category_id: form.category_id || null,
    station_id: form.station_id || null,
    image_url: form.image_url || null,
    available: form.available,
    version: form.version,
  }
  try {
    if (form.id) {
      const data = await api.put(`/api/menu/items/${form.id}`, body)
      Object.assign(form, { ...data.item, modifier_groups: data.item.modifier_groups || [] })
    } else {
      const data = await api.post('/api/menu/items', body)
      Object.assign(form, { ...data.item, modifier_groups: [] })
    }
    await load()
    if (!form.id) editing.value = false
  } catch (e) {
    error.value = e.message
  }
}

async function onUpload(e) {
  const file = e.target.files?.[0]
  if (!file) return
  const fd = new FormData()
  fd.append('file', file)
  try {
    const data = await api.upload('/api/media/upload', fd)
    form.image_url = data.url
  } catch (err) {
    error.value = err.message
  }
}

async function addCategory() {
  await api.post('/api/menu/categories', { name: catName.value })
  catName.value = ''
  await load()
}

async function removeCategory(c) {
  if (!confirm(`Archive ${c.name}?`)) return
  await api.delete(`/api/menu/categories/${c.id}`)
  await load()
}

async function toggleAvail(item) {
  await api.put(`/api/menu/items/${item.id}`, { available: !item.available, version: item.version })
  await load()
}

async function archive(item) {
  if (!confirm(`Archive ${item.name}?`)) return
  await api.delete(`/api/menu/items/${item.id}`)
  await load()
}

async function addGroup() {
  if (!form.id) return
  const data = await api.post(`/api/menu/items/${form.id}/modifier-groups`, {
    name: groupName.value,
    required: groupRequired.value,
    max_select: 1,
  })
  form.modifier_groups = [...(form.modifier_groups || []), data.group]
  modDraft[data.group.id] = { name: '', price_delta: 0 }
  groupName.value = ''
  groupRequired.value = false
  await load()
}

async function deleteGroup(g) {
  await api.delete(`/api/menu/modifier-groups/${g.id}`)
  form.modifier_groups = form.modifier_groups.filter((x) => x.id !== g.id)
  await load()
}

async function addMod(g) {
  const draft = modDraft[g.id] || { name: '', price_delta: 0 }
  const data = await api.post(`/api/menu/modifier-groups/${g.id}/modifiers`, {
    name: draft.name,
    price_delta: draft.price_delta || 0,
  })
  g.modifiers = [...(g.modifiers || []), data.modifier]
  modDraft[g.id] = { name: '', price_delta: 0 }
  await load()
}

async function deleteMod(m) {
  await api.delete(`/api/menu/modifiers/${m.id}`)
  for (const g of form.modifier_groups) {
    g.modifiers = (g.modifiers || []).filter((x) => x.id !== m.id)
  }
  await load()
}

onMounted(async () => {
  await loadConfig()
  await load()
})
</script>

<style scoped>
.menu-page {
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
}
.hero-btn {
  border: 1px solid rgba(255, 255, 255, 0.35);
  background: rgba(255, 255, 255, 0.14);
  color: #fff;
  border-radius: var(--radius);
  min-height: 36px;
  padding: 0.35rem 0.85rem;
  font: inherit;
  font-weight: 650;
  font-size: 0.82rem;
  cursor: pointer;
}
.catalog {
  display: grid;
  grid-template-columns: minmax(220px, 260px) 1fr;
  gap: 1rem;
  align-items: start;
  animation: rise 0.35s ease;
}
.side,
.main {
  background: #fff;
  border: 1px solid #dbe3ec;
  border-radius: 22px;
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.05);
}
.side {
  padding: 1.1rem 1.15rem 1.25rem;
  position: sticky;
  top: 5.5rem;
}
.side header h2,
.main-head h2 {
  margin: 0;
  font-size: 1.05rem;
}
.add-cat {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 0.4rem;
  margin: 0.85rem 0 1rem;
}
.side ul {
  list-style: none;
  margin: 0;
  padding: 0;
}
.side li {
  display: flex;
  justify-content: space-between;
  gap: 0.5rem;
  padding: 0.65rem 0;
  border-bottom: 1px solid #eef2f6;
  font-weight: 600;
  font-size: 0.92rem;
}
.x {
  border: 0;
  background: transparent;
  color: #94a3b8;
  font: inherit;
  font-weight: 700;
  cursor: pointer;
}
.x:hover { color: #dc2626; }
.main {
  padding: 1.1rem 1.15rem 1.35rem;
  min-height: 480px;
}
.main-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  margin-bottom: 1rem;
}
.main-head .muted {
  margin: 0.25rem 0 0;
  font-size: 0.85rem;
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 0.85rem;
}
.card {
  border: 1px solid #e8eef4;
  border-radius: 18px;
  overflow: hidden;
  background: #fff;
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}
.card:hover {
  transform: translateY(-3px);
  box-shadow: 0 14px 28px rgba(15, 23, 42, 0.1);
}
.thumb {
  position: relative;
  aspect-ratio: 1;
  background: #f1f5f9;
}
.thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.avail {
  position: absolute;
  top: 0.55rem;
  left: 0.55rem;
  font-size: 0.68rem;
  font-weight: 800;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  padding: 0.25rem 0.5rem;
  border-radius: 999px;
  background: #fee2e2;
  color: #b91c1c;
}
.avail[data-on='true'] {
  background: #ccfbf1;
  color: #0f766e;
}
.body {
  padding: 0.75rem 0.8rem 0.9rem;
}
.body h3 {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 700;
  line-height: 1.25;
}
.body > p {
  margin: 0.3rem 0 0.65rem;
  font-weight: 750;
  color: #0f766e;
}
.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
}
.actions button {
  border: 1px solid #dbe3ec;
  background: #f8fafc;
  border-radius: 999px;
  padding: 0.3rem 0.65rem;
  font: inherit;
  font-size: 0.75rem;
  font-weight: 700;
  cursor: pointer;
  color: #334155;
}
.actions .danger { color: #dc2626; border-color: #fecaca; }
.empty {
  text-align: center;
  color: #94a3b8;
  padding: 3rem 1rem;
  font-weight: 600;
}
.sheet-scrim {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  z-index: 60;
  display: grid;
  justify-items: end;
  animation: rise 0.2s ease;
}
.sheet {
  width: min(480px, 100%);
  height: 100%;
  background: #fff;
  overflow: auto;
  padding: 1.25rem 1.25rem 2rem;
  box-shadow: -20px 0 50px rgba(15, 23, 42, 0.2);
  animation: slide 0.32s cubic-bezier(0.22, 1, 0.36, 1);
}
.sheet header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}
.sheet h2 { margin: 0; font-size: 1.2rem; }
.stack { display: flex; flex-direction: column; gap: 0.85rem; }
.row2 { display: grid; grid-template-columns: 1fr 1fr; gap: 0.65rem; }
.row { display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center; }
.check { display: inline-flex; gap: 0.4rem; align-items: center; font-weight: 650; }
.mods { margin-top: 0.35rem; }
.mod-block { padding: 0.75rem 0; border-top: 1px solid #eef2f6; }
.mod-head { display: flex; justify-content: space-between; margin-bottom: 0.35rem; }
.mod-block ul { margin: 0.35rem 0; padding-left: 1rem; }

@keyframes rise {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: none; }
}
@keyframes slide {
  from { transform: translateX(40px); opacity: 0.6; }
  to { transform: none; opacity: 1; }
}

@media (max-width: 900px) {
  .catalog { grid-template-columns: 1fr; }
  .side { position: static; }
  .row2 { grid-template-columns: 1fr; }
}
</style>
