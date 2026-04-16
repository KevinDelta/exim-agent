"""Simplified chat service using LangGraph with Mem0."""

from loguru import logger

from exim_agent.config import config
from exim_agent.application.chat_service.graph import memory_graph
from exim_agent.application.reranking_service import reranking_service
from exim_agent.application.evaluation_service import evaluation_service
from exim_agent.application.memory_service.mem0_client import mem0_client


class ChatService:
    """
    Simplified chat service that delegates to LangGraph.
    
    LangGraph handles:
    - Memory retrieval (Mem0)
    - Document retrieval (RAG)
    - Context fusion and reranking
    - Response generation
    - Memory updates
    """

    def __init__(self):
        self.graph = memory_graph
        self.initialized = False
        logger.info("ChatService initialized (LangGraph-powered)")

    def initialize(self):
        """Initialize optional services."""
        try:
            logger.info("Initializing ChatService...")
            
            # Initialize Mem0 client (uses shared ChromaDB client)
            logger.info("Initializing Mem0 client...")
            mem0_client.initialize()
            
            # Initialize reranking service
            if config.enable_reranking:
                logger.info("Initializing reranking service...")
                reranking_service.initialize()
            
            # Initialize evaluation service
            if config.enable_evaluation:
                logger.info("Initializing evaluation service...")
                evaluation_service.initialize()
            
            self.initialized = True
            logger.info("ChatService initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize ChatService: {e}")
            raise

    def chat(
        self,
        message: str,
        user_id: str = "default",
        session_id: str | None = None,
        client_id: str | None = None,
        sku_id: str | None = None,
        lane_id: str | None = None
    ) -> dict:
        """
        Process a chat message via LangGraph.

        Args:
            message: The user's message
            user_id: User identifier for memory
            session_id: Session identifier for memory
            client_id: Optional client identifier for compliance routing
            sku_id: Optional SKU identifier for compliance routing
            lane_id: Optional lane identifier for compliance routing
            
        Returns:
            Dictionary containing the response and metadata
        """
        try:
            logger.info(f"Processing chat via LangGraph: {message[:100]}...")
            
            # Generate session ID if not provided
            if not session_id:
                session_id = f"session-{user_id}"
            
            # Invoke LangGraph with optional identifiers
            result = self.graph.invoke({
                "query": message,
                "user_id": user_id,
                "session_id": session_id,
                "client_id": client_id,
                "sku_id": sku_id,
                "lane_id": lane_id
            })
            
            logger.info("Chat response generated successfully")
            
            return {
                "response": result["response"],
                "citations": result.get("citations", []),
                "snapshot": result.get("snapshot"),
                "routing_path": result.get("routing_path"),
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Error processing chat message: {e}")
            return {
                "response": f"Error: {str(e)}",
                "success": False,
                "error": str(e)
            }


# Global service instance
chat_service = ChatService()
