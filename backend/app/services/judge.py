"""AI judging via Azure OpenAI using structured (JSON-schema) output."""
import json

from openai import AzureOpenAI, BadRequestError

from ..config import settings

SCORING_GUIDE = (
    "점수 기준(각 항목 0–10): 0–2 매우 미흡, 3–4 미흡, 5–6 보통, 7–8 우수, 9–10 매우 탁월. "
    "점수 범위를 충분히 활용하고, 근거(rationale)는 실제 코드/구조를 구체적으로 인용해 한국어로 설명하세요."
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
        "당신은 해커톤 심사위원입니다. 제출된 소스코드를 공정하고 엄격하게 평가합니다. "
        "각 채점 기준에 대해 0–10 점수와 구체적 근거를 제시하고, 전체 총평(summary)을 한국어로 작성하세요. "
        + SCORING_GUIDE
    )
    evidence_block = f"\n## 실행/배포 검증 결과(참고 근거)\n{evidence}\n" if evidence else ""
    user = (
        f"## 프로젝트 정보\n팀: {team_name}\n프로젝트: {project_name}\n\n"
        f"## 채점 기준(루브릭)\n{rubric}\n"
        f"{evidence_block}\n"
        f"## 제출 소스코드\n{digest_text}\n\n"
        "위 코드를 분석하여 각 기준(criterion_key)별 점수와 근거, 그리고 summary 총평을 반환하세요. "
        "실행/배포 검증 결과가 있으면 '기능 완성도'와 '기술적 완성도' 평가에 반드시 반영하세요."
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
