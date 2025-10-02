from llama_index.core import Settings
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from loguru import logger

from acc_llamaindex.config import settings as app_settings


def initialize_llm_providers():
    """Initialize LLM and embedding models for LlamaIndex."""
    try:
        logger.info("Initializing OpenAI LLM and embedding models")
        
        # Set up LLM
        Settings.llm = OpenAI(
            model=app_settings.openai_model,
            api_key=app_settings.openai_api_key,
            temperature=app_settings.llm_temperature,
        )
        
        # Set up embedding model
        Settings.embed_model = OpenAIEmbedding(
            model=app_settings.openai_embedding_model,
            api_key=app_settings.openai_api_key,
        )
        
        # Set chunk size for document processing
        Settings.chunk_size = app_settings.chunk_size
        Settings.chunk_overlap = app_settings.chunk_overlap
        
        logger.info(f"LLM initialized: {app_settings.openai_model}")
        logger.info(f"Embedding model initialized: {app_settings.openai_embedding_model}")
        
    except Exception as e:
        logger.error(f"Failed to initialize LLM providers: {e}")
        raise
