from typing import Dict, List, Any, Optional
from langchain_community.chat_models import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage
from typing import Annotated,Sequence, Literal, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from langchain_core.prompts import ChatPromptTemplate
import json
from app.config.logging import logger
from app.config.config import settings
from app.models.agent import AgentState

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
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""You are a helpful research paper assistant with memory of previous conversations.
            
            You can help users with:
            1. Summarizing research papers
            2. Creating LinkedIn posts
            3. Managing papers
            
            How can I help you with your research today?"""),
            HumanMessage(content=f"""Conversation Context:
{conversation_context}

Current User Input: {user_input}""")
        ])
        
        response = await self.llm.ainvoke(prompt.format_messages())
        logger.info("generate_general_response")
        logger.info(response)
        return response.content