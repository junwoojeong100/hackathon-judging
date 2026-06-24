from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Submission
from ..schemas import LeaderboardEntry

router = APIRouter(prefix="/api/leaderboard", tags=["leaderboard"])


def _tiebreak_score(judgment) -> float:
    """Tie-break on 소스코드 완전성 (completeness) when overall scores are equal."""
    for cs in judgment.scores:
        if cs.criterion_key == "completeness":
            return cs.score
    return 0.0


@router.get("", response_model=list[LeaderboardEntry])
def get_leaderboard(db: Session = Depends(get_db)):
    subs = db.query(Submission).filter(Submission.status == "scored").all()

    # Group scored submissions by team. The representative submission is the
    # latest 'final' submission if any, otherwise the latest submission.
    teams: dict[str, list[Submission]] = defaultdict(list)
    for s in subs:
        if s.judgments:
            teams[s.team_name].append(s)

    ranked = []
    for team_subs in teams.values():
        finals = [s for s in team_subs if (s.stage or "interim") == "final"]
        pool = finals if finals else team_subs
        rep = max(pool, key=lambda s: s.created_at)
        latest = rep.judgments[-1]
        ranked.append(
            (rep, latest.overall_score, _tiebreak_score(latest), len(team_subs), latest.azure_detected)
        )

    # overall desc, then completeness desc, then earlier representative first
    ranked.sort(key=lambda e: (-e[1], -e[2], e[0].created_at))

    return [
        LeaderboardEntry(
            rank=i + 1,
            submission_id=rep.id,
            team_name=rep.team_name,
            project_name=rep.project_name,
            overall_score=score,
            status=rep.status,
            stage=rep.stage or "interim",
            attempts=attempts,
            azure_detected=bool(azure),
        )
        for i, (rep, score, _tech, attempts, azure) in enumerate(ranked)
    ]
