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
    if (criteria.some((c) => !c.name.trim())) {
      setError('모든 AI 평가 항목의 이름을 입력하세요.')
      return
    }
    setSaving(true)
    try {
      // Ensure a stable key for every row (auto for newly added ones).
      const normalized = criteria.map((c, i) => ({
        ...c,
        key: c.key.trim() || `criterion_${i + 1}`,
        order: i + 1,
        weight: Number(c.weight) || 0,
      }))
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
  const bonusMax = health ? health.azure_bonus_max + health.ms_stack_bonus_max : 0

  return (
    <div>
      <div className="page-head">
        <h1>📋 채점 기준 (루브릭)</h1>
        <p className="muted">
          전체 채점 구성입니다. <b>AI 평가</b> 항목만 편집할 수 있고, 실행·가산점은 서버 설정값입니다.
          변경은 새로 제출/재심사한 항목부터 적용됩니다.
        </p>
      </div>

      {error && <div className="alert error">{error}</div>}
      {saved && <div className="alert success">저장되었습니다.</div>}

      <div className="card">
        <table className="table rubric-table">
          <thead>
            <tr>
              <th style={{ width: 190 }}>항목</th>
              <th style={{ width: 80 }}>점수</th>
              <th style={{ width: 110 }}>채점 방식</th>
              <th>설명</th>
              <th style={{ width: 36 }}></th>
            </tr>
          </thead>
          <tbody>
            {criteria.map((c, i) => (
              <tr key={i}>
                <td>
                  <input
                    value={c.name}
                    placeholder="항목 이름"
                    onChange={(e) => update(i, { name: e.target.value })}
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
                  <span className="chip">AI 평가</span>
                </td>
                <td>
                  <textarea
                    rows={2}
                    value={c.description}
                    onChange={(e) => update(i, { description: e.target.value })}
                  />
                </td>
                <td>
                  <button className="link danger" onClick={() => removeRow(i)}>
                    ✕
                  </button>
                </td>
              </tr>
            ))}

            {health && (
              <>
                <tr className="auto-row">
                  <td className="strong">실행 검증</td>
                  <td className="strong">{execWeight}</td>
                  <td>
                    <span className="chip">자동·결정적</span>
                  </td>
                  <td className="muted small">
                    Docker 샌드박스 빌드·테스트 (Node·Python·Go·.NET·Java)
                  </td>
                  <td></td>
                </tr>
                <tr className="auto-row">
                  <td className="strong">☁️ Azure 배포 가산점</td>
                  <td className="strong">
                    +{health.azure_bonus_min}~{health.azure_bonus_max}
                  </td>
                  <td>
                    <span className="chip">자동·가산</span>
                  </td>
                  <td className="muted small">
                    배포 감지(+{health.azure_bonus_min}) / 라이브 URL(+{health.azure_bonus_max})
                  </td>
                  <td></td>
                </tr>
                <tr className="auto-row">
                  <td className="strong">🧩 MS AI 스택 가산점</td>
                  <td className="strong">
                    +{health.ms_stack_bonus_min}~{health.ms_stack_bonus_max}
                  </td>
                  <td>
                    <span className="chip">자동·가산</span>
                  </td>
                  <td className="muted small">
                    Foundry·Agent Framework·AI Search 등 사용 구성요소 수
                  </td>
                  <td></td>
                </tr>
              </>
            )}
          </tbody>
          <tfoot>
            <tr>
              <td className="strong">합계</td>
              <td className="strong">≤100</td>
              <td colSpan={3} className="muted small">
                기본 만점 {baseTotal} (AI {total} + 실행 {execWeight}) + 가산 최대 {bonusMax} ·
                종합 = min(100, 기본 + 가산)
              </td>
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
          <b>AI 평가</b> 항목만 편집·저장됩니다. 실행 검증·가산점 점수는 서버 설정(`.env`)으로 정합니다.
        </p>
      </div>
    </div>
  )
}
