from app.services.ms_stack_detect import (
    MsStackEvidence,
    detect_ms_stack,
    ms_stack_points,
)


def test_detect_foundry_and_search():
    digest = "import azure.ai.projects\nfrom azure.search.documents import SearchClient"
    ev = detect_ms_stack(digest)
    assert ev.detected is True
    assert "Foundry Models" in ev.components
    assert "Azure AI Search" in ev.components


def test_detect_agent_framework():
    digest = '"dependencies": { "@azure/ai-agents": "1.0.0" }  agentsclient'
    ev = detect_ms_stack(digest)
    assert "Microsoft Agent Framework" in ev.components


def test_detect_other_ai_service():
    digest = "from azure.ai.documentintelligence import DocumentIntelligenceClient"
    ev = detect_ms_stack(digest)
    assert "기타 Azure AI 서비스" in ev.components


def test_detect_none():
    ev = detect_ms_stack("import express from 'express'\nconsole.log('hello')")
    assert ev.detected is False
    assert ev.components == []


def test_ms_points_graded_by_component():
    one = MsStackEvidence(detected=True, components=["A"])
    two = MsStackEvidence(detected=True, components=["A", "B"])
    five = MsStackEvidence(detected=True, components=["A", "B", "C", "D", "E"])
    assert ms_stack_points(one, 5, 20) == 5.0
    assert ms_stack_points(two, 5, 20) == 10.0
    assert ms_stack_points(five, 5, 20) == 20.0  # capped at max
    assert ms_stack_points(MsStackEvidence(), 5, 20) == 0.0
