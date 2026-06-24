"""Detect use of Microsoft AI technologies — a required scoring criterion.

Scored by component category, each worth a fixed number of points (default 5,
max 20). Four categories:
  1. Foundry Models        — Azure AI Foundry / Azure OpenAI model deployments
  2. Azure AI Search       — vector / hybrid / keyword search
  3. Microsoft Agent Framework — Agent Framework / Foundry Agent Service / Hosted Agent
  4. 기타 Azure AI 서비스   — Foundry IQ, Speech, Vision, Language, Document
                             Intelligence, Content Understanding, Translator 등
Detection scans the collected repo digest (source + dependency manifests +
config) for specific SDK packages, class names, and endpoints — kept specific to
avoid false positives.
"""
from dataclasses import dataclass, field

# component category label -> list of lowercased signal substrings
MS_STACK_SIGNALS: dict[str, list[str]] = {
    "Foundry Models": [
        "azure-ai-projects",
        "azure.ai.projects",
        "aiprojectclient",
        ".services.ai.azure.com",
        "azure-ai-inference",
        "azure.ai.inference",
        ".openai.azure.com",
        "azure_openai",
        "azureopenai",
        "azure openai",
        "promptagentdefinition",
    ],
    "Azure AI Search": [
        "azure-search-documents",
        "azure.search.documents",
        "searchclient",
        "searchindexclient",
        "search.windows.net",
        "azure ai search",
        "azure cognitive search",
    ],
    "Microsoft Agent Framework": [
        "agent-framework",
        "agent_framework",
        "microsoft agent framework",
        "azure-ai-agents",
        "azure.ai.agents",
        "agentsclient",
        "hosted agent",
        "foundry agent service",
        "connected_agent",
        "semantic-kernel",
        "semantic_kernel",
        "autogen",
    ],
    "기타 Azure AI 서비스": [
        "foundry iq",
        "foundry-iq",
        "foundryiq",
        "azure-ai-textanalytics",
        "azure.ai.textanalytics",
        "azure-ai-language",
        "azure.ai.language",
        "azure-ai-vision",
        "azure.ai.vision",
        "computervision",
        "azure-cognitiveservices-speech",
        "azure.cognitiveservices.speech",
        "speechsdk",
        "speech-to-text",
        "text-to-speech",
        "azure-ai-formrecognizer",
        "azure.ai.formrecognizer",
        "azure-ai-documentintelligence",
        "azure.ai.documentintelligence",
        "documentintelligenceclient",
        "documentanalysisclient",
        "azure-ai-contentunderstanding",
        "azure.ai.contentunderstanding",
        "azure-ai-translation",
        "azure-ai-contentsafety",
        "content safety",
    ],
}


@dataclass
class MsStackEvidence:
    detected: bool = False
    components: list[str] = field(default_factory=list)
    signals: list[str] = field(default_factory=list)


def detect_ms_stack(digest_text: str) -> MsStackEvidence:
    text = digest_text.lower()
    evidence = MsStackEvidence()
    for component, needles in MS_STACK_SIGNALS.items():
        hit = next((n for n in needles if n in text), None)
        if hit:
            evidence.components.append(component)
            evidence.signals.append(f"{component} ({hit})")
    evidence.detected = len(evidence.components) > 0
    return evidence


def ms_stack_points(
    evidence: MsStackEvidence, per_component: float, max_points: float
) -> float:
    """Microsoft AI stack is a required criterion scored by component category:
    `per_component` points for each detected category, capped at `max_points`."""
    return float(min(max_points, per_component * len(evidence.components)))
