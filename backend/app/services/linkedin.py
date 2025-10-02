# services/linkedin_service.py
import aiofiles
from pathlib import Path
from typing import Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from app.services.llm import LLMService
from app.services.database import DatabaseService, LinkedInPost
from app.config.logging import logger
from app.utils.utils import retrieve_prompt


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
        logger.info("Entered LinkedInService.create_post_for_paper_by_position")
        
        paper = await self.database_service.get_paper_by_id(paper_id)        
        if not paper:
            raise ValueError(f"No paper found id: {paper_id}")
        
        # Read the markdown summary from the path stored in database
        summary_path = Path(paper.summary_path)
        if not summary_path.exists():
            raise FileNotFoundError(f"Summary file not found: {paper.summary_path}")
        
        async with aiofiles.open(summary_path, 'r', encoding='utf-8') as f:
            detailed_summary = await f.read()

        linkedin_post_content = await self._generate_linkedin_post(detailed_summary)
        
        linkedin_post = LinkedInPost(
            title=paper.title,
            post=linkedin_post_content
        )
        
        linkedin_post_id = await self.database_service.save_linkedin_post(linkedin_post)
        
        return linkedin_post_content, int(linkedin_post_id)
    
    async def change_post(self, post: str, user_request: str, linkedin_post_id: int): 
        """Generate a new LinkedIn post based on the existing one and user request"""
        logger.info("Entered change_post")

        new_post_content = await self._modify_linkedin_post(post, user_request)
        await self.database_service.change_linkedin_post(linkedin_post_id, new_post_content)
        return new_post_content
    
    async def _generate_linkedin_post(self, detailed_summary: str) -> str:
        """Generate LinkedIn post from detailed summary"""

        system_prompt_content = retrieve_prompt("generate_linkedin_post.txt")
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=system_prompt_content),
            HumanMessage(content=f"Detailed Summary:\n{detailed_summary[:1000]}...")
        ])
        
        response = await self.llm_service.generate_response(prompt.format_messages())
        return response.content
    
    async def _modify_linkedin_post(self, post: str, user_request: str): 
        logger.info("Entered _modify_linkedin_post")
        """Generate a new LinkedIn post based on the existing one and user request"""

        system_prompt_content = retrieve_prompt("modify_linkedin_post.txt")
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=system_prompt_content),
            AIMessage(content=post),
            HumanMessage(content=user_request)
        ])

        response = await self.llm_service.generate_response(prompt.format_messages())
        return response.content
