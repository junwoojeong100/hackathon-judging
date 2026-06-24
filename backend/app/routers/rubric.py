from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import require_admin
from ..database import get_db
from ..models import Criterion
from ..schemas import CriterionOut, RubricUpdate

router = APIRouter(prefix="/api/rubric", tags=["rubric"])


@router.get("", response_model=list[CriterionOut])
def get_rubric(db: Session = Depends(get_db)):
    return db.query(Criterion).order_by(Criterion.order).all()


@router.put("", response_model=list[CriterionOut])
def update_rubric(
    payload: RubricUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    if not payload.criteria:
        raise HTTPException(status_code=400, detail="최소 1개 이상의 채점 기준이 필요합니다.")

    keys = [c.key.strip() for c in payload.criteria]
    if any(not k for k in keys):
        raise HTTPException(status_code=400, detail="채점 기준 key는 비어 있을 수 없습니다.")
    if len(keys) != len(set(keys)):
        raise HTTPException(status_code=400, detail="채점 기준 key가 중복되었습니다.")

    db.query(Criterion).delete()
    for i, c in enumerate(payload.criteria):
        db.add(
            Criterion(
                key=c.key.strip(),
                name=c.name.strip(),
                description=c.description,
                weight=max(0, c.weight),
                order=c.order or (i + 1),
            )
        )
    db.commit()
    return db.query(Criterion).order_by(Criterion.order).all()
