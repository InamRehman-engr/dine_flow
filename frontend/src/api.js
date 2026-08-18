const ACCESS_KEY = 'dineflow_access_token'

export function getAccessToken() {
  return localStorage.getItem(ACCESS_KEY)
}

export function setAccessToken(token) {
  if (token) localStorage.setItem(ACCESS_KEY, token)
  else localStorage.removeItem(ACCESS_KEY)
}

export function clearAccessToken() {
  localStorage.removeItem(ACCESS_KEY)
}

async function request(path, options = {}) {
  const headers = {
    'ngrok-skip-browser-warning': 'true',
    ...(options.headers || {}),
  }
  const token = getAccessToken()
  if (token) headers.Authorization = `Bearer ${token}`

  const isForm = options.body instanceof FormData
  if (!isForm && !headers['Content-Type'] && options.body !== undefined) {
    headers['Content-Type'] = 'application/json'
  }

  const { timeoutMs = 8000, ...rest } = options
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)

  const opts = {
    credentials: 'include',
    ...rest,
    headers,
    signal: rest.signal || controller.signal,
  }
  if (opts.body && typeof opts.body === 'object' && !(opts.body instanceof FormData)) {
    opts.body = JSON.stringify(opts.body)
  }

  let res
  try {
    res = await fetch(path, opts)
  } catch (err) {
    clearTimeout(timer)
    if (err?.name === 'AbortError') {
      const timeout = new Error('Request timed out')
      timeout.status = 0
      throw timeout
    }
    throw err
  } finally {
    clearTimeout(timer)
  }

  // Silent refresh on 401 once
  if (res.status === 401 && !options._retried && !path.includes('/api/auth/')) {
    try {
      const refreshed = await fetch('/api/auth/refresh', {
        method: 'POST',
        credentials: 'include',
        headers: { 'ngrok-skip-browser-warning': 'true' },
      })
      if (refreshed.ok) {
        const data = await refreshed.json()
        if (data.access_token) setAccessToken(data.access_token)
        return request(path, { ...options, _retried: true })
      }
    } catch {
      /* fall through */
    }
  }

  const contentType = res.headers.get('content-type') || ''
  let data = null
  if (contentType.includes('application/json')) {
    data = await res.json()
  } else if (contentType.includes('application/pdf')) {
    data = await res.blob()
  } else {
    data = await res.text()
  }
  if (!res.ok) {
    const err = new Error((data && data.error) || res.statusText || 'Request failed')
    err.status = res.status
    err.data = data
    throw err
  }
  return data
}

export const api = {
  get: (path) => request(path),
  post: (path, body) => request(path, { method: 'POST', body }),
  put: (path, body) => request(path, { method: 'PUT', body }),
  patch: (path, body) => request(path, { method: 'PATCH', body }),
  delete: (path) => request(path, { method: 'DELETE' }),
  upload: (path, formData) => request(path, { method: 'POST', body: formData }),
  download: async (path, filename) => {
    const token = getAccessToken()
    const res = await fetch(path, {
      credentials: 'include',
      headers: {
        'ngrok-skip-browser-warning': 'true',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    })
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      throw new Error(data.error || 'Download failed')
    }
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename || 'download.pdf'
    a.click()
    URL.revokeObjectURL(url)
  },
}
