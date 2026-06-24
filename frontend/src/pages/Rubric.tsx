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
  const azurePts = health?.azure_points ?? 0
  const msPts = health?.ms_stack_points ?? 0
  const msPer = health?.ms_stack_per ?? 5
  const total = aiTotal + execWeight + azurePts + msPts

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
                  <span className="chip">🤖 AI 채점</span>
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
                    <span className="chip">⚙️ 자동 측정</span>
                  </td>
                  <td className="muted small">
                    코드를 Docker 안에서 <b>실제로 실행</b>해 빌드가 되는지, 테스트가
                    통과하는지 확인합니다(Node·Python·Go·.NET·Java). 빌드 성공·테스트
                    통과율을 0–10점으로 환산합니다.
                  </td>
                </tr>
                <tr>
                  <td className="strong">☁️ Azure 배포</td>
                  <td className="strong">{azurePts}</td>
                  <td>
                    <span className="chip">⚙️ 자동 감지</span>
                  </td>
                  <td className="muted small">
                    Azure에 배포한 흔적(azure.yaml·bicep·infra 폴더·GitHub Actions·Azure
                    주소 등)이 있으면 {azurePts}점, 없으면 0점.
                  </td>
                </tr>
                <tr>
                  <td className="strong">🧩 Microsoft AI 스택</td>
                  <td className="strong">{msPts}</td>
                  <td>
                    <span className="chip">⚙️ 자동 감지</span>
                  </td>
                  <td className="muted small">
                    아래 4가지를 쓸 때마다 <b>{msPer}점씩</b>, 최대 {msPts}점입니다.
                    ① Foundry 모델 ② Azure AI Search ③ Microsoft Agent Framework
                    ④ 그 외 Azure AI 서비스(Speech·Vision·Language·Document
                    Intelligence·Content Understanding·Foundry IQ 등). 하나도 안 쓰면 0점.
                  </td>
                </tr>
              </>
            )}
          </tbody>
          <tfoot>
            <tr>
              <td className="strong">합계</td>
              <td className="strong">{total}</td>
              <td colSpan={2} className="muted small">
                5개 필수 항목(기능 구현·완성도 · 문서화 · 실행 검증 · Azure 배포 ·
                Microsoft AI 스택) 각 20점, 종합 = min(100, 합계)
              </td>
            </tr>
          </tfoot>
        </table>
        <p className="muted small">
          각 항목은 0–10으로 채점되어 <b>(점수/10 × 20)</b>으로 환산됩니다. 채점 기준은 고정이며 수정할 수 없습니다.
        </p>
        <div className="muted small" style={{ marginTop: 10, lineHeight: 1.7 }}>
          <p style={{ margin: '0 0 4px' }}><b>채점 방식은 두 가지입니다</b></p>
          <p style={{ margin: '0 0 4px' }}>
            🤖 <b>AI 채점</b> — gpt-5.4가 코드와 문서를 직접 읽고 점수를 매깁니다
            (기능 구현·완성도, 문서화). 사람이 심사하듯 완성도를 해석하므로 같은 코드라도
            점수가 약간 달라질 수 있습니다.
          </p>
          <p style={{ margin: 0 }}>
            ⚙️ <b>자동(측정·감지)</b> — 사람이나 AI의 주관 없이 컴퓨터가 사실만 확인합니다.
            코드를 실제로 돌려 빌드·테스트 통과를 측정하거나(실행 검증), Azure 배포·Microsoft
            AI 스택을 썼는지 감지합니다. <b>같은 제출이면 언제나 같은 결과</b>가 나옵니다.
          </p>
        </div>
      </div>
    </div>
  )
}
