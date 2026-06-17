"""
dags/ci_ingestion_weekly.py
─────────────────────────────
Airflow DAG: ci_ingestion_weekly
Schedule: Every Sunday 02:00 IST (20:30 UTC Saturday)

Task flow:
  start → [scrape_websites, scrape_pdfs, scrape_reviews] → chunk_and_embed → upsert → detect_changes → notify → end
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

# Add backend to path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

DEFAULT_ARGS = {
    "owner": "croma-ci",
    "depends_on_past": False,
    "email_on_failure": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


def _run_async(coro):
    """Helper: run async code in Airflow (sync) task."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ─── Task functions ────────────────────────────────────────────────

def scrape_websites(**context):
    """Scrape all competitor websites and push raw docs to XCom."""
    from app.ingestion.scraper import SCRAPING_TARGETS, scrape_static, scrape_dynamic

    async def _scrape_all():
        all_docs = {}
        for competitor, sources in SCRAPING_TARGETS.items():
            docs = []
            for site in sources.get("website", []):
                fn = scrape_dynamic if site.get("dynamic") else scrape_static
                doc = await fn(site["url"])
                if doc:
                    doc["competitor"] = competitor
                    doc["source_type"] = "website"
                    docs.append(doc)
            all_docs[competitor] = docs
        return all_docs

    docs = _run_async(_scrape_all())
    context["task_instance"].xcom_push(key="website_docs", value=json.dumps(docs, default=str))
    total = sum(len(v) for v in docs.values())
    print(f"Scraped {total} website docs")


def scrape_news(**context):
    """Scrape RSS news feeds for all competitors."""
    from app.ingestion.scraper import SCRAPING_TARGETS, scrape_rss

    async def _scrape_news():
        all_docs = {}
        for competitor, sources in SCRAPING_TARGETS.items():
            docs = []
            for rss_url in sources.get("news_rss", []):
                articles = await scrape_rss(rss_url, max_items=10)
                for a in articles:
                    a["competitor"] = competitor
                    a["source_type"] = "news"
                    docs.append(a)
            all_docs[competitor] = docs
        return all_docs

    docs = _run_async(_scrape_news())
    context["task_instance"].xcom_push(key="news_docs", value=json.dumps(docs, default=str))


def scrape_reviews(**context):
    """
    Collect review data.
    TODO: implement Google Maps / App Store API calls.
    Currently returns placeholder structure.
    """
    reviews = {comp: [] for comp in [
        "reliance_digital", "vijay_sales", "aditya_vision", "poojara", "bajaj_electronics"
    ]}
    context["task_instance"].xcom_push(key="review_docs", value=json.dumps(reviews))
    print("Reviews task: placeholder — connect Google Places / Play Store API")


def chunk_and_embed(**context):
    """Chunk all documents and generate embeddings."""
    from app.ingestion.chunker import chunk_document
    from app.ingestion.embedder import embed_chunks_batch
    from app.ingestion.pdf_extractor import extract_pdf

    ti = context["task_instance"]
    website_raw = json.loads(ti.xcom_pull(key="website_docs") or "{}")
    news_raw = json.loads(ti.xcom_pull(key="news_docs") or "{}")

    all_chunked = {}

    async def _process():
        for competitor, docs in {**website_raw, **news_raw}.items():
            chunks = []
            for doc in docs:
                if not doc.get("content"):
                    continue
                blocks = [{"type": "text", "content": doc["content"], "page": None}]
                c = chunk_document(
                    blocks,
                    competitor=doc.get("competitor", competitor),
                    source_type=doc.get("source_type", "website"),
                    source_url=doc.get("url", ""),
                    publication_date=doc.get("publication_date"),
                )
                chunks.extend(c)

            if chunks:
                chunks = await embed_chunks_batch(chunks)
            all_chunked[competitor] = chunks

        return all_chunked

    chunked = _run_async(_process())
    # Store chunk count per competitor (full data too large for XCom → store to disk)
    chunk_counts = {k: len(v) for k, v in chunked.items()}

    # Write to temp file for upserter task
    import tempfile, pickle
    tmp = tempfile.mktemp(suffix=".pkl")
    with open(tmp, "wb") as f:
        pickle.dump(chunked, f)

    context["task_instance"].xcom_push(key="chunked_file", value=tmp)
    context["task_instance"].xcom_push(key="chunk_counts", value=json.dumps(chunk_counts))
    print(f"Chunk counts: {chunk_counts}")


def upsert_vectors(**context):
    """Insert chunks into ChromaDB."""
    import pickle
    from app.ingestion.upserter import upsert_chunks

    ti = context["task_instance"]
    tmp_path = ti.xcom_pull(key="chunked_file")

    if not tmp_path:
        print("No chunked file found — skipping upsert")
        return

    with open(tmp_path, "rb") as f:
        chunked = pickle.load(f)

    total_inserted = 0
    for competitor, chunks in chunked.items():
        if chunks:
            inserted = upsert_chunks(chunks, competitor)
            total_inserted += inserted
            print(f"Upserted {inserted} chunks for {competitor}")

    context["task_instance"].xcom_push(key="total_inserted", value=total_inserted)


def detect_changes(**context):
    """
    Compare new LLM-extracted key metrics against last week's snapshot.
    Flag dimension/competitor pairs with >5% change.
    """
    from app.ingestion.upserter import collection_stats
    from app.core.config import settings

    changes = []
    for comp in settings.COMPETITORS:
        stats = collection_stats(comp)
        print(f"{comp}: {stats['chunk_count']} total chunks")
        # TODO: compare LLM-extracted key_metrics with DB snapshot
        # For now, log chunk count changes

    context["task_instance"].xcom_push(key="changes", value=json.dumps(changes))


def send_slack_notification(**context):
    """Send Slack alert if significant changes detected."""
    import httpx
    from app.core.config import settings

    ti = context["task_instance"]
    total_inserted = ti.xcom_pull(key="total_inserted") or 0
    changes = json.loads(ti.xcom_pull(key="changes") or "[]")

    if not settings.SLACK_WEBHOOK_URL:
        print("No Slack webhook configured — skipping notification")
        return

    message = {
        "text": f":bar_chart: *Croma CI Weekly Ingestion Complete*\n"
                f"• New chunks: {total_inserted}\n"
                f"• Significant changes: {len(changes)}\n"
                f"• Run date: {date.today()}"
    }

    try:
        r = httpx.post(settings.SLACK_WEBHOOK_URL, json=message, timeout=10)
        r.raise_for_status()
        print("Slack notification sent")
    except Exception as e:
        print(f"Slack notification failed: {e}")


# ─── DAG definition ────────────────────────────────────────────────
with DAG(
    dag_id="ci_ingestion_weekly",
    default_args=DEFAULT_ARGS,
    description="Weekly CI data ingestion: scrape → chunk → embed → upsert → alert",
    schedule_interval="30 20 * * 0",  # Sunday 02:00 IST = Saturday 20:30 UTC
    start_date=days_ago(1),
    catchup=False,
    tags=["croma-ci", "ingestion"],
) as dag:

    t_scrape_web = PythonOperator(task_id="scrape_websites", python_callable=scrape_websites)
    t_scrape_news = PythonOperator(task_id="scrape_news", python_callable=scrape_news)
    t_scrape_reviews = PythonOperator(task_id="scrape_reviews", python_callable=scrape_reviews)
    t_chunk_embed = PythonOperator(task_id="chunk_and_embed", python_callable=chunk_and_embed)
    t_upsert = PythonOperator(task_id="upsert_vectors", python_callable=upsert_vectors)
    t_detect = PythonOperator(task_id="detect_changes", python_callable=detect_changes)
    t_notify = PythonOperator(task_id="send_slack_notification", python_callable=send_slack_notification)

    # Task dependencies
    [t_scrape_web, t_scrape_news, t_scrape_reviews] >> t_chunk_embed >> t_upsert >> t_detect >> t_notify
