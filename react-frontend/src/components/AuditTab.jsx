import { useState } from 'react'
import { API, apiFetch } from '../config.js'

export default function AuditTab() {
  const [layer, setLayer] = useState('')
  const [severity, setSeverity] = useState('')
  const [userId, setUserId] = useState('')
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState(null)
  const [chainResult, setChainResult] = useState(null)
  const [openRows, setOpenRows] = useState({})

  async function search() {
    setLoading(true)
    const body = {
      filters: {},
      pagination: { offset: 0, limit: 50 },
      sort: { field: 'timestamp', order: 'desc' },
    }
    if (layer) body.filters.source_layer = [layer]
    if (severity) body.filters.severity = [severity]
    if (userId) body.filters.user_id = userId
    const r = await apiFetch(`${API.L8}/api/v1/audit/query`, {
      method: 'POST',
      body: JSON.stringify(body),
    })
    setResults(r.ok ? (r.data.events || r.data.entries || r.data.logs || []) : [])
    setLoading(false)
  }

  async function verifyChain() {
    setLoading(true)
    const target = layer || 'L7'
    const r = await apiFetch(`${API.L8}/api/v1/audit/integrity/${target}`)
    setChainResult(r.data)
    setLoading(false)
  }

  const entries = Array.isArray(results) ? results : []

  return (
    <div className="col">
      <div className="card">
        <div className="card-title">🔎 Audit Log Query</div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <select value={layer} onChange={e => setLayer(e.target.value)} style={{ width: 130 }}>
            <option value="">All Layers</option>
            {['L1','L2','L3','L4','L5','L6','L7','L8'].map(l => <option key={l}>{l}</option>)}
          </select>
          <select value={severity} onChange={e => setSeverity(e.target.value)} style={{ width: 130 }}>
            <option value="">All Severities</option>
            {['INFO','WARNING','HIGH','CRITICAL'].map(s => <option key={s}>{s}</option>)}
          </select>
          <input
            value={userId}
            onChange={e => setUserId(e.target.value)}
            placeholder="Filter by user_id"
            style={{ width: 180 }}
          />
          <button className="btn btn-primary" onClick={search} disabled={loading}>
            {loading ? <><span className="spinner" /> Searching…</> : '🔍 Search'}
          </button>
          <button className="btn btn-ghost" onClick={verifyChain} disabled={loading}>
            ⛓ Verify Chain
          </button>
        </div>
      </div>

      {chainResult && (
        <div className="card">
          <div className="card-title">Hash Chain Integrity</div>
          <pre style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: 'var(--text2)', whiteSpace: 'pre-wrap' }}>
            {JSON.stringify(chainResult, null, 2)}
          </pre>
        </div>
      )}

      {results === null
        ? <div className="empty"><div className="empty-icon">📋</div>Run a search to view audit logs</div>
        : entries.length === 0
          ? <div className="empty"><div className="empty-icon">📭</div>No entries found</div>
          : entries.map((e, i) => {
            const isOpen = openRows[i]
            const sevColor = { CRITICAL: '#ef4444', HIGH: 'var(--yellow)', WARNING: '#94a3b8', INFO: 'var(--blue-light)' }[e.severity] || 'var(--text3)'
            return (
              <div key={i} className="audit-row">
                <div className="audit-row-header" onClick={() => setOpenRows(o => ({ ...o, [i]: !o[i] }))}>
                  <span style={{ color: sevColor, fontSize: 11, fontWeight: 700, minWidth: 60 }}>{e.severity || 'INFO'}</span>
                  {(e.source_layer || e.layer) && <span className={`ltag ltag-${(e.source_layer || e.layer).toLowerCase()}`}>{e.source_layer || e.layer}</span>}
                  <span style={{ fontSize: 12, flex: 1 }}>{e.action || e.event_type || 'Event'}</span>
                  <span style={{ fontSize: 11, color: 'var(--text3)' }}>{e.timestamp ? new Date(e.timestamp).toLocaleTimeString() : ''}</span>
                  <span style={{ fontSize: 10, color: 'var(--text3)' }}>{isOpen ? '▲' : '▼'}</span>
                </div>
                {isOpen && (
                  <div className="audit-row-body">
                    <pre>{JSON.stringify(e, null, 2)}</pre>
                  </div>
                )}
              </div>
            )
          })
      }
    </div>
  )
}
