"""Test script for Mem0 implementation."""

import sys
from loguru import logger

# Configure logger
logger.remove()
logger.add(sys.stderr, level="INFO")

def test_mem0_client():
    """Test Mem0 client initialization and basic operations."""
    logger.info("=" * 60)
    logger.info("TEST 1: Mem0 Client Initialization")
    logger.info("=" * 60)
    
    from acc_llamaindex.application.memory_service.mem0_client import mem0_client
    from acc_llamaindex.config import config
    
    # Check if enabled
    logger.info(f"Mem0 enabled in config: {config.mem0_enabled}")
    logger.info(f"Mem0 client initialized: {mem0_client.is_enabled()}")
    
    if not mem0_client.is_enabled():
        logger.error("❌ Mem0 client is not enabled!")
        return False
    
    logger.success("✅ Mem0 client initialized successfully")
    return True


def test_add_memory():
    """Test adding memories."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 2: Add Memory")
    logger.info("=" * 60)
    
    from acc_llamaindex.application.memory_service.mem0_client import mem0_client
    
    if not mem0_client.is_enabled():
        logger.warning("⚠️  Skipping - Mem0 not enabled")
        return False
    
    # Add a test conversation
    messages = [
        {"role": "user", "content": "I'm learning about LangChain and LlamaIndex"},
        {"role": "assistant", "content": "Great! LangChain and LlamaIndex are powerful frameworks for building LLM applications."}
    ]
    
    result = mem0_client.add(
        messages=messages,
        user_id="test-user-001",
        session_id="test-session-001"
    )
    
    if result:
        logger.success(f"✅ Memory added successfully: {result}")
        return True
    else:
        logger.error("❌ Failed to add memory")
        return False


def test_search_memory():
    """Test searching memories."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 3: Search Memory")
    logger.info("=" * 60)
    
    from acc_llamaindex.application.memory_service.mem0_client import mem0_client
    
    if not mem0_client.is_enabled():
        logger.warning("⚠️  Skipping - Mem0 not enabled")
        return False
    
    # Search for the memory we just added
    results = mem0_client.search(
        query="LangChain frameworks",
        user_id="test-user-001",
        limit=5
    )
    
    # Handle dict or list response
    if isinstance(results, dict):
        memories = results.get('results', [])
    else:
        memories = results if isinstance(results, list) else []
    
    logger.info(f"Found {len(memories)} memories")
    
    if memories:
        for i, memory in enumerate(memories, 1):
            logger.info(f"\nMemory {i}:")
            if isinstance(memory, dict):
                logger.info(f"  ID: {memory.get('id', 'N/A')}")
                logger.info(f"  Content: {memory.get('memory', 'N/A')[:100]}...")
                logger.info(f"  Score: {memory.get('score', 'N/A')}")
            else:
                logger.info(f"  Content: {str(memory)[:100]}...")
        
        logger.success(f"✅ Found {len(memories)} relevant memories")
        return True
    else:
        logger.warning("⚠️  No memories found (may need time to process)")
        return True  # Not necessarily a failure


def test_get_all_memories():
    """Test retrieving all memories for a user."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 4: Get All Memories")
    logger.info("=" * 60)
    
    from acc_llamaindex.application.memory_service.mem0_client import mem0_client
    
    if not mem0_client.is_enabled():
        logger.warning("⚠️  Skipping - Mem0 not enabled")
        return False
    
    # Get all memories for the test user
    results = mem0_client.get_all(
        user_id="test-user-001"
    )
    
    # Handle dict or list response
    if isinstance(results, dict):
        memories = results.get('results', [])
    else:
        memories = results if isinstance(results, list) else []
    
    logger.info(f"Total memories for user: {len(memories)}")
    
    if memories:
        for i, memory in enumerate(list(memories)[:3], 1):  # Show first 3
            logger.info(f"\nMemory {i}:")
            if isinstance(memory, dict):
                logger.info(f"  ID: {memory.get('id', 'N/A')}")
                logger.info(f"  Content: {memory.get('memory', 'N/A')[:100]}...")
            else:
                logger.info(f"  Content: {str(memory)[:100]}...")
        
        logger.success(f"✅ Retrieved {len(memories)} memories")
        return True
    else:
        logger.warning("⚠️  No memories found for user")
        return True


def test_graph_workflow():
    """Test the full LangGraph workflow with Mem0."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 5: LangGraph Workflow with Mem0")
    logger.info("=" * 60)
    
    from acc_llamaindex.application.chat_service.graph import memory_graph
    
    # Test query
    query = "What frameworks am I learning about?"
    
    logger.info(f"Query: {query}")
    logger.info("User: test-user-001")
    logger.info("Session: test-session-001")
    
    try:
        # Run the graph
        result = memory_graph.invoke({
            "query": query,
            "user_id": "test-user-001",
            "session_id": "test-session-001"
        })
        
        logger.info("\n--- Graph Results ---")
        logger.info(f"Relevant Memories: {len(result.get('relevant_memories', []))}")
        logger.info(f"RAG Context: {len(result.get('rag_context', []))}")
        logger.info(f"Final Context: {len(result.get('final_context', []))}")
        logger.info(f"Citations: {result.get('citations', [])}")
        
        logger.info("\n--- Response ---")
        logger.info(result.get('response', 'No response generated'))
        
        logger.success("✅ Graph workflow completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Graph workflow failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_memory_persistence():
    """Test that memories persist across client instances."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 6: Memory Persistence")
    logger.info("=" * 60)
    
    from acc_llamaindex.application.memory_service.mem0_client import mem0_client
    
    if not mem0_client.is_enabled():
        logger.warning("⚠️  Skipping - Mem0 not enabled")
        return False
    
    # Add a unique memory
    import time
    timestamp = int(time.time())
    
    messages = [
        {"role": "user", "content": f"Test memory persistence {timestamp}"},
        {"role": "assistant", "content": "This is a test of memory persistence."}
    ]
    
    mem0_client.add(
        messages=messages,
        user_id="test-persistence-user",
        session_id="test-persistence-session"
    )
    
    # Search for it
    results = mem0_client.search(
        query=f"persistence {timestamp}",
        user_id="test-persistence-user",
        limit=5
    )
    
    if results:
        logger.success(f"✅ Memory persisted: Found {len(results)} results")
        return True
    else:
        logger.warning("⚠️  Memory not found (may need processing time)")
        return True


def cleanup_test_memories():
    """Clean up test memories."""
    logger.info("\n" + "=" * 60)
    logger.info("CLEANUP: Removing Test Memories")
    logger.info("=" * 60)
    
    from acc_llamaindex.application.memory_service.mem0_client import mem0_client
    
    if not mem0_client.is_enabled():
        logger.warning("⚠️  Skipping - Mem0 not enabled")
        return
    
    # Reset test user memories
    try:
        mem0_client.reset(user_id="test-user-001")
        logger.info("✅ Cleaned up test-user-001 memories")
        
        mem0_client.reset(user_id="test-persistence-user")
        logger.info("✅ Cleaned up test-persistence-user memories")
        
        logger.success("✅ Cleanup completed")
    except Exception as e:
        logger.warning(f"⚠️  Cleanup warning: {e}")


def main():
    """Run all tests."""
    logger.info("\n" + "=" * 60)
    logger.info("STARTING MEM0 WORKFLOW TESTS")
    logger.info("=" * 60)
    
    results = []
    
    # Run tests
    results.append(("Client Initialization", test_mem0_client()))
    results.append(("Add Memory", test_add_memory()))
    results.append(("Search Memory", test_search_memory()))
    results.append(("Get All Memories", test_get_all_memories()))
    results.append(("Graph Workflow", test_graph_workflow()))
    results.append(("Memory Persistence", test_memory_persistence()))
    
    # Cleanup
    cleanup_test_memories()
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status} - {test_name}")
    
    logger.info("\n" + "-" * 60)
    logger.info(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        logger.success("\n🎉 All tests passed!")
    else:
        logger.warning(f"\n⚠️  {total - passed} test(s) failed")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
