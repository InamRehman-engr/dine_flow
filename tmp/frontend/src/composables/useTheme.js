import { onMounted, ref, watch } from 'vue'

const THEME_KEY = 'dineflow_theme'
const theme = ref('light')

function apply(t) {
  document.documentElement.setAttribute('data-theme', t === 'dark' ? 'dark' : 'light')
}

export function useTheme() {
  onMounted(() => {
    const stored = localStorage.getItem(THEME_KEY) || 'light'
    theme.value = stored === 'dark' ? 'dark' : 'light'
    apply(theme.value)
  })

  watch(theme, (t) => {
    localStorage.setItem(THEME_KEY, t)
    apply(t)
  })

  function toggle() {
    theme.value = theme.value === 'dark' ? 'light' : 'dark'
  }

  function setTheme(t) {
    theme.value = t === 'dark' ? 'dark' : 'light'
  }

  return { theme, toggle, setTheme }
}
