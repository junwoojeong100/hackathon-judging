from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Criterion
from ..schemas import CriterionOut

router = APIRouter(prefix="/api/rubric", tags=["rubric"])


# The rubric is a FIXED scoring scheme (each criterion 20 points). It is read-only —
# there is intentionally no update endpoint so the criteria/weights can't be modified.
@router.get("", response_model=list[CriterionOut])
def get_rubric(db: Session = Depends(get_db)):
    return db.query(Criterion).order_by(Criterion.order).all()
