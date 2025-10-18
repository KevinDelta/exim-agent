from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from loguru import logger

from acc_llamaindex.config import config
from acc_llamaindex.infrastructure.db.chroma_client import chroma_client
from acc_llamaindex.infrastructure.llm_providers.langchain_provider import get_llm
from acc_llamaindex.application.reranking_service import reranking_service
from acc_llamaindex.application.evaluation_service import evaluation_service


class ChatService:
    """Service for RAG-based chat using LangChain v1 agents."""

    def __init__(self):
        self.llm = None
        self.agent = None
        self.vector_store = None
        logger.info("ChatService initialized")

    def initialize(self):
        """Initialize the chat service with LLM and retriever."""
        try:
            logger.info("Initializing ChatService...")
             
            # Get LLM and vector store
            self.llm = get_llm()
            self.vector_store = chroma_client.get_vector_store()
            
            # Initialize reranking service
            if config.enable_reranking:
                logger.info("Initializing reranking service...")
                reranking_service.initialize()
            
            # Initialize evaluation service
            if config.enable_evaluation:
                logger.info("Initializing evaluation service...")
                evaluation_service.initialize()
            
            # Create retriever tool with reranking support
            @tool
            def retrieve_context(query: str) -> str:
                """Retrieve relevant documents from the knowledge base to answer questions."""
                try:
                    # Perform similarity search
                    # retrieval_k is already set to 20 in config for reranking
                    docs = self.vector_store.similarity_search(
                        query, 
                        k=config.retrieval_k
                    )
                    
                    if not docs:
                        return "No relevant documents found in the knowledge base."
                    
                    # Rerank if enabled
                    if reranking_service.is_enabled():
                        logger.info(f"Reranking {len(docs)} documents to top {config.rerank_top_k}")
                        docs = reranking_service.rerank(query, docs, top_k=config.rerank_top_k)
                    
                    # Format retrieved documents
                    context = "\n\n---\n\n".join([
                        f"Document {i+1}:\n{doc.page_content}" 
                        for i, doc in enumerate(docs)
                    ])
                    
                    return context
                    
                except Exception as e:
                    logger.error(f"Error retrieving context: {e}")
                    return f"Error retrieving context: {str(e)}"
            
            # Create agent with retriever tool
            self.agent = create_agent(
                model=self.llm,
                tools=[retrieve_context],
                system_prompt=(
                    "You are a helpful AI assistant with access to a knowledge base. "
                    "When answering questions, use the retrieve_context tool to find relevant information. "
                    "Always cite the sources you use and be honest when you don't have enough information. "
                    "If the retrieved context doesn't contain the answer, say so clearly."
                )
            )
            
            logger.info("ChatService initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize ChatService: {e}")
            raise

    def chat(self, message: str, conversation_history: list | None = None) -> dict:
        """
        Process a chat message and return a response.

        Args:
            message: The user's message
            conversation_history: Optional list of previous messages in the conversation
            
        Returns:
            Dictionary containing the response and metadata
        """
        try:
            if self.agent is None:
                raise RuntimeError("ChatService not initialized. Call initialize() first.")
            
            logger.info(f"Processing chat message: {message[:100]}...")
            
            # Build messages list
            messages = []
            if conversation_history:
                messages.extend(conversation_history)
            messages.append({"role": "user", "content": message})
            
            # Invoke agent
            response = self.agent.invoke({"messages": messages})
            
            # Extract the final AI message
            ai_messages = [msg for msg in response["messages"] if hasattr(msg, "content") and msg.__class__.__name__ == "AIMessage"]
            final_response = ai_messages[-1].content if ai_messages else "No response generated"
            
            logger.info("Chat response generated successfully")
            
            return {
                "response": final_response,
                "messages": response["messages"],
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Error processing chat message: {e}")
            return {
                "response": f"Error: {str(e)}",
                "success": False,
                "error": str(e)
            }

    def stream_chat(self, message: str, conversation_history: list | None = None):
        """
        Stream a chat response.
        
        Args:
            message: The user's message
            conversation_history: Optional list of previous messages
            
        Yields:
            Response chunks as they are generated
        """
        try:
            if self.agent is None:
                raise RuntimeError("ChatService not initialized. Call initialize() first.")
            
            logger.info(f"Streaming chat message: {message[:100]}...")
            
            # Build messages list
            messages = []
            if conversation_history:
                messages.extend(conversation_history)
            messages.append({"role": "user", "content": message})
            
            # Stream response
            for chunk in self.agent.stream({"messages": messages}):
                if "messages" in chunk:
                    for msg in chunk["messages"]:
                        if hasattr(msg, "content") and msg.__class__.__name__ == "AIMessage":
                            if isinstance(msg.content, str):
                                yield msg.content
                            elif isinstance(msg.content, list):
                                for block in msg.content:
                                    if isinstance(block, dict) and block.get("type") == "text":
                                        yield block.get("text", "")
            
        except Exception as e:
            logger.error(f"Error streaming chat: {e}")
            yield f"Error: {str(e)}"


# Global service instance
chat_service = ChatService()
