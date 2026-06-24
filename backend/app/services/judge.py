"""AI judging via Azure OpenAI using structured (JSON-schema) output."""
import json

from openai import AzureOpenAI, BadRequestError

from ..config import settings

SCORING_GUIDE = (
    "이 평가는 '절대 평가'입니다. 다른 제출물과 비교하지 말고, 각 기준의 고정된 절대 기준(앵커)에 따라 "
    "0-10 점수를 매기세요. 판단 근거는 오직 제출된 저장소의 실제 산출물(소스파일·설정파일·README/문서)에서 "
    "관찰되는 사실이어야 하며, 아이디어의 '참신함'이나 추측은 점수에 반영하지 마세요. "
    "rationale에는 어떤 파일/코드의 어떤 내용을 보고 그 점수를 줬는지 구체적으로 인용하세요. "
    "정보가 부족해 확인할 수 없으면 해당 항목은 낮게 평가하세요(추측으로 점수를 올리지 않음)."
)


def _client() -> AzureOpenAI:
    if not settings.azure_openai_endpoint:
        raise ValueError(
            "Azure OpenAI가 설정되지 않았습니다. backend/.env의 "
            "AZURE_OPENAI_ENDPOINT / AZURE_OPENAI_DEPLOYMENT를 확인하세요."
        )
    if settings.azure_openai_api_key:
        return AzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
            timeout=300.0,
            max_retries=2,
        )
    # Entra ID (keyless) — uses DefaultAzureCredential (az login / managed identity /
    # service principal env vars). Requires the "Cognitive Services OpenAI User" role.
    from azure.identity import DefaultAzureCredential, get_bearer_token_provider

    token_provider = get_bearer_token_provider(
        DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
    )
    return AzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        azure_ad_token_provider=token_provider,
        api_version=settings.azure_openai_api_version,
        timeout=300.0,
        max_retries=2,
    )


def _schema(keys: list[str]) -> dict:
    return {
        "name": "hackathon_judgement",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["scores", "summary"],
            "properties": {
                "scores": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["criterion_key", "score", "rationale"],
                        "properties": {
                            "criterion_key": {"type": "string", "enum": keys},
                            "score": {"type": "number"},
                            "rationale": {"type": "string"},
                        },
                    },
                },
                "summary": {"type": "string"},
            },
        },
    }


def _build_messages(team_name, project_name, digest_text, criteria, evidence="") -> list[dict]:
    rubric = "\n".join(
        f"- {c['key']} ({c['name']}, 가중치 {c['weight']}): {c['description']}"
        for c in criteria
    )
    system = (
        "당신은 해커톤 심사위원입니다. 제출된 저장소의 산출물만 근거로 각 채점 기준을 "
        "객관적·절대적으로 평가합니다. 각 기준의 설명에 있는 절대 기준(앵커)을 그대로 적용해 "
        "0-10 점수와 구체적 근거를 제시하고, 전체 총평(summary)을 한국어로 작성하세요. "
        + SCORING_GUIDE
    )
    evidence_block = (
        f"\n## 실행/배포 검증 결과(결정적 근거 — 반드시 반영)\n{evidence}\n" if evidence else ""
    )
    user = (
        f"## 프로젝트 정보\n팀: {team_name}\n프로젝트: {project_name}\n\n"
        f"## 채점 기준(절대 기준 앵커 포함)\n{rubric}\n"
        f"{evidence_block}\n"
        f"## 제출 저장소 산출물(소스·설정·문서)\n{digest_text}\n\n"
        "위 산출물만 근거로 각 기준(criterion_key)별 0-10 점수와 근거(인용 포함), summary 총평을 반환하세요."
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def generate_scores(team_name, project_name, digest_text, criteria, evidence="") -> tuple[dict, str]:
    """Return (parsed_result, model_name). parsed_result = {scores: [...], summary: str}."""
    client = _client()
    keys = [c["key"] for c in criteria]
    messages = _build_messages(team_name, project_name, digest_text, criteria, evidence)

    try:
        resp = client.chat.completions.create(
            model=settings.azure_openai_deployment,
            temperature=0.1,
            messages=messages,
            response_format={"type": "json_schema", "json_schema": _schema(keys)},
        )
    except BadRequestError:
        # Deployment/api-version may not support json_schema; fall back to json_object.
        messages[0]["content"] += " 반드시 유효한 JSON 객체로만 응답하세요."
        resp = client.chat.completions.create(
            model=settings.azure_openai_deployment,
            temperature=0.1,
            messages=messages,
            response_format={"type": "json_object"},
        )

    content = resp.choices[0].message.content or "{}"
    data = json.loads(content)
    if not isinstance(data, dict) or "scores" not in data:
        raise ValueError("AI 응답을 점수 형식으로 해석하지 못했습니다.")
    return data, getattr(resp, "model", settings.azure_openai_deployment)
