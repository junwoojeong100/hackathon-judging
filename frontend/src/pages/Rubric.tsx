import { useEffect, useState } from 'react'
import { api } from '../api'
import type { Health } from '../api'
import type { Criterion } from '../types'

export default function Rubric() {
  const [criteria, setCriteria] = useState<Criterion[]>([])
  const [health, setHealth] = useState<Health | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    Promise.all([api.getRubric(), api.health()])
      .then(([c, h]) => {
        setCriteria(c)
        setHealth(h)
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  const update = (i: number, patch: Partial<Criterion>) => {
    setCriteria((prev) => prev.map((c, idx) => (idx === i ? { ...c, ...patch } : c)))
    setSaved(false)
  }

  const addRow = () => {
    setCriteria((prev) => [
      ...prev,
      { key: `criterion_${prev.length + 1}`, name: '', description: '', weight: 0, order: prev.length + 1 },
    ])
    setSaved(false)
  }

  const removeRow = (i: number) => {
    setCriteria((prev) => prev.filter((_, idx) => idx !== i))
    setSaved(false)
  }

  const total = criteria.reduce((sum, c) => sum + (Number(c.weight) || 0), 0)

  const save = async () => {
    setError('')
    setSaved(false)
    if (criteria.length === 0) {
      setError('최소 1개 이상의 기준이 필요합니다.')
      return
    }
    if (criteria.some((c) => !c.key.trim() || !c.name.trim())) {
      setError('모든 기준의 key와 이름을 입력하세요.')
      return
    }
    setSaving(true)
    try {
      const normalized = criteria.map((c, i) => ({ ...c, order: i + 1, weight: Number(c.weight) || 0 }))
      const result = await api.updateRubric(normalized)
      setCriteria(result)
      setSaved(true)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <div className="muted">불러오는 중…</div>

  const execWeight = health?.execution_enabled ? health.execution_weight : 0
  const baseTotal = total + execWeight

  return (
    <div>
      <div className="page-head">
        <h1>📋 채점 기준 (루브릭)</h1>
        <p className="muted">
          AI 심사에 사용되는 기준과 가중치를 설정합니다. 변경 후 새로 제출/재심사한 항목에 적용됩니다.
        </p>
      </div>

      {error && <div className="alert error">{error}</div>}
      {saved && <div className="alert success">저장되었습니다.</div>}

      {health && (
        <div className="card">
          <h3>전체 채점 구성 (0–100점)</h3>
          <table className="table">
            <tbody>
              <tr>
                <td>AI 루브릭(아래 편집 가능)</td>
                <td className="strong" style={{ width: 120, textAlign: 'right' }}>{total}점</td>
              </tr>
              <tr>
                <td>
                  실행 검증 <span className="chip">결정적</span>{' '}
                  <span className="muted small">
                    {health.execution_enabled ? 'Docker 빌드·테스트' : '(비활성)'}
                  </span>
                </td>
                <td className="strong" style={{ textAlign: 'right' }}>{execWeight}점</td>
              </tr>
              <tr>
                <td className="strong">기본 점수 합계</td>
                <td className="strong" style={{ textAlign: 'right' }}>
                  {baseTotal}점 {baseTotal !== 100 && <span className="stage stage-interim">100 권장</span>}
                </td>
              </tr>
              <tr>
                <td>☁️ Azure 배포 가산점 <span className="muted small">(감지/라이브)</span></td>
                <td style={{ textAlign: 'right' }}>+{health.azure_bonus_min}~{health.azure_bonus_max}</td>
              </tr>
              <tr>
                <td>🧩 MS AI 스택 가산점 <span className="muted small">(구성요소 수)</span></td>
                <td style={{ textAlign: 'right' }}>+{health.ms_stack_bonus_min}~{health.ms_stack_bonus_max}</td>
              </tr>
            </tbody>
          </table>
          <p className="muted small">종합 점수 = min(100, 기본 점수 + 가산점들). 실행 검증·가산점은 코드로 결정됩니다.</p>
        </div>
      )}

      <div className="card">
        <h3>AI 루브릭 항목 (편집)</h3>
        <table className="table rubric-table">
          <thead>
            <tr>
              <th style={{ width: 130 }}>key</th>
              <th style={{ width: 150 }}>이름</th>
              <th>설명(절대 기준)</th>
              <th style={{ width: 80 }}>가중치</th>
              <th style={{ width: 40 }}></th>
            </tr>
          </thead>
          <tbody>
            {criteria.map((c, i) => (
              <tr key={i}>
                <td>
                  <input value={c.key} onChange={(e) => update(i, { key: e.target.value })} />
                </td>
                <td>
                  <input value={c.name} onChange={(e) => update(i, { name: e.target.value })} />
                </td>
                <td>
                  <textarea
                    rows={3}
                    value={c.description}
                    onChange={(e) => update(i, { description: e.target.value })}
                  />
                </td>
                <td>
                  <input
                    type="number"
                    min={0}
                    value={c.weight}
                    onChange={(e) => update(i, { weight: Number(e.target.value) })}
                  />
                </td>
                <td>
                  <button className="link danger" onClick={() => removeRow(i)}>
                    ✕
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <td colSpan={3} className="strong">
                AI 루브릭 가중치 합계
              </td>
              <td className="strong">{total}</td>
              <td></td>
            </tr>
          </tfoot>
        </table>

        <div className="rubric-actions">
          <button className="btn" onClick={addRow} type="button">
            + 기준 추가
          </button>
          <button className="btn primary" onClick={save} disabled={saving} type="button">
            {saving ? '저장 중…' : '저장'}
          </button>
        </div>
        <p className="muted small">
          참고: AI 루브릭은 가중치 합으로 정규화되며, 위 "실행 검증"(결정적)과 합쳐 기본 점수가 됩니다.
        </p>
      </div>
    </div>
  )
}
