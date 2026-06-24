from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import models  # noqa: F401  (ensure models are registered on Base)
from .config import settings
from .database import Base, SessionLocal, engine
from .rubric_defaults import DEFAULT_CRITERIA
from .routers import judging, leaderboard, rubric, submissions


def _seed_rubric() -> None:
    db = SessionLocal()
    try:
        if db.query(models.Criterion).count() == 0:
            for c in DEFAULT_CRITERIA:
                db.add(models.Criterion(**c))
            db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _seed_rubric()
    yield


app = FastAPI(title="Hackathon AI Judging", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(submissions.router)
app.include_router(judging.router)
app.include_router(leaderboard.router)
app.include_router(rubric.router)


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "azure_configured": settings.azure_configured,
        "auth_required": settings.auth_required,
        "execution_enabled": settings.enable_execution,
        "execution_weight": settings.execution_weight,
        "azure_bonus_min": settings.azure_bonus_min,
        "azure_bonus_max": settings.azure_bonus_max,
        "ms_stack_bonus_min": settings.ms_stack_bonus_min,
        "ms_stack_bonus_max": settings.ms_stack_bonus_max,
    }
