import { useState } from 'react'
import Sidebar from './components/Sidebar.jsx'
import QueryTab from './components/QueryTab.jsx'
import AuditTab from './components/AuditTab.jsx'
import AlertsTab from './components/AlertsTab.jsx'
import ReportsTab from './components/ReportsTab.jsx'
import { useToast } from './useToast.jsx'
import { usePipeline } from './hooks/usePipeline.js'

export default function App() {
  const { toast, ToastContainer } = useToast()
  const { auth, layerStates, pipelineState, handleLogin, handleLogout, runPipeline } = usePipeline(toast)
  const [tab, setTab] = useState('query')

  const tabs = [
    { id: 'query',   label: '🔍 Query' },
    { id: 'audit',   label: '📋 Audit Log' },
    { id: 'alerts',  label: '🚨 Alerts' },
    { id: 'reports', label: '📊 Reports' },
  ]

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="topbar-logo">
          <div className="topbar-logo-icon">🏥</div>
          <div>
            <div className="topbar-title">Apollo Hospitals — Zero Trust NL-to-SQL</div>
            <div className="topbar-sub">8-Layer AI Security Pipeline · L1 → L2 → L3 → L4 → L5 → L6 → L7 → L8</div>
          </div>
        </div>
        <div className="topbar-spacer" />
        <div className="topbar-chips">
          {auth
            ? <span className="chip chip-green">✓ {auth.user_id}</span>
            : <span className="chip chip-red">Not Authenticated</span>}
          {pipelineState.running && <span className="chip chip-blue"><span className="spinner" /> Running</span>}
        </div>
      </header>

      <Sidebar auth={auth} onLogin={handleLogin} onLogout={handleLogout} layerStates={layerStates} />

      <main className="main">
        <div className="tabs">
          {tabs.map(t => (
            <button key={t.id} className={`tab-btn ${tab === t.id ? 'active' : ''}`} onClick={() => setTab(t.id)}>
              {t.label}
            </button>
          ))}
        </div>

        {tab === 'query'   && <QueryTab auth={auth} pipelineState={pipelineState} onRun={runPipeline} />}
        {tab === 'audit'   && <AuditTab />}
        {tab === 'alerts'  && <AlertsTab />}
        {tab === 'reports' && <ReportsTab />}
      </main>

      <ToastContainer />
    </div>
  )
}
