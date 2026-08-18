<template>
  <div class="menu-admin">
    <div class="section-head">
      <div>
        <h2 class="page-title">Menu</h2>
        <p class="page-sub">Manage categories and dishes for the guest QR menu.</p>
      </div>
    </div>

    <p v-if="error" class="error-text">{{ error }}</p>

    <div class="cols">
      <section class="block">
        <h3>Categories</h3>
        <form class="add-row" @submit.prevent="addCategory">
          <input v-model="newCategory" class="input" placeholder="New category" required />
          <button class="btn btn-sm" type="submit">Add</button>
        </form>
        <ul class="plain-list">
          <li v-for="c in categories" :key="c.id">
            <span>{{ c.name }}</span>
            <button class="linkish" type="button" @click="removeCategory(c)">Remove</button>
          </li>
        </ul>
      </section>

      <section class="block">
        <h3>Items</h3>
        <form class="stack form" @submit.prevent="addItem">
          <input v-model="form.name" class="input" placeholder="Item name" required />
          <textarea v-model="form.description" class="textarea" rows="2" placeholder="Short description" />
          <input v-model="form.image_url" class="input" type="url" placeholder="Image URL" />
          <div class="row">
            <input v-model.number="form.price" class="input" type="number" min="0" step="0.01" placeholder="Price" required />
            <select v-model="form.category_id" class="select">
              <option value="">No category</option>
              <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.name }}</option>
            </select>
          </div>
          <label class="check">
            <input v-model="form.available" type="checkbox" /> Available
          </label>
          <button class="btn btn-sm" type="submit">Add item</button>
        </form>

        <ul class="item-list">
          <li v-for="item in items" :key="item.id">
            <div class="thumb" :style="thumbStyle(item)">
              <span v-if="!item.image_url">{{ (item.name || '?')[0] }}</span>
            </div>
            <div class="info">
              <div class="title-line">
                <strong>{{ item.name }}</strong>
                <span>${{ Number(item.price).toFixed(2) }}</span>
              </div>
              <p class="muted">{{ item.description || '—' }}</p>
              <div class="row actions">
                <span class="badge" :class="item.available ? 'badge-ready' : 'badge-cancelled'">
                  {{ item.available ? 'Available' : 'Unavailable' }}
                </span>
                <button class="linkish" type="button" @click="editImage(item)">Image</button>
                <button class="linkish" type="button" @click="toggleAvailable(item)">
                  {{ item.available ? 'Disable' : 'Enable' }}
                </button>
                <button class="linkish danger" type="button" @click="removeItem(item)">Delete</button>
              </div>
            </div>
          </li>
        </ul>
      </section>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { api } from '../api'

const categories = ref([])
const items = ref([])
const newCategory = ref('')
const error = ref('')
const form = reactive({
  name: '',
  description: '',
  image_url: '',
  price: 0,
  category_id: '',
  available: true,
})

function thumbStyle(item) {
  if (!item.image_url) return {}
  return { backgroundImage: `url(${JSON.stringify(item.image_url).slice(1, -1)})` }
}

async function load() {
  const data = await api.get('/api/menu/admin')
  categories.value = data.categories || []
  items.value = data.items || []
}
async function addCategory() {
  error.value = ''
  try {
    await api.post('/api/menu/categories', { name: newCategory.value })
    newCategory.value = ''
    await load()
  } catch (e) {
    error.value = e.message
  }
}
async function removeCategory(c) {
  if (!confirm(`Delete category “${c.name}”?`)) return
  await api.delete(`/api/menu/categories/${c.id}`)
  await load()
}
async function addItem() {
  error.value = ''
  try {
    await api.post('/api/menu/items', { ...form })
    form.name = ''
    form.description = ''
    form.image_url = ''
    form.price = 0
    form.category_id = ''
    form.available = true
    await load()
  } catch (e) {
    error.value = e.message
  }
}
async function editImage(item) {
  const raw = prompt('Image URL', item.image_url || '')
  if (raw == null) return
  try {
    await api.put(`/api/menu/items/${item.id}`, { image_url: raw.trim(), version: item.version })
    await load()
  } catch (e) {
    error.value = e.message
    await load()
  }
}
async function toggleAvailable(item) {
  try {
    await api.put(`/api/menu/items/${item.id}`, { available: !item.available, version: item.version })
    await load()
  } catch (e) {
    error.value = e.message
    await load()
  }
}
async function removeItem(item) {
  if (!confirm(`Delete “${item.name}”?`)) return
  await api.delete(`/api/menu/items/${item.id}`)
  await load()
}

onMounted(async () => {
  try { await load() } catch (e) { error.value = e.message }
})
</script>

<style scoped>
.menu-admin {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 1.25rem 1.25rem 1.5rem;
  box-shadow: 0 14px 30px rgba(20, 16, 10, 0.05);
}
.cols {
  display: grid;
  grid-template-columns: 0.9fr 1.4fr;
  gap: 1.5rem;
}
.block h3 {
  margin: 0 0 0.85rem;
  font-size: 0.72rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  font-family: var(--font-body);
  font-weight: 600;
  color: var(--muted);
}
.add-row {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}
.plain-list,
.item-list {
  list-style: none;
  margin: 0;
  padding: 0;
  border-top: 1px solid var(--line);
}
.plain-list li,
.item-list li {
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.7rem 0;
  border-bottom: 1px solid var(--line);
}
.item-list li {
  display: grid;
  grid-template-columns: 56px 1fr;
  align-items: start;
}
.thumb {
  width: 56px;
  height: 56px;
  border-radius: 4px;
  background: var(--surface) center/cover no-repeat;
  display: grid;
  place-items: center;
  color: var(--muted);
  font-weight: 600;
}
.info .title-line {
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
}
.info p { margin: 0.2rem 0 0.45rem; }
.actions { gap: 0.65rem; }
.linkish {
  border: 0;
  background: transparent;
  padding: 0;
  color: var(--ink);
  font: inherit;
  font-size: 0.8rem;
  text-decoration: underline;
  cursor: pointer;
}
.linkish.danger { color: var(--danger); }
.check {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  font-size: 0.875rem;
}
.form .input,
.form .textarea,
.form .select { max-width: 100%; }
@media (max-width: 800px) {
  .cols { grid-template-columns: 1fr; }
}
</style>
