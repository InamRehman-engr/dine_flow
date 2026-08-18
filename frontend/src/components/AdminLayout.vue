<template>
  <div class="floor rise-in">
    <div class="section-head">
      <div>
        <h2 class="page-title">Floor</h2>
        <p class="page-sub">
          {{
            editing
              ? stepHint
              : 'Monitor tables live. Draw your room, place tables, then export QR forms.'
          }}
        </p>
      </div>
      <div class="row actions">
        <template v-if="!editing">
          <button class="btn btn-sm" type="button" @click="startEdit">
            {{ hasLayout ? 'Edit layout' : 'Create layout' }}
          </button>
          <button
            class="btn btn-ghost btn-sm"
            type="button"
            @click="downloadQRs"
            :disabled="downloading || !tables.length"
          >
            {{ downloading ? 'Building…' : 'Export QRs' }}
          </button>
        </template>
        <template v-else>
          <button
            v-if="editPhase === 'boundary'"
            class="btn btn-ghost btn-sm"
            type="button"
            :disabled="!draftBoundary.length"
            @click="draftBoundary.pop()"
          >
            Undo
          </button>
          <button
            v-if="editPhase === 'boundary'"
            class="btn btn-ghost btn-sm"
            type="button"
            :disabled="draftBoundary.length < 3"
            @click="editPhase = 'tables'"
          >
            Next
          </button>
          <button
            v-if="editPhase === 'tables'"
            class="btn btn-ghost btn-sm"
            type="button"
            @click="editPhase = 'boundary'"
          >
            Boundary
          </button>
          <button class="btn btn-ghost btn-sm" type="button" @click="cancelEdit">Cancel</button>
          <button class="btn btn-sm" type="button" :disabled="saving" @click="finishLayout">
            {{ saving ? 'Saving…' : 'Save & export' }}
          </button>
        </template>
      </div>
    </div>

    <p v-if="error" class="error-text">{{ error }}</p>

    <div v-if="editing && editPhase === 'tables'" class="toolbar row">
      <button class="btn btn-sm" type="button" @click="addTable">Add table</button>
      <p class="muted hint">Drag to place. Double-click to renumber. Select + delete to remove.</p>
      <button
        class="btn btn-danger btn-sm"
        type="button"
        :disabled="!selectedId"
        @click="removeSelected"
      >
        Delete
      </button>
    </div>

    <div
      ref="canvasRef"
      class="canvas panel"
      :class="{ editing, drawing: editing && editPhase === 'boundary' }"
      @pointerdown="onCanvasPointerDown"
      @pointermove="onCanvasPointerMove"
      @pointerup="onCanvasPointerUp"
      @pointerleave="onCanvasPointerUp"
    >
      <svg class="boundary-svg" viewBox="0 0 100 100" preserveAspectRatio="none">
        <polygon
          v-if="displayBoundary.length >= 3"
          :points="boundaryPointsAttr"
          class="boundary-fill"
        />
        <polyline
          v-if="displayBoundary.length >= 2"
          :points="boundaryPointsAttr"
          class="boundary-stroke"
        />
        <circle
          v-for="(p, i) in displayBoundary"
          :key="'v' + i"
          :cx="p.x"
          :cy="p.y"
          r="1.2"
          class="boundary-vertex"
        />
      </svg>

      <button
        v-for="t in displayTables"
        :key="t._key"
        type="button"
        class="table-sticker"
        :class="{
          selected: editing && selectedId === t._key,
          occupied: !editing && t.occupancy === 'occupied',
          free: !editing && t.occupancy === 'free' && !t.waiter_alert,
          waiter: !editing && t.waiter_alert,
          dragging: dragKey === t._key,
        }"
        :style="{ left: t.pos_x + '%', top: t.pos_y + '%' }"
        @pointerdown.stop="onTablePointerDown($event, t)"
        @dblclick.stop="renameTable(t)"
      >
        <svg class="sticker-art" viewBox="0 0 96 96" aria-hidden="true">
          <ellipse class="shadow" cx="48" cy="78" rx="28" ry="6" />
          <ellipse class="chair" cx="18" cy="48" rx="7" ry="10" />
          <ellipse class="chair" cx="78" cy="48" rx="7" ry="10" />
          <ellipse class="chair" cx="48" cy="18" rx="10" ry="7" />
          <ellipse class="chair" cx="48" cy="78" rx="10" ry="7" />
          <ellipse class="top-outer" cx="48" cy="48" rx="30" ry="26" />
          <ellipse class="top-inner" cx="48" cy="48" rx="22" ry="18" />
        </svg>
        <span class="tnum">{{ t.number }}</span>
        <span v-if="!editing" class="status-label">
          {{ t.waiter_alert ? 'Waiter' : t.occupancy }}
        </span>
      </button>

      <p v-if="!displayBoundary.length && !editing" class="empty-hint muted">
        No layout yet — press <strong>Create layout</strong> and draw your room outline.
      </p>
      <p v-if="editing && editPhase === 'boundary' && !draftBoundary.length" class="empty-hint muted">
        Click around the canvas to draw your space boundary (at least 3 points).
      </p>
    </div>

    <section v-if="!editing && openOrders.length" class="orders panel">
      <h3>Open orders by table</h3>
      <div v-for="o in openOrders" :key="o.id" class="order-line row">
        <strong>T-{{ o.table_number }}</strong>
        <span class="badge" :class="'badge-' + o.status">{{ o.status }}</span>
        <span class="muted">{{ o.items.map(i => `${i.quantity}× ${i.name}`).join(', ') }}</span>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { api } from '../api'
import { useSocket } from '../composables/useSocket'

const props = defineProps({
  tenant: { type: Object, default: null },
})
const emit = defineEmits(['refresh-alerts'])

const canvasRef = ref(null)
const tables = ref([])
const boundary = ref([])
const openOrders = ref([])
const error = ref('')
const downloading = ref(false)
const saving = ref(false)

const editing = ref(false)
const editPhase = ref('boundary') // boundary | tables
const draftBoundary = ref([])
const draftTables = ref([])
const selectedId = ref(null)
const dragKey = ref(null)
const dragOffset = ref({ x: 0, y: 0 })
let localId = 0

const hasLayout = computed(() => boundary.value.length >= 3 || tables.value.length > 0)

const stepHint = computed(() => {
  if (editPhase.value === 'boundary') {
    return 'Step 1 — Click to place vertices and draw your room boundary (not a fixed rectangle).'
  }
  return 'Step 2 — Add tables, drag them into place, assign numbers, then press Done.'
})

const displayBoundary = computed(() =>
  editing.value ? draftBoundary.value : boundary.value
)

const displayTables = computed(() =>
  editing.value ? draftTables.value : tables.value.map((t) => ({ ...t, _key: t.id }))
)

const boundaryPointsAttr = computed(() =>
  displayBoundary.value.map((p) => `${p.x},${p.y}`).join(' ')
)

function pctFromEvent(e) {
  const el = canvasRef.value
  if (!el) return { x: 0, y: 0 }
  const rect = el.getBoundingClientRect()
  const x = ((e.clientX - rect.left) / rect.width) * 100
  const y = ((e.clientY - rect.top) / rect.height) * 100
  return {
    x: Math.max(0, Math.min(100, x)),
    y: Math.max(0, Math.min(100, y)),
  }
}

function nextNumber(list) {
  const used = new Set(list.map((t) => t.number))
  let n = 1
  while (used.has(n)) n += 1
  return n
}

function startEdit() {
  editing.value = true
  draftBoundary.value = boundary.value.map((p) => ({ ...p }))
  draftTables.value = tables.value.map((t) => ({
    ...t,
    _key: t.id || `local-${++localId}`,
  }))
  editPhase.value = draftBoundary.value.length >= 3 ? 'tables' : 'boundary'
  selectedId.value = null
  error.value = ''
}

function cancelEdit() {
  editing.value = false
  draftBoundary.value = []
  draftTables.value = []
  selectedId.value = null
  dragKey.value = null
}

function onCanvasPointerDown(e) {
  if (!editing.value || editPhase.value !== 'boundary') return
  const p = pctFromEvent(e)
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
    },
  ]
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

async function finishLayout() {
  if (draftBoundary.value.length > 0 && draftBoundary.value.length < 3) {
    error.value = 'Boundary needs at least 3 points (or clear it and skip)'
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
    await downloadQRs()
    await load()
  } catch (e) {
    error.value = e.message
  } finally {
    saving.value = false
  }
}

async function load() {
  error.value = ''
  try {
    const [floor, status] = await Promise.all([
      api.get('/api/tenant/tables'),
      api.get('/api/tenant/floor-status'),
    ])
    tables.value = floor.tables || []
    boundary.value = floor.floor_boundary || status.floor_boundary || []
    openOrders.value = status.open_orders || []
  } catch (e) {
    error.value = e.message
  }
}

async function downloadQRs() {
  downloading.value = true
  error.value = ''
  try {
    await api.download('/api/tenant/export-qrs', 'dineflow-table-qrs.pdf')
  } catch (e) {
    error.value = e.message
  } finally {
    downloading.value = false
  }
}

watch(
  () => props.tenant?.id,
  (id, _prev, onCleanup) => {
    if (!id) return
    const { on } = useSocket(id)
    const offs = [
      on('floor_refresh', () => {
        if (!editing.value) {
          load()
          emit('refresh-alerts')
        }
      }),
      on('new_order', () => {
        if (!editing.value) load()
      }),
      on('status_update', () => {
        if (!editing.value) load()
      }),
    ]
    onCleanup(() => offs.forEach((off) => off && off()))
  },
  { immediate: true }
)

onMounted(load)
</script>

<style scoped>
.actions { gap: 0.45rem; }
.toolbar {
  margin-bottom: 0.75rem;
  gap: 0.75rem;
  align-items: center;
  flex-wrap: wrap;
  padding: 0.75rem 0.9rem;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.8);
}
.hint {
  flex: 1;
  margin: 0;
  min-width: 180px;
}
.canvas {
  position: relative;
  min-height: 460px;
  height: min(66vh, 600px);
  overflow: hidden;
  border: 1px solid #d5d5d5;
  border-radius: 16px;
  box-shadow: 0 12px 28px rgba(20, 20, 20, 0.05);
  background: #eceff2;
  touch-action: none;
  user-select: none;
}
.canvas.drawing { cursor: crosshair; }
.canvas.editing { border-color: #8a7048; box-shadow: 0 0 0 1px #8a7048 inset, 0 12px 28px rgba(20, 20, 20, 0.05); }
.boundary-svg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 1;
}
.boundary-fill {
  fill: rgba(138, 112, 72, 0.14);
  stroke: none;
}
.boundary-stroke {
  fill: none;
  stroke: #5c4630;
  stroke-width: 0.55;
  stroke-linejoin: round;
  stroke-dasharray: 1.4 0.7;
}
.boundary-vertex {
  fill: #8a7048;
  stroke: #fff;
  stroke-width: 0.25;
}
.table-sticker {
  position: absolute;
  transform: translate(-50%, -50%);
  width: 86px;
  height: 86px;
  border: 0;
  padding: 0;
  background: transparent;
  cursor: grab;
  z-index: 2;
  font-family: inherit;
}
.table-sticker.dragging { cursor: grabbing; z-index: 5; }
.sticker-art {
  width: 100%;
  height: 100%;
  display: block;
  filter: drop-shadow(0 8px 10px rgba(20, 14, 8, 0.18));
}
.shadow { fill: rgba(20, 14, 8, 0.18); }
.chair { fill: #d8c3a4; stroke: #b79a74; stroke-width: 1; }
.top-outer { fill: #8b6538; stroke: #5e3f21; stroke-width: 1.5; }
.top-inner { fill: #c49a5d; stroke: #9a7240; stroke-width: 1.2; }
.table-sticker.free .top-outer { fill: #3f6b52; stroke: #274537; }
.table-sticker.free .top-inner { fill: #6fa286; stroke: #4d7a63; }
.table-sticker.occupied .top-outer { fill: #2d3136; stroke: #15171a; }
.table-sticker.occupied .top-inner { fill: #50565e; stroke: #35393f; }
.table-sticker.waiter .top-outer { fill: #b8842d; stroke: #7a5414; }
.table-sticker.waiter .top-inner { fill: #e0b45a; stroke: #b8842d; }
.table-sticker.selected {
  outline: 2px solid #8a7048;
  outline-offset: 4px;
  border-radius: 50%;
}
.tnum {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  font-weight: 700;
  font-size: 1.05rem;
  color: #fff;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.35);
  pointer-events: none;
  padding-bottom: 0.15rem;
}
.status-label {
  position: absolute;
  left: 50%;
  bottom: -0.15rem;
  transform: translateX(-50%);
  font-size: 0.62rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #3d3428;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 999px;
  padding: 0.12rem 0.4rem;
  white-space: nowrap;
}
.empty-hint {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  margin: 0;
  padding: 2rem;
  text-align: center;
  pointer-events: none;
  z-index: 1;
  color: var(--muted);
}
.orders {
  margin-top: 1.25rem;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 1rem 1.1rem;
}
.orders h3 {
  margin: 0 0 0.75rem;
  font-size: 0.72rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  font-family: var(--font-body);
  color: var(--muted);
}
.order-line {
  padding: 0.55rem 0;
  border-top: 1px solid var(--line);
}
</style>
