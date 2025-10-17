import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_chroma import Chroma
from loguru import logger

from acc_llamaindex.config import config
from acc_llamaindex.infrastructure.llm_providers.langchain_provider import get_embeddings


class ChromaDBClient:
    """ChromaDB client for vector storage and retrieval."""

    def __init__(self):
        self._client = None
        self._vector_store = None

    def initialize(self):
        """Initialize ChromaDB client with persistent storage."""
        try:
            logger.info(f"Initializing ChromaDB at {config.chroma_db_path}")
            
            # Initialize embeddings
            embeddings = get_embeddings()
            
            # Create LangChain Chroma vector store
            self._vector_store = Chroma(
                collection_name=config.chroma_collection_name,
                embedding_function=embeddings,
                persist_directory=config.chroma_db_path,
                collection_metadata={"description": "Document embeddings for RAG"}
            )
            
            # Get underlying ChromaDB client and collection for direct operations
            self._client = self._vector_store._client
            self._collection = self._vector_store._collection
            
            logger.info(f"ChromaDB initialized successfully with collection: {config.chroma_collection_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise

    def get_vector_store(self) -> Chroma:
        """Get the LangChain Chroma vector store instance."""
        if self._vector_store is None:
            raise RuntimeError("ChromaDB not initialized. Call initialize() first.")
        return self._vector_store

    def get_collection(self):
        """Get the underlying ChromaDB collection."""
        if self._collection is None:
            raise RuntimeError("ChromaDB not initialized. Call initialize() first.")
        return self._collection

    def reset_collection(self):
        """Reset the collection by deleting and recreating it."""
        try:
            logger.warning(f"Resetting collection: {config.chroma_collection_name}")
            
            # Delete the old collection
            self._client.delete_collection(name=config.chroma_collection_name)
            
            # Reinitialize the vector store with a fresh collection
            embeddings = get_embeddings()
            self._vector_store = Chroma(
                collection_name=config.chroma_collection_name,
                embedding_function=embeddings,
                persist_directory=config.chroma_db_path,
                collection_metadata={"description": "Document embeddings for RAG"}
            )
            
            # Update references
            self._client = self._vector_store._client
            self._collection = self._vector_store._collection
            
            logger.info("Collection reset successfully")
        except Exception as e:
            logger.error(f"Failed to reset collection: {e}")
            raise

    def get_collection_stats(self) -> dict:
        """Get statistics about the collection."""
        try:
            count = self._collection.count()
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
