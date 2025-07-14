"""LangGraph single-node graph template.

Returns a predefined response. Replace logic and configuration as needed.
"""

from langchain_core.runnables import RunnableConfig

from agent.states import PlanningState


async def call_model(state: PlanningState, config: RunnableConfig) -> dict[str, Any]:
    """Process input and returns output.

    Can use runtime configuration to alter behavior.
    """
    configuration = config["configurable"]
    return {
        "changeme": "output from call_model. "
        f"Configured with {configuration.get('my_configurable_param')}"
    }


# # Define the graph
# graph = (
#     StateGraph(State, config_schema=Configuration)
#     .add_node(call_model)
#     .add_edge("__start__", "call_model")
#     .compile(name="New Graph")
# )
