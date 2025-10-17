"""Example usage of PydanticAI-based Vector agent.

This script demonstrates the different ways to use the refactored agent:
1. Classic mode (backward compatible)
2. Tool-enabled mode
3. Direct PydanticAI agent usage
4. Custom tool workflows
"""

import asyncio
from vector.agent import (
    ResearchAgent,
    PydanticResearchAgent,
    AgentDeps,
    ChatSession
)
from vector.config import Config
from vector.embedders.sentence_transformer import SentenceTransformerEmbedder
from vector.stores.factory import create_store
from vector.search.service import SearchService
from vector.ai.factory import AIModelFactory


def example_1_classic_mode():
    """Example 1: Classic mode (backward compatible)."""
    print("=" * 80)
    print("Example 1: Classic Mode (Backward Compatible)")
    print("=" * 80)
    
    # Create agent - works exactly as before
    agent = ResearchAgent()
    
    # Start session
    session_id = agent.start_chat()
    print(f"Started session: {session_id}")
    
    # Chat
    response = agent.chat(
        session_id=session_id,
        user_message="What are the zoning requirements?"
    )
    
    print(f"\nAssistant: {response['assistant'][:200]}...")
    print(f"Agent type: {response['agent_type']}")
    print(f"Results found: {len(response.get('results', []))}")
    print(f"Tokens used: {response['usage_metrics']['total_tokens']}")


def example_2_tool_enabled_mode():
    """Example 2: Tool-enabled mode with PydanticAI."""
    print("\n" + "=" * 80)
    print("Example 2: Tool-Enabled Mode")
    print("=" * 80)
    
    # Create agent with PydanticAI enabled
    agent = ResearchAgent(use_pydantic_ai=True)
    
    # Start session
    session_id = agent.start_chat()
    print(f"Started session: {session_id}")
    
    # Chat with tool use enabled
    response = agent.chat(
        session_id=session_id,
        user_message="What are the permit requirements?",
        use_tools=True  # Enable PydanticAI agent
    )
    
    print(f"\nAssistant: {response['assistant'][:200]}...")
    print(f"Agent type: {response['agent_type']}")
    
    # Show tool calls
    if 'tool_calls' in response:
        print(f"\nTool calls made: {len(response['tool_calls'])}")
        for i, call in enumerate(response['tool_calls'], 1):
            print(f"  {i}. {call.get('tool', 'unknown')}")


async def example_3_direct_pydantic_ai():
    """Example 3: Direct PydanticAI agent usage."""
    print("\n" + "=" * 80)
    print("Example 3: Direct PydanticAI Usage")
    print("=" * 80)
    
    # Setup dependencies
    config = Config()
    embedder = SentenceTransformerEmbedder()
    store = create_store("qdrant", db_path=config.vector_db_path)
    search_service = SearchService(embedder, store, "chunks")
    
    search_model = AIModelFactory.create_model(config, 'search')
    answer_model = AIModelFactory.create_model(config, 'answer')
    
    deps = AgentDeps(
        search_service=search_service,
        config=config,
        search_model=search_model,
        answer_model=answer_model
    )
    
    # Create PydanticAI agent
    agent = PydanticResearchAgent(deps)
    
    # Create session
    session = ChatSession(
        id="test-async",
        system_prompt="You are a helpful assistant.",
        messages=[]
    )
    
    # Use async chat
    result = await agent.chat(
        session=session,
        user_message="What are the building codes?",
        max_tokens=500
    )
    
    print(f"\nAssistant: {result['assistant'][:200]}...")
    print(f"Tool calls: {len(result.get('tool_calls', []))}")
    print(f"Tokens: {result['usage_metrics']['total_tokens']}")


async def example_4_custom_tool_workflow():
    """Example 4: Custom workflow with direct tool usage."""
    print("\n" + "=" * 80)
    print("Example 4: Custom Tool Workflow")
    print("=" * 80)
    
    from vector.agent.tools import expand_query, search_documents
    from pydantic_ai import RunContext
    
    # Setup dependencies (same as example 3)
    config = Config()
    embedder = SentenceTransformerEmbedder()
    store = create_store("qdrant", db_path=config.vector_db_path)
    search_service = SearchService(embedder, store, "chunks")
    
    search_model = AIModelFactory.create_model(config, 'search')
    answer_model = AIModelFactory.create_model(config, 'answer')
    
    deps = AgentDeps(
        search_service=search_service,
        config=config,
        search_model=search_model,
        answer_model=answer_model
    )
    
    # Create minimal context
    ctx = RunContext(deps=deps, retry=0, messages=[])
    
    # Create session
    session = ChatSession(
        id="custom",
        system_prompt="",
        messages=[]
    )
    
    # Custom workflow: expand then search
    print("\nExpanding query...")
    expansion = await expand_query(
        ctx=ctx,
        session=session,
        user_message="zoning rules"
    )
    
    print(f"Expanded query: {expansion['expanded_query']}")
    print(f"Keyphrases: {', '.join(expansion['keyphrases'][:5])}...")
    
    print("\nSearching with expanded query...")
    results = await search_documents(
        ctx=ctx,
        query=expansion['expanded_query'],
        top_k=5
    )
    
    print(f"\nFound {len(results)} results:")
    for i, result in enumerate(results, 1):
        print(f"  {i}. {result.filename} (score: {result.score:.3f})")
        print(f"     {result.text[:100]}...")


def example_5_mcp_server_info():
    """Example 5: MCP server integration info."""
    print("\n" + "=" * 80)
    print("Example 5: MCP Server Integration")
    print("=" * 80)
    
    from vector.agent import MCP_AVAILABLE
    
    print(f"MCP Available: {MCP_AVAILABLE}")
    
    if MCP_AVAILABLE:
        print("\nTo run the MCP server:")
        print("  python -m vector.agent.mcp_server")
        print("\nOr configure in Claude Desktop config:")
        print('  {')
        print('    "mcpServers": {')
        print('      "vector": {')
        print('        "command": "python",')
        print('        "args": ["-m", "vector.agent.mcp_server"],')
        print('        "env": {')
        print('          "OPENAI_API_KEY": "your-key-here"')
        print('        }')
        print('      }')
        print('    }')
        print('  }')
    else:
        print("\nMCP not available. Install with: pip install mcp")


def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("PydanticAI Vector Agent Examples")
    print("=" * 80)
    
    # Run sync examples
    try:
        example_1_classic_mode()
    except Exception as e:
        print(f"Example 1 failed: {e}")
    
    try:
        example_2_tool_enabled_mode()
    except Exception as e:
        print(f"Example 2 failed: {e}")
    
    # Run async examples
    try:
        asyncio.run(example_3_direct_pydantic_ai())
    except Exception as e:
        print(f"Example 3 failed: {e}")
    
    try:
        asyncio.run(example_4_custom_tool_workflow())
    except Exception as e:
        print(f"Example 4 failed: {e}")
    
    # Show MCP info
    example_5_mcp_server_info()
    
    print("\n" + "=" * 80)
    print("Examples complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
