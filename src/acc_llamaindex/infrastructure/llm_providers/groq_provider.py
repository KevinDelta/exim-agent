"""Groq LLM provider implementation."""

from langchain_groq import ChatGroq
from loguru import logger

from acc_llamaindex.config import config
from .base_provider import BaseLLMProvider


class GroqProvider(BaseLLMProvider):
    """Groq provider for fast LLM inference."""
    
    def validate_config(self) -> bool:
        """Validate Groq configuration."""
        if not config.groq_api_key:
            raise ValueError(
                "Groq API key not configured. "
                "Set GROQ_API_KEY in your .env file."
            )
        return True
    
    def get_model_name(self) -> str:
        """Get the Groq model name."""
        return config.groq_model
    
    def initialize_llm(self) -> ChatGroq:
        """Initialize ChatGroq LLM."""
        self.validate_config()
        
        try:
            logger.info(f"Initializing ChatGroq with model: {config.groq_model}")
            
            llm = ChatGroq(
                model=config.groq_model,
                groq_api_key=config.groq_api_key,
                temperature=config.llm_temperature,
                max_tokens=config.max_tokens,
                streaming=config.streaming,
            )
            
            logger.info("ChatGroq initialized successfully")
            return llm
            
        except Exception as e:
            logger.error(f"Failed to initialize ChatGroq: {e}")
            raise
    
    @staticmethod
    def get_available_models() -> list[str]:
        """Get list of available Groq models."""
        return [
            "openai/gpt-oss-120b",
            "qwen/qwen3-32b",
            "moonshotai/kimi-k2-instruct-0905",
        ]
    
    @staticmethod
    def get_model_info(model: str) -> dict:
        """Get information about a specific model."""
        model_info = {
            "openai/gpt-oss-120b": {
                "context_window": 128000,
                "tokens_per_second": 800,
                "description": "OpenAI GPT-120B, best for general use",
            },
            "qwen/qwen3-32b": {
                "context_window": 128000,
                "tokens_per_second": 2000,
                "description": "Qwen Qwen3-32B, best for simple tasks",
            },
            "moonshotai/kimi-k2-instruct-0905": {
                "context_window": 32768,
                "tokens_per_second": 600,
                "description": "Moonshot AI Kimi K2 Instruct, good performance",
            },
        }
        return model_info.get(model, {})
