import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

const API = 'http://localhost:8000/api/v1'

const EXAMPLES = [
  'stripe.com', 'notion.so', 'linear.app', 'vercel.com', 'figma.com'
]

export default function Home() {
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!url.trim()) return
    setLoading(true)
    setError('')
    try {
      const res = await fetch(`${API}/audit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url.trim() }),
      })
      if (!res.ok) throw new Error(`Server error: ${res.status}`)
      const data = await res.json()
      navigate(`/audit/${data.audit_id}/progress`)
    } catch (err) {
      setError(err.message || 'Failed to start audit. Is the backend running?')
      setLoading(false)
    }
  }

  return (
    <div className="home-page">
      <div className="hero">
        <div className="hero-badge">
          <span className="pulse-dot" />
          AI-Powered Analysis
        </div>
        <h1 className="hero-title">
          Audit Any Website in <span className="gradient-text">60 Seconds</span>
        </h1>
        <p className="hero-subtitle">
          8 specialized AI agents analyze your site across every marketing dimension.
          Scored, actionable intelligence — powered by NVIDIA NIM.
        </p>

        <form className="audit-form" onSubmit={handleSubmit}>
          <div className="input-group">
            <span className="input-icon">🌐</span>
            <input
              className="url-input"
              type="text"
              placeholder="Enter any website URL (e.g. stripe.com)"
              value={url}
              onChange={e => setUrl(e.target.value)}
              disabled={loading}
              autoFocus
            />
            <button className="audit-btn" type="submit" disabled={loading || !url.trim()}>
              {loading ? <span className="spinner" /> : '⚡ Analyze'}
            </button>
          </div>
          {error && <div className="error-msg">⚠ {error}</div>}
        </form>

        <div className="examples">
          <span className="examples-label">Try:</span>
          {EXAMPLES.map(ex => (
            <button key={ex} className="example-chip" onClick={() => setUrl(ex)}>
              {ex}
            </button>
          ))}
        </div>
      </div>

      <div className="agents-grid">
        {AGENT_CARDS.map(agent => (
          <div key={agent.name} className="agent-card">
            <div className="agent-icon">{agent.icon}</div>
            <div className="agent-name">{agent.name}</div>
            <div className="agent-desc">{agent.desc}</div>
            <div className="agent-weight">{agent.weight}</div>
          </div>
        ))}
      </div>

      <div className="stats-row">
        <div className="stat"><span className="stat-num">8</span><span className="stat-label">AI Agents</span></div>
        <div className="stat"><span className="stat-num">60s</span><span className="stat-label">Analysis Time</span></div>
        <div className="stat"><span className="stat-num">NVIDIA</span><span className="stat-label">Primary LLM</span></div>
        <div className="stat"><span className="stat-num">PDF</span><span className="stat-label">Report Export</span></div>
      </div>
    </div>
  )
}

const AGENT_CARDS = [
  { name: 'Content & Messaging', icon: '✍️', desc: 'Headline clarity, value prop, copy quality', weight: '15%' },
  { name: 'Business Strategy', icon: '♟️', desc: 'Positioning, pricing, growth loops', weight: '13%' },
  { name: 'Conversion', icon: '🎯', desc: 'CTAs, trust signals, funnel friction', weight: '12%' },
  { name: 'Technical SEO', icon: '🔍', desc: 'Meta tags, schema, indexability', weight: '12%' },
  { name: 'Web Vitals', icon: '⚡', desc: 'LCP, CLS, INP via PageSpeed API', weight: '8%' },
  { name: 'Competitive Intel', icon: '🏆', desc: 'Differentiation, moat, positioning', weight: '8%' },
  { name: 'Accessibility', icon: '♿', desc: 'WCAG 2.1 compliance, ARIA', weight: '6%' },
  { name: 'Security & Trust', icon: '🔒', desc: 'HTTPS, headers, privacy signals', weight: '4%' },
]
