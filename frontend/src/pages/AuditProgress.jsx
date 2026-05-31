import { useEffect, useState, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'

const API = 'http://localhost:8000/api/v1'

const AGENT_LABELS = {
  content: 'Content & Messaging',
  strategy: 'Business Strategy',
  conversion: 'Conversion Optimization',
  technical: 'Technical SEO',
  webvitals: 'Web Vitals & Performance',
  competitive: 'Competitive Intelligence',
  accessibility: 'Accessibility (WCAG)',
  security: 'Security & Trust',
}

const AGENT_ICONS = {
  content: '✍️', strategy: '♟️', conversion: '🎯', technical: '🔍',
  webvitals: '⚡', competitive: '🏆', accessibility: '♿', security: '🔒',
}

const STATUS_LABELS = {
  queued: 'Queued',
  crawling: 'Crawling website...',
  analyzing: 'Running AI agents...',
  scoring: 'Computing scores...',
  generating_report: 'Generating PDF report...',
  completed: 'Completed!',
  failed: 'Failed',
}

export default function AuditProgress() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [audit, setAudit] = useState(null)
  const [error, setError] = useState('')
  const intervalRef = useRef(null)

  const poll = async () => {
    try {
      const res = await fetch(`${API}/audit/${id}`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setAudit(data)
      if (data.status === 'completed') {
        clearInterval(intervalRef.current)
        setTimeout(() => navigate(`/audit/${id}/results`), 800)
      } else if (data.status === 'failed') {
        clearInterval(intervalRef.current)
        setError(data.error_message || 'Audit failed')
      }
    } catch (err) {
      setError(err.message)
      clearInterval(intervalRef.current)
    }
  }

  useEffect(() => {
    poll()
    intervalRef.current = setInterval(poll, 2000)
    return () => clearInterval(intervalRef.current)
  }, [id])

  const progress = audit ? (audit.agents_completed / (audit.agents_total || 8)) * 100 : 0
  const completedAgents = audit?.modules ? Object.keys(audit.modules) : []

  return (
    <div className="progress-page">
      <div className="progress-card">
        <div className="progress-header">
          <div className="progress-pulse">
            <div className="pulse-ring" />
            <span className="pulse-icon">⚡</span>
          </div>
          <h2 className="progress-title">Analyzing Your Website</h2>
          <p className="progress-url">{audit?.url || 'Loading...'}</p>
        </div>

        <div className="status-badge">
          {STATUS_LABELS[audit?.status] || 'Starting...'}
        </div>

        <div className="progress-bar-wrap">
          <div className="progress-bar-track">
            <div
              className="progress-bar-fill"
              style={{ width: `${Math.max(5, progress)}%` }}
            />
          </div>
          <span className="progress-pct">{Math.round(progress)}%</span>
        </div>

        <div className="agent-progress-grid">
          {Object.keys(AGENT_LABELS).map(key => {
            const done = completedAgents.includes(key)
            const active = audit?.current_agent === key
            return (
              <div
                key={key}
                className={`agent-progress-item ${done ? 'done' : ''} ${active ? 'active' : ''}`}
              >
                <span className="ap-icon">{AGENT_ICONS[key]}</span>
                <span className="ap-name">{AGENT_LABELS[key]}</span>
                <span className="ap-status">
                  {done ? '✓' : active ? <span className="mini-spinner" /> : '○'}
                </span>
              </div>
            )
          })}
        </div>

        {error && (
          <div className="error-box">
            <strong>Error:</strong> {error}
          </div>
        )}
      </div>
    </div>
  )
}
