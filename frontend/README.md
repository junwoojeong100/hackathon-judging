# 프론트엔드 — 해커톤 AI 심사

해커톤 AI 심사 앱의 웹 UI입니다. **React + Vite + TypeScript**로 작성되었으며
백엔드(FastAPI)의 REST API를 호출해 리더보드·제출·채점 결과를 보여줍니다.

> 전체 프로젝트 개요·아키텍처·채점 방식은 저장소 루트의 [`README.md`](../README.md)를 참고하세요.

## 페이지
- **리더보드** (`/`) — 팀별 대표 제출 순위(5초마다 자동 갱신)
- **제출물** (`/submissions`) — GitHub URL / ZIP 제출, 재심사·삭제, 진행 상태 폴링
- **제출 상세** (`/submissions/:id`) — 항목별 점수·근거, 필수 항목, 팀 제출 이력
- **채점 기준** (`/rubric`) — 고정 루브릭(읽기 전용)

## 개발 실행
```bash
npm install
npm run dev          # http://localhost:5173 (Vite 개발 서버)
```
백엔드는 기본적으로 `http://localhost:8000`을 호출합니다. 다른 주소를 쓰려면
`VITE_API_BASE_URL` 환경 변수로 지정하세요.

## 스크립트
| 명령 | 설명 |
| --- | --- |
| `npm run dev` | 개발 서버(HMR) |
| `npm run build` | 타입 검사(`tsc -b`) 후 프로덕션 번들 생성 |
| `npm run preview` | 빌드 결과 미리보기 |
| `npm run lint` | Oxlint 정적 분석 |

## 구조
```
src/
  pages/      Leaderboard · Submissions · SubmissionDetail · Rubric
  components/ ScoreBar · StatusBadge · StageBadge
  api.ts      백엔드 REST 클라이언트(관리자 토큰 헤더 포함)
  types.ts    API 응답 타입
  status.ts   상태/단계 라벨 · 날짜 포맷
```

## 관리자 토큰
백엔드에 `ADMIN_TOKEN`이 설정된 경우, 상단 입력칸에 토큰을 넣으면
브라우저(`localStorage`)에 저장되어 변경 요청(제출·업로드·재심사·삭제)에
`X-Admin-Token` 헤더로 자동 첨부됩니다. 조회·리더보드는 토큰 없이 열람할 수 있습니다.
