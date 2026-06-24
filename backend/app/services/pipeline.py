"""End-to-end judging pipeline: ingest -> collect -> execute -> AI judge -> persist.

Run as a FastAPI BackgroundTask. Drives the submission status machine:
pending -> ingesting -> judging -> scored | failed
"""
import os

from ..config import settings
from ..database import SessionLocal
from ..models import Criterion, CriterionScore, Judgment, Submission
from .azure_detect import azure_bonus_points, detect_azure
from .collector import build_digest, render_digest
from .executor import run_execution
from .ingest import cleanup, ingest_github, ingest_zip
from .judge import generate_scores
from .ms_stack_detect import detect_ms_stack, ms_stack_bonus_points
from .scoring import clamp_score, compute_overall


def uploads_dir() -> str:
    d = os.path.join(settings.data_dir, "uploads")
    os.makedirs(d, exist_ok=True)
    return d


def _workspaces_dir() -> str:
    d = os.path.join(settings.data_dir, "workspaces")
    os.makedirs(d, exist_ok=True)
    return d


def _fail(db, submission, message: str) -> None:
    submission.status = "failed"
    submission.error_message = message
    db.commit()


def run_pipeline(submission_id: int) -> None:
    db = SessionLocal()
    ingest_res = None
    try:
        submission = db.get(Submission, submission_id)
        if submission is None:
            return

        submission.status = "ingesting"
        submission.error_message = ""
        db.commit()

        try:
            if submission.source_type == "github":
                ingest_res = ingest_github(submission.source_ref, _workspaces_dir())
            else:
                zip_path = os.path.join(uploads_dir(), submission.source_ref)
                ingest_res = ingest_zip(zip_path, _workspaces_dir())
        except ValueError as exc:
            _fail(db, submission, str(exc))
            return

        digest = build_digest(
            ingest_res.root_dir,
            settings.max_files,
            settings.max_file_chars,
            settings.max_total_chars,
        )
        if digest.included_files == 0:
            _fail(db, submission, "분석할 소스 파일을 찾지 못했습니다.")
            return

        criteria = [
            {"key": c.key, "name": c.name, "description": c.description, "weight": c.weight}
            for c in db.query(Criterion).order_by(Criterion.order).all()
        ]
        weights = {c["key"]: c["weight"] for c in criteria}
        names = {c["key"]: c["name"] for c in criteria}

        submission.status = "judging"
        db.commit()

        digest_text = render_digest(digest)

        # --- Execution sandbox (deterministic build/test signal) ---
        exec_report = None
        if settings.enable_execution:
            try:
                exec_report = run_execution(ingest_res.root_dir, settings.execution_timeout)
            except Exception:  # noqa: BLE001 - execution is best-effort
                exec_report = None

        # --- Deployment / tech-stack bonuses (deterministic, additive) ---
        azure = detect_azure(ingest_res.root_dir, digest_text, submission.deployment_url or "")
        ms_stack = detect_ms_stack(digest_text)

        # Evidence shown to the AI judge: only the execution result, which grounds the
        # functionality/quality rubric. Bonuses (Azure/MS-stack) are scored separately
        # and deterministically, so they are NOT fed to the AI to avoid double-counting.
        evidence_lines = []
        if exec_report and exec_report.summary:
            evidence_lines.append(f"실행 검증: {exec_report.summary}")
        evidence = "\n".join(evidence_lines)

        try:
            data, model = generate_scores(
                submission.team_name,
                submission.project_name,
                digest_text,
                criteria,
                evidence=evidence,
            )
        except Exception as exc:  # noqa: BLE001 - surface any AI/parse error to the user
            _fail(db, submission, f"AI 심사 실패: {exc}")
            return

        judgment = Judgment(
            submission_id=submission.id,
            summary=data.get("summary", ""),
            model=model,
        )
        db.add(judgment)
        db.flush()

        # Map AI scores by criterion key.
        ai_scores = {}
        for item in data.get("scores", []):
            key = item.get("criterion_key")
            if key in weights and key not in ai_scores:
                ai_scores[key] = (clamp_score(item.get("score")), item.get("rationale", ""))

        normalized = []
        # Persist EVERY rubric criterion (0 when the model omitted it). Using the full
        # rubric weight as a fixed denominator makes the base score an absolute,
        # comparable value rather than depending on which criteria happened to be scored.
        for c in criteria:
            key = c["key"]
            score, rationale = ai_scores.get(key, (0.0, "산출물에서 확인할 수 없어 0점 처리"))
            db.add(
                CriterionScore(
                    judgment_id=judgment.id,
                    criterion_key=key,
                    criterion_name=names[key],
                    score=score,
                    weight=weights[key],
                    rationale=rationale,
                )
            )
            normalized.append({"criterion_key": key, "score": score})

        # Execution as a deterministic, weighted criterion (when it actually ran).
        if exec_report and exec_report.score is not None:
            weights["execution"] = settings.execution_weight
            db.add(
                CriterionScore(
                    judgment_id=judgment.id,
                    criterion_key="execution",
                    criterion_name="실행 검증",
                    score=exec_report.score,
                    weight=settings.execution_weight,
                    rationale=exec_report.summary
                    + (f"\n\n{exec_report.log_excerpt}" if exec_report.log_excerpt else ""),
                )
            )
            normalized.append({"criterion_key": "execution", "score": exec_report.score})

        # Weighted base on a 0-100 scale (criteria are 0-10; weights sum to ~100).
        base100 = round(compute_overall(normalized, weights) * 10.0, 1)

        # Bonuses (added on top, total capped at 100):
        #  - Azure deployment: detected -> min, verified live -> max
        #  - Microsoft AI stack: graded by number of components used
        azure_pts = azure_bonus_points(azure, settings.azure_bonus_min, settings.azure_bonus_max)
        ms_pts = ms_stack_bonus_points(
            ms_stack,
            settings.ms_stack_bonus_min,
            settings.ms_stack_bonus_max,
            settings.ms_stack_bonus_per,
        )

        judgment.base_score = base100
        judgment.azure_detected = azure.detected
        judgment.azure_bonus = azure_pts
        judgment.azure_signals = ", ".join(azure.signals)
        judgment.ms_stack_detected = ms_stack.detected
        judgment.ms_stack_bonus = ms_pts
        judgment.ms_stack_signals = ", ".join(ms_stack.signals)
        judgment.overall_score = round(min(100.0, base100 + azure_pts + ms_pts), 1)

        submission.status = "scored"
        db.commit()

    except Exception as exc:  # noqa: BLE001
        db.rollback()
        submission = db.get(Submission, submission_id)
        if submission is not None:
            _fail(db, submission, f"심사 중 오류가 발생했습니다: {exc}")
    finally:
        if ingest_res is not None:
            cleanup(ingest_res.cleanup_dir)
        db.close()
