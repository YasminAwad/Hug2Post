from typing import Dict, List, Any, Optional
from langchain_community.chat_models import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from typing import Annotated,Sequence, Literal, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from langchain_core.prompts import ChatPromptTemplate
import json
from app.config.logging import logger
from app.config.config import settings
from app.models.agent import AgentState
from app.services.llm import LLMService

class IntentClassifierService:
    def __init__(self, llm: LLMService):
        self.llm = llm
        
    async def classify_intent(self, llm: LLMService, state: AgentState) -> AgentState:
        logger.info(f"🤖 Classifying intent:")
        # state.get("messages", [])[-1].content
        role_map = {
            SystemMessage: "System",
            HumanMessage: "Human",
            AIMessage: "Assistant",
        }

        messages = state.get("messages", [])[:-1]  # exclude last message

        history = "\n".join(
            f"{role_map.get(type(msg), 'Unknown')}: {msg.content}"
            for msg in messages
        )
        logger.info(f"History: {history}")
        user_input = state.get("messages", [])[-1].content if state.get("messages") else ""
        logger.info(f"User input: {user_input}")

        """Classify user intent from natural language input"""
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""You are an intent classifier for a research paper assistant. 
            Consider the conversation history to better understand the user's current request.
            
            Classify the user's intent into one of these categories:

            1. "summarize_papers" - User wants to summarize research papers
            2. "create_linkedin_from_position" - User wants to create a LinkedIn post about a paper given its position             
            3. "list_papers_by_date" - User wants to see what papers are available for a given date
            4. "general_chat" - General conversation about papers, research, or the system
            5. "need_clarification" - User request is ambiguous or unclear

            Respond with ONLY the intent category, nothing else."""),
            HumanMessage(content=f"""Conversation History:
    {history}

    Current User Input: {user_input}""")
        ])
        
        response = await llm.generate_response(prompt.format_messages())
        intent = response.content.strip().lower().replace('"', '')
        logger.info(f"Intent: {intent}")
        
        valid_intents = ["summarize_papers", "create_linkedin_from_position", "list_papers_by_date", "general_chat", "need_clarification"]
        return intent if intent in valid_intents else "need_clarification"


async def extract_parameters(self, llm: LLMService, state: AgentState, intent: str) -> Dict[str, Any]:
        logger.info(f"🤖 Classifying intent:")
        messages = state["messages"]
        history = messages[:-1].content if messages else ""
        logger.info(f"History: {history}")
        user_input = messages[-1].content if messages else ""
        logger.info(f"User input: {user_input}")

        """Extract parameters from user input based on intent"""
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=f"""You are a parameter extractor. The user's intent is: {intent}
            Extract relevant parameters and respond with a JSON object, do not add any additional text and don't write "json" in the response:

            For "summarize_papers":
            {{"date": "YYYY-MM-DD or null", "date_description": "what the user said about date"}}
            
            For "create_linkedin_from_title":
            {{"paper_title": "string or null"}}
                          
            For "create_linkedin_from_position":
            {{"paper_position": "int or null"}}
            
            For "list_papers_by_date":
            {{"date": "YYYY-MM-DD or null", "date_description": "what the user said about date"}}

            Respond with ONLY the JSON object, nothing else."""),
            HumanMessage(content=f"""Conversation History:
{history}

Current User Input: {user_input}""")
        ])
        
        response = await llm.generate_response(prompt.format_messages())

        try:
            logger.info("extract_parameters")
            logger.info(response)
            return json.loads(response.content.strip())
        except json.JSONDecodeError:
            return {}