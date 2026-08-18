<template>
  <div class="floor">
    <PageHero
      :image="FLOOR_PHOTO"
      eyebrow="Operations"
      title="Live floor"
      subtitle="See occupancy, kitchen status, and waiter requests on the map — at a glance."
    >
      <template #aside>
        <div class="pulse-strip" aria-label="Floor summary">
          <span class="pulse-item"><i class="dot free" /> {{ freeCount }} free</span>
          <span class="pulse-item"><i class="dot occ" /> {{ occupiedCount }} occupied</span>
          <span class="pulse-item"><i class="dot waiter" /> {{ alertCount }} waiter</span>
          <span class="pulse-item"><i class="dot ticket" /> {{ openOrders.length }} tickets</span>
        </div>
      </template>
    </PageHero>

    <section class="theater">
      <header class="theater-bar">
        <div class="floors">
          <button
            v-for="f in floors"
            :key="f.id"
            type="button"
            class="floor-tab"
            :class="{ active: f.id === activeFloorId }"
            @click="selectFloor(f.id)"
          >
            {{ f.name }}
          </button>
          <button v-if="!editing" class="ghost" type="button" @click="addFloor">
            <Plus :size="14" :stroke-width="2.4" />
            Floor
          </button>
        </div>
        <div class="tools">
          <p class="hint">{{ stepHint }}</p>
          <template v-if="!editing">
            <button class="primary" type="button" @click="startEdit">
              <Pencil :size="15" :stroke-width="2" />
              {{ hasLayout ? 'Edit layout' : 'Create layout' }}
            </button>
          </template>
          <template v-else>
            <div class="phase">
              <button type="button" :class="{ on: editPhase === 'boundary' }" @click="editPhase = 'boundary'">
                1 · Room
              </button>
              <button
                type="button"
                :disabled="draftBoundary.length < 3"
                :class="{ on: editPhase === 'tables' }"
                @click="editPhase = 'tables'"
              >
                2 · Tables
              </button>
            </div>
            <button v-if="editPhase === 'boundary'" class="ghost" type="button" @click="undoPoint">Undo</button>
            <button v-if="editPhase === 'boundary'" class="ghost" type="button" @click="draftBoundary = []">
              Clear
            </button>
            <button v-if="editPhase === 'tables'" class="ghost" type="button" @click="addTable">
              <Plus :size="14" :stroke-width="2.4" />
              Table
            </button>
            <button
              v-if="editPhase === 'tables' && selectedId"
              class="ghost"
              type="button"
              @click="cycleCapacity"
            >
              Shape
            </button>
            <button
              v-if="editPhase === 'tables' && selectedId"
              class="ghost danger"
              type="button"
              @click="removeSelected"
            >
              Remove
            </button>
            <button class="ghost" type="button" @click="cancelEdit">Cancel</button>
            <button class="primary" type="button" :disabled="saving" @click="finishLayout">
              {{ saving ? 'Saving…' : 'Save layout' }}
            </button>
          </template>
        </div>
      </header>

      <p v-if="error" class="err">{{ error }}</p>
      <p v-if="snapHint" class="snap">{{ snapHint }}</p>

      <div class="stage-grid" :class="{ 'has-drawer': !!drawerTable }">
        <div
          ref="canvasRef"
          class="canvas"
          :class="{ editing, drawing: editing && editPhase === 'boundary' }"
          @pointerdown="onCanvasPointerDown"
          @pointermove="onCanvasPointerMove"
          @pointerup="onCanvasPointerUp"
          @pointerleave="onCanvasPointerUp"
        >
          <div class="canvas-atmosphere" aria-hidden="true">
            <div class="photo" :style="{ backgroundImage: `url(${FLOOR_PHOTO})` }" />
            <div class="base" />
            <div class="grid" />
          </div>

          <svg class="boundary-svg" viewBox="0 0 100 100" preserveAspectRatio="none">
            <polygon
              v-if="displayBoundary.length >= 3"
              :points="boundaryPointsAttr"
              class="boundary-fill"
            />
            <polyline
              v-if="displayBoundary.length >= 2"
              :points="boundaryStrokeAttr"
              class="boundary-stroke"
              fill="none"
            />
            <circle
              v-for="(p, i) in displayBoundary"
              :key="i"
              :cx="p.x"
              :cy="p.y"
              r="1.1"
              class="boundary-vertex"
              :class="{ first: i === 0 }"
            />
          </svg>

          <button
            v-for="t in displayTables"
            :key="t._key"
            type="button"
            class="table-node"
            :class="[
              `shape-${tableShape(t)}`,
              `state-${tableState(t)}`,
              { selected: selectedId === t._key || drawerTable?._key === t._key, editing },
            ]"
            :style="{ left: t.pos_x + '%', top: t.pos_y + '%' }"
            :aria-label="`Table ${t.number}, ${stateLabel(tableState(t))}`"
            @pointerdown.stop="onTablePointerDown($event, t)"
            @dblclick.stop="renameTable(t)"
            @click.stop="openDrawer(t)"
          >
            <svg v-if="tableShape(t) === 'round'" class="table-svg" viewBox="0 0 96 96" aria-hidden="true">
              <ellipse class="shadow" cx="48" cy="78" rx="28" ry="7" />
              <circle class="seat" cx="48" cy="14" r="7" />
              <circle class="seat" cx="82" cy="48" r="7" />
              <circle class="seat" cx="48" cy="82" r="7" />
              <circle class="seat" cx="14" cy="48" r="7" />
              <circle class="top" cx="48" cy="48" r="26" />
              <circle class="inner" cx="48" cy="48" r="16" />
            </svg>
            <svg v-else-if="tableShape(t) === 'square'" class="table-svg" viewBox="0 0 96 96" aria-hidden="true">
              <ellipse class="shadow" cx="48" cy="80" rx="26" ry="6" />
              <rect class="seat" x="38" y="6" width="20" height="12" rx="5" />
              <rect class="seat" x="78" y="38" width="12" height="20" rx="5" />
              <rect class="seat" x="38" y="78" width="20" height="12" rx="5" />
              <rect class="seat" x="6" y="38" width="12" height="20" rx="5" />
              <rect class="top" x="22" y="22" width="52" height="52" rx="10" />
              <rect class="inner" x="32" y="32" width="32" height="32" rx="6" />
            </svg>
            <svg v-else class="table-svg" viewBox="0 0 120 80" aria-hidden="true">
              <ellipse class="shadow" cx="60" cy="68" rx="40" ry="6" />
              <rect class="seat" x="18" y="4" width="18" height="11" rx="5" />
              <rect class="seat" x="52" y="4" width="18" height="11" rx="5" />
              <rect class="seat" x="86" y="4" width="18" height="11" rx="5" />
              <rect class="seat" x="18" y="65" width="18" height="11" rx="5" />
              <rect class="seat" x="52" y="65" width="18" height="11" rx="5" />
              <rect class="seat" x="86" y="65" width="18" height="11" rx="5" />
              <rect class="top" x="12" y="18" width="96" height="44" rx="10" />
              <rect class="inner" x="24" y="28" width="72" height="24" rx="6" />
            </svg>

            <span class="num">{{ t.number }}</span>
            <span class="cap">{{ t.capacity || 4 }}</span>
            <span v-if="t.open_ticket_count" class="badge">{{ t.open_ticket_count }}</span>
            <span class="state-chip">{{ stateLabel(tableState(t)) }}</span>
          </button>

          <div v-if="!displayTables.length && !editing" class="empty-floor-wrap">
            <EmptyPanel
              :image="EMPTY_FLOOR_PHOTO"
              title="Your floor is ready to be designed"
              body="Draw the room, place tables, and start taking live orders from QR menus."
            >
              <template #icon>
                <LayoutGrid :size="36" :stroke-width="1.6" />
              </template>
              <template #actions>
                <button class="primary" type="button" @click="startEdit">Create your first table</button>
              </template>
            </EmptyPanel>
          </div>

          <p v-if="editing && editPhase === 'boundary' && !draftBoundary.length" class="guide">
            Click to draw the room outline. Snap to the first point to close.
          </p>

          <div class="legend">
            <span><i class="dot free" /> Available</span>
            <span><i class="dot pending" /> Pending</span>
            <span><i class="dot preparing" /> Preparing</span>
            <span><i class="dot ready" /> Ready</span>
            <span><i class="dot waiter" /> Waiter</span>
          </div>
        </div>

        <aside v-if="drawerTable" class="inspector">
          <header>
            <div>
              <p class="eyebrow">Table</p>
              <h3>{{ drawerTable.number }}</h3>
            </div>
            <button class="icon-close" type="button" aria-label="Close" @click="drawerTable = null">
              <X :size="18" :stroke-width="2" />
            </button>
          </header>

          <div class="status-line">
            <span class="pill" :data-state="tableState(drawerTable)">{{ stateLabel(tableState(drawerTable)) }}</span>
            <span class="pill muted">{{ drawerTable.capacity || 4 }} seats</span>
            <span v-if="drawerTable.open_ticket_count" class="pill muted">
              {{ drawerTable.open_ticket_count }} open
            </span>
          </div>

          <p v-if="drawerTable.waiter_alert" class="waiter-flag">
            <Bell :size="16" :stroke-width="2.25" />
            Waiter requested
          </p>

          <h4>Open orders</h4>
          <ul v-if="tableOrders.length">
            <li v-for="o in tableOrders" :key="o.id">
              <div class="order-top">
                <span class="st" :data-status="o.status">{{ o.status }}</span>
                <small>{{ formatTime(o.created_at) }}</small>
              </div>
              <p>{{ o.items?.map((i) => `${i.quantity}× ${i.name}`).join(', ') }}</p>
              <em v-if="o.notes">{{ o.notes }}</em>
            </li>
          </ul>
          <p v-else class="empty">No open orders on this table.</p>

          <div class="inspector-actions">
            <router-link class="action" :to="{ path: '/admin/orders' }">
              <ClipboardList :size="16" :stroke-width="2" />
              View orders
            </router-link>
            <router-link class="action" to="/admin/qrs">
              <QrCode :size="16" :stroke-width="2" />
              QR codes
            </router-link>
          </div>
        </aside>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { Bell, ClipboardList, LayoutGrid, Pencil, Plus, QrCode, X } from '@lucide/vue'
import { api } from '../api'
import { EMPTY_FLOOR_PHOTO, FLOOR_PHOTO } from '../composables/useFoodImage'
import { useSocket } from '../composables/useSocket'
import EmptyPanel from './EmptyPanel.vue'
import PageHero from './PageHero.vue'

defineProps({ tenant: { type: Object, default: null } })
const emit = defineEmits(['refresh-alerts'])

const canvasRef = ref(null)
const floors = ref([])
const activeFloorId = ref(null)
const tables = ref([])
const boundary = ref([])
const openOrders = ref([])
const error = ref('')
const saving = ref(false)
const snapHint = ref('')
const editing = ref(false)
const editPhase = ref('boundary')
const draftBoundary = ref([])
const draftTables = ref([])
const selectedId = ref(null)
const dragKey = ref(null)
const dragOffset = ref({ x: 0, y: 0 })
const drawerTable = ref(null)
let localId = 0
const SNAP = 2.5

const hasLayout = computed(() => boundary.value.length >= 3 || tables.value.length > 0)
const stepHint = computed(() => {
  if (!editing.value) return 'Select a table · Status shows live kitchen + waiter needs'
  if (editPhase.value === 'boundary') return 'Draw the room, then snap closed'
  return 'Drag tables · Shape cycles capacity · Double-click to renumber'
})
const displayBoundary = computed(() => (editing.value ? draftBoundary.value : boundary.value))
const displayTables = computed(() =>
  editing.value ? draftTables.value : tables.value.map((t) => ({ ...t, _key: t.id })),
)
const boundaryPointsAttr = computed(() => displayBoundary.value.map((p) => `${p.x},${p.y}`).join(' '))
const boundaryStrokeAttr = computed(() => {
  const pts = displayBoundary.value
  if (pts.length < 2) return ''
  const closed = pts.length >= 3 ? [...pts, pts[0]] : pts
  return closed.map((p) => `${p.x},${p.y}`).join(' ')
})
const tableOrders = computed(() => {
  if (!drawerTable.value) return []
  return openOrders.value.filter((o) => o.table_number === drawerTable.value.number)
})
const freeCount = computed(() => tables.value.filter((t) => t.occupancy !== 'occupied').length)
const occupiedCount = computed(() => tables.value.filter((t) => t.occupancy === 'occupied').length)
const alertCount = computed(() => tables.value.filter((t) => t.waiter_alert).length)

function tableOrdersFor(t) {
  return openOrders.value.filter((o) => o.table_number === t.number)
}

function tableState(t) {
  if (t.waiter_alert) return 'waiter'
  const orders = tableOrdersFor(t)
  if (!orders.length) return t.occupancy === 'occupied' ? 'occupied' : 'available'
  if (orders.some((o) => o.status === 'ready')) return 'ready'
  if (orders.some((o) => o.status === 'preparing')) return 'preparing'
  if (orders.some((o) => o.status === 'pending')) return 'pending'
  return 'occupied'
}

function stateLabel(state) {
  return (
    {
      available: 'Available',
      occupied: 'Occupied',
      pending: 'Order pending',
      preparing: 'Preparing',
      ready: 'Ready',
      waiter: 'Waiter',
    }[state] || state
  )
}

function tableShape(t) {
  const c = Number(t.capacity) || 4
  if (c <= 2) return 'square'
  if (c >= 6) return 'rect'
  return 'round'
}

function formatTime(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function pctFromEvent(e) {
  const el = canvasRef.value
  if (!el) return { x: 0, y: 0 }
  const rect = el.getBoundingClientRect()
  return {
    x: Math.max(0, Math.min(100, ((e.clientX - rect.left) / rect.width) * 100)),
    y: Math.max(0, Math.min(100, ((e.clientY - rect.top) / rect.height) * 100)),
  }
}
function dist(a, b) {
  return Math.hypot(a.x - b.x, a.y - b.y)
}
function nextNumber(list) {
  const used = new Set(list.map((t) => t.number))
  let n = 1
  while (used.has(n)) n += 1
  return n
}

async function load() {
  error.value = ''
  try {
    const q = activeFloorId.value ? `?floor_id=${activeFloorId.value}` : ''
    const status = await api.get(`/api/tenant/floor-status${q}`)
    floors.value = status.floors || []
    if (!activeFloorId.value && floors.value[0]) activeFloorId.value = floors.value[0].id
    boundary.value = status.floor_boundary || status.floor?.boundary || []
    tables.value = status.tables || []
    openOrders.value = status.open_orders || []
    if (drawerTable.value) {
      const match = tables.value.find((t) => t.id === drawerTable.value.id || t.number === drawerTable.value.number)
      drawerTable.value = match ? { ...match, _key: match.id } : null
    }
  } catch (e) {
    error.value = e.message
  }
}
function selectFloor(id) {
  if (editing.value) return
  activeFloorId.value = id
  drawerTable.value = null
  load()
}
async function addFloor() {
  const name = prompt('Floor name?', 'Patio')
  if (!name) return
  const data = await api.post('/api/tenant/floors', { name })
  floors.value = [...floors.value, data.floor]
  activeFloorId.value = data.floor.id
  await load()
}
function startEdit() {
  editing.value = true
  draftBoundary.value = boundary.value.map((p) => ({ ...p }))
  draftTables.value = tables.value.map((t) => ({ ...t, _key: t.id || `local-${++localId}` }))
  editPhase.value = draftBoundary.value.length >= 3 ? 'tables' : 'boundary'
  selectedId.value = null
  drawerTable.value = null
  error.value = ''
}
function cancelEdit() {
  editing.value = false
  draftBoundary.value = []
  draftTables.value = []
  selectedId.value = null
  dragKey.value = null
  snapHint.value = ''
}
function undoPoint() {
  draftBoundary.value = draftBoundary.value.slice(0, -1)
}
function onCanvasPointerDown(e) {
  if (!editing.value || editPhase.value !== 'boundary') return
  const p = pctFromEvent(e)
  const first = draftBoundary.value[0]
  if (first && draftBoundary.value.length >= 2 && dist(p, first) <= SNAP) {
    snapHint.value = 'Shape closed'
    setTimeout(() => (snapHint.value = ''), 1200)
    editPhase.value = 'tables'
    return
  }
  draftBoundary.value = [...draftBoundary.value, p]
}
function onTablePointerDown(e, t) {
  if (!editing.value) return
  selectedId.value = t._key
  if (editPhase.value !== 'tables') return
  dragKey.value = t._key
  const p = pctFromEvent(e)
  dragOffset.value = { x: p.x - t.pos_x, y: p.y - t.pos_y }
  e.currentTarget?.setPointerCapture?.(e.pointerId)
}
function onCanvasPointerMove(e) {
  if (editing.value && editPhase.value === 'boundary' && draftBoundary.value[0]) {
    const p = pctFromEvent(e)
    snapHint.value = dist(p, draftBoundary.value[0]) <= SNAP ? 'Close shape' : ''
  }
  if (!dragKey.value) return
  const p = pctFromEvent(e)
  const idx = draftTables.value.findIndex((t) => t._key === dragKey.value)
  if (idx < 0) return
  const next = [...draftTables.value]
  next[idx] = {
    ...next[idx],
    pos_x: Math.max(2, Math.min(98, p.x - dragOffset.value.x)),
    pos_y: Math.max(2, Math.min(98, p.y - dragOffset.value.y)),
  }
  draftTables.value = next
}
function onCanvasPointerUp() {
  dragKey.value = null
}
function addTable() {
  const number = nextNumber(draftTables.value)
  draftTables.value = [
    ...draftTables.value,
    {
      _key: `local-${++localId}`,
      id: null,
      number,
      pos_x: 40 + (draftTables.value.length % 5) * 8,
      pos_y: 35 + Math.floor(draftTables.value.length / 5) * 12,
      capacity: 4,
      occupancy: 'free',
      waiter_alert: false,
      open_ticket_count: 0,
    },
  ]
}
function cycleCapacity() {
  if (!selectedId.value) return
  const idx = draftTables.value.findIndex((t) => t._key === selectedId.value)
  if (idx < 0) return
  const cur = Number(draftTables.value[idx].capacity) || 4
  const nextCap = cur <= 2 ? 4 : cur < 6 ? 6 : 2
  const next = [...draftTables.value]
  next[idx] = { ...next[idx], capacity: nextCap }
  draftTables.value = next
}
function removeSelected() {
  if (!selectedId.value) return
  draftTables.value = draftTables.value.filter((t) => t._key !== selectedId.value)
  selectedId.value = null
}
function renameTable(t) {
  if (!editing.value) return
  const raw = prompt('Table number?', String(t.number))
  if (raw == null) return
  const number = parseInt(raw, 10)
  if (!number || number < 1) {
    error.value = 'Invalid table number'
    return
  }
  if (draftTables.value.some((x) => x._key !== t._key && x.number === number)) {
    error.value = `Table ${number} already exists`
    return
  }
  const idx = draftTables.value.findIndex((x) => x._key === t._key)
  if (idx >= 0) {
    const next = [...draftTables.value]
    next[idx] = { ...next[idx], number }
    draftTables.value = next
  }
}
function openDrawer(t) {
  if (editing.value) return
  drawerTable.value = t
}
async function finishLayout() {
  if (draftBoundary.value.length > 0 && draftBoundary.value.length < 3) {
    error.value = 'Boundary needs at least 3 points'
    return
  }
  if (!draftTables.value.length) {
    error.value = 'Add at least one table before finishing'
    return
  }
  saving.value = true
  error.value = ''
  try {
    const data = await api.put('/api/tenant/layout', {
      floor_id: activeFloorId.value,
      floor_boundary: draftBoundary.value,
      tables: draftTables.value.map((t) => ({
        number: t.number,
        pos_x: t.pos_x,
        pos_y: t.pos_y,
        capacity: t.capacity || 4,
      })),
    })
    boundary.value = data.floor_boundary || []
    tables.value = data.tables || []
    editing.value = false
    await load()
  } catch (e) {
    error.value = e.message
  } finally {
    saving.value = false
  }
}

const { on, joinStaff } = useSocket()
onMounted(async () => {
  joinStaff()
  await load()
  on('floor_refresh', () => {
    if (!editing.value) {
      load()
      emit('refresh-alerts')
    }
  })
  on('new_order', () => {
    if (!editing.value) load()
  })
  on('status_update', () => {
    if (!editing.value) load()
  })
})
</script>

<style scoped>
.floor {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
  animation: rise 0.35s var(--ease);
}

.pulse-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem 0.75rem;
  font-size: 0.78rem;
  font-weight: 650;
  color: rgba(255, 255, 255, 0.9);
  background: rgba(31, 26, 23, 0.35);
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: var(--radius);
  padding: 0.55rem 0.75rem;
  backdrop-filter: blur(6px);
}

.pulse-item {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}
.dot.free { background: var(--tbl-free-stroke); }
.dot.occ { background: var(--tbl-occ); }
.dot.waiter { background: var(--tbl-waiter); }
.dot.ticket { background: var(--tbl-pending); }
.dot.pending { background: var(--tbl-pending); }
.dot.preparing { background: var(--tbl-preparing); }
.dot.ready { background: var(--tbl-ready); }

.theater {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: var(--shadow);
}

.theater-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem 1rem;
  justify-content: space-between;
  align-items: center;
  padding: 0.8rem 1rem;
  border-bottom: 1px solid var(--border);
  background: var(--surface-2);
}

.floors {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  align-items: center;
}

.floor-tab {
  border: 1px solid var(--border-strong);
  background: var(--surface);
  border-radius: var(--radius);
  padding: 0.4rem 0.8rem;
  font: inherit;
  font-weight: 650;
  font-size: 0.82rem;
  cursor: pointer;
  color: var(--muted);
}

.floor-tab.active {
  background: var(--ink);
  border-color: var(--ink);
  color: #fff;
}

.tools {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  align-items: center;
  justify-content: flex-end;
}

.hint {
  margin: 0;
  color: var(--muted);
  font-size: 0.78rem;
  max-width: 280px;
}

.phase {
  display: inline-flex;
  background: var(--surface);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius);
  overflow: hidden;
}

.phase button {
  border: 0;
  background: transparent;
  padding: 0.4rem 0.7rem;
  font: inherit;
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--muted);
  cursor: pointer;
}

.phase button.on {
  background: var(--accent-muted);
  color: var(--accent);
}

.primary,
.ghost {
  border-radius: var(--radius);
  font: inherit;
  font-weight: 700;
  font-size: 0.8rem;
  padding: 0.45rem 0.85rem;
  cursor: pointer;
  min-height: 36px;
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
}

.primary {
  border: 0;
  background: var(--accent);
  color: #fff;
}

.ghost {
  border: 1px solid var(--border-strong);
  background: var(--surface);
  color: var(--ink);
}

.ghost.danger {
  color: var(--danger);
  border-color: var(--danger-border);
}

.err {
  color: var(--danger);
  margin: 0.5rem 1rem 0;
  font-weight: 650;
}
.snap {
  color: var(--accent);
  margin: 0.5rem 1rem 0;
  font-weight: 700;
}

.stage-grid {
  display: grid;
  grid-template-columns: 1fr;
  min-height: 540px;
}
.stage-grid.has-drawer {
  grid-template-columns: 1fr minmax(300px, 340px);
}

.canvas {
  position: relative;
  min-height: 540px;
  height: min(70vh, 720px);
  overflow: hidden;
  touch-action: none;
  user-select: none;
  background: #ebe4db;
}

.canvas-atmosphere {
  position: absolute;
  inset: 0;
  pointer-events: none;
}
.canvas-atmosphere .photo {
  position: absolute;
  inset: 0;
  background-size: cover;
  background-position: center;
  opacity: 0.28;
  filter: saturate(0.85);
}
.canvas-atmosphere .base {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse at 30% 20%, rgba(255, 252, 248, 0.55), transparent 50%),
    linear-gradient(160deg, rgba(240, 233, 224, 0.92) 0%, rgba(229, 221, 210, 0.94) 55%, rgba(221, 212, 200, 0.96) 100%);
}
.canvas-atmosphere .grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(31, 26, 23, 0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(31, 26, 23, 0.04) 1px, transparent 1px);
  background-size: 36px 36px;
}

.canvas.drawing { cursor: crosshair; }

.boundary-svg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}
.boundary-fill {
  fill: rgba(31, 107, 92, 0.08);
}
.boundary-stroke {
  stroke: var(--accent);
  stroke-width: 0.45;
  stroke-linejoin: round;
}
.boundary-vertex { fill: var(--accent); }
.boundary-vertex.first { fill: var(--ink); }

.table-node {
  position: absolute;
  transform: translate(-50%, -50%);
  border: 0;
  background: transparent;
  padding: 0;
  cursor: pointer;
  color: var(--ink);
  transition: transform 0.18s var(--ease);
}
.table-node.shape-round,
.table-node.shape-square { width: 88px; height: 88px; }
.table-node.shape-rect { width: 118px; height: 78px; }
.table-node:hover { transform: translate(-50%, -50%) scale(1.05); }

.table-svg {
  width: 100%;
  height: 100%;
  overflow: visible;
  filter: drop-shadow(0 6px 12px rgba(31, 26, 23, 0.12));
}
.table-svg .shadow { fill: rgba(31, 26, 23, 0.16); }
.table-svg .top { fill: var(--tbl-free); stroke: var(--tbl-free-stroke); stroke-width: 2; }
.table-svg .inner { fill: none; stroke: rgba(31, 26, 23, 0.08); stroke-width: 1.4; }
.table-svg .seat { fill: #e8e0d6; stroke: #fff; stroke-width: 1.4; }

.table-node.state-occupied .table-svg .top { fill: var(--tbl-occ); stroke: #2a8a78; }
.table-node.state-occupied .table-svg .seat { fill: #185749; stroke: #9fd5c8; }
.table-node.state-occupied { color: #f5fffb; }

.table-node.state-pending .table-svg .top { fill: var(--tbl-pending); stroke: #5a8eae; }
.table-node.state-pending .table-svg .seat { fill: #2f5369; stroke: #b5d2e4; }
.table-node.state-pending { color: #f4faff; }

.table-node.state-preparing .table-svg .top { fill: var(--tbl-preparing); stroke: #c9a05a; }
.table-node.state-preparing .table-svg .seat { fill: #8a682c; stroke: #f0dfb8; }
.table-node.state-preparing { color: #fffaf0; }

.table-node.state-ready .table-svg .top { fill: var(--tbl-ready); stroke: #4f9470; }
.table-node.state-ready .table-svg .seat { fill: #24533c; stroke: #b7d9c5; }
.table-node.state-ready { color: #f4fff8; }

.table-node.state-waiter .table-svg .top { fill: var(--tbl-waiter); stroke: #d18aa3; }
.table-node.state-waiter .table-svg .seat { fill: #8a3f59; stroke: #f0c5d3; }
.table-node.state-waiter {
  color: #fff7fa;
  animation: attention 1.2s ease infinite;
}

.table-node.selected::after {
  content: '';
  position: absolute;
  inset: -5px;
  border: 2px solid var(--accent);
  border-radius: 18px;
  pointer-events: none;
}

.num {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  font-weight: 800;
  font-size: 1.15rem;
  letter-spacing: -0.03em;
  pointer-events: none;
  padding-bottom: 10px;
}

.cap {
  position: absolute;
  left: 50%;
  bottom: 18%;
  transform: translateX(-50%);
  font-size: 0.62rem;
  font-weight: 700;
  opacity: 0.75;
  pointer-events: none;
  letter-spacing: 0.04em;
}

.state-chip {
  position: absolute;
  left: 50%;
  bottom: -2px;
  transform: translate(-50%, 100%);
  font-size: 0.58rem;
  font-weight: 750;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  white-space: nowrap;
  color: var(--ink);
  background: rgba(255, 252, 248, 0.92);
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 0.12rem 0.4rem;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.15s ease;
}

.table-node:hover .state-chip,
.table-node.selected .state-chip,
.table-node.state-waiter .state-chip,
.table-node.state-ready .state-chip {
  opacity: 1;
}

.badge {
  position: absolute;
  top: 4px;
  right: 8px;
  min-width: 20px;
  height: 20px;
  border-radius: 999px;
  background: var(--ink);
  color: #fff;
  font-size: 0.68rem;
  font-weight: 800;
  display: grid;
  place-items: center;
  padding: 0 5px;
}

.guide {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  margin: 0;
  color: var(--ink);
  font-weight: 650;
  text-align: center;
  pointer-events: none;
  padding: 2rem;
}
.empty-floor-wrap {
  position: absolute;
  inset: 1rem;
  display: grid;
  place-items: center;
  z-index: 2;
}
.empty-floor-wrap :deep(.empty-panel) {
  width: min(560px, 100%);
  box-shadow: var(--shadow-md);
  background: rgba(255, 252, 248, 0.96);
}

.legend {
  position: absolute;
  left: 0.85rem;
  bottom: 0.85rem;
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem 0.75rem;
  padding: 0.5rem 0.7rem;
  border-radius: var(--radius);
  background: rgba(255, 252, 248, 0.92);
  border: 1px solid var(--border);
  color: var(--ink);
  font-size: 0.7rem;
  font-weight: 650;
}
.legend span {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
}

.inspector {
  border-left: 1px solid var(--border);
  padding: 1.1rem 1.15rem;
  background: var(--surface);
  animation: rise 0.25s var(--ease);
}

.inspector header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 0.75rem;
  margin-bottom: 0.85rem;
}

.eyebrow {
  margin: 0;
  font-size: 0.68rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--muted);
  font-weight: 750;
}

.inspector h3 {
  margin: 0.15rem 0 0;
  font-size: 1.75rem;
  letter-spacing: -0.04em;
}

.icon-close {
  border: 1px solid var(--border-strong);
  background: var(--surface);
  border-radius: var(--radius);
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  cursor: pointer;
  color: var(--muted);
}

.status-line {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-bottom: 0.75rem;
}

.pill {
  padding: 0.28rem 0.6rem;
  border-radius: 999px;
  background: var(--bg-subtle);
  font-size: 0.74rem;
  font-weight: 700;
}
.pill.muted { color: var(--muted); }
.pill[data-state='available'] { background: var(--bg-subtle); color: var(--muted); }
.pill[data-state='occupied'] { background: var(--accent-muted); color: var(--accent); }
.pill[data-state='pending'] { background: var(--info-bg); color: var(--info); }
.pill[data-state='preparing'] { background: var(--warn-bg); color: var(--warn); }
.pill[data-state='ready'] { background: var(--ok-bg); color: var(--ok); }
.pill[data-state='waiter'] { background: var(--attention-bg); color: var(--attention); }

.waiter-flag {
  margin: 0 0 0.85rem;
  padding: 0.6rem 0.7rem;
  border-radius: var(--radius);
  background: var(--attention-bg);
  border: 1px solid var(--attention-border);
  color: var(--attention);
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.inspector h4 {
  margin: 0 0 0.45rem;
  font-size: 0.7rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--muted);
}

.inspector ul {
  list-style: none;
  margin: 0;
  padding: 0;
}

.inspector li {
  padding: 0.7rem 0;
  border-bottom: 1px solid var(--border);
}

.order-top {
  display: flex;
  justify-content: space-between;
  gap: 0.5rem;
  margin-bottom: 0.3rem;
}

.st {
  display: inline-block;
  font-size: 0.66rem;
  text-transform: uppercase;
  font-weight: 800;
  letter-spacing: 0.05em;
  padding: 0.15rem 0.45rem;
  border-radius: 999px;
  background: var(--bg-subtle);
}
.st[data-status='pending'] { background: var(--info-bg); color: var(--info); }
.st[data-status='preparing'] { background: var(--warn-bg); color: var(--warn); }
.st[data-status='ready'] { background: var(--ok-bg); color: var(--ok); }

.inspector p { margin: 0; font-size: 0.9rem; }
.inspector em {
  display: block;
  margin-top: 0.25rem;
  font-style: normal;
  color: var(--muted);
  font-size: 0.8rem;
}
.empty { color: var(--muted); font-size: 0.88rem; }

.inspector-actions {
  display: grid;
  gap: 0.4rem;
  margin-top: 1rem;
}

.action {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  min-height: 40px;
  padding: 0.45rem 0.75rem;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius);
  font-weight: 650;
  font-size: 0.85rem;
  color: var(--ink);
  background: var(--surface-2);
}

@keyframes rise {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: none; }
}

@keyframes attention {
  0%, 100% { filter: drop-shadow(0 0 0 rgba(184, 92, 122, 0.2)); }
  50% { filter: drop-shadow(0 0 10px rgba(184, 92, 122, 0.45)); }
}

@media (max-width: 960px) {
  .stage-grid.has-drawer { grid-template-columns: 1fr; }
  .inspector { border-left: 0; border-top: 1px solid var(--border); }
  .hint { display: none; }
  .canvas { min-height: 400px; height: min(58vh, 520px); }
  .state-chip { display: none; }
}
</style>
