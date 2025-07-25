"""Tests for the supervisor agent subgraph."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

from src.agent.states import StatesKeys, SupervisorState
from src.agent.supervisor_agent import supervisor


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
