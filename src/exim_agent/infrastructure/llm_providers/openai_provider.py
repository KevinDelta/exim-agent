"""OpenAI LLM provider implementation."""

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from loguru import logger

from exim_agent.config import config
from .base_provider import BaseLLMProvider, BaseEmbeddingProvider


class OpenAIProvider(BaseLLMProvider, BaseEmbeddingProvider):
    """OpenAI provider for LLMs and embeddings."""
    
    def validate_config(self) -> bool:
        """Validate OpenAI configuration."""
        if not config.openai_api_key:
            raise ValueError("OpenAI API key not configured")
        return True
    
    def get_model_name(self) -> str:
        """Get the OpenAI model name."""
        return config.openai_model
    
    def initialize_llm(self) -> ChatOpenAI:
        """Initialize ChatOpenAI LLM with explicit timeout."""
        self.validate_config()
        
        try:
            # Get timeout from config, default to 30 seconds
            timeout = getattr(config, 'llm_timeout_seconds', 30.0)
            
            logger.info(
                f"Initializing ChatOpenAI with model: {config.openai_model}, "
                f"timeout: {timeout}s"
            )
            
            llm = ChatOpenAI(
                model=config.openai_model,
                api_key=config.openai_api_key,
                temperature=config.llm_temperature,
                max_tokens=config.max_tokens,
                streaming=config.streaming,
                timeout=timeout,  # Explicit timeout for all LLM calls
            )
            
            logger.info("ChatOpenAI initialized successfully")
            return llm
            
        except Exception as e:
            logger.error(f"Failed to initialize ChatOpenAI: {e}")
            raise

    def initialize_embeddings(self) -> OpenAIEmbeddings:
        """Initialize OpenAI embeddings."""
        self.validate_config()
        
        try:
            logger.info(f"Initializing OpenAIEmbeddings with model: {config.openai_embedding_model}")
            
            embeddings = OpenAIEmbeddings(
                model=config.openai_embedding_model,
                api_key=config.openai_api_key,
            )
            
            logger.info("OpenAIEmbeddings initialized successfully")
            return embeddings
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenAIEmbeddings: {e}")
            raise
