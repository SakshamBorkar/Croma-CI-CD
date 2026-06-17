"""
app/db/crud.py
──────────────
Async CRUD operations for all models.
"""

from datetime import date
from typing import List, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AlertLog, CIReport, CISnapshot, IngestedSource


# ──────────────────────────────────────────────────────────────
# IngestedSource
# ──────────────────────────────────────────────────────────────
async def get_source_by_hash(db: AsyncSession, content_hash: str) -> Optional[IngestedSource]:
    result = await db.execute(select(IngestedSource).where(IngestedSource.content_hash == content_hash))
    return result.scalar_one_or_none()


async def create_source(db: AsyncSession, **kwargs) -> IngestedSource:
    source = IngestedSource(**kwargs)
    db.add(source)
    await db.flush()
    return source


async def list_sources(
    db: AsyncSession,
    competitor: Optional[str] = None,
    source_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[IngestedSource]:
    q = select(IngestedSource).order_by(IngestedSource.ingestion_date.desc())
    if competitor:
        q = q.where(IngestedSource.competitor == competitor)
    if source_type:
        q = q.where(IngestedSource.source_type == source_type)
    q = q.limit(limit).offset(offset)
    result = await db.execute(q)
    return list(result.scalars().all())


# ──────────────────────────────────────────────────────────────
# CISnapshot
# ──────────────────────────────────────────────────────────────
async def upsert_snapshot(db: AsyncSession, **kwargs) -> CISnapshot:
    """Insert or update snapshot for (competitor, ci_dimension, snapshot_date)."""
    existing = await db.execute(
        select(CISnapshot).where(
            and_(
                CISnapshot.competitor == kwargs["competitor"],
                CISnapshot.ci_dimension == kwargs["ci_dimension"],
                CISnapshot.snapshot_date == kwargs["snapshot_date"],
            )
        )
    )
    snap = existing.scalar_one_or_none()
    if snap:
        for k, v in kwargs.items():
            setattr(snap, k, v)
    else:
        snap = CISnapshot(**kwargs)
        db.add(snap)
    await db.flush()
    return snap


async def get_latest_snapshot(
    db: AsyncSession, competitor: str, ci_dimension: str
) -> Optional[CISnapshot]:
    result = await db.execute(
        select(CISnapshot)
        .where(
            and_(
                CISnapshot.competitor == competitor,
                CISnapshot.ci_dimension == ci_dimension,
            )
        )
        .order_by(CISnapshot.snapshot_date.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_snapshot_history(
    db: AsyncSession, competitor: str, ci_dimension: str, limit: int = 12
) -> List[CISnapshot]:
    result = await db.execute(
        select(CISnapshot)
        .where(
            and_(
                CISnapshot.competitor == competitor,
                CISnapshot.ci_dimension == ci_dimension,
            )
        )
        .order_by(CISnapshot.snapshot_date.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


# ──────────────────────────────────────────────────────────────
# CIReport
# ──────────────────────────────────────────────────────────────
async def upsert_report(db: AsyncSession, competitor: str, report_date: date, report_json: dict) -> CIReport:
    existing = await db.execute(
        select(CIReport).where(
            and_(CIReport.competitor == competitor, CIReport.report_date == report_date)
        )
    )
    report = existing.scalar_one_or_none()
    if report:
        report.report_json = report_json
    else:
        report = CIReport(competitor=competitor, report_date=report_date, report_json=report_json)
        db.add(report)
    await db.flush()
    return report


async def get_latest_report(db: AsyncSession, competitor: str) -> Optional[CIReport]:
    result = await db.execute(
        select(CIReport)
        .where(CIReport.competitor == competitor)
        .order_by(CIReport.report_date.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


# ──────────────────────────────────────────────────────────────
# AlertLog
# ──────────────────────────────────────────────────────────────
async def create_alert(db: AsyncSession, **kwargs) -> AlertLog:
    alert = AlertLog(**kwargs)
    db.add(alert)
    await db.flush()
    return alert
