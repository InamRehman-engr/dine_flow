import { computed, ref } from 'vue'
import { api, clearAccessToken, setAccessToken } from '../api'

const tenant = ref(null)
const staff = ref(null)
const loading = ref(false)
const WORKSPACE_KEY = 'dineflow_workspace'

export function getWorkspace() {
  const w = localStorage.getItem(WORKSPACE_KEY)
  return w === 'kitchen' ? 'kitchen' : 'admin'
}

export function setWorkspace(mode) {
  localStorage.setItem(WORKSPACE_KEY, mode === 'kitchen' ? 'kitchen' : 'admin')
}

export function clearWorkspace() {
  localStorage.removeItem(WORKSPACE_KEY)
}

export function useAuth() {
  const isManager = computed(() => staff.value?.role === 'manager')
  const isKitchen = computed(() => staff.value?.role === 'kitchen')
  const homePath = computed(() => {
    const ws = getWorkspace()
    if (staff.value?.role === 'kitchen') return '/kitchen'
    if (ws === 'kitchen') return '/kitchen'
    return '/admin'
  })

  async function fetchMe() {
    loading.value = true
    try {
      const data = await api.get('/api/auth/me')
      tenant.value = data.tenant
      staff.value = data.staff
      return data
    } catch {
      tenant.value = null
      staff.value = null
      return null
    } finally {
      loading.value = false
    }
  }

  async function login(email, password, workspace = 'admin') {
    const data = await api.post('/api/auth/login', { email, password })
    if (data.access_token) setAccessToken(data.access_token)
    tenant.value = data.tenant
    staff.value = data.staff

    // Kitchen staff can only use kitchen workspace
    if (data.staff?.role === 'kitchen') {
      setWorkspace('kitchen')
    } else {
      setWorkspace(workspace === 'kitchen' ? 'kitchen' : 'admin')
    }
    return data
  }

  async function register(payload) {
    const data = await api.post('/api/auth/register', payload)
    if (data.access_token) setAccessToken(data.access_token)
    tenant.value = data.tenant
    staff.value = data.staff
    setWorkspace('admin')
    return data
  }

  async function logout() {
    try {
      await api.post('/api/auth/logout')
    } catch {
      /* still clear local */
    } finally {
      clearAccessToken()
      clearWorkspace()
      tenant.value = null
      staff.value = null
    }
  }

  return {
    tenant,
    staff,
    loading,
    isManager,
    isKitchen,
    homePath,
    fetchMe,
    login,
    register,
    logout,
    getWorkspace,
    setWorkspace,
  }
}
