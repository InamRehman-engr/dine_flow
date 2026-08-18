import { ref } from 'vue'
import { api } from '../api'

const currency = ref('PKR')
const language = ref('en')
let loaded = false

export function useMoney() {
  async function loadConfig() {
    if (loaded) return
    try {
      const data = await api.get('/api/public/config')
      currency.value = data.currency || 'PKR'
      language.value = data.language || 'en'
      loaded = true
    } catch {
      currency.value = 'PKR'
    }
  }

  function formatMoney(amount) {
    const n = Number(amount) || 0
    try {
      return new Intl.NumberFormat(language.value === 'en' ? 'en-PK' : language.value, {
        style: 'currency',
        currency: currency.value,
        maximumFractionDigits: 0,
      }).format(n)
    } catch {
      return `${currency.value} ${n.toFixed(0)}`
    }
  }

  return { currency, language, loadConfig, formatMoney }
}
