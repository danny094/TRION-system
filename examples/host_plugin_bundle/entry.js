export default function HostPluginDemo(props) {
  const React = window.__TRION_REACT__
  const [time, setTime] = React.useState('noch nicht geladen')
  const [status, setStatus] = React.useState('lade…')

  React.useEffect(() => {
    let cancelled = false
    props.bridge.request('/health')
      .then(() => props.bridge.callTool('time_now'))
      .then((response) => {
        if (cancelled) return
        const result = response?.data?.result || response?.data || {}
        setTime(String(result?.time || 'unbekannt'))
        setStatus('verbunden')
      })
      .catch((error) => {
        if (cancelled) return
        setStatus(error instanceof Error ? error.message : 'bridge-fehler')
      })
    return () => {
      cancelled = true
    }
  }, [props.bridge])

  return React.createElement(
    'div',
    { style: { padding: '24px', color: '#f5f5f5', fontFamily: 'system-ui, sans-serif' } },
    React.createElement('div', { style: { fontSize: '12px', opacity: 0.65, textTransform: 'uppercase', letterSpacing: '0.12em' } }, props.plugin.name),
    React.createElement('h1', { style: { margin: '12px 0 8px', fontSize: '28px' } }, 'Host-Mount aktiv'),
    React.createElement('p', { style: { margin: 0, opacity: 0.8 } }, `Status: ${status}`),
    React.createElement('p', { style: { marginTop: '16px', fontSize: '18px' } }, `Aktuelle Zeit: ${time}`)
  )
}
