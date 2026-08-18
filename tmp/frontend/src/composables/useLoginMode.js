const MODE_KEY = 'dineflow_login_mode'

export function getLoginMode() {
  const m = localStorage.getItem(MODE_KEY)
  return m === 'kitchen' ? 'kitchen' : 'admin'
}

export function setLoginMode(mode) {
  localStorage.setItem(MODE_KEY, mode === 'kitchen' ? 'kitchen' : 'admin')
}

export function clearLoginMode() {
  localStorage.removeItem(MODE_KEY)
}

export function homePathForMode(mode = getLoginMode()) {
  return mode === 'kitchen' ? '/kitchen' : '/admin'
}
