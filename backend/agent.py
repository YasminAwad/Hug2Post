from app.services.llm import LLMService
from pathlib import Path
from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import MemorySaver
from typing import Dict, List, Any, Tuple
import json

from app.services.summarizer import SummaryService
from app.services.linkedin import LinkedInService
from app.services.listing import PaperListingService
from app.services.database import DatabaseService
from app.services.downloader import DownloaderService
from app.services.intent_classifier import IntentClassifierService
from app.models.agent import AgentState
from datetime import datetime
from app.config.logging import logger
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from app.services.parameter_extractor import ParameterExtractorService

class ChatBotAgent:
    """Main agent orchestrating all services with database integration"""

    def __init__(self, database_url: str = None, session_id: str = "default"):

        # Initialize database service first
        self.database_service = DatabaseService(database_url) if database_url else DatabaseService()
        
        # Initialize other services
        self.llm_service = LLMService()
        self.intent_classifier = IntentClassifierService(self.llm_service)
        self.parameter_extractor_service = ParameterExtractorService(self.llm_service)
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
        # await self.database_service.drop_tables()
        # await self.database_service.create_tables()
        print("Database connected and initialized")
    
    async def cleanup(self):
        """Cleanup database connections"""
        await self.database_service.disconnect()

    def _setup_directories(self):
        """Create necessary directories"""
        Path("papers").mkdir(exist_ok=True)
        Path("summaries").mkdir(exist_ok=True)

    def _get_history_and_user_input(self, state: AgentState):

        role_map = {
            SystemMessage: "System",
            HumanMessage: "Human",
            AIMessage: "Assistant",
        }

        messages = state.get("messages", [])[:-1]

        history = "\n".join(
            f"{role_map.get(type(msg), 'Unknown')}: {msg.content}"
            for msg in messages
        )

        user_input = state.get("messages", [])[-1].content if state.get("messages") else ""

        return history, user_input

    def _create_graph(self) -> StateGraph:
        """Create the LangGraph workflow"""
        graph = StateGraph(AgentState)

        graph.add_node("intent_classifier", self._intent_classifier_node)
        graph.add_node("parameter_extractor", self._parameter_extractor_node)
        graph.add_node("summarize_papers", self._summarize_papers_node)
        graph.add_node("download_papers", self._download_papers_node)
        graph.add_node("create_linkedin_post_from_position", self._create_linkedin_post_by_position_node)
        graph.add_node("list_papers_by_date", self._list_papers_by_date_node)
        graph.add_node("general_chat", self._general_chat_node)
        graph.add_node("clarify_request", self._clarify_request_node)
        graph.add_node("modify_linkedin_post", self._modify_linkedin_post_node)

        graph.set_entry_point("intent_classifier")

        graph.add_conditional_edges(
            "intent_classifier",
            self._route_by_intent,
            {
                "summarize": "parameter_extractor",
                "linkedin by position": "parameter_extractor",
                "list by date": "parameter_extractor",
                "modify linkedin": "modify_linkedin_post",
                "general": "general_chat",
                "clarify": "clarify_request",
                "error": "__end__"
            }
        )

        graph.add_conditional_edges(
            "parameter_extractor",
            self._route_by_action,
            {
                "summarize": "download_papers",
                "linkedin by position": "create_linkedin_post_from_position",
                "list": "list_papers_by_date",
                "error": "__end__"
            }
        )

        graph.add_edge("download_papers", "summarize_papers")
        graph.add_edge("summarize_papers", "__end__")
        graph.add_edge("create_linkedin_post_from_position", "__end__")
        graph.add_edge("modify_linkedin_post", "__end__")
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
        elif intent == "create_linkedin_from_position":
            return "linkedin by position"
        elif intent == "modify_linkedin_post":
            return "modify linkedin"
        elif intent == "list_papers_by_date":
            return "list by date"
        elif intent == "general_chat":
            return "general"
        elif intent == "need_clarification":
            return "clarify"
        else:
            return "error"

    def _route_by_action(self, state: AgentState) -> str:
        """Route based on the action after parameter extraction"""
        intent = state.get("intent")
        if state.get("error"):
            return "error"
        elif intent == "summarize_papers":
            return "summarize"
        elif intent == "create_linkedin_from_position":
            return "linkedin by position"
        elif intent == "list_papers_by_date":
            return "list"
        else:
            return "error"
        
    async def _intent_classifier_node(self, state: AgentState) -> AgentState:
        """Classify user intent"""
        logger.info("Entered _intent_classifier_node")

        history, user_input = self._get_history_and_user_input(state)

        try:
            intent = await self.intent_classifier.classify_intent(history, user_input)
            return {**state, "intent": intent}
        except Exception as e:
            return {**state, "error": f"Intent classification failed: {str(e)}"}
        
    async def _download_papers_node(self, state: AgentState) -> AgentState:
        """Download papers from HuggingFace Daily Papers"""
        logger.info("Entered _download_papers_node")
        try:
            target_date = state.get("parameters", {}).get("target_date")
            # create folder if not exists
            response = await self.downloader_service.download_papers(target_date)
            logger.info(response)
            return {**state, "last_response": response}
        except Exception as e:
            logger.error(f"Error downloading papers: {str(e)}")
            return {**state, "error": f"Error downloading papers: {str(e)}"}
        
    async def _summarize_papers_node(self, state: AgentState) -> AgentState:
        """Summarize papers and save to database"""
        logger.info("Entered _summarize_papers_node")
        try:
            target_date = state.get("parameters", {}).get("target_date") or datetime.now().strftime("%Y-%m-%d")
            processed_summary_ids, response_msg = await self.summary_service.summarize_papers_for_date(target_date)

            return {**state, "messages": [AIMessage(content=response_msg)], "current_papers": processed_summary_ids} 
        
        except Exception as e:
            return {**state, "error": f"Error summarizing papers: {str(e)}"}
        
    async def _parameter_extractor_node(self, state: AgentState) -> AgentState:
        """Extract parameters from user input"""
        logger.info("Entered _parameter_extractor_node")

        history, user_input = self._get_history_and_user_input(state)
        intent = state.get("intent")

        try:
            parameters = await self.parameter_extractor_service.extract_parameters(history, user_input, intent)

        except Exception as e:
            return {**state, "error": f"Error extracting parameters: {str(e)}"} 
        
        if intent == "summarize_papers" or intent == "list_papers_by_date":
            
            if not parameters.get("year"):
                parameters["year"] = str(datetime.now().year)

            if not parameters.get("month") or int(parameters.get("month")) > 12 or int(parameters.get("month")) < 1 or not parameters.get("day") or int(parameters.get("day")) > 31 or int(parameters.get("day")) < 1:
                return {**state, "error": "Invalid date format. Please specify a year, a month, and a day.", "messages": [AIMessage(content="The date you've sent is invalid. Please specify a year, a month, and a day.")]}
            
            target_date = f"{parameters['year']}-{parameters['month']}-{parameters['day']}" or datetime.now().strftime("%Y-%m-%d")
            parameters["target_date"] = target_date

        logger.info(f"Parameters: {parameters}")
            
        return {**state, "parameters": parameters}
    
    async def _create_linkedin_post_by_position_node(self, state: AgentState) -> AgentState:
        logger.info("Entered _create_linkedin_post_by_position_node")
        position = int(state.get("parameters", {}).get("paper_position"))
        paper_id = int(state.get("current_papers", [])[position-1])
        try:
            linkedin_post_content, linkedin_post_id = await self.linkedin_service.create_post_for_paper_by_position(paper_id)
            return {**state, "messages": [AIMessage(content=linkedin_post_content)], "current_post": linkedin_post_id, "current_post_text": linkedin_post_content}
        except Exception as e:
            return {**state, "error": f"Error creating post: {str(e)}"}
        
    async def _modify_linkedin_post_node(self, state: AgentState) -> AgentState:
        logger.info("Entered _modify_linkedin_post_node")
        post = state.get("current_post_text")
        if post is None:
            return {**state, "error": "No post to modify"}

        user_request = state.get("messages", [])[-1].content
        linkedin_post_id = state.get("current_post")

        try:
            linkedin_post_content = await self.linkedin_service.change_post(post, user_request, linkedin_post_id)
            return {**state, "messages": [AIMessage(content=linkedin_post_content)]}
        except Exception as e:
            return {**state, "error": f"Error modifying post: {str(e)}"}
        
    async def _list_papers_by_date_node(self, state: AgentState) -> AgentState:
        """Entered _list_papers_by_date_node"""
        logger.info("Entered _list_papers_by_date_node")

        target_date = state.get("parameters", {}).get("target_date") or datetime.now().strftime("%Y-%m-%d")

        logger.info(f"target_date: {target_date}")

        try:
            processed_papers_ids, response_msg = await self.listing_service.retrieve_papers_by_date(target_date)

            logger.info("processed_papers_ids:", processed_papers_ids)

            return {**state, "messages": [AIMessage(content=response_msg)], "current_papers": processed_papers_ids}
        except Exception as e:
            return {**state, "error": f"Error listing papers: {str(e)}"}

    async def _general_chat_node(self, state: AgentState) -> AgentState:
        """Generate general chat response"""
        logger.info(f"🤖 Entered General Response")
        role_map = {
            SystemMessage: "System",
            HumanMessage: "Human",
            AIMessage: "Assistant",
        }

        messages = state.get("messages", [])[:-1] 

        history = "\n".join(
            f"{role_map.get(type(msg), 'Unknown')}: {msg.content}"
            for msg in messages
        )
        logger.info(f"History: {history}")
        user_input = state.get("messages", [])[-1].content if state.get("messages") else ""
        logger.info(f"User input: {user_input}")
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""You are a helpful research paper assistant with memory of previous conversations.
            
            You can help users with its request.
                    
            How can I help you with your research today?"""),
            HumanMessage(content=f"""Conversation Context:
{history}

Current User Input: {user_input}""")
        ])
        
        response = await self.llm_service.generate_response(prompt.format_messages())
        logger.info(f"🤖 General Response: {response}")
        return {**state, "messages": [AIMessage(content=response.content)]}

    async def _clarify_request_node(self, state: AgentState) -> AgentState:
        """Handle unclear requests with context"""
        user_input = state.get("messages", [])[-1].content if state.get("messages") else ""
        
        response_msg = f"""I'm not quite sure what you'd like me to do. Here are some things I can help with:

- Summarize papers
- Create LinkedIn posts
- List papers by date

Could you clarify what you'd like me to do?"""
        
        return {**state, "messages": [AIMessage(content=response_msg)]}

    async def process_user_input(self, user_input: str, session_id: str) -> str:
        """Process user input through the conversational workflow"""
        thread_id = session_id_to_int(session_id)

        initial_state = {
            "messages": [HumanMessage(content=user_input)]
        }
        config = {"configurable": {
            "thread_id": int(thread_id)
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

def session_id_to_int(session_id: str) -> int:
    """Convert session ID string to integer for thread_id"""
    try:
        # If it's already a number, return it as int
        return int(session_id)
    except ValueError:
        # If it's a UUID or other string, convert to hash
        return abs(hash(session_id)) % (10**8)
    
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
    #asyncio.run(main())
    pass