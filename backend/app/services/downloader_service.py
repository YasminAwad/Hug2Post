# services/pdf_service.py
import PyPDF2
from pathlib import Path
from typing import Optional
import os
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from datetime import date, datetime
from app.config.logging import logger

class DownloaderService:
    """Service for PDF downloading"""
    def __init__(self, base_papers_dir: Path = Path("papers")):
        self.base_papers_dir = base_papers_dir
    
    async def download_papers(self, target_date: Optional[str] = None) -> str:
        """Download papers for specified date"""
        await self._download_hf_daily_papers(target_date)
        return f"Papers downloaded for {target_date or 'today'}"
    
    async def _fetch(self, session, url):
        async with session.get(url) as resp:
            resp.raise_for_status()
            return await resp.text()

    async def _fetch_pdf(self, session, url, path):
        async with session.get(url) as resp:
            resp.raise_for_status()
            content = await resp.read()
            with open(path, "wb") as f:
                f.write(content)

    # TODO: Add error handling, add path datafolder in input

    async def _download_hf_daily_papers(self, target_date=None):
        """
        Download all PDFs from HuggingFace's daily papers page for a given date (async).
        
        Args:
            target_date (str or None): date in YYYY-MM-DD format.
                                    If None, today's date is used.
        """
        if target_date is None:
            target_date = date.today().isoformat()

        # Parse and format date for folder name
        try:
            dt = datetime.strptime(target_date, "%Y-%m-%d")
        except ValueError:
            raise ValueError("target_date must be in YYYY-MM-DD format")

        folder_name = dt.strftime("%Y%m%d")  # e.g. 20250925
        output_dir = os.path.join(self.base_papers_dir, folder_name)

        os.makedirs(output_dir, exist_ok=True)

        base_url = "https://huggingface.co"
        daily_url = f"{base_url}/papers/date/{target_date}"

        async with aiohttp.ClientSession() as session:
            logger.info(f"📄 Fetching daily papers from {daily_url} ...")
            daily_html = await self._fetch(session, daily_url)
            soup = BeautifulSoup(daily_html, "html.parser")

            # Find all article links
            articles = soup.select("div.relative.grid article a[href]")
            seen = set()
            paper_links = []
            for a in articles:
                href = a.get("href", "").split("#")[0]
                if href.startswith("/papers/") and href not in seen:
                    seen.add(href)
                    paper_links.append(href)

            logger.info(f"🔎 Found {len(paper_links)} papers.")

            pdf_tasks = []

            for link in paper_links:
                paper_url = base_url + link
                logger.info(f"➡️ Visiting paper page: {paper_url}")

                paper_html = await self._fetch(session, paper_url)
                paper_soup = BeautifulSoup(paper_html, "html.parser")

                pdf_button = paper_soup.select_one("a.btn[href*='/pdf/']")
                if not pdf_button:
                    logger.info(f"❌ No PDF found for {paper_url}")
                    continue

                pdf_url = pdf_button["href"]
                if pdf_url.startswith("/"):
                    pdf_url = base_url + pdf_url

                pdf_name = pdf_url.split("/")[-1]
                if not pdf_name.endswith(".pdf"):
                    pdf_name += ".pdf"
                pdf_path = os.path.join(output_dir, pdf_name)

                if os.path.exists(pdf_path):
                    logger.info(f"⏭️ Skipping (already downloaded): {pdf_name}")
                    continue

                logger.info(f"⬇️ Queuing download: {pdf_url} -> {pdf_path}")
                pdf_tasks.append(self._fetch_pdf(session, pdf_url, pdf_path))

            # Wait for all downloads concurrently
            await asyncio.gather(*pdf_tasks)

        logger.info(f"✅ All available PDFs saved in {output_dir}")