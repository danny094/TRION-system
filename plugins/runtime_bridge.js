(function () {
  let csrfToken = null
  const csrfHeaderName = '__TRION_CSRF_HEADER_NAME__'

  function currentPluginId() {
    const match = window.location.pathname.match(/\/api\/plugins\/([^/]+)\/asset\//)
    if (!match) throw new Error('TRIONBridge could not resolve plugin id from current URL.')
    return decodeURIComponent(match[1])
  }

  async function parseBridgeResponse(response) {
    const type = response.headers.get('content-type') || ''
    const data = type.includes('application/json') ? await response.json() : await response.text()
    if (!response.ok) {
      const detail = typeof data === 'string' ? data : data?.detail || JSON.stringify(data)
      throw new Error(detail || `Plugin bridge request failed (${response.status})`)
    }
    return { ok: true, status: response.status, data }
  }

  async function sessionCsrf() {
    if (csrfToken) return csrfToken
    const response = await fetch('/api/auth/session', { credentials: 'same-origin' })
    if (!response.ok) throw new Error(`TRION session unavailable (${response.status})`)
    const session = await response.json()
    csrfToken = String(session.csrf_token || '')
    if (!csrfToken) throw new Error('TRION session did not provide CSRF metadata.')
    return csrfToken
  }

  async function send(pluginId, path, payload) {
    const csrf = await sessionCsrf()
    const response = await fetch(`/api/plugins/${encodeURIComponent(pluginId)}${path}`, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', [csrfHeaderName]: csrf },
      body: JSON.stringify(payload || {}),
    })
    if (response.status === 401) csrfToken = null
    return parseBridgeResponse(response)
  }

  window.TRIONBridge = Object.freeze({
    get pluginId() {
      return currentPluginId()
    },
    async request(path, options) {
      return send(currentPluginId(), '/bridge/request', {
        path,
        method: options?.method,
        params: options?.params,
        headers: options?.headers,
        json: options?.json,
        body: options?.body,
      })
    },
    async callTool(name, args) {
      return send(currentPluginId(), `/bridge/tools/${encodeURIComponent(name)}`, {
        args: args || {},
      })
    },
  })
})()
