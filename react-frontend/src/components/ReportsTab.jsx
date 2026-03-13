import { useState } from 'react'
import { API, apiFetch } from '../config.js'

const REPORT_TYPES = [
  { value: 'daily_summary',       label: 'Daily Access Summary' },
  { value: 'weekly_security',     label: 'Weekly Security Report' },
  { value: 'monthly_compliance',  label: 'Monthly Compliance' },
  { value: 'btg_justification',   label: 'BTG Justification Report' },
  { value: 'breach_investigation',label: 'Breach Investigation' },
]

export default function ReportsTab() {
  const [type, setType] = useState('daily_summary')
  const [loading, setLoading] = useState(false)
  const [report, setReport] = useState(null)

  async function generate() {
    setLoading(true)
    const r = await apiFetch(`${API.L8}/api/v1/reports/generate`, {
      method: 'POST',
      body: JSON.stringify({ report_type: type }),
    })
    setReport(r.data)
    setLoading(false)
  }

  return (
    <div className="col">
      <div className="card">
        <div className="card-title">📊 Generate Compliance Report</div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 11, color: 'var(--text3)', marginBottom: 4 }}>Report Type</div>
            <select value={type} onChange={e => setType(e.target.value)}>
              {REPORT_TYPES.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
            </select>
          </div>
          <button className="btn btn-primary" onClick={generate} disabled={loading}>
            {loading ? <><span className="spinner" /> Generating…</> : '⚙ Generate Report'}
          </button>
        </div>
      </div>

      {report && (
        <div className="card">
          <div className="card-title">Report Output</div>
          {typeof report === 'string'
            ? <div className="report-block">{report}</div>
            : <pre className="report-block">{JSON.stringify(report, null, 2)}</pre>}
        </div>
      )}

      {!report && (
        <div className="empty">
          <div className="empty-icon">📄</div>
          Select a report type and click Generate
        </div>
      )}
    </div>
  )
}
