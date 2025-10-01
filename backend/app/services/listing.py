from typing import List

from app.services.database import DatabaseService
from app.config.logging import logger


class PaperListingService:
    """Service for listing available papers using database"""
    
    def __init__(self, database_service: DatabaseService):
        self.database_service = database_service

    async def retrieve_papers_by_date(self, target_date) -> tuple[List[int], str]:
        """List available papers for a given date"""
        logger.info("Entered PaperListingService._retrieve_papers_by_date")
        
        papers = await self.database_service.get_papers_by_date(target_date)
        processed_papers_ids = []
        processed_papers_title = []

        for paper in papers:
            processed_papers_ids.append(paper.id)
            processed_papers_title.append(paper.title)
        response_msg = f"\n\nAvailable papers for the date {target_date}:"
        if processed_papers_title:
            for idx, title in enumerate(processed_papers_title, start=1):
                response_msg += f"\n{idx}. {title}"

        return processed_papers_ids, response_msg
    