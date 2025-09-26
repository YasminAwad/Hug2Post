# services/linkedin_service.py
import aiofiles
from pathlib import Path
from typing import Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from app.services.llm import LLMService
from app.services.database import DatabaseService, LinkedInPost
from app.config.logging import logger


class LinkedInService:
    """Service for creating LinkedIn posts"""
    
    def __init__(self, llm_service: LLMService, database_service: DatabaseService):
        self.llm_service = llm_service
        self.database_service = database_service

    async def create_post_for_paper_by_position(
        self, 
        paper_id: int,
    ) -> str:
        """Create LinkedIn post for a paper by position using database"""
        
        # Get paper from database by position
        paper = await self.database_service.get_paper_by_id(paper_id)
        print(paper)
        
        if not paper:
            raise ValueError(f"No paper found id: {paper_id}")
        
        # Read the markdown summary from the path stored in database
        summary_path = Path(paper.summary_path)
        if not summary_path.exists():
            raise FileNotFoundError(f"Summary file not found: {paper.summary_path}")
        
        async with aiofiles.open(summary_path, 'r', encoding='utf-8') as f:
            detailed_summary = await f.read()
        
        # Generate LinkedIn post
        linkedin_post_content = await self._generate_linkedin_post(detailed_summary)
        
        # Save LinkedIn post to database
        linkedin_post = LinkedInPost(
            title=paper.title,
            post=linkedin_post_content
        )
        
        await self.database_service.save_linkedin_post(linkedin_post)
        print(f"Saved LinkedIn post to database for paper: {paper.title}")
        
        return linkedin_post_content
    
    async def _generate_linkedin_post(self, detailed_summary: str) -> str:
        """Generate LinkedIn post from detailed summary"""
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""Create an engaging LinkedIn post based on the research paper.
            
            The post should:
            1. Start with a hook that grabs attention
            2. Explain the key insight in simple terms
            3. Include relevant hashtags
            4. Be professional but engaging
            5. Be 150-300 words
            6. Include emojis where appropriate
            7. End with a question to encourage engagement"""),
            HumanMessage(content=f"Detailed Summary:\n{detailed_summary[:1000]}...")
        ])
        
        response = await self.llm_service.generate_response(prompt.format_messages())
        return response.content
