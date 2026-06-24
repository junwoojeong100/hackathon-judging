"""Detect use of Microsoft AI technologies — a required scoring criterion.

Components: Microsoft Foundry, Microsoft Agent Framework, Azure AI Search,
Foundry IQ, Foundry Agent Service / Hosted Agent. Detection scans the collected
repo digest (source + dependency manifests + config) for specific SDK packages,
class names, and endpoints — kept specific to avoid false positives.
"""
from dataclasses import dataclass, field

# component label -> list of lowercased signal substrings
MS_STACK_SIGNALS: dict[str, list[str]] = {
    "Microsoft Foundry": [
        "azure-ai-projects",
        "azure.ai.projects",
        "aiprojectclient",
        ".services.ai.azure.com",
        "azure-ai-inference",
        "azure.ai.inference",
    ],
    "Microsoft Agent Framework": [
        "agent-framework",
        "agent_framework",
        "microsoft agent framework",
        "azure-ai-agents",
        "azure.ai.agents",
        "agentsclient",
    ],
    "Azure AI Search": [
        "azure-search-documents",
        "azure.search.documents",
        "searchclient",
        "searchindexclient",
        "search.windows.net",
        "azure ai search",
    ],
    "Foundry IQ": [
        "foundry iq",
        "foundry-iq",
        "foundryiq",
    ],
    "Foundry Agent Service": [
        "hosted agent",
        "foundry agent service",
        "promptagentdefinition",
        "create_version",
        "connected_agent",
        "fabrictool",
        "agent_reference",
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


def ms_stack_points(evidence: MsStackEvidence, points: float) -> float:
    """Microsoft AI stack usage is a required criterion: full points when any
    component is detected, otherwise 0."""
    return float(points) if evidence.detected else 0.0
