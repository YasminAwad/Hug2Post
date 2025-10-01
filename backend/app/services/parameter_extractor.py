import json
from typing import Dict, List, Any, Tuple
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from app.config.logging import logger
from app.services.llm import LLMService

class ParameterExtractorService:
    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service

    async def extract_parameters(self, history: str, user_input: str, intent: str) -> Tuple[List[Dict[str, Any]], str]:
        """Extract parameters from user input based on intent"""
        logger.info("Entered ParameterExtractorService.extract_parameters")

        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=f"""You are a parameter extractor. The user's intent is: {intent}
            Extract relevant parameters and respond with a JSON object, do not add any additional text and don't write "json" in the response:

            For "summarize_papers":
            {{"year": "YYYY", "month": "MM", "day": "DD", "date_description": "what the user said about date"}}
                          
            For "create_linkedin_from_position":
            {{"paper_position": "int or null"}}
            
            For "list_papers_by_date":
            {{"year": "YYYY", "month": "MM", "day": "DD", "date_description": "what the user said about date"}}

            Respond with ONLY the JSON object, nothing else."""),
            HumanMessage(content=f"""Conversation History:
{history}

Current User Input: {user_input}""")
        ])
        
        response = await self.llm_service.generate_response(prompt.format_messages())

        try:
            return json.loads(response.content.strip())
        except json.JSONDecodeError:
            return {}