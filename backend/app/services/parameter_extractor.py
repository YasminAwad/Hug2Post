import json
from typing import Dict, List, Any, Tuple
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from app.config.logging import logger
from app.services.llm import LLMService
from app.utils.utils import retrieve_prompt

class ParameterExtractorService:
    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service

    async def extract_parameters(self, history: str, user_input: str, intent: str) -> Tuple[List[Dict[str, Any]], str]:
        """Extract parameters from user input based on intent"""
        logger.info("Entered ParameterExtractorService.extract_parameters")

        system_prompt_content = retrieve_prompt("extract_parameters.txt")
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=system_prompt_content),
            HumanMessage(content=f"""Conversation History:
{history}

Current User Input: {user_input}""")
        ])
        
        response = await self.llm_service.generate_response(prompt.format_messages())

        try:
            return json.loads(response.content.strip())
        except json.JSONDecodeError:
            return {}