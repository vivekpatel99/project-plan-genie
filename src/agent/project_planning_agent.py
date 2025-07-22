from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    get_buffer_string,
)
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

try:
    from .clarification_agent_subgraph import clarify_with_user, write_research_brief
    from .configuration import Configuration
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
    from .utils import get_today_str
except ImportError:
    import rootutils

    rootutils.setup_root(__file__, indicator=".git", pythonpath=True)

    from src.agent.clarification_agent_subgraph import clarify_with_user, write_research_brief
    from src.agent.configuration import Configuration
    from src.agent.final_report_generation import final_report_generation
    from src.agent.prompts import CLARIFY_WITH_USER_INSTRUCTIONS, TRANSFORM_MESSAGES_INTO_RESEARCH_TOPIC_PROMPT
    from src.agent.researcher_agent import compress_research, research_agent, research_tools
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
    from src.agent.utils import get_today_str

agent_builder = StateGraph(
    AgentState,
    input_schema=AgentInputState,
    config_schema=Configuration,
)


# --- Supervisor subgraph ----------------------------------------------------------------------
supervisor_builder = StateGraph(SupervisorState, config_schema=Configuration)
supervisor_builder.add_node("supervisor", supervisor)
supervisor_builder.add_node("supervisor_tool", supervisor_tool)

supervisor_builder.add_edge(START, "supervisor")
supervisor_subgraph = supervisor_builder.compile(name="Supervisor")
agent_builder.add_node("clarify_with_user", clarify_with_user)
agent_builder.add_node("write_research_brief", write_research_brief)
agent_builder.add_node("final_report_generation", final_report_generation)
agent_builder.add_node("supervisor_subgraph", supervisor_subgraph)

# --- Researcher subgraph ----------------------------------------------------------------------
# research_builder = StateGraph(ResearchState, output_schema=ResearcherOutputState, config_schema=Configuration)
# research_builder.add_node("research_agent", research_agent)
# research_builder.add_node("research_tools", research_tools)
# research_builder.add_node("compress_research", compress_research)

# research_builder.add_edge(START, "research_agent")
# research_builder.add_edge("compress_research", END)
# researcher_subgraph = research_builder.compile(name="Research Agent")

# --- Clarification subgraph ----------------------------------------------------------------------
# clarify_builder = StateGraph(
#     AgentState,
#     input_schema=AgentInputState,
#     config_schema=Configuration,
# )


# clarify_builder.add_node("clarify_with_user", clarify_with_user)
# clarify_builder.add_node("write_research_brief", write_research_brief)

# clarify_builder.add_edge(START, "clarify_with_user")
# clarify_subgraph = clarify_builder.compile(name="Clarify with User")


# --- Final graph ----------------------------------------------------------------------

agent_builder.add_edge(START, "clarify_with_user")
agent_builder.add_edge("supervisor_subgraph", "final_report_generation")
agent_builder.add_edge("final_report_generation", END)

project_planning_agent = agent_builder.compile(name="Project Planning Agent")


"""  
supervisor_builder = StateGraph(SupervisorState, config_schema=Configuration)
supervisor_builder.add_node("supervisor", supervisor)
supervisor_builder.add_node("supervisor_tools", supervisor_tools)
supervisor_builder.add_edge(START, "supervisor")
supervisor_subgraph = supervisor_builder.compile()


researcher_builder = StateGraph(ResearcherState, output=ResearcherOutputState, config_schema=Configuration)
researcher_builder.add_node("researcher", researcher)
researcher_builder.add_node("researcher_tools", researcher_tools)
researcher_builder.add_node("compress_research", compress_research)
researcher_builder.add_edge(START, "researcher")
researcher_builder.add_edge("compress_research", END)
researcher_subgraph = researcher_builder.compile()


deep_researcher_builder = StateGraph(AgentState, input=AgentInputState, config_schema=Configuration)
deep_researcher_builder.add_node("clarify_with_user", clarify_with_user)
deep_researcher_builder.add_node("write_research_brief", write_research_brief)
deep_researcher_builder.add_node("research_supervisor", supervisor_subgraph)
deep_researcher_builder.add_node("final_report_generation", final_report_generation)
deep_researcher_builder.add_edge(START, "clarify_with_user")
deep_researcher_builder.add_edge("research_supervisor", "final_report_generation")
deep_researcher_builder.add_edge("final_report_generation", END)

deep_researcher = deep_researcher_builder.compile()
"""
