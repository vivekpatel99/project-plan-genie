"""Perplexity Provider definition."""

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_perplexity import ChatPerplexity

from .base_class import LLMProvider


class PerplexityProvider(LLMProvider):
    """
    Concrete LLM provider for Perplexity AI models.

    list of the available models - https://docs.perplexity.ai/models/model-cards.
    """

    def __init__(
        self,
        model_name: str = "sonar",
        temperature: float = 0.0,
        **kwargs,
    ) -> ChatPerplexity:
        """Initialize the OpenAIProvider."""
        self.model_name = model_name
        self.temperature = temperature
        self.kwargs = kwargs
        self.llm = self._create_llm_instance()

    def _create_llm_instance(self) -> BaseChatModel:
        """Concrete LLM provider for OpenAI models."""
        try:
            return ChatPerplexity(
                model=self.model_name,
                temperature=self.temperature,
                **self.kwargs,
            )
        except RuntimeError as e:
            msg = f"Failed to create ChatOpenAI instance: {e}"
            raise RuntimeError(msg)
