import sys
from pathlib import Path

from langgraph.graph import START, StateGraph
from loguru import logger

try:
    from .clarification_agent_subgraph import clarify_with_user, write_research_brief
    from .configuration import Configuration
    from .final_report_generation import final_report_graph
    from .states import (
        AgentInputState,
        AgentState,
        SupervisorState,
    )
    from .supervisor_agent import supervisor, supervisor_tool
except ImportError:
    import rootutils

    rootutils.setup_root(__file__, indicator=".git", pythonpath=True)

    from src.agent.clarification_agent_subgraph import (
        clarify_with_user,
        write_research_brief,
    )
    from src.agent.configuration import Configuration
    from src.agent.final_report_generation import final_report_graph
    from src.agent.states import (
        AgentInputState,
        AgentState,
        SupervisorState,
    )
    from src.agent.supervisor_agent import supervisor, supervisor_tool

config = {
    "handlers": [
        {"sink": sys.stdout, "level": "ERROR", "colorize": True},
        {
            "sink": f"{Path.cwd().parent.parent / f'{__name__}.log'}",
            "enqueue": True,
            "level": "DEBUG",
            "rotation": "10 MB",
            "compression": "zip",
        },
    ],
}


logger.configure(**config)

logger.info("Initializing Project Planning Genie...")
supervisor_builder = StateGraph(SupervisorState, context_schema=Configuration)
supervisor_builder.add_node("supervisor", supervisor)
supervisor_builder.add_node("supervisor_tool", supervisor_tool)
supervisor_builder.add_edge(START, "supervisor")
supervisor_subgraph = supervisor_builder.compile(name="Supervisor")

agent_builder = StateGraph(
    AgentState,
    input_schema=AgentInputState,
    context_schema=Configuration,
)

agent_builder.add_node("clarify_with_user", clarify_with_user)
agent_builder.add_node("write_research_brief", write_research_brief)
agent_builder.add_node("supervisor_subgraph", supervisor_subgraph)
agent_builder.add_node("final_report_generation", final_report_graph)


agent_builder.add_edge(START, "clarify_with_user")
agent_builder.add_edge(
    "supervisor_subgraph",
    "final_report_generation",
)
logger.info("Compiling Project Planning Genie...")
project_planning_genie_graph = agent_builder.compile(name="Project Planning Genie")
