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
    from .clarification_agent_subgraph import clarify_subgraph
    from .configuration import Configuration
    from .final_report_generation import final_report_generation
    from .states import AgentInputState, AgentState, ClarifyWithUser, ResearchQuestion, StatesKeys
    from .supervisor_agent import supervisor_subgraph
    from .utils import get_today_str
except ImportError:
    import rootutils

    rootutils.setup_root(__file__, indicator=".git", pythonpath=True)
    from src.agent.clarification_agent_subgraph import clarify_subgraph
    from src.agent.configuration import Configuration
    from src.agent.final_report_generation import final_report_generation
    from src.agent.prompts import CLARIFY_WITH_USER_INSTRUCTIONS, TRANSFORM_MESSAGES_INTO_RESEARCH_TOPIC_PROMPT
    from src.agent.states import AgentInputState, AgentState, ClarifyWithUser, ResearchQuestion, StatesKeys
    from src.agent.supervisor_agent import supervisor_subgraph
    from src.agent.utils import get_today_str


agent_builder = StateGraph(
    AgentState,
    input_schema=AgentInputState,
    config_schema=Configuration,
)


agent_builder.add_node("clarify_subgraph", clarify_subgraph)
agent_builder.add_node("supervisor_subgraph", supervisor_subgraph)
agent_builder.add_node("final_report_generation", final_report_generation)

agent_builder.add_edge(START, "clarify_subgraph")
agent_builder.add_edge("clarify_subgraph", "supervisor_subgraph")
agent_builder.add_edge("supervisor_subgraph", "final_report_generation")
agent_builder.add_edge("final_report_generation", END)

project_planning_agent = agent_builder.compile(name="Project Planning Agent")
