import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_file_encoding="utf-8")
    
    # API Keys
    openai_api_key: str
    anthropic_api_key: str | None = None
    groq_api_key: str | None = None
    huggingface_api_key: str | None = None
    llama_cloud_api_key: str | None = None
    
    # LangSmith Configuration
    langsmith_workspace_id: str | None = None
    langsmith_api_key: str | None = None  
    langsmith_endpoint: str | None = None  
    langsmith_project: str | None = None  
      
    # Provider Selection
    llm_provider: str = "openai"  # Options: openai, anthropic, groq
    embedding_provider: str = "openai"  # Currently only openai supported
    
    # OpenAI Configuration
    openai_model: str = "gpt-5-nano-2025-08-07"
    openai_embedding_model: str = "text-embedding-3-small"
    
    # Anthropic Configuration
    anthropic_model: str = "claude-haiku-4-5-20251001"
    
    # Groq Configuration
    groq_model: str = "openai/gpt-oss-120b"
    
    # Common LLM Settings (apply to all providers)
    llm_temperature: float = 0.7
    max_tokens: int | None = None
    streaming: bool = True
    
    # Document Processing
    chunk_size: int = 1024
    chunk_overlap: int = 200
    
    # RAG Configuration
    retrieval_k: int = 20  # Number of documents to retrieve (increased for reranking)
    retrieval_score_threshold: float = 0.7  # Minimum similarity score
    
    # Reranking Configuration
    enable_reranking: bool = True
    rerank_top_k: int = 5  # Number of documents after reranking
    cross_encoder_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    
    # Evaluation Configuration
    enable_evaluation: bool = False  # Auto-evaluate responses
    evaluation_threshold: float = 0.7  # Minimum acceptable score
    
    # Mem0 Memory Configuration (ALWAYS ENABLED)
    mem0_enabled: bool = True  # Mem0 is now the primary memory system
    mem0_vector_store: str = "chroma"  # Use existing ChromaDB
    mem0_llm_provider: str = "openai"  # LLM for memory operations
    mem0_llm_model: str = "gpt-5-nano-2025-08-07"  # Model for summarization/extraction
    mem0_embedder_model: str = "text-embedding-3-small"  # Embedding model
    mem0_enable_dedup: bool = True  # Enable automatic deduplication
    mem0_history_limit: int = 10  # Conversation history window
    mem0_history_db_path: str = os.getenv("MEM0_HISTORY_DB_PATH", "/app/data/mem0_history.db")  # SQLite history
    
    # Paths - explicit configuration via environment variables
    # Docker default: /app/data/* (matches volume mount in docker-compose.yaml)
    # Local: set absolute paths in .env file
    documents_path: str = os.getenv("DOCUMENTS_PATH", "/app/data/documents")
    chroma_db_path: str = os.getenv("CHROMA_DB_PATH", "/app/data/chroma_db")
    
    # ChromaDB Configuration
    chroma_collection_name: str = "documents"
    
    # Supported file extensions for ingestion
    supported_file_extensions: list[str] = [
        ".txt", ".pdf", ".docx", ".md", 
        ".csv", ".json", ".html", ".xml", ".epub"
    ]


config = Settings()
