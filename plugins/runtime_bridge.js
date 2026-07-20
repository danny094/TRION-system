(function () {
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

  async function send(pluginId, path, payload) {
    const response = await fetch(`/api/plugins/${encodeURIComponent(pluginId)}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload || {}),
    })
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
