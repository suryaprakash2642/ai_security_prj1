import { useState, useEffect } from 'react'
import { API, apiFetch } from '../config.js'

export default function AlertsTab() {
  const [status, setStatus] = useState('')
  const [severity, setSeverity] = useState('')
  const [alerts, setAlerts] = useState(null)
  const [loading, setLoading] = useState(false)

  async function load() {
    setLoading(true)
    const params = new URLSearchParams()
    if (status) params.set('status', status)
    if (severity) params.set('severity', severity)
    params.set('limit', '50')
    const r = await apiFetch(`${API.L8}/api/v1/alerts?${params}`)
    setAlerts(r.ok ? (r.data.alerts || r.data || []) : [])
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  const items = Array.isArray(alerts) ? alerts : []

  return (
    <div className="col">
      <div className="card">
        <div className="card-title">🚨 Anomaly Alerts</div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
          <select value={status} onChange={e => setStatus(e.target.value)} style={{ width: 150 }}>
            <option value="">All Statuses</option>
            <option value="OPEN">Open</option>
            <option value="ACKNOWLEDGED">Acknowledged</option>
            <option value="RESOLVED">Resolved</option>
          </select>
          <select value={severity} onChange={e => setSeverity(e.target.value)} style={{ width: 140 }}>
            <option value="">All Severities</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="WARNING">Warning</option>
          </select>
          <button className="btn btn-primary" onClick={load} disabled={loading}>
            {loading ? <><span className="spinner" /> Loading…</> : '↻ Refresh'}
          </button>
        </div>
      </div>

      {alerts === null
        ? <div className="empty"><div className="empty-icon">🔔</div>Loading alerts…</div>
        : items.length === 0
          ? <div className="empty"><div className="empty-icon">✅</div>No alerts found</div>
          : items.map((a, i) => (
            <div key={i} className={`alert-card ${a.severity || 'INFO'}`}>
              <div className="flex-center">
                <span style={{ fontWeight: 700, fontSize: 11 }}>{a.severity || 'INFO'}</span>
                {a.status && (
                  <span className={`chip ${a.status === 'OPEN' ? 'chip-red' : a.status === 'RESOLVED' ? 'chip-green' : 'chip-yellow'}`} style={{ marginLeft: 8 }}>
                    {a.status}
                  </span>
                )}
              </div>
              <div className="alert-title" style={{ marginTop: 4 }}>{a.alert_type || a.type || 'Alert'}</div>
              {a.message && <div style={{ fontSize: 12, color: 'var(--text2)', marginTop: 4 }}>{a.message}</div>}
              <div className="alert-meta">
                {a.user_id && <span>user: {a.user_id} · </span>}
                {a.layer && <span>layer: {a.layer} · </span>}
                {a.timestamp && <span>{new Date(a.timestamp).toLocaleString()}</span>}
              </div>
            </div>
          ))
      }
    </div>
  )
}
