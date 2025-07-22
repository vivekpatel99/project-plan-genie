from langchain_core.runnables import RunnableConfig

# try:
#     from .configuration import Configuration
#     from .states import AgentInputState, AgentState, ClarifyWithUser, ResearchQuestion, StatesKeys
#     from .utils import get_today_str
# except ImportError:
#     import rootutils
#     rootutils.setup_root(__file__, indicator=".git", pythonpath=True)
from src.agent.states import AgentState


async def final_report_generation(state: AgentState, config: RunnableConfig):
    pass
