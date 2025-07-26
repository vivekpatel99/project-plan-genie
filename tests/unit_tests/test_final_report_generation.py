"""Tests for the final_report_generation function."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig

from src.agent.final_report_generation import final_report_generation
from src.agent.states import AgentState, StatesKeys


@pytest.fixture
def mock_state() -> AgentState:
    """Provides a mock AgentState for testing."""
    return AgentState(notes=["finding 1", "finding 2"], research_brief="Test research brief", messages=[])


@pytest.fixture
def mock_config() -> RunnableConfig:
    """Provides a mock RunnableConfig for testing."""
    return RunnableConfig(
        configurable={
            "final_report_generation_model": "test-model",
            "final_report_generation_model_max_tokens": 1000,
        },
    )


@pytest.mark.anyio
@patch("src.agent.final_report_generation.init_chat_model")
@patch("src.agent.final_report_generation.get_today_str", return_value="2023-10-27")
async def test_final_report_generation_success_first_try(
    mock_get_today: MagicMock,
    mock_init_chat_model: MagicMock,
    mock_state: AgentState,
    mock_config: RunnableConfig,
) -> None:
    """Test successful final report generation on the first attempt."""
    # Arrange
    mock_report_model = MagicMock()
    mock_ainvoke = AsyncMock(return_value=AIMessage(content="This is the final report."))
    mock_report_model.with_config.return_value.ainvoke = mock_ainvoke
    mock_init_chat_model.return_value = mock_report_model

    # Act
    result = await final_report_generation(mock_state, mock_config)

    # Assert
    assert StatesKeys.FINAL_REPORT.value in result
    assert result[StatesKeys.FINAL_REPORT.value] == "This is the final report."
    assert StatesKeys.MSGS.value in result
    assert result[StatesKeys.MSGS.value] == [HumanMessage(content="This is the final report.")]
    mock_ainvoke.assert_called_once()


@pytest.mark.anyio
@patch("src.agent.final_report_generation.asyncio.sleep", new_callable=AsyncMock)
@patch("src.agent.final_report_generation.init_chat_model")
@patch("src.agent.final_report_generation.get_today_str", return_value="2023-10-27")
async def test_final_report_generation_success_on_retry(
    mock_get_today: MagicMock,
    mock_init_chat_model: MagicMock,
    mock_sleep: AsyncMock,
    mock_state: AgentState,
    mock_config: RunnableConfig,
) -> None:
    """Test successful final report generation after one failed attempt."""
    # Arrange
    mock_report_model = MagicMock()
    mock_ainvoke = AsyncMock(
        side_effect=[
            Exception("First attempt failed"),
            AIMessage(content="This is the final report."),
        ],
    )
    mock_report_model.with_config.return_value.ainvoke = mock_ainvoke
    mock_init_chat_model.return_value = mock_report_model

    # Act
    result = await final_report_generation(mock_state, mock_config)

    # Assert
    assert StatesKeys.FINAL_REPORT.value in result
    assert result[StatesKeys.FINAL_REPORT.value] == "This is the final report."
    assert StatesKeys.MSGS.value in result
    assert result[StatesKeys.MSGS.value] == [HumanMessage(content="This is the final report.")]
    assert mock_ainvoke.call_count == 2
    mock_sleep.assert_called_once_with(0.1)


@pytest.mark.anyio
@patch("src.agent.final_report_generation.asyncio.sleep", new_callable=AsyncMock)
@patch("src.agent.final_report_generation.init_chat_model")
@patch("src.agent.final_report_generation.get_today_str", return_value="2023-10-27")
async def test_final_report_generation_max_retries_exceeded(
    mock_get_today: MagicMock,
    mock_init_chat_model: MagicMock,
    mock_sleep: AsyncMock,
    mock_state: AgentState,
    mock_config: RunnableConfig,
) -> None:
    """Test final report generation failure after exceeding max retries."""
    # Arrange
    mock_report_model = MagicMock()
    test_exception = Exception("Model always fails")
    mock_ainvoke = AsyncMock(side_effect=test_exception)
    mock_report_model.with_config.return_value.ainvoke = mock_ainvoke
    mock_init_chat_model.return_value = mock_report_model

    # Act
    result = await final_report_generation(mock_state, mock_config)

    # Assert
    assert StatesKeys.FINAL_REPORT.value in result
    assert "Error generating final report: Maximum retries exceeded" in result[StatesKeys.FINAL_REPORT.value]
    assert "Last error: Model always fails" in result[StatesKeys.FINAL_REPORT.value]
    assert StatesKeys.MSGS.value not in result
    assert mock_ainvoke.call_count == 4  # Initial call + 3 retries
    assert mock_sleep.call_count == 3  # Sleep between retries
