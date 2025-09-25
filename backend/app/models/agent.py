from langchain_core.messages import HumanMessage, SystemMessage
from typing import Annotated,Sequence, Literal, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing import Dict, List, Any, Optional, Annotated

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    last_response: Optional[str]
    current_papers: Optional[List[int]]
    intent: Optional[str]
    parameters: Optional[Dict[str, Any]]
    target_date: Optional[str]
    error: Optional[str]