from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from app.config.logging import logger
from app.services.llm import LLMService
from app.utils.utils import retrieve_prompt

class IntentClassifierService:
    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service
        
    async def classify_intent(self, history: str, user_input: str) -> str:
        """Classify user intent from natural language input"""
        logger.info("Entered IntentClassifierService.classify_intent")

        system_prompt_content = retrieve_prompt("classify_intent.txt")

        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=system_prompt_content),
            HumanMessage(content=f"""Conversation History:
    {history}

    Current User Input: {user_input}""")
        ])
        
        response = await self.llm_service.generate_response(prompt.format_messages())
        intent = response.content.strip().lower().replace('"', '')
        logger.info(f"Intent: {intent}")
        
        valid_intents = ["summarize_papers", "create_linkedin_from_position", "list_papers_by_date", "general_chat", "need_clarification", "modify_linkedin_post"]
        return intent if intent in valid_intents else "need_clarification"