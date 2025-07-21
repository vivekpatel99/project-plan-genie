from langchain_core.runnables import RunnableConfig

try:
    from .configuration import Configuration
    from .states import AgentInputState, AgentState, ClarifyWithUser, ResearchQuestion, StatesKeys
    from .utils import get_today_str
except ImportError:
    import rootutils

    rootutils.setup_root(__file__, indicator=".git", pythonpath=True)
    from src.agent.configuration import Configuration
    from src.agent.prompts import CLARIFY_WITH_USER_INSTRUCTIONS, TRANSFORM_MESSAGES_INTO_RESEARCH_TOPIC_PROMPT
    from src.agent.states import AgentInputState, AgentState, ClarifyWithUser, ResearchQuestion, StatesKeys
    from src.agent.utils import get_today_str


async def final_report_generation(state: AgentState, config: RunnableConfig):
    pass
