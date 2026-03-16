import { useState } from 'react'
import Accordion from './Accordion.jsx'

const PIPE_STEPS = [
  { id: 'l1', label: 'L1\nIdentity' },
  { id: 'l2', label: 'L2\nKnowledge' },
  { id: 'l3', label: 'L3\nRetrieval' },
  { id: 'l4', label: 'L4\nPolicy' },
  { id: 'l5', label: 'L5\nGeneration' },
  { id: 'l6', label: 'L6\nValidation' },
  { id: 'l7', label: 'L7\nExecution' },
  { id: 'l8', label: 'L8\nAudit' },
]

const QUICK = [
  { label: 'Admissions', q: 'Show all patients admitted this month' },
  { label: 'Hypertension', q: 'Get all encounters with diagnosis hypertension in the last 30 days' },
  { label: 'Patient contacts', q: 'List patients with their contact information' },
  { label: 'ICU labs', q: 'Show all lab results for ICU patients' },
  { label: '⚠ Injection test', q: 'DROP TABLE patients' },
]

export default function QueryTab({ auth, pipelineState, onRun }) {
  const [query, setQuery] = useState('')
  const { running, pipeSteps, pipeStatus, sql, sqlDialect, detectedDb, detectedDialect,
    valDetail, valDecision, results, resultCols, execMetrics, layerDetails, shown } = pipelineState

  return (
    <div className="col">
      {/* Query Input */}
      <div className="card">
        <div className="card-title">🔍 Natural Language Query</div>
        <div className="row" style={{ alignItems: 'flex-start' }}>
          <textarea
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Ask a clinical question, e.g.: Show me all patients admitted this month with diagnosis of hypertension"
            rows={3}
            onKeyDown={e => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) onRun(query) }}
          />
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6, flex: '0 0 auto' }}>
            <button
              className="btn btn-success"
              id="btn-run"
              onClick={() => onRun(query)}
              disabled={!auth || running}
            >
              {running ? <><span className="spinner" /> Running…</> : '▶ Run'}
            </button>
            <button className="btn btn-ghost" onClick={() => setQuery('')}>✕ Clear</button>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 10, alignItems: 'center' }}>
          <span style={{ fontSize: 11, color: 'var(--text3)' }}>Quick:</span>
          {QUICK.map(q => (
            <button key={q.label} className="btn btn-ghost btn-sm" onClick={() => setQuery(q.q)}>
              {q.label}
            </button>
          ))}
        </div>
      </div>

      {/* Pipeline Viz */}
      {shown && (
        <div className="card">
          <div className="card-title">Pipeline Progress</div>
          <div className="pipeline-viz">
            {PIPE_STEPS.map((s, i) => {
              const st = pipeSteps[s.id] || 'pending'
              return (
                <div key={s.id} className="pipe-node">
                  <div className={`pipe-box ${st}`}>
                    {s.label.split('\n').map((l, j) => (
                      <span key={j}>{j > 0 && <br />}{l}</span>
                    ))}
                  </div>
                  {i < PIPE_STEPS.length - 1 && <div className="pipe-arrow">→</div>}
                </div>
              )
            })}
          </div>
          {pipeStatus && (
            <div style={{ fontSize: 12, color: 'var(--text3)', marginTop: 8 }}>{pipeStatus}</div>
          )}
          {detectedDialect && (
            <div style={{ display: 'flex', gap: 8, marginTop: 10, alignItems: 'center', fontSize: 12 }}>
              <span style={{ color: 'var(--text3)' }}>Dialect:</span>
              <span className="chip chip-green">{detectedDialect.toUpperCase()}</span>
              {detectedDb && (
                <>
                  <span style={{ color: 'var(--text3)' }}>Database:</span>
                  <span className="chip chip-blue" style={{ background: 'var(--accent)', color: '#fff' }}>{detectedDb}</span>
                </>
              )}
            </div>
          )}
        </div>
      )}

      {/* SQL + Validation */}
      {sql && (
        <div className="row">
          <div className="card">
            <div className="card-title">
              Generated SQL{' '}
              {sqlDialect && <span className="ltag ltag-l5">{sqlDialect.toUpperCase()}</span>}
            </div>
            <div className="sql-block">{sql}</div>
          </div>
          <div className="card">
            <div className="card-title">
              Validation Result{' '}
              {valDecision && (
                <span className={`chip ${valDecision === 'APPROVED' ? 'chip-green' : valDecision === 'BLOCKED' ? 'chip-red' : 'chip-yellow'}`}>
                  {valDecision}
                </span>
              )}
            </div>
            {valDetail ? (
              <div style={{ fontSize: 12, color: 'var(--text2)' }}>
                {typeof valDetail === 'string'
                  ? <pre style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, whiteSpace: 'pre-wrap' }}>{valDetail}</pre>
                  : Object.entries(valDetail).map(([k, v]) => (
                    <div key={k} style={{ marginBottom: 4 }}>
                      <span style={{ color: 'var(--text3)' }}>{k}:</span>{' '}
                      <span>{JSON.stringify(v)}</span>
                    </div>
                  ))}
              </div>
            ) : <div className="empty"><div className="empty-icon">🛡</div>Awaiting validation</div>}
          </div>
        </div>
      )}

      {/* Results */}
      {results && (
        <div className="card">
          <div className="card-title">
            Query Results{' '}
            {results.length > 0 && <span className="chip chip-green">{results.length} rows</span>}
            {execMetrics?.truncated && <span className="chip chip-yellow" style={{ marginLeft: 4 }}>TRUNCATED</span>}
          </div>
          {execMetrics && Object.keys(execMetrics).length > 0 && (
            <div className="metrics-grid" style={{ marginBottom: 12 }}>
              {execMetrics.rows_returned != null && <div className="metric-card"><div className="metric-val">{execMetrics.rows_returned}</div><div className="metric-label">Rows</div></div>}
              {execMetrics.execution_time_ms != null && <div className="metric-card"><div className="metric-val">{execMetrics.execution_time_ms}</div><div className="metric-label">ms</div></div>}
              {execMetrics.columns_masked != null && <div className="metric-card"><div className="metric-val">{execMetrics.columns_masked}</div><div className="metric-label">Masked cols</div></div>}
            </div>
          )}
          {results.length === 0
            ? <div className="empty"><div className="empty-icon">📭</div>No rows returned</div>
            : (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>{resultCols.map(c => <th key={c}>{c}</th>)}</tr>
                  </thead>
                  <tbody>
                    {results.map((row, i) => (
                      <tr key={i}>
                        {resultCols.map(c => (
                          <td key={c}>
                            {row[c] === '***MASKED***'
                              ? <span style={{ color: 'var(--yellow)', fontStyle: 'italic' }}>***MASKED***</span>
                              : String(row[c] ?? '')}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
        </div>
      )}

      {/* Layer Detail Accordions */}
      {layerDetails.length > 0 && (
        <div>
          {layerDetails.map((d, i) => (
            <Accordion key={i} layerId={d.layerId} title={d.title} data={d.data} status={d.status} />
          ))}
        </div>
      )}
    </div>
  )
}
