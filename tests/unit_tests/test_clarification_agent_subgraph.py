"""Tests for the clarification agent subgraph."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END
from langgraph.types import Command

from src.agent.clarification_agent_subgraph import (
    clarify_with_user,
    write_research_brief,
)
from src.agent.prompts import LEAD_RESEARCHER_PROMPT
from src.agent.states import AgentState, ClarifyWithUser, ResearchQuestion, StatesKeys
from src.agent.utils import get_today_str


@pytest.mark.anyio
async def test_clarify_with_user_no_clarification_allowed() -> None:
    """Test clarify_with_user when clarification is not allowed in the config."""
    state = AgentState(messages=[HumanMessage(content="test idea")])
    config = RunnableConfig(
        configurable={"allow_clarification": False},
    )

    result = await clarify_with_user(state, config)

    assert isinstance(result, Command)
    assert result.goto == "write_research_brief"
    assert result.update is None


@pytest.mark.anyio
@patch("src.agent.clarification_agent_subgraph.clarification_model", new_callable=MagicMock)
async def test_clarify_with_user_needs_clarification(mock_model) -> None:
    """Test clarify_with_user when the model determines clarification is needed."""
    # Arrange
    state = AgentState(messages=[HumanMessage(content="test idea")])
    config = RunnableConfig(
        configurable={"allow_clarification": True, "research_model": "test_model"},
    )
    mock_response = ClarifyWithUser(
        need_clarification=True,
        question="What is your timeline?",
        verification="",
    )
    # Mock the chain of calls
    mock_chain = AsyncMock()
    mock_chain.ainvoke.return_value = mock_response
    mock_model.with_structured_output.return_value.with_retry.return_value.with_config.return_value = mock_chain

    # Act
    result = await clarify_with_user(state, config)

    # Assert
    assert isinstance(result, Command)
    assert result.goto == END
    assert StatesKeys.MSGS.value in result.update
    messages = result.update[StatesKeys.MSGS.value]
    assert len(messages) == 2  # noqa: PLR2004
    assert isinstance(messages[0], HumanMessage)
    assert isinstance(messages[1], AIMessage)
    assert messages[1].content == "What is your timeline?"
    mock_chain.ainvoke.assert_called_once()


@pytest.mark.anyio
@patch("src.agent.clarification_agent_subgraph.clarification_model", new_callable=MagicMock)
async def test_clarify_with_user_no_clarification_needed(mock_model) -> None:
    """Test clarify_with_user when the model determines no clarification is needed."""
    # Arrange
    state = AgentState(messages=[HumanMessage(content="test idea")])
    config = RunnableConfig(
        configurable={"allow_clarification": True, "research_model": "test_model"},
    )
    mock_response = ClarifyWithUser(
        need_clarification=False,
        question="",
        verification="Thanks, I have enough information to proceed.",
    )
    # Mock the chain of calls
    mock_chain = AsyncMock()
    mock_chain.ainvoke.return_value = mock_response
    mock_model.with_structured_output.return_value.with_retry.return_value.with_config.return_value = mock_chain

    # Act
    result = await clarify_with_user(state, config)

    # Assert
    assert isinstance(result, Command)
    assert result.goto == "write_research_brief"
    assert StatesKeys.MSGS.value in result.update
    messages = result.update[StatesKeys.MSGS.value]
    assert len(messages) == 2  # noqa: PLR2004
    assert isinstance(messages[0], HumanMessage)
    assert isinstance(messages[1], AIMessage)
    assert messages[1].content == "Thanks, I have enough information to proceed."
    mock_chain.ainvoke.assert_called_once()


@pytest.mark.anyio
@patch("src.agent.clarification_agent_subgraph.clarification_model", new_callable=MagicMock)
async def test_write_research_brief(mock_model) -> None:
    """Test write_research_brief function."""
    # Arrange
    initial_messages = [HumanMessage(content="test idea")]
    state = AgentState(messages=initial_messages)
    config = RunnableConfig(configurable={"research_model": "test_model", "max_concurrent_research_units": 3})
    mock_response = ResearchQuestion(research_brief="This is the research brief.")

    # Mock the chain of calls
    mock_chain = AsyncMock()
    mock_chain.ainvoke.return_value = mock_response
    mock_model.with_structured_output.return_value.with_retry.return_value.with_config.return_value = mock_chain

    # Act
    result = await write_research_brief(state, config)

    # Assert
    assert isinstance(result, Command)
    assert result.goto == "supervisor_subgraph"

    update = result.update
    assert update[StatesKeys.RESEARCH_BRIEF.value] == "This is the research brief."

    supervisor_messages = update[StatesKeys.SUPERVISOR_MSGS.value]
    assert len(supervisor_messages) == 2  # noqa: PLR2004
    assert isinstance(supervisor_messages[0], SystemMessage)
    expected_system_message = LEAD_RESEARCHER_PROMPT.format(
        date=get_today_str(),
        max_concurrent_research_units=3,
    )
    assert supervisor_messages[0].content == expected_system_message
    assert isinstance(supervisor_messages[1], HumanMessage)
    assert supervisor_messages[1].content == "This is the research brief."

    mock_chain.ainvoke.assert_called_once()
