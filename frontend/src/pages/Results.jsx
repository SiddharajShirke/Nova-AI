import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'

const API = 'http://localhost:8000/api/v1'

const AGENT_LABELS = {
  content: 'Content & Messaging', strategy: 'Business Strategy',
  conversion: 'Conversion', technical: 'Technical SEO',
  webvitals: 'Web Vitals', competitive: 'Competitive Intel',
  accessibility: 'Accessibility', security: 'Security',
}
const AGENT_ICONS = {
  content: '✍️', strategy: '♟️', conversion: '🎯', technical: '🔍',
  webvitals: '⚡', competitive: '🏆', accessibility: '♿', security: '🔒',
}

function gradeColor(grade) {
  if (!grade) return '#64748B'
  if (grade.startsWith('A')) return '#10B981'
  if (grade.startsWith('B')) return '#3B82F6'
  if (grade.startsWith('C')) return '#F59E0B'
  return '#EF4444'
}

function ScoreRing({ score, grade, size = 120 }) {
  const r = (size / 2) - 12
  const circ = 2 * Math.PI * r
  const filled = ((score || 0) / 100) * circ
  const color = gradeColor(grade)

  return (
    <div className="score-ring-wrap" style={{ width: size, height: size }}>
      <svg width={size} height={size}>
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="#1E293B" strokeWidth="10" />
        <circle
          cx={size/2} cy={size/2} r={r}
          fill="none" stroke={color} strokeWidth="10"
          strokeDasharray={`${filled} ${circ - filled}`}
          strokeLinecap="round"
          transform={`rotate(-90 ${size/2} ${size/2})`}
          style={{ transition: 'stroke-dasharray 1s ease' }}
        />
      </svg>
      <div className="score-ring-inner">
        <span className="score-num" style={{ color }}>{Math.round(score || 0)}</span>
        <span className="score-grade" style={{ color }}>{grade}</span>
      </div>
    </div>
  )
}

function RadarChart({ modules }) {
  const entries = Object.entries(modules || {}).filter(([, v]) => !v.error)
  if (entries.length < 3) return null
  const cx = 150, cy = 150, r = 110
  const n = entries.length
  const points = entries.map(([, v], i) => {
    const angle = (i / n) * 2 * Math.PI - Math.PI / 2
    const pct = (v.score || 0) / 100
    return { x: cx + r * pct * Math.cos(angle), y: cy + r * pct * Math.sin(angle) }
  })
  const polygon = points.map(p => `${p.x},${p.y}`).join(' ')
  const labels = entries.map(([k, v], i) => {
    const angle = (i / n) * 2 * Math.PI - Math.PI / 2
    const lx = cx + (r + 24) * Math.cos(angle)
    const ly = cy + (r + 24) * Math.sin(angle)
    return { x: lx, y: ly, label: AGENT_LABELS[k] || k, score: v.score }
  })
  const rings = [0.25, 0.5, 0.75, 1.0]

  return (
    <div className="radar-wrap">
      <svg width="300" height="300" viewBox="0 0 300 300">
        {rings.map(pct => {
          const pts = entries.map((_, i) => {
            const angle = (i / n) * 2 * Math.PI - Math.PI / 2
            return `${cx + r * pct * Math.cos(angle)},${cy + r * pct * Math.sin(angle)}`
          }).join(' ')
          return <polygon key={pct} points={pts} fill="none" stroke="#1E293B" strokeWidth="1" />
        })}
        {entries.map((_, i) => {
          const angle = (i / n) * 2 * Math.PI - Math.PI / 2
          return <line key={i} x1={cx} y1={cy} x2={cx + r * Math.cos(angle)} y2={cy + r * Math.sin(angle)} stroke="#1E293B" strokeWidth="1" />
        })}
        <polygon points={polygon} fill="rgba(99,102,241,0.25)" stroke="#6366F1" strokeWidth="2" />
        {labels.map((l, i) => (
          <text key={i} x={l.x} y={l.y} textAnchor="middle" dominantBaseline="middle"
            fontSize="9" fill="#94A3B8" fontFamily="Inter, sans-serif">
            {l.label.split(' ')[0]}
          </text>
        ))}
      </svg>
    </div>
  )
}

export default function Results() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [audit, setAudit] = useState(null)
  const [activeTab, setActiveTab] = useState('overview')

  useEffect(() => {
    fetch(`${API}/audit/${id}`)
      .then(r => r.json())
      .then(setAudit)
      .catch(() => navigate('/'))
  }, [id])

  if (!audit) return <div className="loading-screen"><span className="spinner-lg" />Loading results...</div>

  const modules = audit.modules || {}

  return (
    <div className="results-page">
      {/* Header */}
      <div className="results-header">
        <div className="results-header-left">
          <ScoreRing score={audit.overall_score} grade={audit.grade} size={140} />
          <div className="results-meta">
            <h1 className="results-url">{audit.url}</h1>
            <p className="results-biz">Business Type: <strong>{(audit.business_type || 'N/A').toUpperCase()}</strong></p>
            <div className="tech-chips">
              {(audit.tech_stack || []).slice(0, 6).map(t => (
                <span key={t} className="tech-chip">{t}</span>
              ))}
            </div>
          </div>
        </div>
        <div className="results-header-right">
          <RadarChart modules={modules} />
        </div>
      </div>

      {/* Tab nav */}
      <div className="tab-nav">
        {['overview', 'narrative', 'findings', 'modules'].map(tab => (
          <button key={tab} className={`tab-btn ${activeTab === tab ? 'active' : ''}`}
            onClick={() => setActiveTab(tab)}>
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
        {audit.report_available && (
          <a href={`${API}/audit/${id}/report`} className="download-btn" target="_blank" rel="noreferrer">
            ⬇ Download PDF
          </a>
        )}
      </div>

      {/* Tab content */}
      <div className="tab-content">
        {activeTab === 'overview' && (
          <div className="overview-grid">
            {Object.entries(modules).map(([key, mod]) => (
              <div key={key} className={`module-card ${mod.error ? 'mod-error' : ''}`}>
                <div className="mod-header">
                  <span className="mod-icon">{AGENT_ICONS[key] || '📊'}</span>
                  <span className="mod-name">{AGENT_LABELS[key] || key}</span>
                </div>
                <div className="mod-score" style={{ color: gradeColor(mod.grade) }}>
                  {Math.round(mod.score || 0)}
                  <span className="mod-grade">{mod.grade}</span>
                </div>
                <div className="mod-bar-track">
                  <div className="mod-bar-fill"
                    style={{ width: `${mod.score || 0}%`, background: gradeColor(mod.grade) }} />
                </div>
                <p className="mod-justification">{mod.score_justification}</p>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'narrative' && (
          <div className="narrative-section">
            <h2>Executive Summary</h2>
            <div className="narrative-text">
              {(audit.executive_narrative || 'Narrative not available.').split('\n\n').map((para, i) => (
                <p key={i}>{para}</p>
              ))}
            </div>
            {audit.pagespeed_data && (
              <div className="vitals-row">
                <h3>Core Web Vitals (Google PageSpeed)</h3>
                <div className="vitals-grid">
                  {[
                    { label: 'Performance', val: `${audit.pagespeed_data.performance_score}/100` },
                    { label: 'LCP', val: audit.pagespeed_data.lcp },
                    { label: 'CLS', val: audit.pagespeed_data.cls },
                    { label: 'TBT', val: audit.pagespeed_data.tbt },
                  ].map(v => (
                    <div key={v.label} className="vital-card">
                      <div className="vital-val">{v.val}</div>
                      <div className="vital-label">{v.label}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'findings' && (
          <div className="findings-section">
            <div className="findings-col">
              <h2>🔴 Issues Found</h2>
              {(audit.findings || []).map((f, i) => (
                <div key={i} className="finding-item">
                  <span className="finding-tag">{typeof f === 'object' ? f.agent?.toUpperCase() : ''}</span>
                  {typeof f === 'object' ? f.text : f}
                </div>
              ))}
            </div>
            <div className="findings-col">
              <h2>✅ Quick Wins</h2>
              {(audit.quick_wins || []).map((w, i) => (
                <div key={i} className="win-item">✓ {w}</div>
              ))}
              <h2 style={{ marginTop: '24px' }}>💪 Strengths</h2>
              {(audit.strengths || []).map((s, i) => (
                <div key={i} className="strength-item">⭐ {s}</div>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'modules' && (
          <div className="modules-detail">
            {Object.entries(modules).map(([key, mod]) => (
              <div key={key} className="module-detail-card">
                <div className="mod-detail-header">
                  <span>{AGENT_ICONS[key]} {AGENT_LABELS[key] || key}</span>
                  <span style={{ color: gradeColor(mod.grade), fontWeight: 700 }}>
                    {Math.round(mod.score || 0)}/100 · {mod.grade}
                  </span>
                </div>
                <p className="mod-justification">{mod.score_justification}</p>
                {mod.strengths?.length > 0 && (
                  <div className="mod-list green">
                    {mod.strengths.map((s, i) => <div key={i}>✓ {s}</div>)}
                  </div>
                )}
                {mod.findings?.length > 0 && (
                  <div className="mod-list red">
                    {mod.findings.map((f, i) => <div key={i}>✗ {f}</div>)}
                  </div>
                )}
                {mod.quick_wins?.length > 0 && (
                  <div className="mod-list blue">
                    <strong>Quick Wins:</strong>
                    {mod.quick_wins.map((w, i) => <div key={i}>→ {w}</div>)}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="results-footer">
        <button className="back-btn" onClick={() => navigate('/')}>
          ← New Audit
        </button>
        <span className="footer-powered">Powered by NVIDIA NIM + Gemini · Nova AI</span>
      </div>
    </div>
  )
}
