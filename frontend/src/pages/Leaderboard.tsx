import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import ScoreBar from '../components/ScoreBar'
import StageBadge from '../components/StageBadge'
import type { LeaderboardEntry } from '../types'

const MEDALS = ['🥇', '🥈', '🥉']

export default function Leaderboard() {
  const [entries, setEntries] = useState<LeaderboardEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    const load = () =>
      api
        .leaderboard()
        .then((d) => {
          setEntries(d)
          setError('')
        })
        .catch((e) => setError(e.message))
        .finally(() => setLoading(false))
    load()
    const t = setInterval(load, 5000)
    return () => clearInterval(t)
  }, [])

  return (
    <div>
      <div className="page-head">
        <h1>🏆 리더보드</h1>
        <p className="muted">팀별 최고 대표 제출(최종 우선, 없으면 최신) 기준 순위 · 5초마다 자동 갱신</p>
      </div>

      {error && <div className="alert error">{error}</div>}

      {loading ? (
        <div className="muted">불러오는 중…</div>
      ) : entries.length === 0 ? (
        <div className="empty">
          아직 심사 완료된 제출물이 없습니다.
          <br />
          <Link className="link" to="/submissions">
            제출물 페이지
          </Link>
          에서 코드를 제출해 보세요.
        </div>
      ) : (
        <div className="card">
          <table className="table">
            <thead>
              <tr>
                <th style={{ width: 70 }}>순위</th>
                <th>팀</th>
                <th>프로젝트</th>
                <th style={{ width: 90 }}>대표 단계</th>
                <th style={{ width: 200 }}>종합 점수</th>
                <th style={{ width: 70 }}></th>
              </tr>
            </thead>
            <tbody>
              {entries.map((e) => (
                <tr key={e.submission_id} className={e.rank <= 3 ? 'top' : ''}>
                  <td className="rank">{MEDALS[e.rank - 1] || e.rank}</td>
                  <td className="strong">{e.team_name}</td>
                  <td>
                    {e.project_name}
                    {e.azure_detected && <span title="Azure 배포 감지"> ☁️</span>}
                    {e.ms_stack_detected && <span title="MS AI 스택 사용"> 🧩</span>}
                    {e.attempts > 1 && <span className="muted small"> · {e.attempts}회 제출</span>}
                  </td>
                  <td>
                    <StageBadge stage={e.stage} />
                  </td>
                  <td>
                    <ScoreBar value={e.overall_score} max={100} />
                  </td>
                  <td>
                    <Link className="link" to={`/submissions/${e.submission_id}`}>
                      상세
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
