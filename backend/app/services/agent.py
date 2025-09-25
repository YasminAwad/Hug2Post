from app.services.llm import LLMService
from pathlib import Path
from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import MemorySaver

from app.services.nodes.summary_service import SummaryService
from app.services.nodes.linkedin_service import LinkedInService
from app.services.nodes.paper_listing_service import PaperListingService
from datetime import datetime
from app.services.database import DatabaseService
from app.models.agent import AgentState
from app.services.nodes.downloader_service import DownloaderService
from app.services.nodes.intent_classifier_service import IntentClassifierService
from app.config.logging import logger
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate

class ChatBotAgent:
    """Main agent orchestrating all services with database integration"""

    def __init__(self, database_url: str = None, session_id: str = "default"):

        # Initialize database service first
        self.database_service = DatabaseService(database_url) if database_url else DatabaseService()
        
        # Initialize other services
        self.llm_service = LLMService()
        self.intent_classifier = IntentClassifierService(self.llm_service)
        self.downloader_service = DownloaderService()
        self.summary_service = SummaryService(self.llm_service, self.database_service)
        self.linkedin_service = LinkedInService(self.llm_service, self.database_service)
        self.listing_service = PaperListingService(self.database_service)

        self.memory = MemorySaver()

        self._setup_directories()
        self.graph = self._create_graph()

    async def initialize(self):
        """Initialize database connections"""
        await self.database_service.connect()
        await self.database_service.drop_tables()
        await self.database_service.create_tables()
        print("Database connected and initialized")
    
    async def cleanup(self):
        """Cleanup database connections"""
        await self.database_service.disconnect()

    def _setup_directories(self):
        """Create necessary directories"""
        Path("papers").mkdir(exist_ok=True)
        Path("summaries").mkdir(exist_ok=True)

    def _create_graph(self) -> StateGraph:
        """Create the LangGraph workflow"""
        graph = StateGraph(AgentState)

        graph.add_node("intent_classifier", self._intent_classifier_node)
        graph.add_node("summarize_papers", self._summarize_papers_node)
        graph.add_node("download_papers", self._download_papers_node)
        graph.add_node("create_linkedin_post_from_position", self._create_linkedin_post_by_position_node)
        graph.add_node("create_linkedin_post_from_title", self._create_linkedin_post_by_title_node)
        graph.add_node("list_papers_by_date", self._list_papers_by_date_node)
        graph.add_node("general_chat", self._general_chat_node)
        graph.add_node("clarify_request", self._clarify_request_node)

        graph.set_entry_point("intent_classifier")

        graph.add_conditional_edges(
            "intent_classifier",
            self._route_by_intent,
            {
                "summarize": "download_papers",
                "linkedin by position": "create_linkedin_post_from_position",
                "linkedin by title": "create_linkedin_post_from_title",
                "list by date": "list_papers_by_date",
                "general": "general_chat",
                "clarify": "clarify_request",
                "error": "__end__"
            }
        )

        graph.add_edge("download_papers", "summarize_papers")
        graph.add_edge("summarize_papers", "__end__")
        graph.add_edge("create_linkedin_post_from_title", "__end__")
        graph.add_edge("create_linkedin_post_from_position", "__end__")
        graph.add_edge("list_papers_by_date", "__end__")
        graph.add_edge("general_chat", "__end__")
        graph.add_edge("clarify_request", "__end__")

        return graph.compile(checkpointer=self.memory)
    
    def _route_by_intent(self, state: AgentState) -> str:
        """Route based on classified intent"""
        intent = state.get("intent")
        if state.get("error"):
            return "error"
        elif intent == "summarize_papers":
            return "summarize"
        elif intent == "create_linkedin_from_title":
            return "linkedin by title"
        elif intent == "create_linkedin_from_position":
            return "linkedin by position"
        elif intent == "list_papers_by_date":
            return "list by date"
        elif intent == "general_chat":
            return "general"
        elif intent == "need_clarification":
            return "clarify"
        else:
            return "error"
        
    async def _intent_classifier_node(self, state: AgentState) -> AgentState:
        """Classify user intent"""
        try:
            intent = await self.intent_classifier.classify_intent(self.llm_service, state)
            return {**state, "intent": intent}
        except Exception as e:
            return {**state, "error": f"Intent classification failed: {str(e)}"}
        
    async def _download_papers_node(self, state: AgentState) -> AgentState:
        """Download papers from HuggingFace Daily Papers"""
        logger.info("Entered _download_papers_node")
        try:
            target_date = state.get("target_date")
            response = await self.downloader_service.download_papers(target_date)
            logger.info(response)
            return {**state, "last_response": response}
        except Exception as e:
            logger.error(f"Error downloading papers: {str(e)}")
            return {**state, "error": f"Error downloading papers: {str(e)}"}
        
    async def _summarize_papers_node(self, state: AgentState) -> AgentState:
        """Summarize papers and save to database"""
        try:
            target_date = state.get("target_date") or datetime.now().strftime("%Y-%m-%d")
            processed_summary_ids, response_msg = await self.summary_service.summarize_papers_for_date(target_date)

            return {**state, "messages": [AIMessage(content=response_msg)], "current_papers": processed_summary_ids} # una lista degli ID dei papers correnti. Cosi' poi dall'id se l'utente ti chiede paper numero 1, tu scegli il primo della lista, cerchi nel db, ottieni la posizione del summary e crei il post.
        except Exception as e:
            return {**state, "error": f"Error summarizing papers: {str(e)}"}
    
    
    async def _create_linkedin_post_by_position_node(self: AgentState) -> AgentState:
        pass

    async def _create_linkedin_post_by_title_node(self: AgentState) -> AgentState:
        pass

    async def _list_papers_by_date_node(self: AgentState) -> AgentState:
        pass

    async def _general_chat_node(self, state: AgentState) -> AgentState:
        pass



    async def _clarify_request_node(self: AgentState) -> AgentState:
        pass



    async def process_user_input(self, user_input: str, session_id: str) -> str:
        """Process user input through the conversational workflow"""
        initial_state = {
            "messages": [HumanMessage(content=user_input)],
        }
        config = {"configurable": {
            "thread_id": int(session_id)
        }}
        
        final_state = await self.graph.ainvoke(
            initial_state,
            config=config
        )
        
        # Extract response and intent for memory
        response_text = final_state.get("messages", [])[-1].content if final_state.get("messages") else "I'm not sure how to respond to that."
        
        if final_state.get("error"):
            return f"Error: {final_state['error']}"
        
        return response_text

import asyncio

async def main():
    agent = ChatBotAgent()
    await agent.initialize()

    print("🤖 ChatBotAgent started! Type 'exit' to quit.\n")

    try:
        while True:
            user_input = input("You: ")
            if user_input.lower() in ["exit", "quit"]:
                break

            response = await agent.process_user_input(user_input, "123")
            print(f"Agent: {response}\n")
    finally:
        await agent.cleanup()


if __name__ == "__main__":
    asyncio.run(main())