// Container Commander UI Plugin — v2.0.0
// Mount: launchpad | Requires MCP: container-commander
// Pattern: window.__TRION_REACT__ (no bare imports, browser-ready ESM)

const TABS = [
  { id:'status',     label:'Status',      color:'#059669', icon:'M1 1h6v6H1zm8 0h6v6H9zM1 9h6v6H1zm8 0h6v6H9z' },
  { id:'blueprints', label:'Blueprints',  color:'#3B82F6', icon:'M2 5h12M2 8h12M5 11h6M3 2h10l2 3H1z' },
  { id:'dockerfile', label:'Dockerfile',  color:'#8B5CF6', icon:'M4 4L1 8l3 4M12 4l3 4-3 4M8 1v14' },
  { id:'resources',  label:'Resources',   color:'#D97706', icon:'M2 2h12v3H2zm0 5h12v3H2zm0 5h8v3H2z' },
  { id:'security',   label:'Security',    color:'#E11D48', icon:'M8 1L1 4v5c0 4 3 6 7 7 4-1 7-3 7-7V4z' },
  { id:'logs',       label:'Logs',        color:'#475569', icon:'M2 4h12M2 7h12M2 10h9' },
]

const MOCK_CONTAINERS = [
  { name:'trion-core',      desc:'Orchestration Engine',      cpu:23, ram:'1.2 GB', up:'3d 4h',  on:true  },
  { name:'jarvis-webui',    desc:'Web Interface',             cpu:4,  ram:'340 MB', up:'3d 4h',  on:true  },
  { name:'sql-memory',      desc:'PostgreSQL backend',        cpu:8,  ram:'780 MB', up:'3d 4h',  on:true  },
  { name:'trion-admin-api', desc:'Admin API',                 cpu:0,  ram:'—',      up:'stopped',on:false },
  { name:'container-cmdr',  desc:'Container management',      cpu:2,  ram:'180 MB', up:'3d 4h',  on:true  },
  { name:'fs-bridge',       desc:'Sandboxed filesystem',      cpu:1,  ram:'95 MB',  up:'1d 2h',  on:true  },
]

const MOCK_BPS = [
  { id:'gaming-station', name:'gaming-station', desc:'Sunshine/Moonlight + Steam + NVIDIA', inst:true  },
  { id:'sql-memory',     name:'sql-memory',     desc:'PostgreSQL memory backend for TRION', inst:true  },
  { id:'ml-toolbox',     name:'ml-toolbox',     desc:'CUDA + PyTorch dev environment',      inst:false },
  { id:'web-scraper',    name:'web-scraper',    desc:'Playwright + Node.js scraping stack', inst:false },
]

const MOCK_LOGS = [
  { t:'01:23:44', l:'INFO',  m:'ThinkingLayer initialized',           c:'#34D399' },
  { t:'01:23:45', l:'INFO',  m:'MCP Hub listening on :7433',          c:'#34D399' },
  { t:'01:24:12', l:'DEBUG', m:'Processing task loop iteration 847',  c:'#94A3B8' },
  { t:'01:24:13', l:'INFO',  m:'Tool execution: time_now → 23ms',     c:'#34D399' },
  { t:'01:24:13', l:'INFO',  m:'Output dispatched to stream',         c:'#34D399' },
]

const SAMPLE_DOCKERFILE = `FROM nvidia/cuda:12.3.0-base-ubuntu22.04
ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \\
    steam-installer sunshine \\
    pulseaudio xvfb && \\
    rm -rf /var/lib/apt/lists/*

ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=all

COPY sunshine.conf /etc/sunshine/sunshine.conf
VOLUME ["/home/steam"]
EXPOSE 47984 47989 48010
CMD ["sunshine"]`

const PLACEHOLDER_STATE = {
  dockerfile: { placeholder:true, phase:'future', data_source:'mock' },
  resources:  { placeholder:true, phase:'future', data_source:'mock' },
  security:   { placeholder:true, phase:'future', data_source:'mock' },
}


// ── CSS injected once into host document, scoped under .cc-root ──────────────
const CSS = `
.cc-root{height:100%;display:flex;background:#17171a;font-family:var(--font-sans,system-ui,sans-serif);color:rgba(255,255,255,.90);font-size:13px;box-sizing:border-box}
.cc-root *{box-sizing:border-box}
.cc-sb{width:180px;flex-shrink:0;background:rgba(255,255,255,.015);border-right:.5px solid rgba(255,255,255,.07);padding:14px 11px;display:flex;flex-direction:column}
.cc-hd{display:flex;align-items:center;gap:10px;padding:4px 6px 20px}
.cc-hd-ic{width:34px;height:34px;border-radius:10px;background:#e8e8ea;display:flex;align-items:center;justify-content:center;color:#17171a;font-size:11px;font-weight:700;flex-shrink:0}
.cc-tab{display:flex;align-items:center;gap:9px;padding:5px 8px;border-radius:8px;font-size:12px;color:rgba(255,255,255,.48);cursor:pointer;background:none;border:none;width:100%;text-align:left;transition:background .15s}
.cc-tab:hover{background:rgba(255,255,255,.04);color:rgba(255,255,255,.8)}
.cc-tab.act{background:rgba(255,255,255,.08);color:rgba(255,255,255,.92)}
.cc-tic{width:20px;height:20px;border-radius:5px;display:flex;align-items:center;justify-content:center;color:#fff;flex-shrink:0}
.cc-ft{margin-top:auto;padding:12px 8px 4px;border-top:.5px solid rgba(255,255,255,.06)}
.cc-ct{flex:1;overflow-y:auto;padding:22px 26px}
.cc-eb{font-size:10px;letter-spacing:.17em;text-transform:uppercase;color:rgba(255,255,255,.32)}
.cc-tt{font-size:21px;font-weight:500;color:rgba(255,255,255,.93);margin:7px 0 0;line-height:1.25}
.cc-sub{font-size:12px;color:rgba(255,255,255,.48);margin:7px 0 0;line-height:1.55;max-width:400px}
.cc-card{background:rgba(255,255,255,.025);border:.5px solid rgba(255,255,255,.07);border-radius:13px;padding:13px 15px;margin-top:12px}
.cc-cl{font-size:10px;letter-spacing:.13em;text-transform:uppercase;color:rgba(255,255,255,.32);margin-bottom:10px}
.cc-stats{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:14px}
.cc-stat{border-radius:10px;padding:10px 13px}
.cc-sn{font-size:22px;font-weight:500;line-height:1}
.cc-sl{font-size:9px;text-transform:uppercase;letter-spacing:.12em;margin-top:4px}
.cc-g2{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:10px}
.cc-ccard{background:rgba(255,255,255,.025);border:.5px solid rgba(255,255,255,.07);border-radius:12px;padding:12px 13px}
.cc-badge{display:inline-block;font-size:9px;padding:2px 7px;border-radius:4px;text-transform:uppercase;letter-spacing:.1em;font-weight:500}
.cc-bar{height:3px;background:rgba(255,255,255,.07);border-radius:2px;margin-top:4px}
.cc-barf{height:100%;border-radius:2px}
.cc-sel{width:100%;background:rgba(0,0,0,.3);border:.5px solid rgba(255,255,255,.1);border-radius:8px;color:rgba(255,255,255,.8);padding:6px 10px;font-size:12px;outline:none}
.cc-btn{display:inline-flex;align-items:center;gap:5px;border-radius:8px;border:.5px solid rgba(255,255,255,.1);background:rgba(255,255,255,.04);color:rgba(255,255,255,.7);font-size:11px;padding:5px 10px;cursor:pointer}
.cc-btn:hover{background:rgba(255,255,255,.08);color:rgba(255,255,255,.95)}
.cc-pre{font-family:var(--font-mono,monospace);font-size:11px;color:rgba(255,255,255,.75);line-height:1.7;margin:0;white-space:pre-wrap;word-break:break-word}
.cc-kw{color:rgba(139,92,246,.9)}
.cc-demo{background:rgba(217,119,6,.08);border:.5px solid rgba(217,119,6,.25);border-radius:10px;padding:8px 12px;font-size:11px;color:rgba(251,191,36,.85);margin-top:12px}
.cc-rtbl{display:grid;grid-template-columns:1fr 80px 80px 90px;gap:8px}
.cc-rtbl-hd{font-size:10px;text-transform:uppercase;letter-spacing:.12em;color:rgba(255,255,255,.28);padding:0 2px 8px;border-bottom:.5px solid rgba(255,255,255,.06)}
.cc-row{align-items:center;padding:7px 2px}
.cc-toggle{position:relative;width:28px;height:16px;border-radius:8px;cursor:pointer;border:none;transition:background .2s}
.cc-toggle-knob{position:absolute;top:2px;width:12px;height:12px;border-radius:50%;background:#fff;transition:transform .2s}
`

function injectStyles() {
  if (document.getElementById('cc-styles')) return
  const s = document.createElement('style')
  s.id = 'cc-styles'
  s.textContent = CSS
  document.head.appendChild(s)
}

// ── Tiny helpers ──────────────────────────────────────────────────────────────
function h(tag, props, ...ch) { return window.__TRION_REACT__.createElement(tag, props, ...ch) }

function Icon({ d, size = 12 }) {
  return h('svg', {
    viewBox:'0 0 16 16', width:size, height:size,
    fill:'none', stroke:'currentColor',
    strokeWidth:1.5, strokeLinecap:'round', strokeLinejoin:'round',
  }, h('path', { d }))
}

function isStub(text) {
  return typeof text === 'string' && text.includes('Backend-Implementation')
}

function toolData(res) {
  return res?.data?.result ?? res?.data ?? {}
}

function mapContainerSummary(item) {
  return {
    id: item.container_id,
    name: item.name,
    desc: item.image || 'Container',
    status: item.status || 'unknown',
    on: item.status === 'running',
    createdAt: item.created_at || '',
    managed: !!item.managed_by_trion,
    actionsAllowed: !!item.actions_allowed,
    protected: !!item.protected,
  }
}

function mapContainerDetail(item) {
  return {
    id: item.container_id,
    name: item.name,
    image: item.image || '',
    status: item.status || 'unknown',
    labels: item.labels || {},
    ports: Array.isArray(item.ports) ? item.ports : [],
    mounts: Array.isArray(item.mounts) ? item.mounts : [],
    runtimeState: item.runtime_state || {},
    createdAt: item.created_at || '',
    managed: !!item.managed_by_trion,
    actionsAllowed: !!item.actions_allowed,
    protected: !!item.protected,
  }
}

function mapBlueprintSummary(item) {
  return {
    id: item.blueprint_id,
    name: item.name,
    desc: item.description || 'Blueprint',
    version: item.version || '',
    inst: true,
  }
}

function mapBlueprintDetail(item) {
  return {
    id: item.blueprint_id,
    name: item.name,
    desc: item.description || 'Blueprint',
    version: item.version || '',
    definition: item.definition || {},
  }
}


// ── Sidebar ───────────────────────────────────────────────────────────────────
function Sidebar({ active, onSelect, running, stopped }) {
  const R = window.__TRION_REACT__
  return h('aside', { className:'cc-sb' },
    h('div', { className:'cc-hd' },
      h('div', { className:'cc-hd-ic' }, 'CC'),
      h('div', {},
        h('div', { style:{fontSize:12,color:'rgba(255,255,255,.90)',fontWeight:500,lineHeight:1.2} }, 'Container Cmdr'),
        h('div', { style:{fontSize:10,color:'rgba(255,255,255,.28)',marginTop:2} }, 'v 2.0 · TRION'),
      )
    ),
    h('nav', { style:{display:'flex',flexDirection:'column',gap:2} },
      TABS.map(t => h('button', {
        key: t.id,
        className:`cc-tab${active===t.id?' act':''}`,
        onClick: () => onSelect(t.id),
      },
        h('div', { className:'cc-tic', style:{background:t.color} }, h(Icon, { d:t.icon })),
        t.label
      ))
    ),
    h('div', { className:'cc-ft' },
      h('div', { style:{fontSize:10,color:'rgba(255,255,255,.28)'} }, `${running} running · ${stopped} stopped`),
      h('div', { style:{fontSize:10,color:'rgba(255,255,255,.20)',marginTop:2} }, 'Docker 24.0.5'),
    )
  )
}

// ── Panel header (shared) ─────────────────────────────────────────────────────
function PanelHeader({ eyebrow, title, subtitle, action }) {
  return h('div', { style:{display:'flex',alignItems:'flex-start',justifyContent:'space-between',gap:16} },
    h('div', {},
      h('div', { className:'cc-eb' }, eyebrow),
      h('h1', { className:'cc-tt' }, title),
      h('p',  { className:'cc-sub' }, subtitle),
    ),
    action || null,
  )
}

// ── Demo banner ───────────────────────────────────────────────────────────────
function DemoBanner() {
  return h('div', { className:'cc-demo' }, '⚡ Demo-Daten · MCP-Backend antwortet noch mit Stub. Echtdaten folgen wenn die Tool-Logik verdrahtet ist.')
}

function PlaceholderBanner({ state }) {
  return h('div', { className:'cc-demo' },
    `Placeholder · not wired to MCP yet · phase=${state.phase} · data_source=${state.data_source}`
  )
}

// ── Container card (Status tab) ───────────────────────────────────────────────
function ContainerCard({ c, active, onSelect }) {
  const dot    = c.on ? '#10B981' : 'rgba(255,255,255,.25)'
  const upCol  = c.on ? 'rgba(52,211,153,.85)' : 'rgba(255,255,255,.45)'
  const upBg   = c.on ? 'rgba(5,150,105,.08)' : 'rgba(255,255,255,.04)'
  const upBd   = c.on ? 'rgba(5,150,105,.2)'  : 'rgba(255,255,255,.08)'
  return h('button', {
    className:'cc-ccard',
    onClick:() => onSelect && onSelect(c),
    style:{
      width:'100%',
      textAlign:'left',
      cursor:'pointer',
      boxShadow: active ? '0 0 0 1px rgba(59,130,246,.45) inset' : 'none'
    }
  },
    h('div', { style:{display:'flex',alignItems:'flex-start',justifyContent:'space-between',gap:8} },
      h('div', { style:{display:'flex',alignItems:'center',gap:7,minWidth:0} },
        h('span', { style:{width:7,height:7,borderRadius:'50%',background:dot,flexShrink:0,marginTop:2,display:'inline-block'} }),
        h('div', { style:{minWidth:0} },
          h('div', { style:{fontFamily:'var(--font-mono,monospace)',fontSize:11,color:'rgba(255,255,255,.85)',whiteSpace:'nowrap',overflow:'hidden',textOverflow:'ellipsis'} }, c.name),
          h('div', { style:{fontSize:10,color:'rgba(255,255,255,.38)',marginTop:1,whiteSpace:'nowrap',overflow:'hidden',textOverflow:'ellipsis'} }, c.desc),
        )
      ),
      h('span', { className:'cc-badge', style:{background:upBg,color:upCol,border:`0.5px solid ${upBd}`,flexShrink:0} }, c.status || 'unknown'),
    ),
    h('div', { style:{marginTop:9,fontSize:10,color:'rgba(255,255,255,.38)',lineHeight:1.6} },
      h('div', {}, `managed_by_trion: ${c.managed ? 'true' : 'false'}`),
      h('div', {}, `actions_allowed: ${c.actionsAllowed ? 'true' : 'false'}`),
      h('div', {}, `protected: ${c.protected ? 'true' : 'false'}`),
      c.createdAt && h('div', {}, `created_at: ${c.createdAt}`),
    ),
    c.actionsAllowed && h('div', { style:{display:'flex',gap:8,marginTop:10} },
      h('span', { className:'cc-btn', style:{opacity:c.on ? .55 : 1} }, 'Start'),
      h('span', { className:'cc-btn', style:{opacity:c.on ? 1 : .55} }, 'Stop'),
    )
  )
}

function DetailRow({ label, value }) {
  return h('div', { style:{display:'flex',justifyContent:'space-between',gap:14,padding:'4px 0',borderBottom:'0.5px solid rgba(255,255,255,.05)'} },
    h('span', { style:{fontSize:10,color:'rgba(255,255,255,.32)',textTransform:'uppercase',letterSpacing:'.08em'} }, label),
    h('span', { style:{fontSize:11,color:'rgba(255,255,255,.72)',fontFamily:'var(--font-mono,monospace)',textAlign:'right',wordBreak:'break-word'} }, value || '—')
  )
}

function InspectPanel({ detail, loading }) {
  if (!detail && !loading) return null
  const ports = (detail?.ports || []).map(p => `${p.host || '—'} → ${p.container}${p.ip ? ` (${p.ip})` : ''}`)
  const labels = Object.entries(detail?.labels || {}).slice(0, 6)
  const runtimeKeys = ['Status', 'Running', 'StartedAt', 'FinishedAt']
  return h('div', { className:'cc-card' },
    h('div', { className:'cc-cl' }, 'Container Details'),
    loading && h('div', { style:{fontSize:11,color:'rgba(255,255,255,.42)'} }, 'Lade Details ...'),
    !loading && detail && h('div', {},
      h(DetailRow, { label:'Container', value:detail.name }),
      h(DetailRow, { label:'Image', value:detail.image }),
      h(DetailRow, { label:'Status', value:detail.status }),
      h(DetailRow, { label:'Managed', value:String(detail.managed) }),
      h(DetailRow, { label:'Actions', value:String(detail.actionsAllowed) }),
      h(DetailRow, { label:'Protected', value:String(detail.protected) }),
      detail.createdAt && h(DetailRow, { label:'Created', value:detail.createdAt }),
      h('div', { style:{marginTop:10} },
        h('div', { style:{fontSize:10,color:'rgba(255,255,255,.32)',textTransform:'uppercase',letterSpacing:'.08em',marginBottom:6} }, 'Ports'),
        ports.length
          ? ports.map((port, i) => h('div', { key:i, style:{fontSize:11,color:'rgba(255,255,255,.72)',fontFamily:'var(--font-mono,monospace)',padding:'3px 0'} }, port))
          : h('div', { style:{fontSize:11,color:'rgba(255,255,255,.42)'} }, 'Keine Ports'),
      ),
      h('div', { style:{marginTop:10} },
        h('div', { style:{fontSize:10,color:'rgba(255,255,255,.32)',textTransform:'uppercase',letterSpacing:'.08em',marginBottom:6} }, 'Mounts'),
        (detail.mounts || []).length
          ? detail.mounts.map((mount, i) => h('div', { key:i, style:{fontSize:11,color:'rgba(255,255,255,.72)',fontFamily:'var(--font-mono,monospace)',padding:'3px 0'} }, mount))
          : h('div', { style:{fontSize:11,color:'rgba(255,255,255,.42)'} }, 'Keine Mounts'),
      ),
      h('div', { style:{marginTop:10} },
        h('div', { style:{fontSize:10,color:'rgba(255,255,255,.32)',textTransform:'uppercase',letterSpacing:'.08em',marginBottom:6} }, 'Labels'),
        labels.length
          ? labels.map(([key, value]) => h('div', { key, style:{fontSize:11,color:'rgba(255,255,255,.72)',fontFamily:'var(--font-mono,monospace)',padding:'3px 0'} }, `${key}=${value}`))
          : h('div', { style:{fontSize:11,color:'rgba(255,255,255,.42)'} }, 'Keine Labels'),
      ),
      h('div', { style:{marginTop:10} },
        h('div', { style:{fontSize:10,color:'rgba(255,255,255,.32)',textTransform:'uppercase',letterSpacing:'.08em',marginBottom:6} }, 'Runtime State'),
        runtimeKeys.map(key => h('div', { key, style:{fontSize:11,color:'rgba(255,255,255,.72)',fontFamily:'var(--font-mono,monospace)',padding:'3px 0'} }, `${key}: ${String(detail.runtimeState?.[key] ?? '—')}`)),
      )
    )
  )
}


// ── Status Tab ────────────────────────────────────────────────────────────────
function StatusTab({ bridge }) {
  const R = window.__TRION_REACT__
  const [containers, setContainers] = R.useState(MOCK_CONTAINERS)
  const [isDemo,     setIsDemo]     = R.useState(false)
  const [loading,    setLoading]    = R.useState(true)
  const [selectedId, setSelectedId] = R.useState('')
  const [detail, setDetail] = R.useState(null)
  const [detailLoading, setDetailLoading] = R.useState(false)
  const [actionState, setActionState] = R.useState('')

  function refreshContainers() {
    return bridge.callTool('container_list', {})
      .then(res => {
        const payload = toolData(res)
        const rows = Array.isArray(payload?.containers) ? payload.containers.map(mapContainerSummary) : []
        if (rows.length) {
          setContainers(rows)
          setSelectedId(prev => prev || rows[0].id)
          setIsDemo(false)
        } else {
          setIsDemo(true)
        }
        setLoading(false)
      })
      .catch(() => {
        setIsDemo(true)
        setLoading(false)
      })
  }

  R.useEffect(() => {
    let alive = true
    refreshContainers().then(() => {
      if (!alive) return
    })
    return () => { alive = false }
  }, [bridge])

  R.useEffect(() => {
    if (!selectedId) return
    let alive = true
    setDetailLoading(true)
    bridge.callTool('container_inspect', { container_id:selectedId })
      .then(res => {
        if (!alive) return
        const payload = toolData(res)
        setDetail(payload?.container ? mapContainerDetail(payload.container) : null)
        setDetailLoading(false)
      })
      .catch(() => {
        if (!alive) return
        setDetail(null)
        setDetailLoading(false)
      })
    return () => { alive = false }
  }, [selectedId, bridge])

  const running = containers.filter(c => c.on).length
  const stopped = containers.length - running
  const selected = containers.find(c => c.id === selectedId) || null

  function runAction(toolName) {
    if (!selected?.actionsAllowed) return
    setActionState('Arbeite ...')
    bridge.callTool(toolName, { container_id:selected.id })
      .then(() => refreshContainers())
      .then(() => setActionState(toolName === 'stop_container' ? 'Stop angefragt.' : 'Start angefragt.'))
      .catch(err => setActionState(String(err?.message || 'Aktion fehlgeschlagen')))
  }

  return h('div', {},
    h(PanelHeader, {
      eyebrow:'Container Commander',
      title:'Status',
      subtitle:'Alle Container auf einen Blick — Prozesse, Ressourcen und Verfügbarkeit.',
      action: selected && selected.actionsAllowed ? h('div', { style:{display:'flex',gap:8,alignItems:'center'} },
        h('button', {
          className:'cc-btn',
          onClick:() => runAction('start_stopped_container'),
          disabled:selected.on,
          style:{opacity:selected.on ? .45 : 1}
        }, 'Start'),
        h('button', {
          className:'cc-btn',
          onClick:() => runAction('stop_container'),
          disabled:!selected.on,
          style:{opacity:selected.on ? 1 : .45}
        }, 'Stop')
      ) : null,
    }),
    isDemo && h(DemoBanner),
    actionState && h('div', { className:'cc-demo', style:{marginTop:10} }, actionState),
    h('div', { className:'cc-stats' },
      h('div', { className:'cc-stat', style:{background:'rgba(5,150,105,.07)',border:'.5px solid rgba(5,150,105,.2)'} },
        h('div', { className:'cc-sn', style:{color:'rgba(52,211,153,.9)'} }, running),
        h('div', { className:'cc-sl', style:{color:'rgba(52,211,153,.5)'} }, 'Running'),
      ),
      h('div', { className:'cc-stat', style:{background:'rgba(255,255,255,.02)',border:'.5px solid rgba(255,255,255,.07)'} },
        h('div', { className:'cc-sn', style:{color:'rgba(255,255,255,.5)'} }, stopped),
        h('div', { className:'cc-sl', style:{color:'rgba(255,255,255,.25)'} }, 'Stopped'),
      ),
      h('div', { className:'cc-stat', style:{background:'rgba(255,255,255,.02)',border:'.5px solid rgba(255,255,255,.07)'} },
        h('div', { className:'cc-sn', style:{color:'rgba(255,255,255,.3)'} }, 0),
        h('div', { className:'cc-sl', style:{color:'rgba(255,255,255,.2)'} }, 'Error'),
      ),
    ),
    h('div', { className:'cc-g2' },
      containers.map(c => h(ContainerCard, { key:c.id || c.name, c, active:selectedId === c.id, onSelect:(item) => setSelectedId(item.id) }))
    ),
    !isDemo && h(InspectPanel, { detail, loading:detailLoading })
  )
}

// ── Blueprints Tab ────────────────────────────────────────────────────────────
function BlueprintsTab({ bridge }) {
  const R = window.__TRION_REACT__
  const [bps, setBps] = R.useState(MOCK_BPS)
  const [demo, setDemo] = R.useState(false)
  const [selectedId, setSelectedId] = R.useState('')
  const [detail, setDetail] = R.useState(null)
  const [detailLoading, setDetailLoading] = R.useState(false)

  R.useEffect(() => {
    let alive = true
    bridge.callTool('blueprint_list', {})
      .then(res => {
        if (!alive) return
        const payload = toolData(res)
        const rows = Array.isArray(payload?.blueprints) ? payload.blueprints.map(mapBlueprintSummary) : []
        if (rows.length) {
          setBps(rows)
          setSelectedId(prev => prev || rows[0].id)
          setDemo(false)
        }
        else setDemo(true)
      })
      .catch(() => { if (alive) setDemo(true) })
    return () => { alive = false }
  }, [bridge])

  R.useEffect(() => {
    if (!selectedId) return
    let alive = true
    setDetailLoading(true)
    bridge.callTool('blueprint_get', { blueprint_id:selectedId })
      .then(res => {
        if (!alive) return
        const payload = toolData(res)
        setDetail(payload?.blueprint ? mapBlueprintDetail(payload.blueprint) : null)
        setDetailLoading(false)
      })
      .catch(() => {
        if (!alive) return
        setDetail(null)
        setDetailLoading(false)
      })
    return () => { alive = false }
  }, [selectedId, bridge])

  function BpCard({ bp }) {
    const inst = bp.inst
    return h('button', {
      className:'cc-ccard',
      onClick:() => setSelectedId(bp.id),
      style:{
        width:'100%',
        textAlign:'left',
        cursor:'pointer',
        boxShadow: selectedId === bp.id ? '0 0 0 1px rgba(59,130,246,.45) inset' : 'none'
      }
    },
      h('div', { style:{display:'flex',alignItems:'flex-start',justifyContent:'space-between',gap:8} },
        h('div', { style:{fontFamily:'var(--font-mono,monospace)',fontSize:11,color:'rgba(255,255,255,.85)'} }, bp.name),
        h('span', { className:'cc-badge', style: inst
          ? {background:'rgba(5,150,105,.08)',color:'rgba(52,211,153,.9)',border:'.5px solid rgba(5,150,105,.2)'}
          : {background:'rgba(59,130,246,.08)',color:'rgba(147,197,253,.9)',border:'.5px solid rgba(59,130,246,.2)'}
        }, inst ? 'Installed' : 'Verfügbar'),
      ),
      h('div', { style:{fontSize:11,color:'rgba(255,255,255,.4)',marginTop:5,lineHeight:1.4} }, bp.desc),
      bp.version && h('div', { style:{fontSize:10,color:'rgba(255,255,255,.28)',marginTop:6,fontFamily:'var(--font-mono,monospace)'} }, `version: ${bp.version}`),
      h('button', { className:'cc-btn', style:{marginTop:9,width:'100%',justifyContent:'center'} },
        inst ? 'Installed' : 'Verfügbar'
      ),
    )
  }

  function BlueprintDetailPanel({ detail, loading }) {
    if (!detail && !loading) return null
    const definition = detail?.definition || {}
    const ports = Array.isArray(definition.ports) ? definition.ports : []
    const mounts = Array.isArray(definition.mounts) ? definition.mounts : []
    const tags = Array.isArray(definition.tags) ? definition.tags : []
    const envEntries = Object.entries(definition.environment || {}).slice(0, 8)
    return h('div', { className:'cc-card' },
      h('div', { className:'cc-cl' }, 'Blueprint Details'),
      loading && h('div', { style:{fontSize:11,color:'rgba(255,255,255,.42)'} }, 'Lade Blueprint ...'),
      !loading && detail && h('div', {},
        h(DetailRow, { label:'Blueprint', value:detail.name }),
        h(DetailRow, { label:'Version', value:detail.version || '—' }),
        h(DetailRow, { label:'Image', value:definition.image || '—' }),
        h(DetailRow, { label:'Runtime', value:definition.runtime || '—' }),
        h(DetailRow, { label:'Icon', value:definition.icon || '—' }),
        h('div', { style:{marginTop:10} },
          h('div', { style:{fontSize:10,color:'rgba(255,255,255,.32)',textTransform:'uppercase',letterSpacing:'.08em',marginBottom:6} }, 'Description'),
          h('div', { style:{fontSize:11,color:'rgba(255,255,255,.72)',lineHeight:1.6} }, detail.desc || 'Keine Beschreibung'),
        ),
        h('div', { style:{marginTop:10} },
          h('div', { style:{fontSize:10,color:'rgba(255,255,255,.32)',textTransform:'uppercase',letterSpacing:'.08em',marginBottom:6} }, 'Ports'),
          ports.length
            ? ports.map((port, i) => h('div', { key:i, style:{fontSize:11,color:'rgba(255,255,255,.72)',fontFamily:'var(--font-mono,monospace)',padding:'3px 0'} }, String(port)))
            : h('div', { style:{fontSize:11,color:'rgba(255,255,255,.42)'} }, 'Keine Ports'),
        ),
        h('div', { style:{marginTop:10} },
          h('div', { style:{fontSize:10,color:'rgba(255,255,255,.32)',textTransform:'uppercase',letterSpacing:'.08em',marginBottom:6} }, 'Mounts'),
          mounts.length
            ? mounts.map((mount, i) => h('div', { key:i, style:{fontSize:11,color:'rgba(255,255,255,.72)',fontFamily:'var(--font-mono,monospace)',padding:'3px 0'} }, JSON.stringify(mount)))
            : h('div', { style:{fontSize:11,color:'rgba(255,255,255,.42)'} }, 'Keine Mounts'),
        ),
        h('div', { style:{marginTop:10} },
          h('div', { style:{fontSize:10,color:'rgba(255,255,255,.32)',textTransform:'uppercase',letterSpacing:'.08em',marginBottom:6} }, 'Environment'),
          envEntries.length
            ? envEntries.map(([key, value]) => h('div', { key, style:{fontSize:11,color:'rgba(255,255,255,.72)',fontFamily:'var(--font-mono,monospace)',padding:'3px 0'} }, `${key}=${value}`))
            : h('div', { style:{fontSize:11,color:'rgba(255,255,255,.42)'} }, 'Keine Environment-Werte'),
        ),
        h('div', { style:{marginTop:10} },
          h('div', { style:{fontSize:10,color:'rgba(255,255,255,.32)',textTransform:'uppercase',letterSpacing:'.08em',marginBottom:6} }, 'Tags'),
          tags.length
            ? tags.map((tag, i) => h('span', { key:i, className:'cc-badge', style:{background:'rgba(255,255,255,.05)',color:'rgba(255,255,255,.58)',border:'.5px solid rgba(255,255,255,.1)',marginRight:6} }, tag))
            : h('div', { style:{fontSize:11,color:'rgba(255,255,255,.42)'} }, 'Keine Tags'),
        )
      )
    )
  }

  return h('div', {},
    h(PanelHeader, {
      eyebrow:'Container Commander',
      title:'Blueprints',
      subtitle:'Vorgefertigte Container-Pakete installieren, verwalten und aktualisieren.',
    }),
    demo && h(DemoBanner),
    h('div', { className:'cc-g2' }, bps.map(bp => h(BpCard, { key:bp.id, bp }))),
    !demo && h(BlueprintDetailPanel, { detail, loading:detailLoading })
  )
}


// ── Dockerfile Tab ────────────────────────────────────────────────────────────
function DockerfileTab({ bridge }) {
  const R = window.__TRION_REACT__
  const names = MOCK_CONTAINERS.map(c => c.name)
  const [sel, setSel] = R.useState(names[0])
  const [src, setSrc] = R.useState(SAMPLE_DOCKERFILE)

  const lines = src.split('\n').map((line, i) => {
    const kw = line.match(/^(FROM|RUN|COPY|ENV|VOLUME|EXPOSE|CMD|ARG|WORKDIR|ENTRYPOINT|LABEL|USER|ADD)/)
    return h('div', { key:i },
      kw ? h('span', {}, h('span', { className:'cc-kw' }, kw[0]), line.slice(kw[0].length)) : line
    )
  })

  return h('div', {},
    h(PanelHeader, {
      eyebrow:'Container Commander',
      title:'Dockerfile',
      subtitle:'Dockerfile pro Container ansehen. Änderungen lösen einen Rebuild aus.',
    }),
    h(PlaceholderBanner, { state:PLACEHOLDER_STATE.dockerfile }),
    h('div', { className:'cc-card' },
      h('div', { className:'cc-cl' }, 'Container'),
      h('select', { className:'cc-sel', value:sel, onChange:e => setSel(e.target.value) },
        names.map(n => h('option', { key:n, value:n }, n))
      )
    ),
    h('div', { className:'cc-card' },
      h('div', { className:'cc-cl' }, `Dockerfile — ${sel}`),
      h('pre', { className:'cc-pre' }, lines)
    )
  )
}

// ── Resources Tab ─────────────────────────────────────────────────────────────
const RES_DATA = [
  { n:'trion-core',      cpu:'4 vCPU',  ram:'4 GB',   gpu:'—'        },
  { n:'jarvis-webui',    cpu:'1 vCPU',  ram:'512 MB', gpu:'—'        },
  { n:'sql-memory',      cpu:'2 vCPU',  ram:'2 GB',   gpu:'—'        },
  { n:'trion-admin-api', cpu:'1 vCPU',  ram:'512 MB', gpu:'—'        },
  { n:'container-cmdr',  cpu:'1 vCPU',  ram:'256 MB', gpu:'—'        },
  { n:'gaming-station',  cpu:'8 vCPU',  ram:'16 GB',  gpu:'RTX 3080' },
]

function ResourcesTab() {
  function Row({ r, i }) {
    return h('div', { className:'cc-rtbl cc-row', style:{background:i%2?'rgba(255,255,255,.015)':'transparent',borderRadius:6} },
      h('span', { style:{fontFamily:'var(--font-mono,monospace)',fontSize:11,color:'rgba(255,255,255,.8)'} }, r.n),
      h('span', { style:{fontSize:11,color:'rgba(255,255,255,.5)'} }, r.cpu),
      h('span', { style:{fontSize:11,color:'rgba(255,255,255,.5)'} }, r.ram),
      h('span', { style:{fontSize:11,color: r.gpu==='—'?'rgba(255,255,255,.3)':'rgba(250,204,21,.85)'} }, r.gpu),
    )
  }
  return h('div', {},
    h(PanelHeader, {
      eyebrow:'Container Commander',
      title:'Resources',
      subtitle:'CPU-, RAM-Limits und GPU-Zuweisung pro Container. Änderungen beim nächsten Start wirksam.',
    }),
    h(PlaceholderBanner, { state:PLACEHOLDER_STATE.resources }),
    h('div', { className:'cc-card' },
      h('div', { className:'cc-cl' }, 'Limits pro Container'),
      h('div', { className:'cc-rtbl cc-rtbl-hd' },
        h('span',{},'Container'), h('span',{},'CPU'), h('span',{},'RAM'), h('span',{},'GPU')
      ),
      RES_DATA.map((r,i) => h(Row, { key:r.n, r, i }))
    )
  )
}


// ── Security Tab ──────────────────────────────────────────────────────────────
const CAP_DROPPED  = ['CAP_SYS_ADMIN','CAP_NET_ADMIN','CAP_SYS_RAWIO','CAP_PTRACE']
const CAP_RETAINED = ['CAP_CHOWN','CAP_DAC_OVERRIDE','CAP_SETUID']

function SecurityTab() {
  function Toggle({ label, on }) {
    const knob = { position:'absolute',top:2,width:12,height:12,borderRadius:'50%',background:'#fff',transition:'transform .2s', transform:on?'translateX(14px)':'translateX(2px)' }
    return h('div', { style:{display:'flex',alignItems:'center',justifyContent:'space-between',padding:'5px 0',borderBottom:'.5px solid rgba(255,255,255,.05)'} },
      h('span', { style:{fontSize:12,color:'rgba(255,255,255,.6)'} }, label),
      h('div', { style:{position:'relative',width:28,height:16,borderRadius:8,background:on?'rgba(5,150,105,.7)':'rgba(255,255,255,.12)',cursor:'pointer'} },
        h('div', { style:knob })
      )
    )
  }
  return h('div', {},
    h(PanelHeader, {
      eyebrow:'Container Commander',
      title:'Security',
      subtitle:'Seccomp-Profile, Capabilities und Dateisystem-Isolation — basiert auf dem TRION Vault-Profil.',
    }),
    h(PlaceholderBanner, { state:PLACEHOLDER_STATE.security }),
    h('div', { className:'cc-card' },
      h('div', { className:'cc-cl' }, 'Seccomp-Profil'),
      h('div', { style:{display:'flex',alignItems:'center',justifyContent:'space-between'} },
        h('div', {},
          h('div', { style:{fontFamily:'var(--font-mono,monospace)',fontSize:12,color:'rgba(255,255,255,.8)'} }, 'trion-restricted.json'),
          h('div', { style:{fontSize:11,color:'rgba(255,255,255,.4)',marginTop:2} }, 'Custom — 312 syscalls whitelisted'),
        ),
        h('span', { className:'cc-badge', style:{background:'rgba(5,150,105,.12)',color:'rgba(52,211,153,.9)',border:'.5px solid rgba(5,150,105,.25)'} }, 'Active'),
      )
    ),
    h('div', { className:'cc-card' },
      h('div', { className:'cc-cl' }, 'Linux Capabilities'),
      h('div', { style:{fontSize:11,color:'rgba(255,255,255,.35)',marginBottom:6} }, 'Dropped'),
      h('div', { style:{display:'flex',flexWrap:'wrap',gap:5,marginBottom:12} },
        CAP_DROPPED.map(c => h('span', { key:c, className:'cc-badge', style:{background:'rgba(225,29,72,.08)',color:'rgba(251,113,133,.85)',border:'.5px solid rgba(225,29,72,.2)'} }, c))
      ),
      h('div', { style:{fontSize:11,color:'rgba(255,255,255,.35)',marginBottom:6} }, 'Retained'),
      h('div', { style:{display:'flex',flexWrap:'wrap',gap:5} },
        CAP_RETAINED.map(c => h('span', { key:c, className:'cc-badge', style:{background:'rgba(255,255,255,.05)',color:'rgba(255,255,255,.5)',border:'.5px solid rgba(255,255,255,.1)'} }, c))
      )
    ),
    h('div', { className:'cc-card' },
      h('div', { className:'cc-cl' }, 'Dateisystem'),
      h(Toggle, { label:'Read-only root filesystem', on:false }),
      h(Toggle, { label:'Noexec /tmp',              on:true  }),
      h(Toggle, { label:'No new privileges',         on:true  }),
    )
  )
}

// ── Logs Tab ──────────────────────────────────────────────────────────────────
function LogsTab({ bridge }) {
  const R = window.__TRION_REACT__
  const [containers, setContainers] = R.useState([])
  const [sel,  setSel]  = R.useState('')
  const [logs, setLogs] = R.useState(MOCK_LOGS)
  const [demo, setDemo] = R.useState(false)

  R.useEffect(() => {
    let alive = true
    bridge.callTool('container_list', {})
      .then(res => {
        if (!alive) return
        const payload = toolData(res)
        const rows = Array.isArray(payload?.containers) ? payload.containers.map(mapContainerSummary) : []
        setContainers(rows)
        if (rows[0] && !sel) setSel(rows[0].id)
      })
      .catch(() => {})
    return () => { alive = false }
  }, [bridge])

  R.useEffect(() => {
    if (!sel) return
    let alive = true
    setDemo(false)
    bridge.callTool('container_logs', { container_id:sel, tail:50, limit_chars:12000 })
      .then(res => {
        if (!alive) return
        const payload = toolData(res)
        const text = String(payload?.logs || '')
        if (!text) { setDemo(true); return }
        const parsed = text.split('\n').filter(Boolean).map(line => ({ t:'', l:'', m:line, c:'rgba(255,255,255,.65)' }))
        if (parsed.length) setLogs(parsed)
        else setDemo(true)
      })
      .catch(() => { if (alive) setDemo(true) })
    return () => { alive = false }
  }, [sel, bridge])

  return h('div', {},
    h(PanelHeader, {
      eyebrow:'Container Commander',
      title:'Logs',
      subtitle:'Read-only Log-Stream pro Container — kein Terminal nötig, keine Shell-Rechte erforderlich.',
    }),
    demo && h(DemoBanner),
    h('div', { className:'cc-card' },
      h('div', { className:'cc-cl' }, 'Container'),
      h('select', { className:'cc-sel', value:sel, onChange:e => setSel(e.target.value) },
        containers.map(c => h('option', { key:c.id, value:c.id }, c.name))
      )
    ),
    h('div', { className:'cc-card' },
      h('div', { style:{display:'flex',alignItems:'center',justifyContent:'space-between',marginBottom:10} },
        h('div', { className:'cc-cl', style:{margin:0} }, 'Output'),
        h('span', { className:'cc-badge', style:{background:'rgba(5,150,105,.1)',color:'rgba(52,211,153,.8)',border:'.5px solid rgba(5,150,105,.2)'} }, 'Live'),
      ),
      h('div', { style:{fontFamily:'var(--font-mono,monospace)',fontSize:11,lineHeight:1.8,color:'rgba(255,255,255,.65)'} },
        logs.map((l,i) => h('div', { key:i },
          l.t && h('span', { style:{color:'rgba(255,255,255,.25)'} }, `[2026-05-14 ${l.t}] `),
          l.l && h('span', { style:{color:l.c} }, `${l.l} `),
          h('span', { style:{color:'rgba(255,255,255,.65)'} }, l.m),
        ))
      )
    )
  )
}


// ── Root export ───────────────────────────────────────────────────────────────
export default function ContainerCommander({ plugin, bridge, assetUrl }) {
  const R = window.__TRION_REACT__
  const [tab, setTab] = R.useState('status')

  // Inject scoped CSS once on mount
  R.useEffect(() => {
    injectStyles()
    return () => {
      const el = document.getElementById('cc-styles')
      if (el) el.remove()
    }
  }, [])

  const containers = MOCK_CONTAINERS // used for sidebar footer counts
  const running = containers.filter(c => c.on).length
  const stopped = containers.length - running

  const content = {
    status:     h(StatusTab,     { key:'status',     bridge }),
    blueprints: h(BlueprintsTab, { key:'blueprints', bridge }),
    dockerfile: h(DockerfileTab, { key:'dockerfile', bridge }),
    resources:  h(ResourcesTab,  { key:'resources'         }),
    security:   h(SecurityTab,   { key:'security'          }),
    logs:       h(LogsTab,       { key:'logs',       bridge }),
  }

  return h('div', { className:'cc-root' },
    h(Sidebar, { active:tab, onSelect:setTab, running, stopped }),
    h('main', { className:'cc-ct' }, content[tab] ?? null)
  )
}
