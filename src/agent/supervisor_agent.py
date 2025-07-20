"""Superviser Agent Subgraph."""

import asyncio
from typing import Literal

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

try:
    from .configuration import Configuration
    from .states import ConductResearch, ResearchComplete, SupervisorState
    from .utils import get_notes_from_tool_calls, is_token_limit_exceeded
except ImportError:
    import rootutils

    rootutils.setup_root(__file__, indicator=".git", pythonpath=True)
    from src.agent.configuration import Configuration
    from src.agent.researcher_agent import researcher_subgraph
    from src.agent.states import ConductResearch, ResearchComplete, SupervisorState
    from src.agent.utils import get_notes_from_tool_calls, is_token_limit_exceeded
    # from src.agent.prompts import PROJECT_RESEARCH_AGENT_PROMPT, SEARCH_INSTRUCTIONS

# Initialize a configurable model that we will use throughout the agent
configurable_model = init_chat_model(
    configurable_fields=("model", "max_tokens", "api_key"),
)
RESEARCH_SYSTEM_PROMPT = """You are a research assistant conducting deep research on the user's input topic. Use the tools and search methods provided to research the user's input topic. For context,
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
- You MUST conduct research using web search or a different tool before you are allowed to call "ResearchComplete"! You cannot call "ResearchComplete" without conducting research first!
- Do not repeat or summarize your research findings unless the user explicitly asks you to do so. Your main job is to call tools. You should call tools until you are satisfied with the research findings, and then call "ResearchComplete".
</Critical Reminders>
"""

LEAD_RESEARCHER_PROMPT = """You are a research supervisor. Your job is to conduct research by calling the "ConductResearch" tool. For context, today's date is {date}.

<Task>
Your focus is to call the "ConductResearch" tool to conduct research against the overall research question passed in by the user.
When you are completely satisfied with the research findings returned from the tool calls, then you should call the "ResearchComplete" tool to indicate that you are done with your research.
</Task>

<Instructions>
1. When you start, you will be provided a research question from a user.
2. You should immediately call the "ConductResearch" tool to conduct research for the research question. You can call the tool up to {max_concurrent_research_units} times in a single iteration.
3. Each ConductResearch tool call will spawn a research agent dedicated to the specific topic that you pass in. You will get back a comprehensive report of research findings on that topic.
4. Reason carefully about whether all of the returned research findings together are comprehensive enough for a detailed report to answer the overall research question.
5. If there are important and specific gaps in the research findings, you can then call the "ConductResearch" tool again to conduct research on the specific gap.
6. Iteratively call the "ConductResearch" tool until you are satisfied with the research findings, then call the "ResearchComplete" tool to indicate that you are done with your research.
7. Don't call "ConductResearch" to synthesize any information you've gathered. Another agent will do that after you call "ResearchComplete". You should only call "ConductResearch" to research net new topics and get net new information.
</Instructions>


<Important Guidelines>
**The goal of conducting research is to get information, not to write the final report. Don't worry about formatting!**
- A separate agent will be used to write the final report.
- Do not grade or worry about the format of the information that comes back from the "ConductResearch" tool. It's expected to be raw and messy. A separate agent will be used to synthesize the information once you have completed your research.
- Only worry about if you have enough information, not about the format of the information that comes back from the "ConductResearch" tool.
- Do not call the "ConductResearch" tool to synthesize information you have already gathered.

**Parallel research saves the user time, but reason carefully about when you should use it**
- Calling the "ConductResearch" tool multiple times in parallel can save the user time.
- You should only call the "ConductResearch" tool multiple times in parallel if the different topics that you are researching can be researched independently in parallel with respect to the user's overall question.
- This can be particularly helpful if the user is asking for a comparison of X and Y, if the user is asking for a list of entities that each can be researched independently, or if the user is asking for multiple perspectives on a topic.
- Each research agent needs to be provided all of the context that is necessary to focus on a sub-topic.
- Do not call the "ConductResearch" tool more than {max_concurrent_research_units} times at once. This limit is enforced by the user. It is perfectly fine, and expected, that you return less than this number of tool calls.
- If you are not confident in how you can parallelize research, you can call the "ConductResearch" tool a single time on a more general topic in order to gather more background information, so you have more context later to reason about if it's necessary to parallelize research.
- Each parallel "ConductResearch" linearly scales cost. The benefit of parallel research is that it can save the user time, but carefully think about whether the additional cost is worth the benefit.
- For example, if you could search three clear topics in parallel, or break them each into two more subtopics to do six total in parallel, you should think about whether splitting into smaller subtopics is worth the cost. The researchers are quite comprehensive, so it's possible that you could get the same information with less cost by only calling the "ConductResearch" tool three times in this case.
- Also consider where there might be dependencies that cannot be parallelized. For example, if asked for details about some entities, you first need to find the entities before you can research them in detail in parallel.

**Different questions require different levels of research depth**
- If a user is asking a broader question, your research can be more shallow, and you may not need to iterate and call the "ConductResearch" tool as many times.
- If a user uses terms like "detailed" or "comprehensive" in their question, you may need to be more stingy about the depth of your findings, and you may need to iterate and call the "ConductResearch" tool more times to get a fully detailed answer.

**Research is expensive**
- Research is expensive, both from a monetary and time perspective.
- As you look at your history of tool calls, as you have conducted more and more research, the theoretical "threshold" for additional research should be higher.
- In other words, as the amount of research conducted grows, be more stingy about making even more follow-up "ConductResearch" tool calls, and more willing to call "ResearchComplete" if you are satisfied with the research findings.
- You should only ask for topics that are ABSOLUTELY necessary to research for a comprehensive answer.
- Before you ask about a topic, be sure that it is substantially different from any topics that you have already researched. It needs to be substantially different, not just rephrased or slightly different. The researchers are quite comprehensive, so they will not miss anything.
- When you call the "ConductResearch" tool, make sure to explicitly state how much effort you want the sub-agent to put into the research. For background research, you may want it to be a shallow or small effort. For critical topics, you may want it to be a deep or large effort. Make the effort level explicit to the researcher.
</Important Guidelines>


<Crucial Reminders>
- If you are satisfied with the current state of research, call the "ResearchComplete" tool to indicate that you are done with your research.
- Calling ConductResearch in parallel will save the user time, but you should only do this if you are confident that the different topics that you are researching are independent and can be researched in parallel with respect to the user's overall question.
- You should ONLY ask for topics that you need to help you answer the overall research question. Reason about this carefully.
- When calling the "ConductResearch" tool, provide all context that is necessary for the researcher to understand what you want them to research. The independent researchers will not get any context besides what you write to the tool each time, so make sure to provide all context to it.
- This means that you should NOT reference prior tool call results or the research brief when calling the "ConductResearch" tool. Each input to the "ConductResearch" tool should be a standalone, fully explained topic.
- Do NOT use acronyms or abbreviations in your research questions, be very clear and specific.
</Crucial Reminders>

With all of the above in mind, call the ConductResearch tool to conduct research on specific topics, OR call the "ResearchComplete" tool to indicate that you are done with your research.
"""


async def supervisor(state: SupervisorState, config: RunnableConfig):
    Command[Literal["supervisor_tool"]]
    config = Configuration.from_runnable_config(config)
    research_model_config = {
        "model": config.research_model,
        "max_tokens": config.research_model_max_tokens,
        # "api_key": config.research_model_api_key,
        "tags": ["langsmith:nostream"],
    }

    lead_research_tool = [ConductResearch, ResearchComplete]
    research_model = (
        configurable_model.with_structured_output(lead_research_tool)
        .with_retry(stop_after_attempt=config.max_structured_output_retries)
        .with_config(
            research_model_config,
        )
    )
    supervisor_message = state.get("supervisor_messages", [])
    response = await research_model.ainvoke(
        supervisor_message,
    )
    return Command(
        goto="supervisor_tool",
        update={
            "supervisor_messages": [response],
            "research_iterations": state.get("research_iterations", 0) + 1,
        },
    )


async def supervisor_tool(state: SupervisorState, config: RunnableConfig) -> Command[Literal["supervisor", "__end__"]]:
    """Supervisor tool to conduct research on specific topics, or to indicate that you are done with your research."""
    config = Configuration.from_runnable_config(config)
    supervisor_messages = state.get("supervisor_messages", [])
    research_iterations = state.get("research_iterations", 0)
    most_recent_message = supervisor_messages[-1]

    # Exit Criteria
    # 1. we have exceeded our max guardrail research  iteration
    # 2. No tool call were made by supervisor
    # 3. The most recent message contain a ResearchComplete tool call and there is only one tool call in the message
    exceeded_allowed_iterations = research_iterations >= config.max_research_iterations
    no_tool_calls = not most_recent_message.tool_calls
    research_complete_tool_call = any(
        tool_call["name"] == "ResearchComplete" for tool_call in most_recent_message.tool_calls
    )
    if exceeded_allowed_iterations or no_tool_calls or research_complete_tool_call:
        return Command(
            goto=END,
            update={
                "notes": get_notes_from_tool_calls(supervisor_messages),
                "research_brief": state.get("research_brief"),
            },
        )
    # otherwise, continue with research
    try:
        all_conduct_research = [
            tool_call for tool_call in most_recent_message.tool_calls if tool_call["name"] == "ConductResearch"
        ]
        # Limit total concurrent research units/calls
        conduct_research_calls = all_conduct_research[: config.max_concurrent_research_units]
        overflow_conduct_research_calls = all_conduct_research[config.max_concurrent_research_units :]

        coros = [
            researcher_subgraph.invoke(
                {
                    "researcher_messages": [
                        SystemMessage(content=RESEARCH_SYSTEM_PROMPT),
                        HumanMessage(content=tool_call["args"]["research_topic"]),
                    ],
                    "research_topic": tool_call["args"]["research_topic"],
                },
                config,
            )
            for tool_call in conduct_research_calls
        ]
        tool_results = await asyncio.gather(*coros)
        tool_messages = [
            ToolMessage(
                content=observation.get(
                    "compressed_research",
                    "Error synthesizing research report: Maximum retries exceeded",
                ),
                name=tool_call["name"],
                tool_call_id=tool_call["id"],
            )
            for observation, tool_call in zip(tool_results, conduct_research_calls, strict=False)
        ]
        # Handle any tool calls made > max_concurrent_research_units
        for overflow_conduct_research_call in overflow_conduct_research_calls:
            tool_messages.append(
                ToolMessage(
                    content=f"Error: Did not run this research as you have already exceeded the maximum number of concurrent research units. Please try again with {config.max_concurrent_research_units} or fewer research units.",
                    name="ConductResearch",
                    tool_call_id=overflow_conduct_research_call["id"],
                ),
            )
        raw_notes_concat = "\n".join(["\n".join(observation.get("raw_notes", [])) for observation in tool_results])
        return Command(
            goto="supervisor",
            update={"supervisor_messages": tool_messages, "raw_notes": [raw_notes_concat]},
        )
    except Exception as e:
        if is_token_limit_exceeded(e, config.research_model):
            print(f"Token limit exceeded while reflecting: {e}")
        else:
            print(f"Other error in reflection phase: {e}")
        return Command(
            goto=END,
            update={
                "notes": get_notes_from_tool_calls(supervisor_messages),
                "research_brief": state.get("research_brief", ""),
            },
        )


supervisor_builder = StateGraph(SupervisorState, config_schema=Configuration)
supervisor_builder.add_node("supervisor", supervisor)
supervisor_builder.add_node("supervisor_tool", supervisor_tool)
supervisor_builder.add_edge(START, "supervisor")
supervisor_builder.add_edge("supervisor_tool", END)
supervisor_graph = supervisor_builder.compile(name="Supervisor")
