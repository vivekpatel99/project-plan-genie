"""Tests for the supervisor agent subgraph."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.messages.tool import ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END
from langgraph.types import Command

from src.agent.states import StatesKeys, SupervisorState
from src.agent.supervisor_agent import supervisor, supervisor_tool


@pytest.mark.anyio
@patch("src.agent.supervisor_agent.supervisor_model", new_callable=MagicMock)
async def test_supervisor_initial_run(mock_model: MagicMock) -> None:
    """Test the supervisor function on an initial run to ensure it calls the model and returns the correct command."""
    # Arrange
    initial_messages = [HumanMessage(content="test research brief")]
    state = SupervisorState(supervisor_messages=initial_messages, research_iterations=0)
    config = RunnableConfig(configurable={"research_model": "test_model", "max_structured_output_retries": 1})
    mock_response = AIMessage(content="mock response from model")

    # Mock the chain of calls
    mock_chain = AsyncMock()
    mock_chain.ainvoke.return_value = mock_response
    mock_model.bind_tools.return_value.with_retry.return_value.with_config.return_value = mock_chain

    # Act
    result = await supervisor(state, config)

    # Assert
    assert isinstance(result, Command)
    assert result.goto == "supervisor_tool"
    update = result.update
    assert update[StatesKeys.SUPERVISOR_MSGS.value] == [mock_response]
    assert update[StatesKeys.RESEARCH_ITERATIONS.value] == 1
    mock_chain.ainvoke.assert_called_once_with(initial_messages)


@pytest.mark.anyio
@patch("src.agent.supervisor_agent.supervisor_model", new_callable=MagicMock)
async def test_supervisor_subsequent_run(mock_model: MagicMock) -> None:
    """Test the supervisor function on a subsequent run with existing research iterations."""
    # Arrange
    state = SupervisorState(supervisor_messages=[], research_iterations=2)
    config = RunnableConfig(configurable={"research_model": "test_model", "max_structured_output_retries": 1})
    mock_response = AIMessage(content="another mock response")

    mock_chain = AsyncMock()
    mock_chain.ainvoke.return_value = mock_response
    mock_model.bind_tools.return_value.with_retry.return_value.with_config.return_value = mock_chain

    # Act
    result = await supervisor(state, config)

    # Assert
    assert isinstance(result, Command)
    assert result.goto == "supervisor_tool"
    update = result.update
    assert update[StatesKeys.SUPERVISOR_MSGS.value] == [mock_response]
    assert update[StatesKeys.RESEARCH_ITERATIONS.value] == 3  # noqa: PLR2004
    mock_chain.ainvoke.assert_called_once_with([])


@pytest.mark.anyio
async def test_supervisor_tool_max_iterations_exceeded() -> None:
    """Test supervisor_tool exits when max research iterations are exceeded."""
    # Arrange
    state = SupervisorState(
        supervisor_messages=[AIMessage(content="some message")],
        research_iterations=3,
        research_brief="test brief",
    )
    config = RunnableConfig(configurable={"max_research_iterations": 3})

    # Act
    result = await supervisor_tool(state, config)

    # Assert
    assert isinstance(result, Command)
    assert result.goto == END
    update = result.update
    assert update[StatesKeys.NOTES.value] == []  # No tool messages in supervisor_messages
    assert update[StatesKeys.RESEARCH_BRIEF.value] == "test brief"


@pytest.mark.anyio
async def test_supervisor_tool_no_tool_calls() -> None:
    """Test supervisor_tool exits when there are no tool calls from the supervisor."""
    # Arrange
    state = SupervisorState(
        supervisor_messages=[AIMessage(content="some message")],  # No tool_calls attribute
        research_iterations=1,
        research_brief="test brief",
    )
    config = RunnableConfig(configurable={"max_research_iterations": 3})

    # Act
    result = await supervisor_tool(state, config)

    # Assert
    assert isinstance(result, Command)
    assert result.goto == END
    update = result.update
    assert update[StatesKeys.NOTES.value] == []
    assert update[StatesKeys.RESEARCH_BRIEF.value] == "test brief"


@pytest.mark.anyio
async def test_supervisor_tool_research_complete() -> None:
    """Test supervisor_tool exits when ResearchComplete tool is called."""
    # Arrange
    state = SupervisorState(
        supervisor_messages=[
            AIMessage(
                content="Research is done.",
                tool_calls=[{"name": "ResearchComplete", "args": {}, "id": "1"}],
            ),
        ],
        research_iterations=1,
        research_brief="test brief",
    )
    config = RunnableConfig(configurable={"max_research_iterations": 3})

    # Act
    result = await supervisor_tool(state, config)

    # Assert
    assert isinstance(result, Command)
    assert result.goto == END
    update = result.update
    assert update[StatesKeys.NOTES.value] == []
    assert update[StatesKeys.RESEARCH_BRIEF.value] == "test brief"


@pytest.mark.anyio
@patch("src.agent.supervisor_agent.researcher_subgraph", new_callable=AsyncMock)
async def test_supervisor_tool_conduct_research(mock_researcher_subgraph: AsyncMock) -> None:
    """Test supervisor_tool continues research when ConductResearch is called."""
    # Arrange
    tool_call_id = "call_123"
    state = SupervisorState(
        supervisor_messages=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "ConductResearch",
                        "args": {"research_topic": "topic 1"},
                        "id": tool_call_id,
                    },
                ],
            ),
        ],
        research_iterations=1,
    )
    config = RunnableConfig(configurable={"max_research_iterations": 3, "max_concurrent_research_units": 3})
    mock_researcher_subgraph.ainvoke.return_value = {
        StatesKeys.COMPRESSED_RESEARCH.value: "compressed result",
        StatesKeys.RAW_NOTES.value: ["raw note 1"],
    }

    # Act
    result = await supervisor_tool(state, config)

    # Assert
    assert isinstance(result, Command)
    assert result.goto == "supervisor"
    mock_researcher_subgraph.ainvoke.assert_called_once()

    update = result.update
    assert StatesKeys.SUPERVISOR_MSGS.value in update
    supervisor_msgs = update[StatesKeys.SUPERVISOR_MSGS.value]
    assert len(supervisor_msgs) == 1
    assert isinstance(supervisor_msgs[0], ToolMessage)
    assert supervisor_msgs[0].content == "compressed result"
    assert supervisor_msgs[0].tool_call_id == tool_call_id

    assert StatesKeys.RAW_NOTES.value in update
    assert update[StatesKeys.RAW_NOTES.value] == ["raw note 1"]


@pytest.mark.anyio
@patch("src.agent.supervisor_agent.researcher_subgraph", new_callable=AsyncMock)
async def test_supervisor_tool_exception_during_research(mock_researcher_subgraph: AsyncMock) -> None:
    """Test supervisor_tool exits gracefully when an exception occurs during research."""
    # Arrange
    state = SupervisorState(
        supervisor_messages=[
            AIMessage(
                content="",
                tool_calls=[{"name": "ConductResearch", "args": {"research_topic": "topic 1"}, "id": "1"}],
            ),
        ],
        research_iterations=1,
        research_brief="test brief",
    )
    config = RunnableConfig(configurable={"max_research_iterations": 3})
    mock_researcher_subgraph.ainvoke.side_effect = Exception("Something went wrong")

    # Act
    result = await supervisor_tool(state, config)

    # Assert
    assert isinstance(result, Command)
    assert result.goto == END
    update = result.update
    assert update[StatesKeys.NOTES.value] == []
    assert update[StatesKeys.RESEARCH_BRIEF.value] == "test brief"
