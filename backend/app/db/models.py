"""
app/db/models.py
─────────────────
SQLAlchemy 2.0 ORM models.

Tables:
  ingested_sources  — audit trail for every ingested document
  ci_snapshots      — weekly key-metric snapshots for change detection
  ci_reports        — generated full competitor reports (JSON blob)
  users             — local user table (augments JWT / Azure AD)
"""

from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ──────────────────────────────────────────────────────────────
# 1. Ingested Sources — one row per ingested document chunk's source
# ──────────────────────────────────────────────────────────────
class IngestedSource(Base):
    __tablename__ = "ingested_sources"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    competitor: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    publication_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    ingestion_date: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    ci_dimensions: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)  # list[str]
    status: Mapped[str] = mapped_column(String(32), default="ok")   # ok | error | skipped
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ──────────────────────────────────────────────────────────────
# 2. CI Snapshots — weekly extracted key metrics per competitor+dimension
# ──────────────────────────────────────────────────────────────
class CISnapshot(Base):
    __tablename__ = "ci_snapshots"
    __table_args__ = (
        UniqueConstraint("competitor", "ci_dimension", "snapshot_date", name="uq_snapshot"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    competitor: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    ci_dimension: Mapped[str] = mapped_column(String(64), nullable=False)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    key_metrics: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    citations: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    raw_llm_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ──────────────────────────────────────────────────────────────
# 3. CI Reports — full generated reports (all dimensions, one competitor)
# ──────────────────────────────────────────────────────────────
class CIReport(Base):
    __tablename__ = "ci_reports"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    competitor: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    report_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    report_json: Mapped[dict] = mapped_column(JSON, nullable=False)   # full structured report
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ──────────────────────────────────────────────────────────────
# 4. Alert Log
# ──────────────────────────────────────────────────────────────
class AlertLog(Base):
    __tablename__ = "alert_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    competitor: Mapped[str] = mapped_column(String(64), nullable=False)
    ci_dimension: Mapped[str] = mapped_column(String(64), nullable=False)
    alert_type: Mapped[str] = mapped_column(String(64), nullable=False)   # change_detected | new_source
    message: Mapped[str] = mapped_column(Text, nullable=False)
    delta_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    notified_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    slack_sent: Mapped[bool] = mapped_column(Boolean, default=False)
