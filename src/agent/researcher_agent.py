"""Research Agent Subgraph."""

import asyncio

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage, filter_messages
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

try:
    from .configuration import Configuration
    from .prompts import COMPRESS_RESEARCH_SIMPLE_HUMAN_MESSAGE, COMPRESS_RESEARCH_SYSTEM_PROMPT
    from .states import ResearcherOutputState, ResearchState
    from .utils import execute_tool_safely, get_all_tools, openai_websearch_called
except ImportError:
    import rootutils

    rootutils.setup_root(__file__, indicator=".git", pythonpath=True)
    from src.agent.configuration import Configuration
    from src.agent.prompts import COMPRESS_RESEARCH_SIMPLE_HUMAN_MESSAGE, COMPRESS_RESEARCH_SYSTEM_PROMPT
    from src.agent.states import ResearcherOutputState, ResearchState
    from src.agent.utils import execute_tool_safely, get_all_tools, openai_websearch_called

# Initialize a configurable model that we will use throughout the agent
configurable_model = init_chat_model(
    configurable_fields=("model", "max_tokens", "api_key"),
)


async def research_agent(state: ResearchState, config: RunnableConfig):
    config = Configuration.from_runnable_config(config)
    research_msgs = state.get("research_messages", [])
    tools = await get_all_tools(config)

    if len(tools) <= 1:  # ResearchComplete is default tool in the list
        msg = "No tools found to conduct research, please configure Search API"
        raise ValueError(msg)

    research_model_config = {
        "model": config.research_model,
        "max_tokens": config.research_model_max_tokens,
        # "api_key": config.research_model_api_key,
        "tags": ["langsmith:nostream"],
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
        goto="research_tools",
        update={
            "research_messages": [response],
            "tool_call_iterations": state.get("tool_call_iterations", 0) + 1,
        },
    )


async def research_tools(state: ResearchState, config: RunnableConfig):
    config = Configuration.from_runnable_config(config)
    research_msgs = state.get("research_messages", [])
    most_recent_message = research_msgs[-1]

    # Early exit Criteria: No tools calls (or native web search calls) were made by the researcher
    if not most_recent_message.tool_calls and not openai_websearch_called(most_recent_message):
        return Command(goto="compress_research")

    # Otherwise, execute tools and gather results
    tools = await get_all_tools(config)

    tools_by_name = {tool.name if hasattr(tool, "name") else tool.get("name", "web_search"): tool for tool in tools}

    tool_calls = most_recent_message.tool_calls

    async_responses = [
        execute_tool_safely(tools_by_name[tool_call["name"]], tool_call["args"], config) for tool_call in tool_calls
    ]
    observations = await asyncio.gather(*async_responses)
    tool_outputs = [
        ToolMessage(
            content=observation,
            name=tool_call["name"],
            tool_call_id=tool_call["id"],
        )
        for observation, tool_call in zip(observations, tool_calls, strict=False)
    ]
    # Late Exit Criteria: We have exceeded our max guardrail tool call iterations or the most recent message contains ResearchComplete tool call
    # These are late exit criteria because we need to add ToolMessage
    update = {"research_messages": tool_outputs}
    if state.get("tool_call_iterations", 0) >= config.max_react_tool_calls or any(
        tool_call["name"] == "ResearchComplete" for tool_call in tool_calls
    ):
        return Command(
            goto="compress_research",
            update=update,
        )
    return Command(goto="research_agent", update=update)


async def compress_research(state: ResearchState, config: RunnableConfig):
    config = Configuration.from_runnable_config(config)
    synthesize_attempts = 0
    compression_model = configurable_model.with_config(
        {
            "model": config.compression_model,
            "max_tokens": config.compression_model_max_tokens,
            # "api_key": config.compress_model_api_key,
        },
    )
    researcher_msgs = state.get("research_messages", [])

    # Update the system prompts to now focus on compression rather than research
    researcher_msgs[0] = SystemMessage(
        content=COMPRESS_RESEARCH_SYSTEM_PROMPT,
    )
    researcher_msgs.append(HumanMessage(content=COMPRESS_RESEARCH_SIMPLE_HUMAN_MESSAGE))
    while synthesize_attempts < config.compression_attempts:
        try:
            response = await compression_model.ainvoke(
                researcher_msgs,
            )
            return {
                "compressed_research": str(response.content),
                "raw_notes": [
                    "\n".join(
                        [str(m.content) for m in filter_messages(researcher_msgs, include_types=["tool", "ai"])],
                    ),
                ],
            }
        except Exception as e:
            # import traceback

            # print(e, traceback.format_exc())
            synthesize_attempts += 1
            # TODO(@viv): #123 Add token limit check
            # if is_token_limit_exceeded(e, configurable.research_model):
            #     researcher_msgs = remove_up_to_last_ai_message(researcher_msgs)
            #     print(f"Token limit exceeded while synthesizing: {e}. Pruning the messages to try again.")
            #     continue
            print(f"Error synthesizing research report: {e}")
    return {
        "compressed_research": "Error synthesizing research report: Maximum retries exceeded",
        "raw_notes": [
            "\n".join([str(m.content) for m in filter_messages(researcher_msgs, include_types=["tool", "ai"])]),
        ],
    }


research_builder = StateGraph(ResearchState, output_schema=ResearcherOutputState, config_schema=Configuration)
research_builder.add_node("research_agent", research_agent)
research_builder.add_node("compress_research", compress_research)
research_builder.add_node("research_tools", research_tools)

research_builder.add_edge(START, "research_agent")
research_builder.add_edge("compress_research", END)
researcher_graph = research_builder.compile(name="Research Agent")

research_brief = """
How can I develop an agentic AI-powered note-taking application leveraging LangGraph for my personal use, with features including image-to-text conversion, formatting, and integration with Notion, while showcasing my skills? I am seeking to:
1. Employ a robust Optical Character Recognition (OCR) solution for converting handwritten notes, potentially containing equations and block diagrams, into digital text.
   - Specific OCR tool preferences are currently open-ended; the research should explore both existing solutions and state-of-the-art alternatives.
2. Customize LangGraph's prebuilt UI for seamless interaction from a PC without any specific customization specifications, leaving room for creative design choices.
3. Develop a seamless interface with Notion, utilizing either existing APIs or custom integration methods.
   - The research should identify the best method for ensuring efficient data management and retrieval in Notion.
4. Implement a multi-agent system where one agent focuses on image-to-text conversion and another takes charge of text integration and formatting using markdown.
   - The interaction dynamics between agents require exploration to ensure efficiency and smooth operation.
5. Deliver an initial MVP capable of converting images to well-formatted text within 2 weeks.
6. Maintain an open architectural design, allowing flexibility in programming languages and frameworks, as no constraints have been specified.
7. Enhance the application to demonstrate my capabilities to potential employers, focusing on cutting-edge approach and effective solutions.
"""
