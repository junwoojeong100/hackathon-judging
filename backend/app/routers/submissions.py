import os

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
)
from sqlalchemy.orm import Session

from ..auth import require_admin
from ..database import get_db
from ..models import Submission
from ..schemas import SubmissionCreate, SubmissionOut
from ..services.pipeline import run_pipeline, uploads_dir
from .serialize import to_submission_out

router = APIRouter(prefix="/api/submissions", tags=["submissions"])

MAX_ZIP_BYTES = 50 * 1024 * 1024  # 50 MB upload cap
VALID_STAGES = {"interim", "final"}


def _normalize_stage(stage: str) -> str:
    stage = (stage or "interim").strip().lower()
    if stage not in VALID_STAGES:
        raise HTTPException(
            status_code=400, detail="stage는 'interim'(중간) 또는 'final'(최종)이어야 합니다."
        )
    return stage


@router.get("", response_model=list[SubmissionOut])
def list_submissions(
    team: str | None = Query(default=None, description="팀명으로 필터(제출 이력 조회)"),
    db: Session = Depends(get_db),
):
    query = db.query(Submission)
    if team:
        query = query.filter(Submission.team_name == team)
    subs = query.order_by(Submission.created_at.desc()).all()
    return [to_submission_out(s) for s in subs]


@router.get("/{submission_id}", response_model=SubmissionOut)
def get_submission(submission_id: int, db: Session = Depends(get_db)):
    sub = db.get(Submission, submission_id)
    if sub is None:
        raise HTTPException(status_code=404, detail="제출물을 찾을 수 없습니다.")
    return to_submission_out(sub)


@router.post("", response_model=SubmissionOut, status_code=201)
def create_github_submission(
    payload: SubmissionCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    url = payload.github_url.strip()
    if not url.startswith("http"):
        raise HTTPException(status_code=400, detail="유효한 GitHub URL을 입력하세요.")

    sub = Submission(
        team_name=payload.team_name.strip(),
        project_name=payload.project_name.strip(),
        source_type="github",
        source_ref=url,
        deployment_url=(payload.deployment_url or "").strip(),
        stage=_normalize_stage(payload.stage),
        status="pending",
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)

    background_tasks.add_task(run_pipeline, sub.id)
    return to_submission_out(sub)


@router.post("/upload", response_model=SubmissionOut, status_code=201)
async def create_zip_submission(
    background_tasks: BackgroundTasks,
    team_name: str = Form(...),
    project_name: str = Form(...),
    stage: str = Form("interim"),
    deployment_url: str = Form(""),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    if not (file.filename or "").lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="ZIP 파일만 업로드할 수 있습니다.")

    sub = Submission(
        team_name=team_name.strip(),
        project_name=project_name.strip(),
        source_type="zip",
        source_ref="pending",
        deployment_url=(deployment_url or "").strip(),
        stage=_normalize_stage(stage),
        status="pending",
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)

    stored_name = f"{sub.id}.zip"
    dest = os.path.join(uploads_dir(), stored_name)
    size = 0
    with open(dest, "wb") as out:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_ZIP_BYTES:
                out.close()
                os.remove(dest)
                db.delete(sub)
                db.commit()
                raise HTTPException(status_code=413, detail="ZIP 파일이 너무 큽니다 (최대 50MB).")
            out.write(chunk)

    sub.source_ref = stored_name
    db.commit()
    db.refresh(sub)

    background_tasks.add_task(run_pipeline, sub.id)
    return to_submission_out(sub)


@router.delete("/{submission_id}", status_code=204)
def delete_submission(
    submission_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    sub = db.get(Submission, submission_id)
    if sub is None:
        raise HTTPException(status_code=404, detail="제출물을 찾을 수 없습니다.")
    if sub.source_type == "zip":
        path = os.path.join(uploads_dir(), sub.source_ref)
        if os.path.exists(path):
            os.remove(path)
    db.delete(sub)
    db.commit()
