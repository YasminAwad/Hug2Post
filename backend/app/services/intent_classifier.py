from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from app.config.logging import logger
from app.services.llm import LLMService

class IntentClassifierService:
    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service
        
    async def classify_intent(self, history: str, user_input: str) -> str:
        """Classify user intent from natural language input"""
        logger.info("Entered IntentClassifierService.classify_intent")

        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""You are an intent classifier for a research paper assistant. 
            Consider the conversation history to better understand the user's current request.
            
            Classify the user's intent into one of these categories:

            1. "summarize_papers" - User wants to summarize research papers
            2. "create_linkedin_from_position" - User wants to create a LinkedIn post about a paper given its position             
            3. "modify_linkedin_post" - User wants to modify or change an existing LinkedIn post
            4. "list_papers_by_date" - User wants to see what papers are available for a given date
            5. "general_chat" - General conversation about papers, research, or the system
            6. "need_clarification" - User request is ambiguous or unclear

            Respond with ONLY the intent category, nothing else."""),
            HumanMessage(content=f"""Conversation History:
    {history}

    Current User Input: {user_input}""")
        ])
        
        response = await self.llm_service.generate_response(prompt.format_messages())
        intent = response.content.strip().lower().replace('"', '')
        logger.info(f"Intent: {intent}")
        
        valid_intents = ["summarize_papers", "create_linkedin_from_position", "list_papers_by_date", "general_chat", "need_clarification", "modify_linkedin_post"]
        return intent if intent in valid_intents else "need_clarification"