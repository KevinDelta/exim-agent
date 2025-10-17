"""Anthropic (Claude) LLM provider implementation."""

from langchain_anthropic import ChatAnthropic
from loguru import logger

from acc_llamaindex.config import config
from .base_provider import BaseLLMProvider


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude provider for LLMs."""
    
    def validate_config(self) -> bool:
        """Validate Anthropic configuration."""
        if not config.anthropic_api_key:
            raise ValueError(
                "Anthropic API key not configured. "
                "Set ANTHROPIC_API_KEY in your .env file."
            )
        return True
    
    def get_model_name(self) -> str:
        """Get the Anthropic model name."""
        return config.anthropic_model
    
    def initialize_llm(self) -> ChatAnthropic:
        """Initialize ChatAnthropic LLM."""
        self.validate_config()
        
        try:
            logger.info(f"Initializing ChatAnthropic with model: {config.anthropic_model}")
            
            llm = ChatAnthropic(
                model=config.anthropic_model,
                anthropic_api_key=config.anthropic_api_key,
                temperature=config.llm_temperature,
                max_tokens=config.max_tokens if config.max_tokens else 4096,
                streaming=config.streaming,
            )
            
            logger.info("ChatAnthropic initialized successfully")
            return llm
            
        except Exception as e:
            logger.error(f"Failed to initialize ChatAnthropic: {e}")
            raise
    
    @staticmethod
    def get_available_models() -> list[str]:
        """Get list of available Anthropic models."""
        return [
            "claude-sonnet-4-5-20250929",
            "claude-haiku-4-5-20251001",
            "claude-opus-4-20250514",
        ]
    
    @staticmethod
    def get_model_info(model: str) -> dict:
        """Get information about a specific model."""
        model_info = {
            "claude-sonnet-4-5-20250929": {
                "context_window": 200000,
                "max_output": 8192,
                "description": "Most intelligent model, best for complex tasks",
            },
            "claude-haiku-4-5-20251001": {
                "context_window": 200000,
                "max_output": 8192,
                "description": "Fast and efficient, best for simple tasks",
            },
            "claude-opus-4-20250514": {
                "context_window": 200000,
                "max_output": 4096,
                "description": "Current generation, high capability",
            },
        }
        return model_info.get(model, {})
