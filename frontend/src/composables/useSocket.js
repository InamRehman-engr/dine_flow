import { io } from 'socket.io-client'
import { onUnmounted, ref, watch } from 'vue'

let sharedSocket = null

function getSocket() {
  if (!sharedSocket) {
    sharedSocket = io({
      path: '/socket.io',
      withCredentials: true,
      transports: ['websocket', 'polling'],
      extraHeaders: {
        'ngrok-skip-browser-warning': 'true',
      },
    })
  }
  return sharedSocket
}

export function useSocket(tenantId) {
  const connected = ref(false)
  const lastEvent = ref(null)
  const socket = getSocket()

  function join(id) {
    if (id) socket.emit('join_session', { tenant_id: String(id) })
  }

  function onConnect() {
    connected.value = true
    const id = typeof tenantId === 'object' && tenantId !== null ? tenantId.value : tenantId
    join(id)
  }

  function onDisconnect() {
    connected.value = false
  }

  socket.on('connect', onConnect)
  socket.on('disconnect', onDisconnect)
  if (socket.connected) onConnect()

  if (typeof tenantId === 'object' && tenantId !== null && 'value' in tenantId) {
    watch(tenantId, (id) => {
      if (socket.connected) join(id)
    })
  }

  function on(event, handler) {
    const wrap = (payload) => {
      lastEvent.value = { event, payload }
      handler(payload)
    }
    socket.on(event, wrap)
    return () => socket.off(event, wrap)
  }

  onUnmounted(() => {
    socket.off('connect', onConnect)
    socket.off('disconnect', onDisconnect)
  })

  return { socket, connected, lastEvent, on }
}
