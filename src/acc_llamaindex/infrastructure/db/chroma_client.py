import chromadb
from chromadb.config import Settings as ChromaSettings
from llama_index.core import StorageContext, VectorStoreIndex
from llama_index.vector_stores.chroma import ChromaVectorStore
from loguru import logger

from acc_llamaindex.config import settings


class ChromaDBClient:
    """ChromaDB client for vector storage and retrieval."""

    def __init__(self):
        self._client = None
        self._collection = None
        self._vector_store = None
        self._storage_context = None

    def initialize(self):
        """Initialize ChromaDB client with persistent storage."""
        try:
            logger.info(f"Initializing ChromaDB at {settings.chroma_db_path}")
            
            self._client = chromadb.PersistentClient(
                path=settings.chroma_db_path,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                )
            )
            
            # Get or create collection
            self._collection = self._client.get_or_create_collection(
                name=settings.chroma_collection_name,
                metadata={"description": "Document embeddings for RAG"}
            )
            
            # Create vector store for LlamaIndex
            self._vector_store = ChromaVectorStore(chroma_collection=self._collection)
            self._storage_context = StorageContext.from_defaults(vector_store=self._vector_store)
            
            logger.info(f"ChromaDB initialized successfully with collection: {settings.chroma_collection_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise

    def get_storage_context(self) -> StorageContext:
        """Get the storage context for LlamaIndex."""
        if self._storage_context is None:
            raise RuntimeError("ChromaDB not initialized. Call initialize() first.")
        return self._storage_context

    def get_vector_store(self) -> ChromaVectorStore:
        """Get the vector store instance."""
        if self._vector_store is None:
            raise RuntimeError("ChromaDB not initialized. Call initialize() first.")
        return self._vector_store

    def get_collection(self):
        """Get the ChromaDB collection."""
        if self._collection is None:
            raise RuntimeError("ChromaDB not initialized. Call initialize() first.")
        return self._collection

    def reset_collection(self):
        """Reset the collection by deleting and recreating it."""
        try:
            logger.warning(f"Resetting collection: {settings.chroma_collection_name}")
            self._client.delete_collection(name=settings.chroma_collection_name)
            self._collection = self._client.create_collection(
                name=settings.chroma_collection_name,
                metadata={"description": "Document embeddings for RAG"}
            )
            self._vector_store = ChromaVectorStore(chroma_collection=self._collection)
            self._storage_context = StorageContext.from_defaults(vector_store=self._vector_store)
            logger.info("Collection reset successfully")
        except Exception as e:
            logger.error(f"Failed to reset collection: {e}")
            raise

    def get_collection_stats(self) -> dict:
        """Get statistics about the collection."""
        try:
            count = self._collection.count()
            return {
                "collection_name": settings.chroma_collection_name,
                "document_count": count,
                "status": "active"
            }
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {"error": str(e)}


# Global instance
chroma_client = ChromaDBClient()
