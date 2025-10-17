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
            "llama-3.3-70b-versatile",
            "llama-3.1-70b-versatile",
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768",
            "gemma2-9b-it",
        ]
    
    @staticmethod
    def get_model_info(model: str) -> dict:
        """Get information about a specific model."""
        model_info = {
            "llama-3.3-70b-versatile": {
                "context_window": 128000,
                "tokens_per_second": 800,
                "description": "Fastest Llama 3.3 70B, best for general use",
            },
            "llama-3.1-8b-instant": {
                "context_window": 128000,
                "tokens_per_second": 2000,
                "description": "Ultra-fast, best for simple tasks",
            },
            "mixtral-8x7b-32768": {
                "context_window": 32768,
                "tokens_per_second": 600,
                "description": "Mixture of experts, good performance",
            },
        }
        return model_info.get(model, {})
