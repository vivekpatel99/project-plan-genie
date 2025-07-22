from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    get_buffer_string,
)
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

try:
    from .configuration import Configuration  # noqa: I001
    from .final_report_generation import final_report_generation
    from .researcher_agent import compress_research, research_agent, research_tools
    from .states import (
        AgentInputState,
        AgentState,
        ClarifyWithUser,
        ResearcherOutputState,
        ResearchQuestion,
        ResearchState,
        StatesKeys,
        SupervisorState,
    )
    from .supervisor_agent import supervisor, supervisor_tool

    from .clarification_agent_subgraph import clarify_with_user, write_research_brief
except ImportError:
    import rootutils

    rootutils.setup_root(__file__, indicator=".git", pythonpath=True)

    from src.agent.clarification_agent_subgraph import clarify_with_user, write_research_brief
    from src.agent.configuration import Configuration
    from src.agent.final_report_generation import final_report_generation
    from src.agent.prompts import CLARIFY_WITH_USER_INSTRUCTIONS, TRANSFORM_MESSAGES_INTO_RESEARCH_TOPIC_PROMPT
    from src.agent.states import (
        AgentInputState,
        AgentState,
        ClarifyWithUser,
        ResearcherOutputState,
        ResearchQuestion,
        ResearchState,
        StatesKeys,
        SupervisorState,
    )
    from src.agent.supervisor_agent import supervisor, supervisor_tool


supervisor_builder = StateGraph(SupervisorState, config_schema=Configuration)
supervisor_builder.add_node("supervisor", supervisor)
supervisor_builder.add_node("supervisor_tool", supervisor_tool)
supervisor_builder.add_edge(START, "supervisor")
supervisor_subgraph = supervisor_builder.compile(name="Supervisor")

agent_builder = StateGraph(
    AgentState,
    input_schema=AgentInputState,
    config_schema=Configuration,
)

agent_builder.add_node("clarify_with_user", clarify_with_user)
agent_builder.add_node("write_research_brief", write_research_brief)
agent_builder.add_node("final_report_generation", final_report_generation)
agent_builder.add_node("supervisor_subgraph", supervisor_subgraph)

agent_builder.add_edge(START, "clarify_with_user")
agent_builder.add_edge(
    "supervisor_subgraph",
    "final_report_generation",
)
agent_builder.add_edge("final_report_generation", END)

project_planning_agent = agent_builder.compile(name="Project Planning Agent")


# --- Final graph ----------------------------------------------------------------------
# agent_builder.add_node("clarify_subgraph", clarify_subgraph)


# agent_builder.add_edge(START, "clarify_subgraph")
# agent_builder.add_edge("supervisor_subgraph", "final_report_generation")
# agent_builder.add_edge("final_report_generation", END)

# project_planning_agent = agent_builder.compile(name="Project Planning Agent")
