"""Research Agent Subgraph."""

from langchain.chat_models import init_chat_model
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

from agent.utils import get_all_tools

try:
    from .configuration import Configuration
    from .states import ResearchState
    # from prompts import PROJECT_RESEARCH_AGENT_PROMPT, SEARCH_INSTRUCTIONS
    # from providers.model_provider_factory import ModelProviderFactory
    # from states import PlanningState, ResearchState, SearchQuery

except ImportError:
    import rootutils

    rootutils.setup_root(__file__, indicator=".git", pythonpath=True)
    from src.agent.configuration import Configuration
    from src.agent.states import ResearchState

# Initialize a configurable model that we will use throughout the agent
configurable_model = init_chat_model(
    configurable_fields=("model", "max_tokens", "api_key"),
)


async def research_agent(state: ResearchState, config: RunnableConfig):
    config = Configuration.from_runnable_config(config)
    research_msgs = state.get("research_messages", [])
    tools = await get_all_tools(config)

    if len(tools) == 0:
        msg = "No tools found to conduct research, please configure Search API"
        raise ValueError(msg)
    research_model_config = {
        "model": config.research_model,
        "max_tokens": config.research_model_max_tokens,
        # "api_key": config.research_model_api_key,
    }
    research_model = (
        configurable_model.bind_tools(
            tools,
        )
        .with_retry(stop_after_attempt=config.max_structured_output_retries)
        .with_config(research_model_config)
    )
    response = await research_model.ainvoke(
        research_msgs,
    )
    return Command(
        goto="research_tool",
        update={
            "research_messages": [response],
            "tool_call_iterations": state.get("tool_call_iterations", 0) + 1,
        },
    )


async def research_tools(state: ResearchState, config: RunnableConfig): ...


async def compres_research(state: ResearchState, config: RunnableConfig): ...
