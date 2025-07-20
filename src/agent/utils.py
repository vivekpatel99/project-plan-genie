import asyncio
import datetime
from typing import Annotated, Literal

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, MessageLikeRepresentation, filter_messages
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg, tool
from tavily import AsyncTavilyClient

try:
    from .configuration import Configuration, SearchAPI
    from .prompts import SUMMARIZE_WEBPAGE_PROMPT
    from .states import ResearchComplete, Summary
except ImportError:
    import rootutils

    rootutils.setup_root(__file__, indicator=".git", pythonpath=True)
    from src.agent.configuration import Configuration, SearchAPI
    from src.agent.prompts import SUMMARIZE_WEBPAGE_PROMPT
    from src.agent.states import ResearchComplete, Summary


def get_notes_from_tool_calls(messages: list[MessageLikeRepresentation]):
    return [tools_msg.content for tools_msg in filter_messages(messages, include_types="tool")]


# --- Tavily Search Tool Utils ---------------------------------------------------------------
TAVILY_SEARCH_DESCRIPTION = (
    "A search engine optimized for comprehensive, accurate, and trusted results. "
    "Useful for when you need to answer questions about current events."
)


async def tavily_search_sync(
    *,
    search_queries,
    max_results: int = 5,
    # topic: Literal["software design", "programming", "technology"] = "programming",
    topic: Literal["general", "news", "finance"] = "general",  # tavily topic hints
    include_raw_content: bool = True,
):
    tavily_async_client = AsyncTavilyClient()
    search_tasks = []
    for query in search_queries:
        search_tasks.append(
            tavily_async_client.search(
                query=query,
                max_results=max_results,
                include_raw_content=include_raw_content,
                topic=topic,
            ),
        )
    search_doc = await asyncio.gather(*search_tasks)
    return search_doc


async def summarize_webpage(model: BaseChatModel, webpage_content: str) -> str:
    try:
        summary = await asyncio.wait_for(
            model.ainvoke(
                [HumanMessage(content=SUMMARIZE_WEBPAGE_PROMPT.format(webpage_content=webpage_content))],
            ),
            timeout=60.0,
        )
        formatted_summary = (
            f"""<summary>\n{summary.summary}\n</summary>\n\n<key_excerpts>\n{summary.key_excerpts}\n</key_excerpts>"""
        )
        # return formatted_summary

    except (TimeoutError, Exception):
        # import traceback

        # print(f"Failed to summarize webpage: {e} - {traceback.format_exc()}")
        return webpage_content
    else:
        return formatted_summary


@tool(description=TAVILY_SEARCH_DESCRIPTION)
async def tavily_search(
    queries: list[str],
    max_results: Annotated[int, InjectedToolArg] = 5,
    # tavily topic hints
    topic: Annotated[Literal["general", "news", "finance"], InjectedToolArg] = "general",
    config: RunnableConfig | None = None,
):
    """Fetch results from Tavily Search."""
    search_results = await tavily_search_sync(
        search_queries=queries,
        max_results=max_results,
        topic=topic,
        include_raw_content=True,
    )
    # Format the search results and deduplicate the  results by URL
    unique_results = {}
    for response in search_results:
        for result in response["results"]:
            url = result["url"]
            if url not in unique_results:
                unique_results[url] = {**result, "query": response["query"]}
    config = Configuration.from_runnable_config(config)
    summarization_model = init_chat_model(
        model=config.summarization_model,
        max_tokens=config.summarization_model_max_tokens,
    )
    structured_summarize_model = summarization_model.with_structured_output(
        Summary,
    ).with_retry(stop_after_attempt=config.max_structured_output_retries)
    max_char_to_include = 10_000  #  Kept under max input token limit

    async def _noop():
        return None

    summarization_tasks = [
        _noop()
        if not result.get("raw_content")
        else summarize_webpage(structured_summarize_model, result["raw_content"][:max_char_to_include])
        for result in unique_results.values()
    ]
    summaries = await asyncio.gather(*summarization_tasks)
    summarized_results = {
        url: {"title": result["title"], "content": result["content"] if summary is None else summary}
        for url, result, summary in zip(unique_results.keys(), unique_results.values(), summaries, strict=False)
    }
    formatted_output = "Search Results:\n"
    for i, (url, result) in enumerate(summarized_results.items()):
        formatted_output += f"\n\n--- SOURCE {i + 1}: {result['title']} ---\n"
        formatted_output += f"URL: {url}\n\n"
        formatted_output += f"SUMMARY:\n{result['content']}\n\n"
        formatted_output += "\n\n" + "-" * 80 + "\n"
    if summarized_results:
        return formatted_output
    return "No valid search results found. Please try different search queries or use a different search API."


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
    tools = [tool(ResearchComplete)]
    # config = Configuration.from_runnable_config(config)
    search_api_name = get_config_value(config.search_api)  # get the name of the api
    search_api = SearchAPI(search_api_name)  # create a ENUM object for comparison
    tools.extend(await get_search_tool(search_api))
    # existing_tool_names = {tool.name if hasattr(tool, "name") else tool.get("name", "web_search") for tool in tools}
    return tools


def openai_websearch_called(response):
    tool_outputs = response.additional_kwargs.get("tool_outputs")
    if tool_outputs:
        for tool_output in tool_outputs:
            if tool_output.get("type") == "web_search_call":
                return True
    return False


async def execute_tool_safely(tool, args, config: dict | None = None):
    # config = Configuration.from_runnable_config(config)
    try:
        return await tool.ainvoke(args, config)
    except Exception as e:
        # import traceback

        # print(f"Error executing tool: {e} - {traceback.format_exc()}")
        return f"Error executing tool: {e}"  # - {traceback.format_exc()}"


def get_today_str() -> str:
    """Get current date in a human-readable format."""
    return datetime.datetime.now(tz=datetime.UTC).strftime("%a %b %-d, %Y")


def is_token_limit_exceeded(exception: Exception, model_name: str | None = None):
    """
    Checks if a given exception indicates that the token limit for a specific model provider has been exceeded.

        exception (Exception): The exception to inspect.
        model_name (str | None, optional): The name of the model that raised the exception. Used to determine the provider.

        bool: True if the exception is due to exceeding the token limit for the detected provider, False otherwise.

    Supported Providers:
        - OpenAI (model_name starts with "openai")
        - Gemini/Google (model_name starts with "gemini:" or "google:")
        - Perplexity (model_name starts with "sonar")

    Note:
        If model_name is not provided or does not match a supported provider, returns False.

    """
    error_str = str(exception).lower()
    provider = None
    if model_name:
        model_name = model_name.lower()
        if model_name.startswith("openai"):
            provider = "openai"
        elif model_name.startswith(("gemini:", "google:")):
            provider = "gemini"
        elif model_name.startswith("sonar"):
            provider = "perplexity"

    if provider == "openai":
        return _check_openai_token_limit(exception, error_str)
    if provider == "gemini":
        return _check_gemini_token_limit(exception, error_str)
    if provider == "perplexity":
        return _check_perplexity_ai_token_limit(exception, error_str)
    return False


def _check_openai_token_limit(exception: Exception, error_message: str | None = None):
    """
    Check if the given exception is related to OpenAI token limit issues.

    This function determines whether an exception is specifically due to exceeding OpenAI's
    token limits by inspecting the exception type, class name, and module. It checks for
    OpenAI-related errors that indicate token or context length issues.

    Args:
        exception (Exception): The exception to examine.
        error_message (str | None): Optional additional error message to search for keywords.

    Returns:
        bool: True if the exception indicates a token limit issue with OpenAI, False otherwise.

    """
    exception_type = str(type(exception))
    class_name = exception.__class__.__name__
    module_name = getattr(exception.__class__, "__module__", "")
    is_openai_exception = "openai" in exception_type.lower() or "openai" in module_name.lower()

    is_bad_request = class_name == ["BadRequestError", "InvalidRequestError"]
    if is_openai_exception and is_bad_request:
        token_keywords = ("token", "context", "length", "maximum context", "reduce")
        if any(keyword in error_message for keyword in token_keywords):
            return True
    return bool(
        hasattr(exception, "code")
        and hasattr(exception, "type")
        and (
            getattr(exception, "code", "") == "context_length_exceeded"
            or getattr(exception, "type", "") == "invalid_request_error"
        ),
    )


def _check_perplexity_ai_token_limit(exception: Exception, error_message: str | None = None):
    raise NotImplementedError


def _check_gemini_token_limit(exception: Exception):
    exception_type = str(type(exception))
    class_name = exception.__class__.__name__
    module_name = getattr(exception.__class__, "__module__", "")

    is_google_exception = "google" in exception_type.lower() or "google" in module_name.lower()
    is_resource_exhausted = class_name in ["ResourceExhausted", "GoogleGenerativeAIFetchError"]
    if is_google_exception and is_resource_exhausted:
        return True
    return "google.api_core.exceptions.resourceexhausted" in exception_type.lower()


# TODO(@viv): fill  out this  -Move to constants 123
MAX_TOKEN_LIMITS = {}
