"""Superviser Agent Subgraph."""

from langchain.chat_models import init_chat_model
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    get_buffer_string,
)
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

try:
    from .configuration import Configuration
    from .states import AgentInputState, AgentState, ClarifyWithUser, ResearchQuestion
    # from prompts import PROJECT_RESEARCH_AGENT_PROMPT, SEARCH_INSTRUCTIONS
    # from providers.model_provider_factory import ModelProviderFactory
    # from states import PlanningState, ResearchState, SearchQuery

except ImportError:
    import rootutils

    rootutils.setup_root(__file__, indicator=".git", pythonpath=True)
    from src.agent.configuration import Configuration

    # from src.agent.prompts import PROJECT_RESEARCH_AGENT_PROMPT, SEARCH_INSTRUCTIONS
    from src.agent.states import (
        AgentInputState,
        AgentState,
        ClarifyWithUser,
        ResearchQuestion,
    )
