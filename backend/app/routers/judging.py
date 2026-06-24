from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import require_admin
from ..database import get_db
from ..models import Submission
from ..schemas import SubmissionOut
from ..services.pipeline import run_pipeline
from .serialize import to_submission_out

router = APIRouter(prefix="/api/submissions", tags=["judging"])


@router.post("/{submission_id}/rejudge", response_model=SubmissionOut)
def rejudge(
    submission_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    sub = db.get(Submission, submission_id)
    if sub is None:
        raise HTTPException(status_code=404, detail="제출물을 찾을 수 없습니다.")

    # Allow restarting from any state — including a submission stuck in
    # 'ingesting'/'judging' (e.g. a hung model call). Resetting to 'pending' and
    # scheduling a fresh pipeline run effectively cancels the previous attempt:
    # the newest judgment wins, so a late-finishing stale run is harmless.
    sub.status = "pending"
    sub.error_message = ""
    db.commit()

    background_tasks.add_task(run_pipeline, sub.id)
    return to_submission_out(sub)
