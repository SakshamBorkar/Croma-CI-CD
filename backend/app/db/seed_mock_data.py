"""
backend/app/db/seed_mock_data.py
──────────────────────────────────
Seeds ChromaDB with realistic competitive intelligence data for Croma's main competitors.
Uses Ollama to generate real embeddings so the data is instantly searchable.
"""

import asyncio
import sys
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from loguru import logger
from app.ingestion.chunker import chunk_document
from app.ingestion.embedder import embed_chunks_batch
from app.ingestion.upserter import upsert_chunks, get_chroma_client

MOCK_DATA = {
    "reliance_digital": [
        {
            "content": "Reliance Digital, the consumer electronics arm of Reliance Retail, reported a record revenue of Rs 22,500 crore for FY2024. This represents a solid 12% year-on-year growth compared to FY2023. The company maintained an operating EBITDA margin of 5.8%, driven by strong sales in private labels like Reconnect and exclusive brand partnerships.",
            "url": "https://www.reliancedigital.in/investor-relations/reports-fy24",
            "date": "2024-05-15",
            "type": "annual_report"
        },
        {
            "content": "Reliance Digital has significantly expanded its store footprint in India. As of mid-2024, it operates over 620 large-format Reliance Digital stores across more than 210 cities, making it the largest electronics retailer in the country. Additionally, it leverages over 2,000 JioMart Digital points for smaller towns. Expansion plans for 2025 focus on Tier-3 and Tier-4 cities, aiming to add 50 new flagship outlets.",
            "url": "https://www.reliancedigital.in/press-release/footprint-expansion",
            "date": "2024-07-10",
            "type": "press_release"
        },
        {
            "content": "A key strategic initiative for Reliance Digital in 2024 is the deep integration of its Online-to-Offline (O2O) operations. Customers can order online and get delivery from the nearest physical store within 3 hours. Reliance is also upgrading its stores to include interactive 'experience zones' for smart home appliances, IoT devices, and high-end gaming laptops.",
            "url": "https://www.reliancedigital.in/about-us/strategy",
            "date": "2024-03-05",
            "type": "website"
        }
    ],
    "vijay_sales": [
        {
            "content": "Vijay Sales reported a total turnover of Rs 7,200 crore in FY2024, representing an 8.5% growth YoY. Net profit margin stood at 2.4% with a PAT of Rs 172 crore. The company saw strong demand in the air conditioner and washing machine segments, which accounted for 40% of summer sales.",
            "url": "https://www.vijaysales.com/corporate/financials-fy24",
            "date": "2024-06-20",
            "type": "annual_report"
        },
        {
            "content": "Vijay Sales operates 130 retail showrooms across India as of 2024. The brand is highly dominant in Western and Northern India, with 60 stores in Maharashtra (including Mumbai), 25 in Gujarat, 30 in Delhi NCR, and a growing presence of 15 stores in Telangana and Andhra Pradesh. In late 2024, the company announced it will invest Rs 150 crore to open 15 new stores in South India by late 2025.",
            "url": "https://www.vijaysales.com/press-release/store-count-2024",
            "date": "2024-08-01",
            "type": "press_release"
        },
        {
            "content": "Vijay Sales launched its premium loyalty program 'VS Rewards' in early 2024. The program has registered over 2 million members, offering instant cashback points and priority after-sales service. The retailer is also expanding its finance offerings, partnering with Bajaj Finserv and HDFC to offer no-cost EMI options, which now drive 55% of all high-value purchases.",
            "url": "https://www.vijaysales.com/about-us/loyalty-program",
            "date": "2024-04-12",
            "type": "website"
        }
    ],
    "aditya_vision": [
        {
            "content": "Aditya Vision, a publicly listed electronics retailer on the BSE, reported exceptional financial performance for FY2024. Total revenue reached Rs 1,452 crore, registering a massive 24.5% YoY growth. The net profit (PAT) increased by 32% to Rs 76 crore. Operating EBITDA margins improved to 7.1%, which is among the highest in the physical electronics retail industry in India.",
            "url": "https://www.adityavision.com/financials/annual-report-2024",
            "date": "2024-05-30",
            "type": "annual_report"
        },
        {
            "content": "Aditya Vision is the undisputed market leader in Bihar and Jharkhand. As of June 2024, the company operates 145 showrooms. Over 90 showrooms are located in Bihar, 35 in Jharkhand, and the company has successfully expanded with 20 showrooms in Uttar Pradesh. The expansion strategy involves opening showrooms in Tier-3 and Tier-4 towns where competitor presence is minimal.",
            "url": "https://www.adityavision.com/investor-relations/expansion-update",
            "date": "2024-06-15",
            "type": "press_release"
        },
        {
            "content": "Unlike metro-focused retailers, Aditya Vision's business model targets semi-urban and rural consumer demand. They offer localized marketing campaigns, celebrate regional festivals with massive promotions, and run a popular customer loyalty program called 'Aditya Vision Sambandh'. Over 70% of their showrooms are owned rather than leased, which significantly keeps rental expenses low and improves profitability.",
            "url": "https://www.adityavision.com/corporate-governance/business-model",
            "date": "2024-02-18",
            "type": "website"
        }
    ],
    "poojara": [
        {
            "content": "Poojara Telecom, a leading mobile and gadget retailer, reported a total revenue of Rs 1,120 crore for FY2024. Driven by the expansion of its smartphone accessory private labels and smart TV portfolios, the company saw a 15% revenue increase. Net margins hover around 1.8% due to high competition in the mobile retail segment.",
            "url": "https://www.poojaratelecom.com/about/financial-highlights-24",
            "date": "2024-06-05",
            "type": "annual_report"
        },
        {
            "content": "Poojara operates 260 retail outlets as of mid-2024. Its core strength lies in Gujarat, where it has over 180 showrooms. The company has recently expanded, adding 50 stores in Maharashtra and 30 stores in Rajasthan. Poojara operates on a mix of company-owned (60%) and franchise-owned (40%) models.",
            "url": "https://www.poojaratelecom.com/press/store-network-update",
            "date": "2024-07-22",
            "type": "press_release"
        }
    ],
    "bajaj_electronics": [
        {
            "content": "Bajaj Electronics (operated by Electronics Mart India Limited - EMIL) reported a revenue of Rs 4,850 crore for FY2024, indicating a 14% growth YoY. Operating profit (EBITDA) stood at Rs 310 crore with a margin of 6.4%. Mobile phones and large appliances (refrigerators, ACs) contributed equally to the sales mix, making up 70% of total revenue.",
            "url": "https://www.electronicsmartindia.com/investor-relations/fy24-results",
            "date": "2024-05-25",
            "type": "annual_report"
        },
        {
            "content": "Bajaj Electronics has a dominant presence in South India. As of late 2024, it operates 115 retail stores. Over 80 stores are in Telangana (with a heavy concentration in Hyderabad), 25 stores in Andhra Pradesh, and 10 stores in Delhi NCR. EMIL plans to expand Bajaj Electronics into Karnataka and Kerala in 2025, targetting 15 new locations.",
            "url": "https://www.electronicsmartindia.com/news/store-locations-2024",
            "date": "2024-08-15",
            "type": "press_release"
        }
    ]
}


async def seed_data():
    logger.info("Initializing ChromaDB client...")
    client = get_chroma_client()
    
    total_loaded = 0
    for competitor, docs in MOCK_DATA.items():
        logger.info(f"Clearing old database collections for {competitor}...")
        try:
            # Delete old collection to prevent duplicates
            client.delete_collection(f"croma_ci_{competitor}")
        except Exception:
            pass # Collection didn't exist yet
            
        chunks = []
        for idx, doc in enumerate(docs):
            blocks = [{"type": "text", "content": doc["content"], "page": None}]
            c = chunk_document(
                blocks,
                competitor=competitor,
                source_type=doc["type"],
                source_url=doc["url"],
                publication_date=doc["date"],
            )
            chunks.extend(c)
            
        if chunks:
            logger.info(f"Generating embeddings for {len(chunks)} chunks of {competitor}...")
            try:
                embedded = await embed_chunks_batch(chunks)
                logger.info(f"Upserting {len(embedded)} chunks into ChromaDB for {competitor}...")
                inserted = upsert_chunks(embedded, competitor)
                total_loaded += inserted
                logger.info(f"Loaded {inserted} chunks for {competitor}")
            except Exception as e:
                logger.error(f"Failed to load data for {competitor}: {e}")
                
    logger.info(f"Database seeding completed! Successfully loaded {total_loaded} chunks.")


if __name__ == "__main__":
    asyncio.run(seed_data())
