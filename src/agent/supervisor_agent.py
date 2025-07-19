"""Superviser Agent Subgraph."""

from typing import Literal

from langchain.chat_models import init_chat_model
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

from agent.states import ConductResearch, ResearchComplete, SupervisorState

try:
    from .configuration import Configuration
    # from prompts import PROJECT_RESEARCH_AGENT_PROMPT, SEARCH_INSTRUCTIONS
    # from providers.model_provider_factory import ModelProviderFactory
    # from states import PlanningState, ResearchState, SearchQuery

except ImportError:
    import rootutils

    rootutils.setup_root(__file__, indicator=".git", pythonpath=True)

    # from src.agent.prompts import PROJECT_RESEARCH_AGENT_PROMPT, SEARCH_INSTRUCTIONS

# Initialize a configurable model that we will use throughout the agent
configurable_model = init_chat_model(
    configurable_fields=("model", "max_tokens", "api_key"),
)
research_system_prompt = """You are a research assistant conducting deep research on the user's input topic. Use the tools and search methods provided to research the user's input topic. For context,
<Task>
Your job is to use tools and search methods to find information that can answer the question that a user asks.
You can use any of the tools provided to you to find resources that can help answer the research question. You can call these tools in series or in parallel, your research is conducted in a tool-calling loop.
</Task>

<Tool Calling Guidelines>
- Make sure you review all of the tools you have available to you, match the tools to the user's request, and select the tool that is most likely to be the best fit.
- In each iteration, select the BEST tool for the job, this may or may not be general websearch.
- When selecting the next tool to call, make sure that you are calling tools with arguments that you have not already tried.
- Tool calling is costly, so be sure to be very intentional about what you look up. Some of the tools may have implicit limitations. As you call tools, feel out what these limitations are, and adjust your tool calls accordingly.
- This could mean that you need to call a different tool, or that you should call "ResearchComplete", e.g. it's okay to recognize that a tool has limitations and cannot do what you need it to.
- Don't mention any tool limitations in your output, but adjust your tool calls accordingly.
- {mcp_prompt}
<Tool Calling Guidelines>

<Criteria for Finishing Research>
- In addition to tools for research, you will also be given a special "ResearchComplete" tool. This tool is used to indicate that you are done with your research.
- The user will give you a sense of how much effort you should put into the research. This does not translate ~directly~ to the number of tool calls you should make, but it does give you a sense of the depth of the research you should conduct.
- DO NOT call "ResearchComplete" unless you are satisfied with your research.
- One case where it's recommended to call this tool is if you see that your previous tool calls have stopped yielding useful information.
</Criteria for Finishing Research>

<Helpful Tips>
1. If you haven't conducted any searches yet, start with broad searches to get necessary context and background information. Once you have some background, you can start to narrow down your searches to get more specific information.
2. Different topics require different levels of research depth. If the question is broad, your research can be more shallow, and you may not need to iterate and call tools as many times.
3. If the question is detailed, you may need to be more stingy about the depth of your findings, and you may need to iterate and call tools more times to get a fully detailed answer.
</Helpful Tips>

<Critical Reminders>
- You MUST conduct research using web search or a different tool before you are allowed tocall "ResearchComplete"! You cannot call "ResearchComplete" without conducting research first!
- Do not repeat or summarize your research findings unless the user explicitly asks you to do so. Your main job is to call tools. You should call tools until you are satisfied with the research findings, and then call "ResearchComplete".
</Critical Reminders>
"""


async def supervisor(state: SupervisorState, config: RunnableConfig):
    Command[Literal["superviser_tool"]]
    config = Configuration.from_runnable_config(config)
    # research_model_config = {
    #     "model": config.research_model,
    #     "max_tokens": config.research_model_max_tokens,
    #     # "api_key": config.research_model_api_key,
    #     "tags": ["langsmith:nostream"],
    # }

    lead_research_tool = [ConductResearch, ResearchComplete]
    research_model = (
        configurable_model.with_structured_output(lead_research_tool)
        .with_retry(stop_after_attempt=config.max_structured_output_retries)
        .with_config(
            config,
        )
    )
    supervisor_message = state.get("supervisor_message", [])
    response = await research_model.ainvoke(
        supervisor_message,
    )
    return Command(
        goto="superviser_tool",
        update={
            "supervisor_message": [response],
            "research_iteration": state.get("research_iteration", 0) + 1,
        },
    )


# async def superviser_tool(state: SuperviserState, config: RunnableConfig) -> Command[Literal["superviser", "__end__"]]:
#     """ """
#     config = Configuration.from_runnable_config(config)
#     supervisor_messages = state.get("supervisor_message", [])
#     research_iteration = state.get("research_iteration", 0)
#     most_recent_message = supervisor_messages[-1]

#     # Exit Criteria
#     # 1. we havae exceeded our max guardrail research  iteration
#     # 2. No tool call were made by supervisor
#     # 3. The most recent message contain a ResearchComplete tool call and there is only one tool call in the message
#     exceeded_allowed_iterations = research_iteration >= config.max_research_iterations
#     no_tool_calls = not most_recent_message.tool_calls
#     research_complete_tool_call = any(
#         tool_call["name"] == "ResearchComplete" for tool_call in most_recent_message.tool_calls
#     )
#     if exceeded_allowed_iterations or no_tool_calls or research_complete_tool_call:
#         return Command(
#             goto=END,
#             update={
#                 "notes": get_notes_from_tool_calls(supervisor_messages),
#                 "research_brief": state.get("research_brief"),
#             },
#         )
# otherwise, continue with research
# try:
#     all_conduct_research = [tool_call for  tool_call in most_recent_message.tool_calls if tool_call["name"] == "ConductResearch"]
#     conduct_research_calls = all_conduct_research[:config.max_concurrent_research_units]
#     overflow_conduct_research_calls = all_conduct_research[config.max_concurrent_research_units:]
#     coros = [
#         research_subgraph.invoke({
#             "researcher_messages": [
#                 SystemMessage(content=researcher_syste_prompt),
#                 HumanMessage(content=tool_call["args"]["research_topic"]),

#             ],
#             "research_topic":tool_call["args"]["research_topic"],
#         }, config) for tool_call in conduct_research_calls
#     ]
