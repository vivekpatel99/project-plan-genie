from typing import Annotated, Literal

from langchain_core.messages import MessageLikeRepresentation, filter_messages
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg, tool

from agent.configuration import Configuration, SearchAPI
from agent.states import ResearchComplete


def get_notes_from_tool_calls(messages: list[MessageLikeRepresentation]):
    return [tools_msg.content for tools_msg in filter_messages(messages, include_types="tool")]


# --- Tavily Search Tool Utils ---------------------------------------------------------------
TAVILY_SEARCH_DESCRIPTION = (
    "A search engine optimized for comprehensive, accurate, and trusted results. "
    "Useful for when you need to answer questions about current events."
)


async def tavily_search(
    queries: list[str],
    max_results: Annotated[int, InjectedToolArg],
    topic: Annotated[Literal["general", "science", "technology"], InjectedToolArg] = "general",
    config: RunnableConfig | None = None,
): ...


@tool(description="TAVILY_SEARCH_DESCPRIPTION")
async def get_search_tool(search_api: SearchAPI):
    if search_api == SearchAPI.OPENAI:
        return [{"type": "web_search_preview"}]
    if search_api == SearchAPI.TAVILY:
        search_tool = tavily_search
        search_tool.metadata = {**(search_tool.metadata or {}), "type": "search", "name": "web_search"}
        return [search_tool]
    if search_api == SearchAPI.NONE:
        return []
    return []


def get_config_value(value):
    if value == "none":
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return value
    return value.value


async def get_all_tools(config: RunnableConfig):
    tools = [tool[ResearchComplete]]
    config = Configuration.from_runnable_config(config)
    search_api = SearchAPI(get_config_value(config.search_api))
    tools.extend(await get_search_tool(search_api))
    existing_tool_names = {tool.name if hasattr(tool, "name") else tool.get("name", "web_search") for tool in tools}
    return existing_tool_names
