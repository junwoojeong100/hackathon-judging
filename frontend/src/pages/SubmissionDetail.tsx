import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api'
import ScoreBar from '../components/ScoreBar'
import StatusBadge from '../components/StatusBadge'
import StageBadge from '../components/StageBadge'
import { formatDate, isInProgress } from '../status'
import type { Submission } from '../types'

export default function SubmissionDetail() {
  const { id } = useParams()
  const submissionId = Number(id)
  const [sub, setSub] = useState<Submission | null>(null)
  const [history, setHistory] = useState<Submission[]>([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let timer: number | undefined
    const load = () =>
      api
        .getSubmission(submissionId)
        .then((d) => {
          setSub(d)
          setError('')
          api.listSubmissions(d.team_name).then(setHistory).catch(() => {})
          if (isInProgress(d.status)) {
            timer = window.setTimeout(load, 3000)
          }
        })
        .catch((e) => setError(e.message))
        .finally(() => setLoading(false))
    load()
    return () => {
      if (timer) window.clearTimeout(timer)
    }
  }, [submissionId])

  const rejudge = async () => {
    try {
      const updated = await api.rejudge(submissionId)
      setSub(updated)
      // resume polling
      const poll = () =>
        api.getSubmission(submissionId).then((d) => {
          setSub(d)
          if (isInProgress(d.status)) window.setTimeout(poll, 3000)
        })
      poll()
    } catch (e) {
      setError((e as Error).message)
    }
  }

  if (loading) return <div className="muted">불러오는 중…</div>
  if (error) return <div className="alert error">{error}</div>
  if (!sub) return <div className="empty">제출물을 찾을 수 없습니다.</div>

  const j = sub.latest_judgment

  return (
    <div>
      <div className="page-head">
        <Link className="link" to="/submissions">
          ← 제출물 목록
        </Link>
        <h1>{sub.project_name}</h1>
        <p className="muted">
          {sub.team_name} ·{' '}
          {sub.source_type === 'github' ? (
            <a className="link" href={sub.source_ref} target="_blank" rel="noreferrer">
              {sub.source_ref}
            </a>
          ) : (
            `ZIP 업로드 (${sub.source_ref})`
          )}
        </p>
      </div>

      <div className="card detail-head">
        <div>
          <StageBadge stage={sub.stage} />{' '}
          <StatusBadge status={sub.status} />
          {isInProgress(sub.status) && <span className="spinner" />}
          <span className="muted small" style={{ marginLeft: 12 }}>
            제출: {formatDate(sub.created_at)}
          </span>
        </div>
        <div className="detail-actions">
          {j && <div className="overall">종합 {j.overall_score.toFixed(1)}<span> / 100</span></div>}
          <button className="btn" onClick={rejudge} disabled={isInProgress(sub.status)}>
            재심사
          </button>
        </div>
      </div>

      {history.length > 1 && (
        <div className="card">
          <h3>{sub.team_name} 팀 제출 이력 ({history.length}건)</h3>
          <table className="table">
            <thead>
              <tr>
                <th style={{ width: 70 }}>단계</th>
                <th>프로젝트</th>
                <th style={{ width: 120 }}>상태</th>
                <th style={{ width: 70 }}>점수</th>
                <th style={{ width: 150 }}>제출 시각</th>
                <th style={{ width: 50 }}></th>
              </tr>
            </thead>
            <tbody>
              {history.map((h) => (
                <tr key={h.id} className={h.id === sub.id ? 'top' : ''}>
                  <td>
                    <StageBadge stage={h.stage} />
                  </td>
                  <td>{h.project_name}</td>
                  <td>
                    <StatusBadge status={h.status} />
                  </td>
                  <td className="strong">
                    {h.status === 'scored' && h.latest_judgment
                      ? h.latest_judgment.overall_score.toFixed(1)
                      : '—'}
                  </td>
                  <td className="muted small">{formatDate(h.created_at)}</td>
                  <td>
                    {h.id === sub.id ? (
                      <span className="muted small">현재</span>
                    ) : (
                      <Link className="link" to={`/submissions/${h.id}`}>
                        보기
                      </Link>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {sub.status === 'failed' && (
        <div className="alert error">심사 실패: {sub.error_message}</div>
      )}

      {isInProgress(sub.status) && (
        <div className="alert info">AI가 코드를 분석하고 있습니다… 잠시만 기다려 주세요.</div>
      )}

      {j && (
        <>
          {(j.azure_detected || j.azure_bonus > 0) && (
            <div className="card azure-card">
              <div>
                <span className="stage stage-final">☁️ Azure 배포 가산점 +{j.azure_bonus.toFixed(1)}</span>
                <span className="muted small" style={{ marginLeft: 10 }}>
                  기본 {j.base_score.toFixed(1)} → 종합 {j.overall_score.toFixed(1)}
                </span>
              </div>
              {j.azure_signals && <p className="muted small">감지된 신호: {j.azure_signals}</p>}
            </div>
          )}

          {j.summary && (
            <div className="card">
              <h3>총평</h3>
              <p className="summary">{j.summary}</p>
              {j.model && <p className="muted small">모델: {j.model}</p>}
            </div>
          )}

          <div className="card">
            <h3>항목별 점수</h3>
            <div className="criteria-list">
              {j.scores.map((cs) => (
                <div key={cs.criterion_key} className="criterion">
                  <div className="criterion-top">
                    <span className="criterion-name">
                      {cs.criterion_key === 'execution' ? '⚙️ ' : ''}
                      {cs.criterion_name}
                    </span>
                    <span className="muted small">가중치 {cs.weight}</span>
                  </div>
                  <ScoreBar value={cs.score} />
                  <p className="rationale">{cs.rationale}</p>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
