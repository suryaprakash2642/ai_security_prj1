import { useState } from 'react'

export default function Accordion({ layerId, title, data, status = 'success' }) {
  const [open, setOpen] = useState(false)
  const dotColor = status === 'success' ? 'var(--green)' : status === 'error' ? '#ef4444' : 'var(--yellow)'

  return (
    <div className="accordion">
      <div className="accordion-header" onClick={() => setOpen(o => !o)}>
        <div style={{ width: 7, height: 7, borderRadius: '50%', background: dotColor, flexShrink: 0 }} />
        <span className={`ltag ltag-${layerId}`}>{layerId.toUpperCase()}</span>
        <span className="accordion-title">{title}</span>
        <span className={`accordion-chevron ${open ? 'open' : ''}`}>▼</span>
      </div>
      {open && (
        <div className="accordion-body">
          <pre>{JSON.stringify(data, null, 2)}</pre>
        </div>
      )}
    </div>
  )
}
