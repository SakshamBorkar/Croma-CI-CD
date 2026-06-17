"""
dags/ci_news_daily.py
──────────────────────
Daily 06:00 IST news ingestion for all competitors.
"""

from __future__ import annotations
import asyncio, json, sys, pickle, tempfile
from datetime import timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

DEFAULT_ARGS = {
    "owner": "croma-ci",
    "retries": 1,
    "retry_delay": timedelta(minutes=3),
}

def _run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def fetch_news(**context):
    from app.ingestion.scraper import SCRAPING_TARGETS, scrape_rss

    async def _go():
        results = {}
        for competitor, sources in SCRAPING_TARGETS.items():
            docs = []
            for rss_url in sources.get("news_rss", []):
                articles = await scrape_rss(rss_url, max_items=5)
                for a in articles:
                    a["competitor"] = competitor
                    a["source_type"] = "news"
                docs.extend(articles)
            results[competitor] = docs
        return results

    docs = _run_async(_go())
    context["task_instance"].xcom_push(key="news_docs", value=json.dumps(docs, default=str))
    print(f"Fetched {sum(len(v) for v in docs.values())} news articles")


def embed_and_upsert_news(**context):
    from app.ingestion.chunker import chunk_document
    from app.ingestion.embedder import embed_chunks_batch
    from app.ingestion.upserter import upsert_chunks

    ti = context["task_instance"]
    news_raw = json.loads(ti.xcom_pull(key="news_docs") or "{}")

    async def _process():
        total = 0
        for competitor, docs in news_raw.items():
            chunks = []
            for doc in docs:
                if not doc.get("content"):
                    continue
                blocks = [{"type": "text", "content": doc["content"], "page": None}]
                c = chunk_document(
                    blocks,
                    competitor=competitor,
                    source_type="news",
                    source_url=doc.get("url", ""),
                    publication_date=doc.get("publication_date"),
                )
                chunks.extend(c)

            if chunks:
                chunks = await embed_chunks_batch(chunks)
                inserted = upsert_chunks(chunks, competitor)
                total += inserted
                print(f"{competitor}: inserted {inserted} news chunks")
        return total

    total = _run_async(_process())
    print(f"Daily news: {total} new chunks inserted")


with DAG(
    dag_id="ci_news_daily",
    default_args=DEFAULT_ARGS,
    description="Daily news RSS ingestion for competitor monitoring",
    schedule_interval="30 0 * * *",  # 06:00 IST = 00:30 UTC
    start_date=days_ago(1),
    catchup=False,
    tags=["croma-ci", "news"],
) as news_dag:

    t_fetch = PythonOperator(task_id="fetch_news", python_callable=fetch_news)
    t_embed_upsert = PythonOperator(task_id="embed_and_upsert_news", python_callable=embed_and_upsert_news)
    t_fetch >> t_embed_upsert


# ═══════════════════════════════════════════════════════════════════
# dags/ci_report_generate.py — Monday 07:00 IST report generation
# ═══════════════════════════════════════════════════════════════════

from airflow import DAG as _DAG
from airflow.operators.python import PythonOperator as _PO


def generate_all_reports(**context):
    """Generate full CI reports for all competitors and store in PostgreSQL."""
    from app.core.config import settings
    from app.rag.pipeline import full_competitor_report
    from app.db.session import AsyncSessionLocal
    from app.db import crud
    from datetime import date as _date

    async def _go():
        async with AsyncSessionLocal() as db:
            for competitor in settings.COMPETITORS:
                print(f"Generating report for {competitor}...")
                report = await full_competitor_report(competitor, use_cache=False)
                await crud.upsert_report(db, competitor, _date.today(), report)
                await db.commit()
                print(f"Report saved for {competitor}")

    _run_async(_go())


with _DAG(
    dag_id="ci_report_generate",
    default_args=DEFAULT_ARGS,
    description="Weekly CI report generation for all competitors",
    schedule_interval="30 1 * * 1",  # Monday 07:00 IST = 01:30 UTC
    start_date=days_ago(1),
    catchup=False,
    tags=["croma-ci", "report"],
) as report_dag:

    _PO(task_id="generate_all_reports", python_callable=generate_all_reports)
