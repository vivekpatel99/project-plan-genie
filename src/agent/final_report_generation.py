from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

try:
    from .configuration import Configuration
    from .prompts import SYSTEM_PROMPT_PROJECT_PLAN_STRUCTURE
    from .states import AgentState, StatesKeys
    from .utils import get_today_str
except ImportError:
    import rootutils

    rootutils.setup_root(__file__, indicator=".git", pythonpath=True)
    from src.agent.prompts import SYSTEM_PROMPT_PROJECT_PLAN_STRUCTURE
    from src.agent.states import AgentState


async def final_report_generation(state: AgentState, config: RunnableConfig) -> dict[str, str]:
    """
    Generate final report from the  research notes and findings.

    Takes in a state and config and generates a final report by calling
    the report generator model. If the model fails to generate a report, it retries
    up to `max_retries` times before giving up and returning an error message.
    """
    # Initialize a configurable model that we will use throughout the agent
    report_generator_model = init_chat_model(
        configurable_fields=("model", "max_tokens", "api_key"),
    )

    notes = state.get(StatesKeys.NOTES.value, [])
    config = Configuration.from_runnable_config(config)
    report_generator_config = {
        "model": config.final_report_generation_model,
        "max_tokens": config.final_report_generation_model_max_tokens,
    }
    findings = "\n".join(notes)
    max_retries = 3
    current_retry = 0

    while current_retry <= max_retries:
        final_report_prompt = SYSTEM_PROMPT_PROJECT_PLAN_STRUCTURE.format(
            research_brief=state[StatesKeys.RESEARCH_BRIEF.value],
            findings=findings,
            date=get_today_str(),
        )
        try:
            final_report = await report_generator_model.with_config(report_generator_config).ainvoke(
                [HumanMessage(content=final_report_prompt)],
            )
            return {
                StatesKeys.FINAL_REPORT.value: final_report.content,
                StatesKeys.MSGS.value: [HumanMessage(content=final_report.content)],
            }
        except Exception as e:
            return {
                StatesKeys.FINAL_REPORT.value: f"Error generating final report: {e}",
            }
    return {
        StatesKeys.FINAL_REPORT.value: "Error generating final report: Maximum retries exceeded",
    }
