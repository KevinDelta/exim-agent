import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_chroma import Chroma
from loguru import logger

from acc_llamaindex.config import config
from acc_llamaindex.infrastructure.llm_providers.langchain_provider import get_embeddings


class ChromaDBClient:
    """
    ChromaDB client for vector storage and retrieval.
    
    Uses a single persistent client instance with shared embeddings
    to minimize memory usage and connection overhead.
    """

    def __init__(self):
        self._client = None
        self._embeddings = None
        self._vector_store = None  # Semantic Memory (SM)
        self._episodic_store = None  # Episodic Memory (EM)
        self._collection = None
        self._episodic_collection = None

    def initialize(self):
        """
        Initialize ChromaDB client with persistent storage.
        
        Creates a single PersistentClient instance and shared embeddings
        to reduce memory usage and connection overhead.
        """
        try:
            logger.info(f"Initializing ChromaDB at {config.chroma_db_path}")
            
            # Create single persistent client instance (connection pooling)
            self._client = chromadb.PersistentClient(path=config.chroma_db_path)
            
            # Initialize embeddings once (shared across all collections)
            self._embeddings = get_embeddings()
            
            logger.info("ChromaDB client and embeddings initialized")
            
            # Create LangChain Chroma vector store using existing client
            self._vector_store = Chroma(
                client=self._client,
                collection_name=config.chroma_collection_name,
                embedding_function=self._embeddings,
                collection_metadata={"description": "Document embeddings for RAG"},
            )
            
            # Get direct collection reference
            self._collection = self._vector_store._collection
            
            logger.info(f"Semantic memory collection initialized: {config.chroma_collection_name}")
            
            # Initialize episodic memory collection if memory system is enabled
            if config.enable_memory_system:
                self._initialize_episodic_memory()
            
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise
    
    def _initialize_episodic_memory(self):
        """
        Initialize the episodic memory collection using existing client.
        
        Reuses the same ChromaDB client and embeddings instance
        to avoid duplicate connections and memory overhead.
        """
        try:
            logger.info(f"Initializing episodic memory collection: {config.em_collection_name}")
            
            # Create episodic store using SAME client and embeddings
            self._episodic_store = Chroma(
                client=self._client,  # Reuse existing client
                collection_name=config.em_collection_name,
                embedding_function=self._embeddings,  # Reuse existing embeddings
                collection_metadata={"description": "Episodic memory for conversations"},
            )
            
            # Get direct collection reference
            self._episodic_collection = self._episodic_store._collection
            
            logger.info("Episodic memory collection initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize episodic memory: {e}")
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
        """
        Reset the collection by deleting and recreating it.
        
        Uses existing client and embeddings instances to maintain
        connection pooling benefits.
        """
        try:
            logger.warning(f"Resetting collection: {config.chroma_collection_name}")
            
            # Delete the old collection
            self._client.delete_collection(name=config.chroma_collection_name)
            
            # Reinitialize the vector store using existing client and embeddings
            self._vector_store = Chroma(
                client=self._client,  # Reuse existing client
                collection_name=config.chroma_collection_name,
                embedding_function=self._embeddings,  # Reuse existing embeddings
                collection_metadata={"description": "Document embeddings for RAG"},
            )
            
            # Update collection reference
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
    
    def get_episodic_store(self) -> Chroma:
        """Get the episodic memory vector store instance."""
        if self._episodic_store is None:
            raise RuntimeError("Episodic memory not initialized. Enable memory system in config.")
        return self._episodic_store
    
    def query_episodic(
        self,
        session_id: str,
        query: str,
        k: int = 5
    ) -> list:
        """
        Query episodic memory collection filtered by session.
        
        Args:
            session_id: Session to filter by
            query: Query text
            k: Number of results
            
        Returns:
            List of documents
        """
        if self._episodic_store is None:
            logger.warning("Episodic memory not initialized")
            return []
        
        try:
            # Query with session filter
            results = self._episodic_store.similarity_search(
                query,
                k=k,
                filter={"session_id": session_id}
            )
            return results
        except Exception as e:
            logger.error(f"Failed to query episodic memory: {e}")
            return []
    
    def write_episodic(self, texts: list, metadatas: list):
        """
        Write items to episodic memory.
        
        Args:
            texts: List of text content
            metadatas: List of metadata dicts (must include session_id, salience, ttl_date)
        """
        if self._episodic_store is None:
            logger.warning("Episodic memory not initialized")
            return
        
        try:
            self._episodic_store.add_texts(
                texts=texts,
                metadatas=metadatas
            )
            logger.info(f"Wrote {len(texts)} items to episodic memory")
        except Exception as e:
            logger.error(f"Failed to write to episodic memory: {e}")
            raise


# Global instance
chroma_client = ChromaDBClient()
