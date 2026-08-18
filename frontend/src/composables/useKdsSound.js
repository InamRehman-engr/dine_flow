import { ref } from 'vue'

let audioCtx = null
const unlocked = ref(false)
const soundEnabled = ref(localStorage.getItem('dineflow_kds_sound') !== '0')

function ensureCtx() {
  if (!audioCtx) {
    const Ctx = window.AudioContext || window.webkitAudioContext
    if (Ctx) audioCtx = new Ctx()
  }
  return audioCtx
}

export function useKdsSound() {
  function unlock() {
    const ctx = ensureCtx()
    if (!ctx) return
    if (ctx.state === 'suspended') ctx.resume()
    unlocked.value = true
  }

  function setEnabled(on) {
    soundEnabled.value = !!on
    localStorage.setItem('dineflow_kds_sound', on ? '1' : '0')
  }

  function playChime() {
    if (!soundEnabled.value) return
    const ctx = ensureCtx()
    if (!ctx) return
    if (ctx.state === 'suspended') ctx.resume()
    const now = ctx.currentTime
    ;[523.25, 659.25, 783.99].forEach((freq, i) => {
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      osc.type = 'sine'
      osc.frequency.value = freq
      gain.gain.setValueAtTime(0.0001, now)
      gain.gain.exponentialRampToValueAtTime(0.12, now + 0.02 + i * 0.05)
      gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.35 + i * 0.08)
      osc.connect(gain)
      gain.connect(ctx.destination)
      osc.start(now + i * 0.05)
      osc.stop(now + 0.45 + i * 0.08)
    })
  }

  return { soundEnabled, unlocked, unlock, setEnabled, playChime }
}
