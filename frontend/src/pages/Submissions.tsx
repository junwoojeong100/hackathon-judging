import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import StatusBadge from '../components/StatusBadge'
import StageBadge from '../components/StageBadge'
import { formatDate, isInProgress } from '../status'
import type { Submission } from '../types'

export default function Submissions() {
  const [items, setItems] = useState<Submission[]>([])
  const [error, setError] = useState('')

  // form state
  const [mode, setMode] = useState<'github' | 'zip'>('github')
  const [team, setTeam] = useState('')
  const [project, setProject] = useState('')
  const [stage, setStage] = useState<'interim' | 'final'>('interim')
  const [githubUrl, setGithubUrl] = useState('')
  const [deploymentUrl, setDeploymentUrl] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState('')
  const fileRef = useRef<HTMLInputElement>(null)

  const load = () =>
    api
      .listSubmissions()
      .then((d) => {
        setItems(d)
        setError('')
      })
      .catch((e) => setError(e.message))

  useEffect(() => {
    load()
    const t = setInterval(load, 4000)
    return () => clearInterval(t)
  }, [])

  const resetForm = () => {
    setTeam('')
    setProject('')
    setGithubUrl('')
    setDeploymentUrl('')
    setFile(null)
    if (fileRef.current) fileRef.current.value = ''
  }

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setFormError('')
    if (!team.trim() || !project.trim()) {
      setFormError('팀명과 프로젝트명을 입력하세요.')
      return
    }
    setSubmitting(true)
    try {
      if (mode === 'github') {
        if (!githubUrl.trim()) throw new Error('GitHub URL을 입력하세요.')
        await api.createGithub({
          team_name: team,
          project_name: project,
          github_url: githubUrl,
          stage,
          deployment_url: deploymentUrl,
        })
      } else {
        if (!file) throw new Error('ZIP 파일을 선택하세요.')
        const form = new FormData()
        form.append('team_name', team)
        form.append('project_name', project)
        form.append('stage', stage)
        form.append('deployment_url', deploymentUrl)
        form.append('file', file)
        await api.uploadZip(form)
      }
      resetForm()
      await load()
    } catch (err) {
      setFormError((err as Error).message)
    } finally {
      setSubmitting(false)
    }
  }

  const rejudge = async (id: number) => {
    try {
      await api.rejudge(id)
      await load()
    } catch (err) {
      setError((err as Error).message)
    }
  }

  const remove = async (id: number) => {
    if (!confirm('이 제출물을 삭제할까요?')) return
    try {
      await api.deleteSubmission(id)
      await load()
    } catch (err) {
      setError((err as Error).message)
    }
  }

  return (
    <div>
      <div className="page-head">
        <h1>📥 제출물</h1>
        <p className="muted">GitHub 리포지토리 또는 ZIP 파일을 제출하면 AI가 자동으로 심사합니다.</p>
      </div>

      <div className="card form-card">
        <div className="seg">
          <button
            className={mode === 'github' ? 'active' : ''}
            onClick={() => setMode('github')}
            type="button"
          >
            GitHub URL
          </button>
          <button
            className={mode === 'zip' ? 'active' : ''}
            onClick={() => setMode('zip')}
            type="button"
          >
            ZIP 업로드
          </button>
        </div>

        <form onSubmit={submit} className="form">
          <div className="row">
            <label>
              팀명
              <input value={team} onChange={(e) => setTeam(e.target.value)} placeholder="예: 알파팀" />
            </label>
            <label>
              프로젝트명
              <input
                value={project}
                onChange={(e) => setProject(e.target.value)}
                placeholder="예: 스마트 일정 도우미"
              />
            </label>
          </div>

          <div className="row">
            <label>
              제출 단계
              <div className="seg stage-seg">
                <button
                  type="button"
                  className={stage === 'interim' ? 'active' : ''}
                  onClick={() => setStage('interim')}
                >
                  중간 점검
                </button>
                <button
                  type="button"
                  className={stage === 'final' ? 'active' : ''}
                  onClick={() => setStage('final')}
                >
                  최종 제출
                </button>
              </div>
            </label>
          </div>

          {mode === 'github' ? (
            <label>
              GitHub 리포지토리 URL
              <input
                value={githubUrl}
                onChange={(e) => setGithubUrl(e.target.value)}
                placeholder="https://github.com/org/repo"
              />
            </label>
          ) : (
            <label>
              ZIP 파일
              <input
                ref={fileRef}
                type="file"
                accept=".zip"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
            </label>
          )}

          <label>
            Azure 배포 URL <span className="muted small">(선택 · 입력 시 라이브 상태 확인)</span>
            <input
              value={deploymentUrl}
              onChange={(e) => setDeploymentUrl(e.target.value)}
              placeholder="https://my-app.azurewebsites.net"
            />
          </label>

          {formError && <div className="alert error">{formError}</div>}

          <button className="btn primary" type="submit" disabled={submitting}>
            {submitting ? '제출 중…' : '제출하고 심사 시작'}
          </button>
        </form>
      </div>

      {error && <div className="alert error">{error}</div>}

      <div className="card">
        {items.length === 0 ? (
          <div className="empty">아직 제출물이 없습니다.</div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>팀 / 프로젝트</th>
                <th style={{ width: 80 }}>단계</th>
                <th style={{ width: 80 }}>유형</th>
                <th style={{ width: 120 }}>상태</th>
                <th style={{ width: 70 }}>점수</th>
                <th style={{ width: 150 }}>제출 시각</th>
                <th style={{ width: 170 }}></th>
              </tr>
            </thead>
            <tbody>
              {items.map((s) => (
                <tr key={s.id}>
                  <td>
                    <div className="strong">{s.team_name}</div>
                    <div className="muted small">{s.project_name}</div>
                  </td>
                  <td>
                    <StageBadge stage={s.stage} />
                  </td>
                  <td>
                    <span className="chip">{s.source_type === 'github' ? 'GitHub' : 'ZIP'}</span>
                  </td>
                  <td>
                    <StatusBadge status={s.status} />
                    {isInProgress(s.status) && <span className="spinner" />}
                  </td>
                  <td className="strong">
                    {s.status === 'scored' && s.latest_judgment
                      ? s.latest_judgment.overall_score.toFixed(1)
                      : '—'}
                  </td>
                  <td className="muted small">{formatDate(s.created_at)}</td>
                  <td>
                    <div className="actions">
                      <Link className="link" to={`/submissions/${s.id}`}>
                        상세
                      </Link>
                      <button
                        className="link"
                        onClick={() => rejudge(s.id)}
                        disabled={isInProgress(s.status)}
                      >
                        재심사
                      </button>
                      <button className="link danger" onClick={() => remove(s.id)}>
                        삭제
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
