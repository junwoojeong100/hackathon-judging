from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Criterion(Base):
    __tablename__ = "criteria"

    id = Column(Integer, primary_key=True)
    key = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, default="")
    weight = Column(Integer, default=0)
    order = Column(Integer, default=0)


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True)
    team_name = Column(String, nullable=False)
    project_name = Column(String, nullable=False)
    source_type = Column(String, nullable=False)  # github | zip
    source_ref = Column(String, nullable=False)  # repo URL or uploaded filename
    deployment_url = Column(String, default="")  # optional Azure deployment URL
    stage = Column(String, default="interim")  # interim | final
    status = Column(String, default="pending")  # pending|ingesting|judging|scored|failed
    error_message = Column(Text, default="")
    created_at = Column(DateTime, default=_utcnow)

    judgments = relationship(
        "Judgment",
        back_populates="submission",
        cascade="all, delete-orphan",
        order_by="Judgment.created_at",
    )


class Judgment(Base):
    __tablename__ = "judgments"

    id = Column(Integer, primary_key=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=False)
    overall_score = Column(Float, default=0.0)  # 0-100 total (all 5 required criteria)
    base_score = Column(Float, default=0.0)  # AI rubric + execution subtotal
    azure_detected = Column(Boolean, default=False)
    azure_score = Column(Float, default=0.0)
    azure_signals = Column(Text, default="")
    ms_stack_detected = Column(Boolean, default=False)
    ms_stack_score = Column(Float, default=0.0)
    ms_stack_signals = Column(Text, default="")
    summary = Column(Text, default="")
    model = Column(String, default="")
    created_at = Column(DateTime, default=_utcnow)

    submission = relationship("Submission", back_populates="judgments")
    scores = relationship(
        "CriterionScore",
        back_populates="judgment",
        cascade="all, delete-orphan",
    )


class CriterionScore(Base):
    __tablename__ = "criterion_scores"

    id = Column(Integer, primary_key=True)
    judgment_id = Column(Integer, ForeignKey("judgments.id"), nullable=False)
    criterion_key = Column(String, nullable=False)
    criterion_name = Column(String, default="")
    score = Column(Float, default=0.0)  # 0-10
    weight = Column(Integer, default=0)
    rationale = Column(Text, default="")

    judgment = relationship("Judgment", back_populates="scores")
