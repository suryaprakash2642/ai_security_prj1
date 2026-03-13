import { useState, useEffect } from 'react'
import { HEALTH_ENDPOINTS, LAYERS, apiFetch } from '../config.js'

export default function Sidebar({ auth, onLogin, onLogout, layerStates }) {
  const [userKey, setUserKey] = useState('physician')
  const [loggingIn, setLoggingIn] = useState(false)
  const [health, setHealth] = useState({})
  const [healthChecking, setHealthChecking] = useState(false)

  async function checkHealth() {
    setHealthChecking(true)
    const results = {}
    await Promise.all(
      HEALTH_ENDPOINTS.map(async (s) => {
        const r = await apiFetch(s.url)
        results[s.id] = r.ok ? 'up' : 'down'
      })
    )
    setHealth(results)
    setHealthChecking(false)
  }

  useEffect(() => { checkHealth() }, [])

  async function handleLogin() {
    setLoggingIn(true)
    await onLogin(userKey)
    setLoggingIn(false)
  }

  return (
    <aside className="sidebar">
      {/* Identity / Login */}
      <div>
        <div className="sidebar-section-label">Identity — L1</div>
        <select value={userKey} onChange={e => setUserKey(e.target.value)} disabled={!!auth}>
          <option value="physician">Dr. Rajesh Patel — Attending Physician (Clinical)</option>
          <option value="nurse">Anita Kumar — Registered Nurse (Clinical)</option>
          <option value="billing">Maria Fernandes — Billing Clerk (Business)</option>
          <option value="admin">Vikram Joshi — IT Administrator (IT)</option>
          <option value="hr">Priya Mehta — HR Manager (HR)</option>
          <option value="revenue">James Thomas — Revenue Cycle Manager (Business)</option>
          <option value="researcher">Dr. Anirban Das — Clinical Researcher (Analytics)</option>
        </select>

        <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
          <button
            className="btn btn-primary"
            style={{ flex: 1 }}
            onClick={handleLogin}
            disabled={!!auth || loggingIn}
          >
            {loggingIn ? <><span className="spinner" /> Authenticating…</> : '⚡ Login'}
          </button>
          <button
            className="btn btn-ghost"
            onClick={onLogout}
            disabled={!auth}
          >
            Logout
          </button>
        </div>

        {auth && (
          <div className="auth-panel" style={{ marginTop: 10 }}>
            <div><span className="k">user_id:</span> {auth.user_id || '—'}</div>
            <div><span className="k">roles:</span> {(auth.effective_roles || []).join(', ')}</div>
            <div><span className="k">clearance:</span> {auth.clearance_level ?? '—'}</div>
            <div><span className="k">dept:</span> {auth.department || '—'}</div>
          </div>
        )}
      </div>

      {/* Pipeline Layers */}
      <div>
        <div className="sidebar-section-label">Pipeline Layers</div>
        {LAYERS.map(l => {
          const st = layerStates[l.id] || ''
          return (
            <div key={l.id} className={`layer-row ${st ? `state-${st}` : ''}`}>
              <div className="layer-dot" />
              <div className="layer-name">
                <span className={`ltag ltag-${l.id}`}>{l.id.toUpperCase()}</span>{' '}
                {l.label}
              </div>
              {layerStates[l.id + '_ms'] != null && (
                <div className="layer-ms">{layerStates[l.id + '_ms']}ms</div>
              )}
            </div>
          )
        })}
      </div>

      {/* Health */}
      <div>
        <div className="sidebar-section-label">Service Health</div>
        {HEALTH_ENDPOINTS.map(s => (
          <div key={s.id} className="health-row">
            <div className={`health-dot ${health[s.id] || ''}`} />
            <div className="health-name">{s.name}</div>
            <div className="health-status" style={{ color: health[s.id] === 'up' ? 'var(--green)' : health[s.id] === 'down' ? '#ef4444' : 'var(--text3)' }}>
              {health[s.id] === 'up' ? '✓' : health[s.id] === 'down' ? '✗' : '…'}
            </div>
          </div>
        ))}
        <button
          className="btn btn-ghost btn-sm"
          style={{ width: '100%', marginTop: 8 }}
          onClick={checkHealth}
          disabled={healthChecking}
        >
          {healthChecking ? <><span className="spinner" /> Checking…</> : '↻ Refresh'}
        </button>
      </div>
    </aside>
  )
}
