from langchain_community.chat_models import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
import json
from app.config.logging import logger
from app.config.config import settings
from app.utils.utils import retrieve_prompt

class LLMService:
    """Service for the LLM interactions"""

    def __init__(self):
        self.model_name = settings.MODEL_NAME
        self.temperature = settings.TEMPERATURE

        self.llm = ChatOllama(model=self.model_name, temperature=self.temperature)

    async def generate_response(self, prompt):
        logger.info("Entered llm generate_response")
        response = await self.llm.ainvoke(prompt)
        return response
    
        

    async def generate_general_response(self, user_input: str, conversation_context: str = "") -> str:
        """Generate general chat response"""
        logger.info("Entered generate_general_response")

        system_prompt_content = retrieve_prompt("generate_general_response.txt")
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=system_prompt_content),
            HumanMessage(content=f"""Conversation Context:
{conversation_context}

Current User Input: {user_input}""")
        ])
        
        response = await self.llm.ainvoke(prompt.format_messages())
        logger.info("generate_general_response")
        logger.info(response)
        return response.content