"""
app/ingestion/scraper.py
─────────────────────────
Two-mode web scraping:
  1. Static pages  → httpx + BeautifulSoup4 + trafilatura
  2. Dynamic pages → Playwright headless Chromium

Also handles RSS feed ingestion for news sources.
"""

import asyncio
import hashlib
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import feedparser
import httpx
import trafilatura
from bs4 import BeautifulSoup
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings


# ─── Static scraper ─────────────────────────────────────────────
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def scrape_static(url: str, timeout: int = settings.SCRAPE_REQUEST_TIMEOUT) -> Optional[Dict[str, Any]]:
    """
    Fetch a static page with httpx, clean content with trafilatura.
    Returns: {url, title, content, publication_date, content_hash}
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; CromaCIBot/1.0; +https://croma.com)",
        "Accept-Language": "en-IN,en;q=0.9",
    }
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            html = resp.text

        # trafilatura for main-content extraction
        content = trafilatura.extract(
            html,
            include_tables=True,
            include_links=False,
            favor_recall=True,
        )
        if not content:
            # fallback: BeautifulSoup paragraph extraction
            soup = BeautifulSoup(html, "html.parser")
            for tag in soup(["nav", "footer", "header", "aside", "script", "style"]):
                tag.decompose()
            content = soup.get_text(separator="\n", strip=True)

        if not content or len(content.strip()) < 100:
            logger.warning(f"Skipping {url}: content too short or empty")
            return None

        # extract title
        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.string.strip() if soup.title else urlparse(url).netloc

        content_hash = hashlib.md5(content.encode()).hexdigest()

        return {
            "url": url,
            "title": title,
            "content": content.strip(),
            "publication_date": _extract_date_from_html(html),
            "content_hash": content_hash,
        }

    except httpx.HTTPError as e:
        logger.error(f"HTTP error scraping {url}: {e}")
        raise


# ─── Dynamic scraper (Playwright) ───────────────────────────────
async def scrape_dynamic(url: str, wait_selector: str = "body", timeout: int = 30000) -> Optional[Dict[str, Any]]:
    """
    Use Playwright headless Chrome for JS-rendered pages (e.g., store locator).
    Requires: playwright install chromium
    """
    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (compatible; CromaCIBot/1.0)",
            })
            await page.goto(url, timeout=timeout)
            await page.wait_for_selector(wait_selector, timeout=timeout)
            html = await page.content()
            await browser.close()

        content = trafilatura.extract(html, include_tables=True, favor_recall=True)
        if not content:
            soup = BeautifulSoup(html, "html.parser")
            content = soup.get_text(separator="\n", strip=True)

        if not content or len(content.strip()) < 100:
            return None

        content_hash = hashlib.md5(content.encode()).hexdigest()
        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.string.strip() if soup.title else url

        return {
            "url": url,
            "title": title,
            "content": content.strip(),
            "publication_date": None,
            "content_hash": content_hash,
        }

    except Exception as e:
        logger.error(f"Playwright error scraping {url}: {e}")
        return None


# ─── RSS / News feed ingestion ───────────────────────────────────
async def scrape_rss(feed_url: str, max_items: int = 20) -> List[Dict[str, Any]]:
    """
    Parse an RSS/Atom feed and scrape each article's full content.
    Returns a list of scraped article dicts.
    """
    loop = asyncio.get_event_loop()
    feed = await loop.run_in_executor(None, feedparser.parse, feed_url)

    results = []
    semaphore = asyncio.Semaphore(settings.SCRAPE_CONCURRENCY)

    async def fetch_entry(entry):
        async with semaphore:
            url = entry.get("link")
            if not url:
                return None
            doc = await scrape_static(url)
            if doc:
                doc["publication_date"] = _parse_rss_date(entry.get("published"))
            return doc

    tasks = [fetch_entry(e) for e in feed.entries[:max_items]]
    raw = await asyncio.gather(*tasks, return_exceptions=True)
    for r in raw:
        if isinstance(r, dict) and r:
            results.append(r)

    logger.info(f"RSS feed {feed_url}: {len(results)}/{max_items} articles scraped")
    return results


# ─── Helpers ─────────────────────────────────────────────────────
def _extract_date_from_html(html: str) -> Optional[str]:
    """Try to extract publication date from meta tags."""
    patterns = [
        r'<meta[^>]*property=["\']article:published_time["\'][^>]*content=["\']([^"\']+)',
        r'<meta[^>]*name=["\']date["\'][^>]*content=["\']([^"\']+)',
        r'"datePublished"\s*:\s*"([^"]+)"',
    ]
    for p in patterns:
        m = re.search(p, html, re.IGNORECASE)
        if m:
            return m.group(1)[:10]
    return None


def _parse_rss_date(date_str: Optional[str]) -> Optional[str]:
    if not date_str:
        return None
    try:
        from email.utils import parsedate_to_datetime
        return parsedate_to_datetime(date_str).date().isoformat()
    except Exception:
        return date_str[:10] if date_str else None


# ─── Source catalog (all scraping targets) ───────────────────────
SCRAPING_TARGETS = {
    "reliance_digital": {
        "website": [
            {"url": "https://www.reliancedigital.in/store-finder", "dynamic": True},
            {"url": "https://www.reliancedigital.in/about-us", "dynamic": False},
        ],
        "news_rss": [
            "https://economictimes.indiatimes.com/rss/topic/reliance-digital",
        ],
        "annual_reports": [
            # PDFs — ingested separately via pdf_extractor
            "https://www.ril.com/investor-relations/annual-reports",
        ],
    },
    "vijay_sales": {
        "website": [
            {"url": "https://www.vijaysales.com/about-us", "dynamic": False},
            {"url": "https://www.vijaysales.com/store-locator", "dynamic": True},
        ],
        "news_rss": [
            "https://economictimes.indiatimes.com/rss/topic/vijay-sales",
        ],
        "annual_reports": [],
    },
    "aditya_vision": {
        "website": [
            {"url": "https://adityavision.com/about", "dynamic": False},
            {"url": "https://adityavision.com/stores", "dynamic": True},
        ],
        "news_rss": [
            "https://economictimes.indiatimes.com/rss/topic/aditya-vision",
        ],
        "annual_reports": [
            "https://www.bseindia.com/stockinfo/AnnStockExch.aspx?scripcode=526235&Etype=A",
        ],
    },
    "poojara": {
        "website": [
            {"url": "https://www.poojara.com/about-us", "dynamic": False},
        ],
        "news_rss": [],
        "annual_reports": [],
    },
    "bajaj_electronics": {
        "website": [
            {"url": "https://www.bajajelectronics.com/about", "dynamic": False},
            {"url": "https://www.bajajelectronics.com/store-locator", "dynamic": True},
        ],
        "news_rss": [],
        "annual_reports": [],
    },
}
