import { useEffect, useState } from 'react'
import { api } from '../api'
import type { Health } from '../api'
import type { Criterion } from '../types'

export default function Rubric() {
  const [criteria, setCriteria] = useState<Criterion[]>([])
  const [health, setHealth] = useState<Health | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([api.getRubric(), api.health()])
      .then(([c, h]) => {
        setCriteria(c)
        setHealth(h)
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="muted">불러오는 중…</div>

  const execWeight = health?.execution_enabled ? health.execution_weight : 0
  const aiTotal = criteria.reduce((s, c) => s + (Number(c.weight) || 0), 0)
  const baseTotal = aiTotal + execWeight
  const bonusMax = health ? health.azure_bonus_max + health.ms_stack_bonus_max : 0

  return (
    <div>
      <div className="page-head">
        <h1>📋 채점 기준 (루브릭)</h1>
        <p className="muted">
          고정된 채점 구성입니다 — 각 항목 20점, 총 100점. 모든 제출에 동일하게 적용되며 변경할 수 없습니다.
        </p>
      </div>

      {error && <div className="alert error">{error}</div>}

      <div className="card">
        <table className="table rubric-table">
          <thead>
            <tr>
              <th style={{ width: 180 }}>항목</th>
              <th style={{ width: 64 }}>점수</th>
              <th style={{ width: 104 }}>채점 방식</th>
              <th>설명</th>
            </tr>
          </thead>
          <tbody>
            {criteria.map((c) => (
              <tr key={c.key}>
                <td className="strong">{c.name}</td>
                <td className="strong">{c.weight}</td>
                <td>
                  <span className="chip">AI 평가</span>
                </td>
                <td className="muted small">{c.description}</td>
              </tr>
            ))}

            {health && (
              <>
                <tr>
                  <td className="strong">실행 검증</td>
                  <td className="strong">{execWeight}</td>
                  <td>
                    <span className="chip">자동·결정적</span>
                  </td>
                  <td className="muted small">
                    Docker 샌드박스에서 실제로 빌드·테스트를 실행한 결과
                    (Node·Python·Go·.NET·Java). 빌드 성공·테스트 통과율로 0–10 환산.
                  </td>
                </tr>
                <tr>
                  <td className="strong">☁️ Azure 배포 가산점</td>
                  <td className="strong">+{health.azure_bonus_max}</td>
                  <td>
                    <span className="chip">자동·가산</span>
                  </td>
                  <td className="muted small">
                    Azure 배포 증거(azure.yaml·bicep·호스트명 등) 감지 시 +{health.azure_bonus_max}.
                  </td>
                </tr>
                <tr>
                  <td className="strong">🧩 MS AI 스택 가산점</td>
                  <td className="strong">+{health.ms_stack_bonus_max}</td>
                  <td>
                    <span className="chip">자동·가산</span>
                  </td>
                  <td className="muted small">
                    Foundry·Agent Framework·Azure AI Search·Foundry IQ·Agent Service
                    중 하나 이상 사용 시 +{health.ms_stack_bonus_max}.
                  </td>
                </tr>
              </>
            )}
          </tbody>
          <tfoot>
            <tr>
              <td className="strong">합계</td>
              <td className="strong">100</td>
              <td colSpan={2} className="muted small">
                기본 {baseTotal}(AI {aiTotal} + 실행 {execWeight}) + 가산 최대 {bonusMax} ·
                종합 = min(100, 기본 + 가산)
              </td>
            </tr>
          </tfoot>
        </table>
        <p className="muted small">
          각 항목은 0–10으로 채점되어 <b>(점수/10 × 20)</b>으로 환산됩니다. 채점 기준은 고정이며 수정할 수 없습니다.
        </p>
      </div>
    </div>
  )
}
