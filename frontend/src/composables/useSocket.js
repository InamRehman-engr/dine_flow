import { io } from 'socket.io-client'
import { onUnmounted, ref } from 'vue'
import { getAccessToken } from '../api'

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

export function useSocket() {
  const connected = ref(false)
  const lastEvent = ref(null)
  const socket = getSocket()

  function joinStaff() {
    const token = getAccessToken()
    if (token) socket.emit('join_session', { access_token: token })
  }

  function joinGuest(guestTicket) {
    if (guestTicket) socket.emit('join_guest', { guest_ticket: guestTicket })
  }

  function onConnect() {
    connected.value = true
  }

  function onDisconnect() {
    connected.value = false
  }

  socket.on('connect', onConnect)
  socket.on('disconnect', onDisconnect)
  if (socket.connected) onConnect()

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

  return { socket, connected, lastEvent, on, joinStaff, joinGuest }
}
