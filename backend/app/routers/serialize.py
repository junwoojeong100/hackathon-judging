from ..models import Submission
from ..schemas import JudgmentOut, SubmissionOut


def to_submission_out(submission: Submission) -> SubmissionOut:
    latest = submission.judgments[-1] if submission.judgments else None
    return SubmissionOut(
        id=submission.id,
        team_name=submission.team_name,
        project_name=submission.project_name,
        source_type=submission.source_type,
        source_ref=submission.source_ref,
        deployment_url=submission.deployment_url or "",
        stage=submission.stage or "interim",
        status=submission.status,
        error_message=submission.error_message or "",
        created_at=submission.created_at,
        latest_judgment=JudgmentOut.model_validate(latest) if latest else None,
    )
