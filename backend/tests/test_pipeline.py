from app.database import SessionLocal
from app.models import Submission
from app.services import pipeline
from app.services.executor import ExecutionReport
from app.services.ingest import IngestResult


def test_run_pipeline_scores_submission(tmp_path, monkeypatch):
    # Fixture source tree
    (tmp_path / "README.md").write_text("# Demo project")
    (tmp_path / "main.py").write_text("print('hello')")

    monkeypatch.setattr(
        pipeline, "ingest_github", lambda url, wd: IngestResult(str(tmp_path), str(tmp_path))
    )
    monkeypatch.setattr(pipeline, "cleanup", lambda p: None)
    # Keep execution hermetic (no Docker dependency in tests).
    monkeypatch.setattr(pipeline, "run_execution", lambda root, timeout: ExecutionReport())

    def fake_generate(team, project, digest_text, criteria, evidence=""):
        return (
            {
                "summary": "전반적으로 우수합니다.",
                "scores": [
                    {"criterion_key": c["key"], "score": 8, "rationale": "근거"}
                    for c in criteria
                ],
            },
            "test-model",
        )

    monkeypatch.setattr(pipeline, "generate_scores", fake_generate)

    db = SessionLocal()
    sub = Submission(
        team_name="t",
        project_name="p",
        source_type="github",
        source_ref="http://example.com/repo",
        status="pending",
    )
    db.add(sub)
    db.commit()
    sid = sub.id
    db.close()

    pipeline.run_pipeline(sid)

    db = SessionLocal()
    sub = db.get(Submission, sid)
    assert sub.status == "scored"
    judgment = sub.judgments[-1]
    # criteria all 8/10, AI weights sum 40, no execution (None), no bonuses
    # absolute base = 0.8 * 40 = 32.0
    assert judgment.overall_score == 32.0
    assert judgment.base_score == 32.0
    assert judgment.azure_bonus == 0.0
    assert judgment.summary == "전반적으로 우수합니다."
    assert judgment.model == "test-model"
    assert len(judgment.scores) == 2  # 2 objective rubric criteria (execution excluded)
    db.close()


def test_run_pipeline_fails_on_ingest_error(tmp_path, monkeypatch):
    def boom(url, wd):
        raise ValueError("GitHub 클론 실패: repository not found")

    monkeypatch.setattr(pipeline, "ingest_github", boom)

    db = SessionLocal()
    sub = Submission(
        team_name="t",
        project_name="p",
        source_type="github",
        source_ref="http://example.com/missing",
        status="pending",
    )
    db.add(sub)
    db.commit()
    sid = sub.id
    db.close()

    pipeline.run_pipeline(sid)

    db = SessionLocal()
    sub = db.get(Submission, sid)
    assert sub.status == "failed"
    assert "클론 실패" in sub.error_message
    db.close()
