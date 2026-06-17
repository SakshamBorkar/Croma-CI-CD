"""
app/ingestion/run_once.py
─────────────────────────
One-shot ingestion runner: scrapes websites and RSS feeds, chunks,
embeds them via Ollama, and loads them into ChromaDB.
"""

import asyncio
import sys
from pathlib import Path

# Add backend directory to path if run directly
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from loguru import logger
from app.ingestion.scraper import SCRAPING_TARGETS, scrape_static, scrape_dynamic, scrape_rss
from app.ingestion.chunker import chunk_document
from app.ingestion.embedder import embed_chunks_batch
from app.ingestion.upserter import upsert_chunks


async def main():
    logger.info("Starting Croma CI Ingestion Pipeline...")

    all_docs = {}
    
    # 1. Scrape Websites
    logger.info("Phase 1: Scraping competitor websites...")
    for competitor, sources in SCRAPING_TARGETS.items():
        docs = []
        for site in sources.get("website", []):
            logger.info(f"Scraping website: {site['url']} ({competitor})")
            try:
                fn = scrape_dynamic if site.get("dynamic") else scrape_static
                doc = await fn(site["url"])
                if doc:
                    doc["competitor"] = competitor
                    doc["source_type"] = "website"
                    docs.append(doc)
            except Exception as e:
                logger.error(f"Failed to scrape {site['url']}: {e}")
        all_docs[competitor] = docs

    # 2. Scrape News RSS Feeds
    logger.info("Phase 2: Scraping competitor RSS news feeds...")
    for competitor, sources in SCRAPING_TARGETS.items():
        for rss_url in sources.get("news_rss", []):
            logger.info(f"Scraping RSS feed: {rss_url} ({competitor})")
            try:
                articles = await scrape_rss(rss_url, max_items=5)
                for a in articles:
                    a["competitor"] = competitor
                    a["source_type"] = "news"
                    all_docs[competitor].append(a)
            except Exception as e:
                logger.error(f"Failed to parse RSS feed {rss_url}: {e}")

    # 3. Chunk, Embed, and Load
    logger.info("Phase 3: Chunking, embedding, and upserting to ChromaDB...")
    total_inserted = 0
    for competitor, docs in all_docs.items():
        chunks = []
        for doc in docs:
            if not doc.get("content"):
                continue
            blocks = [{"type": "text", "content": doc["content"], "page": None}]
            c = chunk_document(
                blocks,
                competitor=competitor,
                source_type=doc.get("source_type", "website"),
                source_url=doc.get("url", ""),
                publication_date=doc.get("publication_date"),
            )
            chunks.extend(c)
        
        if chunks:
            logger.info(f"Embedding {len(chunks)} chunks for {competitor}...")
            try:
                embedded_chunks = await embed_chunks_batch(chunks)
                logger.info(f"Upserting {len(embedded_chunks)} chunks to ChromaDB for {competitor}...")
                inserted = upsert_chunks(embedded_chunks, competitor)
                total_inserted += inserted
                logger.info(f"Successfully loaded {inserted} chunks for {competitor}")
            except Exception as e:
                logger.error(f"Failed to embed/upsert chunks for {competitor}: {e}")

    logger.info(f"Ingestion pipeline complete! Loaded a total of {total_inserted} chunks.")


if __name__ == "__main__":
    asyncio.run(main())
