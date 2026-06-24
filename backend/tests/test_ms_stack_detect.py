from app.services.ms_stack_detect import (
    MsStackEvidence,
    detect_ms_stack,
    ms_stack_points,
)


def test_detect_foundry_and_search():
    digest = "import azure.ai.projects\nfrom azure.search.documents import SearchClient"
    ev = detect_ms_stack(digest)
    assert ev.detected is True
    assert "Microsoft Foundry" in ev.components
    assert "Azure AI Search" in ev.components


def test_detect_agent_framework():
    digest = '"dependencies": { "@azure/ai-agents": "1.0.0" }  agentsclient'
    ev = detect_ms_stack(digest)
    assert "Microsoft Agent Framework" in ev.components


def test_detect_none():
    ev = detect_ms_stack("import express from 'express'\nconsole.log('hello')")
    assert ev.detected is False
    assert ev.components == []


def test_ms_points_full_when_detected_else_zero():
    one = MsStackEvidence(detected=True, components=["A"])
    four = MsStackEvidence(detected=True, components=["A", "B", "C", "D"])
    assert ms_stack_points(one, 20) == 20.0
    assert ms_stack_points(four, 20) == 20.0  # required: flat points regardless of count
    assert ms_stack_points(MsStackEvidence(), 20) == 0.0
