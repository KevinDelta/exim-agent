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
    
    # Memory System Configuration
    use_langgraph: bool = False  # Toggle LangGraph vs LangChain agents
    enable_memory_system: bool = True  # Toggle entire memory system
    
    # Working Memory (WM)
    wm_max_turns: int = 10  # Max turns to keep in working memory
    wm_session_ttl_minutes: int = 30  # Session timeout
    wm_max_sessions: int = 100  # Max concurrent sessions (LRU eviction)
    
    # Episodic Memory (EM)
    em_collection_name: str = "episodic_memory"
    em_ttl_days: int = 14  # EM facts expire after 14 days
    em_distill_every_n_turns: int = 5  # Trigger distillation frequency
    em_k_default: int = 5  # Default number of EM results to retrieve
    em_salience_threshold: float = 0.3  # Min salience for retrieval
    
    # Semantic Memory (SM) - uses existing chroma_collection_name
    sm_k_default: int = 10  # Default number of SM results to retrieve
    sm_verified_only: bool = False  # For compliance queries, only verified docs
    
    # Memory Distillation & Promotion
    enable_em_distillation: bool = True
    enable_sm_promotion: bool = True
    enable_intent_classification: bool = True 
    promotion_salience_threshold: float = 0.8
    promotion_citation_count: int = 5
    promotion_age_days: int = 7
    
    # Memory Performance
    enable_em_cache: bool = True
    max_context_tokens: int = 8000
    
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
