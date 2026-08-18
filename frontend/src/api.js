async function request(path, options = {}) {
  const opts = {
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      // Avoid ngrok free-tier interstitial HTML breaking JSON APIs
      'ngrok-skip-browser-warning': 'true',
      ...(options.headers || {}),
    },
    ...options,
  }
  if (opts.body && typeof opts.body === 'object' && !(opts.body instanceof FormData)) {
    opts.body = JSON.stringify(opts.body)
  }
  const res = await fetch(path, opts)
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
  download: async (path, filename) => {
    const res = await fetch(path, {
      credentials: 'include',
      headers: { 'ngrok-skip-browser-warning': 'true' },
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
