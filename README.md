# 해커톤 AI 심사 앱 (Hackathon AI Judging)

해커톤 제출 소스코드(GitHub 리포 또는 ZIP)를 **Azure OpenAI**가 루브릭 기반으로 자동 채점하고,
결과를 **리더보드**에 반영하는 웹 앱입니다.

- **백엔드**: FastAPI + SQLAlchemy + SQLite
- **프론트엔드**: React (Vite + TypeScript)
- **AI 심사**: Azure OpenAI (구조화 출력 / JSON 스키마)
- **실행**: `docker-compose` (인증 없음, 로컬/데모용)

## 채점 루브릭 — 저장소 산출물 기반 **절대 평가** (절대 점수 합산)
GitHub Copilot로 작성한 **실제 동작하는 앱**을 평가하는 데 맞춰, **실행 여부**를 가장 크게 봅니다.
각 항목은 0–10으로 채점되어 **(점수/10 × 가중치)** 의 합이 기본 점수가 됩니다(가중치 = 점수 상한).
(IaC/CI 자동화는 채점 기준이 아닙니다. UI에서 가중치 조정 가능)

| 기준 | 점수(상한) | 근거 | 채점 방식 |
| --- | --- | --- | --- |
| 실행 검증 (execution) | **20** | Docker 실제 실행 | **결정적(빌드·테스트)** |
| 기능 구현·완성도 (functionality) | 20 | 소스 + 실행/테스트 | AI(절대 앵커, **동작 기능 수** 강조) |
| README·문서화 (documentation) | 20 | README/문서 | AI(절대 앵커) |

- **기본 점수 만점 = 60점** (실행 20 + 기능 20 + 문서 20). 여기에 가산점 **최대 40점**(Azure 20 + MS 스택 20)이 더해집니다.
- **종합 = min(100, 기본 + Azure 가산 + MS 스택 가산)** → 모두 갖추면 정확히 100점.
- 코드 품질은 GitHub Copilot가 코드를 생성하는 특성상 변별력이 낮다고 보아 기준에서 제외했습니다.
  주관적 '아이디어 참신함'도 저장소만으로 객관 판단이 어려워 제외했습니다.
- 실행 검증 지원 스택: **Node · Python · Go · .NET(C#) · Java(Maven/Gradle)**. 그 외는 실행 점수 0.

## 제출 단계(중간/최종)와 다회 제출
- 한 팀은 **중간 점검(interim)** 과 **최종 제출(final)** 을 **횟수 제한 없이** 여러 번 제출할 수 있습니다.
- 팀은 **팀명(team_name)** 으로 그룹화됩니다(별도 팀 등록 없음 — 제출 시 팀명 입력).
- **리더보드는 팀별 1행**: 최종 제출이 있으면 **가장 최근 최종**, 없으면 **가장 최근 제출**을
  대표로 순위화하고 "N회 제출"을 함께 표시합니다.
- 제출 상세 페이지에서 해당 팀의 **전체 제출 이력**(단계·점수·시각)을 타임라인으로 볼 수 있습니다.

## 실행 기반 채점 (Docker 샌드박스)
- 제출 코드를 **격리된 Docker 컨테이너**에서 실제로 `install → build → test` 실행하고, 그 결과
  (빌드 성공 여부·테스트 통과 비율)를 **"실행 검증" 항목(기본 가중치 20)** 으로 종합 점수에 반영합니다.
- 자동 감지 스택: **Node**(package.json), **Python**(requirements.txt/pyproject), **Go**(go.mod).
  감지 실패 시 실행 항목은 제외됩니다.
- **보안**: 신뢰할 수 없는 코드를 실행하므로 컨테이너에 `--cap-drop ALL`,
  `--security-opt no-new-privileges`, 메모리/CPU/PID/시간 제한을 적용합니다. Docker가 없으면
  실행 검증은 **자동으로 건너뜁니다**(나머지 채점은 정상). `ENABLE_EXECUTION=false`로 끌 수 있습니다.
  > docker-compose의 백엔드 컨테이너에서 실행 채점을 쓰려면 Docker 소켓 접근이 필요합니다(보안 주의).
  > 가장 간단한 사용은 백엔드를 **호스트에서 직접 실행**하는 것입니다.

## Azure 배포 가산점 (10–20점)
- **Azure 배포 증거**가 있으면 **10점**, 제출한 **Azure 배포 URL이 실제 응답(live)** 하면 **20점**을 더합니다(종합 상한 100).
- 감지 신호: `azure.yaml`(azd), `*.bicep`/`infra/`, GitHub Actions Azure 배포/로그인,
  `azurewebsites.net`·`azurecontainerapps.io` 등 호스트명, ACR 등.

## Microsoft AI 스택 가산점 (10–20점)
- 다음 기술을 사용하면 **사용한 구성요소 수에 따라** 가산점을 줍니다(1개 10점, 2개 이상 20점):
  **Microsoft Foundry · Microsoft Agent Framework · Azure AI Search · Foundry IQ · Foundry Agent Service(Hosted Agent)**
- 감지 방식: 의존성·임포트·엔드포인트(예: `azure-ai-projects`, `azure-ai-agents`, `azure-search-documents`,
  `search.windows.net`, `PromptAgentDefinition` 등)를 저장소 산출물에서 탐지(오탐 방지를 위해 구체 신호만).
- (가산점은 결정적으로 계산되며, AI 루브릭과 별개로 더해집니다 — 중복 가산 없음)

## 접근 제어 (선택적 관리자 토큰)
- 기본은 **개방**(데모용 — 누구나 제출). `ADMIN_TOKEN`을 설정하면 **제출·업로드·재심사·삭제·루브릭 변경**에
  `X-Admin-Token` 헤더가 필요합니다. 리더보드·조회는 항상 공개입니다.
- 프론트엔드 상단의 "관리자 토큰" 입력칸에 값을 넣으면 브라우저에 저장되어 변경 요청에 자동 첨부됩니다.

## 빠른 시작 (docker-compose)
```bash
# 1) Azure OpenAI 자격증명 설정
cp backend/.env.example .env        # 루트에 .env 생성 후 값 채우기 (compose가 읽음)

# 2) 전체 기동
docker compose up --build

# 백엔드:  http://localhost:8000  (문서: http://localhost:8000/docs)
# 프론트:  http://localhost:5173
```

## 인증 (키리스 / Entra ID)
이 앱은 **키리스(Entra ID) 인증**을 우선 지원합니다. 일부 테넌트는 정책으로 API 키(로컬 인증)를
비활성화하므로, `AZURE_OPENAI_API_KEY`를 비워 두면 `DefaultAzureCredential`로 인증합니다.

- **로컬 실행**: `az login` 한 사용자의 자격으로 호출합니다. 해당 사용자(또는 ID)에 리소스의
  **"Cognitive Services OpenAI User"** 역할이 필요합니다.
- **컨테이너 실행**: 서비스 주체를 사용하려면 `AZURE_CLIENT_ID` / `AZURE_CLIENT_SECRET` /
  `AZURE_TENANT_ID`를 설정하세요(같은 역할 필요).
- **API 키 사용 시**: `AZURE_OPENAI_API_KEY`에 키를 넣으면 키 인증으로 동작합니다.

## 로컬 개발 (Docker 없이)
```bash
# 백엔드
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                 # 값 채우기
uvicorn app.main:app --reload

# 프론트엔드
cd frontend
npm install
npm run dev
```

## 환경 변수 (`backend/.env`)
| 변수 | 설명 |
| --- | --- |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI 엔드포인트 URL |
| `AZURE_OPENAI_API_KEY` | API 키 (선택 — 비우면 Entra ID 인증) |
| `AZURE_OPENAI_DEPLOYMENT` | 배포(모델) 이름 (예: gpt-5.4) |
| `AZURE_OPENAI_API_VERSION` | API 버전 (예: 2024-10-21) |
| `DATABASE_URL` | SQLite 경로 |
| `CORS_ORIGINS` | 허용 오리진(쉼표 구분) |
| `MAX_FILES` / `MAX_FILE_CHARS` / `MAX_TOTAL_CHARS` | 코드 수집 상한(토큰 가드레일) |
| `ENABLE_EXECUTION` | 실행 기반 채점 on/off (기본 true) |
| `EXECUTION_WEIGHT` | "실행 검증" 항목 점수 상한 (기본 20) |
| `EXECUTION_TIMEOUT` | 샌드박스 실행 제한 시간(초, 기본 240) |
| `AZURE_BONUS_MIN` / `AZURE_BONUS_MAX` | Azure 배포 가산점 (감지 10 / 라이브 20) |
| `MS_STACK_BONUS_MIN` / `MAX` / `PER` | MS AI 스택 가산점 (구성요소당 10, 10~20) |
| `ADMIN_TOKEN` | 관리자 토큰 (비우면 개방, 설정 시 변경 작업 보호) |

> Azure OpenAI 설정(엔드포인트/배포 + 인증)이 없으면 심사는 실패(`failed`) 상태가 되며, 제출/리더보드 UI는 정상 동작합니다.
