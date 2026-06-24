from app.services.ms_stack_detect import (
    MsStackEvidence,
    detect_ms_stack,
    ms_stack_bonus_points,
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


def test_ms_bonus_graded_by_count():
    one = MsStackEvidence(detected=True, components=["A"])
    two = MsStackEvidence(detected=True, components=["A", "B"])
    four = MsStackEvidence(detected=True, components=["A", "B", "C", "D"])
    assert ms_stack_bonus_points(one, 10, 30, 10) == 10.0
    assert ms_stack_bonus_points(two, 10, 30, 10) == 20.0
    assert ms_stack_bonus_points(four, 10, 30, 10) == 30.0  # capped at max
    assert ms_stack_bonus_points(MsStackEvidence(), 10, 30, 10) == 0.0
