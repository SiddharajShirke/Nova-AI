import { useState } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import Home from './pages/Home'
import AuditProgress from './pages/AuditProgress'
import Results from './pages/Results'
import './App.css'

export default function App() {
  return (
    <Router>
      <div className="app">
        <nav className="navbar">
          <div className="nav-brand">
            <span className="nav-logo">⚡</span>
            <span className="nav-title">Nova<span className="nav-accent">AI</span></span>
          </div>
          <div className="nav-tagline">Marketing Intelligence Engine</div>
        </nav>
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/audit/:id/progress" element={<AuditProgress />} />
            <Route path="/audit/:id/results" element={<Results />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </Router>
  )
}
