import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_chroma import Chroma
from loguru import logger

from exim_agent.config import config
from exim_agent.infrastructure.llm_providers.langchain_provider import get_embeddings


class ChromaDBClient:
    """
    Shared ChromaDB client managing multiple collections.
    
    Collections:
    - documents: RAG document embeddings
    - mem0_memories: Mem0 conversational memory (if enabled)
    
    Single client instance shared across all services for connection pooling.
    """

    def __init__(self):
        self._client = None
        self._embeddings = None
        self._rag_vector_store = None
        self._rag_collection = None

    def initialize(self):
        """Initialize shared ChromaDB client and RAG collection."""
        try:
            logger.info(f"Initializing shared ChromaDB client at {config.chroma_db_path}")
            
            chroma_settings = ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True,
            )
            self._client = chromadb.PersistentClient(
                path=config.chroma_db_path,
                settings=chroma_settings
            )
            
            self._embeddings = get_embeddings()
            
            logger.info("Shared ChromaDB client initialized")
            
            # Create RAG documents collection
            self._rag_vector_store = Chroma(
                client=self._client,
                collection_name=config.chroma_collection_name,
                embedding_function=self._embeddings,
                collection_metadata={"description": "Document embeddings for RAG"},
            )
            
            self._rag_collection = self._rag_vector_store._collection
            
            logger.info(f"RAG collection initialized: {config.chroma_collection_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise
    
    def get_client(self):
        """Get the shared ChromaDB client for use by other services (e.g., Mem0)."""
        if self._client is None:
            raise RuntimeError("ChromaDB not initialized. Call initialize() first.")
        return self._client

    def get_vector_store(self) -> Chroma:
        """Get the RAG LangChain Chroma vector store instance."""
        if self._rag_vector_store is None:
            raise RuntimeError("ChromaDB not initialized. Call initialize() first.")
        return self._rag_vector_store

    def get_collection(self):
        """Get the RAG collection for direct operations."""
        if self._rag_collection is None:
            raise RuntimeError("ChromaDB not initialized. Call initialize() first.")
        return self._rag_collection

    def reset_collection(self):
        """Reset the RAG documents collection."""
        try:
            logger.warning(f"Resetting RAG collection: {config.chroma_collection_name}")
            
            self._client.delete_collection(name=config.chroma_collection_name)
            
            self._rag_vector_store = Chroma(
                client=self._client,
                collection_name=config.chroma_collection_name,
                embedding_function=self._embeddings,
                collection_metadata={"description": "Document embeddings for RAG"},
            )
            
            self._rag_collection = self._rag_vector_store._collection
            
            logger.info("RAG collection reset successfully")
        except Exception as e:
            logger.error(f"Failed to reset RAG collection: {e}")
            raise

    def get_collection_stats(self) -> dict:
        """Get statistics about the RAG collection."""
        try:
            count = self._rag_collection.count()
            return {
                "collection_name": config.chroma_collection_name,
                "document_count": count,
                "status": "active"
            }
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {"error": str(e)}


# Global instance
chroma_client = ChromaDBClient()
