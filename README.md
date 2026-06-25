# 해커톤 AI 심사 앱 (Hackathon AI Judging)

해커톤 제출 소스코드(GitHub 리포 또는 ZIP)를 **Azure OpenAI**가 루브릭 기반으로 자동 채점하고,
결과를 **리더보드**에 반영하는 웹 앱입니다.

- **백엔드**: FastAPI + SQLAlchemy + SQLite
- **프론트엔드**: React (Vite + TypeScript)
- **AI 심사**: Azure OpenAI (구조화 출력 / JSON 스키마)
- **실행**: `docker-compose` (인증 없음, 로컬/데모용)

## 동작 방식 (파이프라인)
제출(GitHub URL 또는 ZIP) 후 백그라운드로 심사가 진행됩니다.
상태 머신: `pending → ingesting → judging → scored | failed`

1. **인제스트**: GitHub는 shallow clone, ZIP은 안전 추출(zip-slip 방지)
2. **코드 수집(digest)**: 소스·설정·문서를 모아 파일 트리 + 내용 구성(`.git`/`node_modules`/바이너리 제외, 용량 상한)
3. **실행 검증**: Docker 샌드박스에서 `install → build → test` 실행 (코드를 직접 실행 — 같은 제출이면 항상 같은 결과)
4. **AI 심사**: gpt-5.4가 digest + 실행 결과를 근거로 루브릭 항목을 0–10 채점 (JSON 구조화 출력)
5. **점수 합산**: `(점수/10 × 상한)` 합(AI·실행) + 필수 항목(Azure·MS) → 종합 `min(100, …)`, 리더보드 반영

## 채점 루브릭 — 저장소 산출물 기반 **절대 평가** (각 항목 20점 고정)
GitHub Copilot로 작성한 **실제 동작하는 앱**을 평가하는 데 맞춰, **실행 여부와 동작 기능**을 핵심으로 봅니다.
각 항목은 0–10으로 채점되어 **(점수/10 × 20)** 으로 환산됩니다.
**채점 기준은 고정이며 수정할 수 없습니다.** (IaC/CI 자동화는 채점 기준이 아닙니다.)

| 기준 | 점수 | 근거 | 채점 방식 |
| --- | --- | --- | --- |
| 실행 검증 (execution) | **20** | Docker 실제 실행 | ⚙️ 자동 측정 (코드를 직접 실행) |
| 기능 구현·완성도 (functionality) | **20** | 소스 + 실행/테스트 | 🤖 AI 채점 (코드를 읽고 평가) |
| README·문서화 (documentation) | **20** | README/문서 | 🤖 AI 채점 (문서를 읽고 평가) |
| ☁️ Azure 배포 (필수) | **20** | 배포 증거 | ⚙️ 자동 감지 (있으면 20, 없으면 0) |
| 🧩 Microsoft AI 스택 (필수) | **20** | 사용 기술 | ⚙️ 자동 감지 (구성요소당 5점, 최대 20) |

> **채점 방식은 두 가지입니다.**
> - 🤖 **AI 채점** — gpt-5.4가 코드·문서를 직접 읽고 점수를 매깁니다(기능 구현·완성도, 문서화).
>   사람이 심사하듯 완성도를 해석하므로 같은 코드라도 점수가 약간 달라질 수 있습니다.
> - ⚙️ **자동(측정·감지)** — 사람·AI의 주관 없이 컴퓨터가 사실만 확인합니다. 코드를 실제로 돌려
>   빌드·테스트 통과를 측정하거나(실행 검증), Azure 배포·Microsoft AI 스택 사용 여부를 감지합니다.
>   **같은 제출이면 언제나 같은 결과**가 나옵니다.

- **5개 필수 항목 각 20점 = 총 100점** (실행 20 + 기능 20 + 문서 20 + Azure 20 + MS 스택 20).
- **종합 = min(100, 항목 점수 합)** → 다섯 항목을 모두 충족하면 정확히 100점.
- Azure 배포·Microsoft AI 스택은 **가산이 아니라 필수 평가 항목**이며, 충족하지 못하면 해당 항목은 0점입니다.
- 코드 품질은 GitHub Copilot가 코드를 생성하는 특성상 변별력이 낮다고 보아 기준에서 제외했습니다.
  주관적 '아이디어 참신함'도 저장소만으로 객관 판단이 어려워 제외했습니다.
- 실행 검증 지원 스택: **Node · Python · Go · .NET(C#) · Java(Maven/Gradle)**. 그 외는 실행 점수 0.

## 🤖 AI는 어떻게 채점하나
"AI 채점"은 gpt-5.4가 **저장소 산출물(소스·설정·README)만 읽고** 점수를 매기는 항목(기능 구현·완성도, 문서화)입니다.
- 각 항목에 **0–10점 기준표**(예: 0점은 어떤 상태, 10점은 어떤 상태인지)를 주고, *"다른 팀과 비교하지 말고
  눈으로 확인한 사실로만 판단하며, 어떤 파일·코드를 보고 그렇게 판단했는지 근거를 함께 적도록"* 지시합니다.
- 답변의 일관성을 위해 창의성 설정(temperature)을 0.1로 낮추고, 결과를 정해진 JSON 형식으로 받아 안정적으로 처리합니다.
- "실제로 동작하는가"는 AI의 추측에 맡기지 않고 **실행 검증(코드를 직접 실행)** 으로 따로 확인한 뒤,
  그 결과를 AI 채점의 참고 자료로 함께 넘깁니다.
- 한계: AI 판단이라 같은 코드라도 점수가 약간 달라질 수 있고(완전히 똑같이 재현되지는 않음),
  저장소가 아주 크면 일부만 읽습니다.

## 제출 단계(중간/최종)와 다회 제출
- 한 팀은 **중간 점검(interim)** 과 **최종 제출(final)** 을 **횟수 제한 없이** 여러 번 제출할 수 있습니다.
- 팀은 **팀명(team_name)** 으로 그룹화됩니다(별도 팀 등록 없음 — 제출 시 팀명 입력).
- **리더보드는 팀별 1행**: 최종 제출이 있으면 **가장 최근 최종**, 없으면 **가장 최근 제출**을
  대표로 순위화하고 "N회 제출"을 함께 표시합니다.
- 제출 상세 페이지에서 해당 팀의 **전체 제출 이력**(단계·점수·시각)을 타임라인으로 볼 수 있습니다.

## 실행 기반 채점 (Docker 샌드박스)
- 제출 코드를 **격리된 Docker 컨테이너**에서 실제로 `install → build → test` 실행하고, 그 결과
  (빌드 성공 여부·테스트 통과 비율)를 **"실행 검증" 항목(기본 상한 20)** 으로 종합 점수에 반영합니다.
- 자동 감지 스택: **Node**(package.json) · **Python**(requirements.txt/pyproject) · **Go**(go.mod) ·
  **.NET**(*.csproj/*.sln → `dotnet test`) · **Java**(pom.xml → Maven, build.gradle → Gradle).
  감지 실패 시 실행 항목은 제외됩니다(나머지 항목으로 채점).
- **보안**: 신뢰할 수 없는 코드를 실행하므로 컨테이너에 `--cap-drop ALL`,
  `--security-opt no-new-privileges`, 메모리/CPU/PID/시간 제한을 적용합니다. Docker가 없으면
  실행 검증은 **자동으로 건너뜁니다**(나머지 채점은 정상). `ENABLE_EXECUTION=false`로 끌 수 있습니다.
  > docker-compose의 백엔드 컨테이너에서 실행 채점을 쓰려면 Docker 소켓 접근이 필요합니다(보안 주의).
  > 가장 간단한 사용은 백엔드를 **호스트에서 직접 실행**하는 것입니다.

## ☁️ Azure 배포 (필수 항목, 20점)
- **Azure 배포 증거**가 감지되면 **20점**, 감지되지 않으면 **0점**입니다(종합 상한 100).
- 제출한 Azure 배포 URL은 **실제 응답(live)이 확인될 때만** 단독 증거로 인정합니다. 응답이 없는
  URL만 제출하면 점수가 부여되지 않으며(임의의 호스트명으로 점수를 받는 것을 방지), 저장소 산출물
  증거(IaC·CI 등)가 별도로 필요합니다.
- 감지 신호: `azure.yaml`(azd), `*.bicep`/`infra/`, GitHub Actions Azure 배포/로그인
  (`.github/workflows/*` 직접 스캔), `azurewebsites.net`·`azurecontainerapps.io` 등 호스트명, ACR 등.

## 🧩 Microsoft AI 스택 (필수 항목, 최대 20점)
- 아래 **4가지 구성요소를 쓸 때마다 5점씩** 더하며, 최대 **20점**입니다(하나도 안 쓰면 0점):

  | 구성요소 | 점수 | 감지 신호(예) |
  | --- | --- | --- |
  | ① Foundry 모델 | 5 | `azure-ai-projects`, `azure-ai-inference`, `*.openai.azure.com`, `*.services.ai.azure.com` |
  | ② Azure AI Search | 5 | `azure-search-documents`, `search.windows.net`, `SearchClient` |
  | ③ Microsoft Agent Framework | 5 | `agent-framework`, `azure-ai-agents`, `semantic-kernel`, `Hosted Agent` |
  | ④ 그 외 Azure AI 서비스 | 5 | Foundry IQ, Speech, Vision, Language, Document Intelligence, Content Understanding 등 |

- 감지 방식: 의존성·임포트·엔드포인트를 저장소 산출물에서 탐지합니다(오탐 방지를 위해 구체 신호만).
- (Azure 배포와 이 항목은 AI 채점과 별개로, 컴퓨터가 사실만 확인해 자동으로 계산합니다 — 같은 제출이면 항상 같은 결과.)

## 접근 제어 (선택적 관리자 토큰)
- 기본은 **개방**(데모용 — 누구나 제출). `ADMIN_TOKEN`을 설정하면 **제출·업로드·재심사·삭제**에
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
| `DATA_DIR` | 데이터 디렉터리(업로드·작업공간, 기본 `./data`) |
| `MAX_FILES` / `MAX_FILE_CHARS` / `MAX_TOTAL_CHARS` | 코드 수집 상한(토큰 가드레일) |
| `ENABLE_EXECUTION` | 실행 기반 채점 on/off (기본 true) |
| `EXECUTION_WEIGHT` | "실행 검증" 항목 점수 상한 (기본 20) |
| `EXECUTION_TIMEOUT` | 샌드박스 실행 제한 시간(초, 기본 240) |
| `AZURE_POINTS` | Azure 배포 필수 항목 점수 (감지 시 20, 미감지 0) |
| `MS_STACK_POINTS` | Microsoft AI 스택 필수 항목 최대 점수 (기본 20) |
| `MS_STACK_PER` | MS AI 스택 구성요소당 점수 (기본 5, 4개 × 5 = 20) |
| `ADMIN_TOKEN` | 관리자 토큰 (비우면 개방, 설정 시 변경 작업 보호) |

> Azure OpenAI 설정(엔드포인트/배포 + 인증)이 없으면 심사는 실패(`failed`) 상태가 되며, 제출/리더보드 UI는 정상 동작합니다.

## API 엔드포인트
전체 대화형 문서: `http://localhost:8000/docs` (Swagger UI)

| 메서드 | 경로 | 설명 |
| --- | --- | --- |
| GET | `/api/health` | 상태 + 채점 구성(항목 점수·필수 항목 값) |
| GET | `/api/leaderboard` | 팀별 리더보드 |
| GET | `/api/submissions` `[?team=]` | 제출 목록(팀 필터) |
| POST | `/api/submissions` | GitHub URL 제출 |
| POST | `/api/submissions/upload` | ZIP 업로드(multipart) |
| GET | `/api/submissions/{id}` | 제출 상세(항목별 점수·근거) |
| POST | `/api/submissions/{id}/rejudge` | 재심사 |
| DELETE | `/api/submissions/{id}` | 삭제 |
| GET | `/api/rubric` | 루브릭 조회(고정·읽기전용) |

> 변경 작업(제출·업로드·재심사·삭제)은 `ADMIN_TOKEN`이 설정된 경우 `X-Admin-Token` 헤더가 필요합니다. 루브릭은 고정이라 수정 API가 없습니다.

## 프로젝트 구조
```
backend/app/
  main.py · config.py · database.py · models.py · schemas.py · auth.py · rubric_defaults.py
  routers/    submissions · judging · leaderboard · rubric
  services/   ingest · collector · executor · azure_detect · ms_stack_detect · judge · scoring · pipeline
  tests/      pytest 스위트
frontend/src/
  pages/      Leaderboard · Submissions · SubmissionDetail · Rubric
  components/ ScoreBar · StatusBadge · StageBadge
  api.ts · types.ts · status.ts
```

## 테스트
```bash
cd backend
.venv/bin/python -m pytest        # 또는: source .venv/bin/activate && pytest
```
단위 테스트는 채점 합산(scoring), 코드 수집(collector), 실행기 감지·파싱(executor),
Azure/Microsoft AI 스택 필수 항목 탐지, 파이프라인, 인증을 커버합니다(외부 호출은 모킹).
