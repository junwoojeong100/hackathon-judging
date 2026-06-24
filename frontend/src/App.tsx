import { useEffect, useState } from 'react'
import { NavLink, Route, Routes } from 'react-router-dom'
import { api, getAdminToken, setAdminToken } from './api'
import Leaderboard from './pages/Leaderboard'
import Submissions from './pages/Submissions'
import SubmissionDetail from './pages/SubmissionDetail'
import Rubric from './pages/Rubric'

export default function App() {
  const [token, setToken] = useState(getAdminToken())
  const [authRequired, setAuthRequired] = useState(false)

  useEffect(() => {
    api.health().then((h) => setAuthRequired(h.auth_required)).catch(() => {})
  }, [])

  const onTokenChange = (v: string) => {
    setToken(v)
    setAdminToken(v)
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="topbar-inner">
          <div className="brand">
            <span className="brand-logo">⚖️</span>
            <span className="brand-name">해커톤 AI 심사</span>
          </div>
          <nav className="nav">
            <NavLink to="/" end className={({ isActive }) => (isActive ? 'active' : '')}>
              🏆 리더보드
            </NavLink>
            <NavLink to="/submissions" className={({ isActive }) => (isActive ? 'active' : '')}>
              📥 제출물
            </NavLink>
            <NavLink to="/rubric" className={({ isActive }) => (isActive ? 'active' : '')}>
              📋 채점 기준
            </NavLink>
          </nav>
          <div className={`admintoken ${authRequired && !token ? 'need' : ''}`}>
            <span title={authRequired ? '이 서버는 관리자 토큰이 필요합니다' : '관리자 토큰(설정 시에만 필요)'}>
              {authRequired ? '🔒' : '🔑'}
            </span>
            <input
              type="password"
              placeholder="관리자 토큰"
              value={token}
              onChange={(e) => onTokenChange(e.target.value)}
            />
          </div>
        </div>
      </header>

      <main className="container">
        <Routes>
          <Route path="/" element={<Leaderboard />} />
          <Route path="/submissions" element={<Submissions />} />
          <Route path="/submissions/:id" element={<SubmissionDetail />} />
          <Route path="/rubric" element={<Rubric />} />
        </Routes>
      </main>
    </div>
  )
}
