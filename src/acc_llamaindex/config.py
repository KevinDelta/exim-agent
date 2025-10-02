from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_file_encoding="utf-8")
    
    # API Keys
    openai_api_key: str
    huggingface_api_key: str | None = None
    groq_api_key: str | None = None
    llama_cloud_api_key: str | None = None
    
    # LLM Configuration
    openai_model: str = "gpt-5-nano-2025-08-07"
    openai_embedding_model: str = "text-embedding-3-small"
    llm_temperature: float = 0.7
    
    # Document Processing
    chunk_size: int = 1024
    chunk_overlap: int = 200
    
    # Paths
    documents_path: str = "./data/documents"
    chroma_db_path: str = "./data/chroma_db"
    
    # ChromaDB Configuration
    chroma_collection_name: str = "documents"
    
    # Supported file extensions for ingestion
    supported_file_extensions: list[str] = [
        ".txt", ".pdf", ".docx", ".md", 
        ".csv", ".json", ".html", ".xml"
    ]


settings = Settings()
