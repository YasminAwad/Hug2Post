from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
import asyncio
import uuid
from typing import Dict
import logging

from app.services.agent import ChatBotAgent

# Import your existing agent class
# from your_agent_module import ChatBotAgent

# Global agent instance and session storage
agent = None
sessions: Dict[str, str] = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    global agent
    
    # Startup
    try:
        # Replace with your actual agent class import
        agent = ChatBotAgent()
        await agent.initialize()
        print("🤖 ChatBot Agent initialized successfully!")
    except Exception as e:
        logging.error(f"Failed to initialize agent: {e}")
        raise e
    
    yield
    
    # Shutdown
    if agent:
        try:
            await agent.cleanup()
            print("🤖 ChatBot Agent cleaned up successfully!")
        except Exception as e:
            logging.error(f"Error during cleanup: {e}")

app = FastAPI(
    title="ChatBot API", 
    description="API for chatbot interactions",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response models
class ChatRequest(BaseModel):
    message: str
    session_id: str = None

class ChatResponse(BaseModel):
    response: str
    session_id: str

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Main chat endpoint that processes user messages
    """
    global agent
    
    if not agent:
        raise HTTPException(status_code=500, detail="Agent not initialized")
    
    try:
        # Generate session ID if not provided
        if not request.session_id:
            session_id = str(uuid.uuid4())
        else:
            session_id = request.session_id
        
        # Store session (optional: implement session management logic here)
        sessions[session_id] = session_id
        
        # Process the user input through your existing agent
        response_text = await agent.process_user_input(request.message, session_id)
        
        return ChatResponse(
            response=response_text,
            session_id=session_id
        )
        
    except Exception as e:
        logging.error(f"Error processing chat request: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "ChatBot API is running"}

@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Get session information (optional endpoint for session management)"""
    if session_id in sessions:
        return {"session_id": session_id, "active": True}
    else:
        raise HTTPException(status_code=404, detail="Session not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",  # Replace with your actual file name
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )