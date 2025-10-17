# PydanticAI Migration Guide

## Overview

The Vector agent module has been refactored to use **PydanticAI**, a modern framework for building production-grade AI agents with type safety, tool use, and observability.

## What Changed

### New Architecture

```
vector/agent/
├── agent.py          # Main ResearchAgent (now with PydanticAI support)
├── agents.py         # NEW: PydanticAI agent implementations
├── deps.py           # NEW: Dependency injection container
├── tools.py          # NEW: PydanticAI tool definitions
├── mcp_server.py     # NEW: Model Context Protocol server
├── models.py         # Enhanced with PydanticAI compatibility
├── pipeline.py       # Kept for backward compatibility
├── steps.py          # Kept for backward compatibility
├── retrieval.py      # Kept for backward compatibility
├── prompting.py      # Kept for backward compatibility
└── memory.py         # Kept for backward compatibility
```

### Key Features

1. **Tool-Based Architecture**: Tools are now first-class citizens with proper schemas
2. **Multi-Agent System**: Specialized agents (SearchAgent, AnswerAgent) that can be composed
3. **MCP Integration**: Expose agent capabilities to MCP-compatible clients (Claude Desktop, etc.)
4. **Full Observability**: Track all tool calls, token usage, and agent decisions
5. **Backward Compatible**: Existing code continues to work without changes

## Installation

```bash
# Install PydanticAI and dependencies
pip install pydantic-ai[openai] httpx

# Or update from requirements.txt
pip install -r requirements.txt
```

## Usage

### Option 1: Classic Mode (Backward Compatible)

```python
from vector.agent import ResearchAgent

# Create agent (classic mode by default)
agent = ResearchAgent()

# Start chat session
session_id = agent.start_chat()

# Chat as before - no changes needed
response = agent.chat(
    session_id=session_id,
    user_message="What are the zoning requirements?",
    top_k=12
)

print(response['assistant'])
```

### Option 2: Tool-Based Mode (New)

```python
from vector.agent import ResearchAgent

# Create agent with PydanticAI enabled
agent = ResearchAgent(use_pydantic_ai=True)

# Start chat session
session_id = agent.start_chat()

# Chat with tool use enabled
response = agent.chat(
    session_id=session_id,
    user_message="What are the zoning requirements?",
    use_tools=True  # Enable PydanticAI agent
)

# Response includes tool call information
print(response['assistant'])
print(f"Agent type: {response['agent_type']}")  # 'pydantic_ai'
```

### Option 3: Direct PydanticAI Agent Usage

```python
from vector.agent import PydanticResearchAgent, AgentDeps
from vector.config import Config
from vector.embedders.sentence_transformer import SentenceTransformerEmbedder
from vector.stores.factory import create_store
from vector.search.service import SearchService
from vector.ai.factory import AIModelFactory

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

# Use with async
import asyncio

async def main():
    from vector.agent import ChatSession
    
    session = ChatSession(
        id="test",
        system_prompt="You are a helpful assistant.",
        messages=[]
    )
    
    result = await agent.chat(
        session=session,
        user_message="What are the permit requirements?",
        max_tokens=800
    )
    
    print(result['assistant'])
    print(f"Tool calls: {len(result['tool_calls'])}")
    
asyncio.run(main())
```

## Available Tools

The agent now has access to these tools:

### 1. `retrieve_chunks`
Performs full retrieval pipeline (expansion + search)

```python
from vector.agent.tools import retrieve_chunks

bundle = await retrieve_chunks(
    ctx=context,
    session=session,
    user_message="search query",
    top_k=12,
    window=2
)
```

### 2. `expand_query`
Expands query into keyphrases using conversation context

```python
result = await expand_query(
    ctx=context,
    session=session,
    user_message="zoning rules"
)
# Returns: {"expanded_query": "...", "keyphrases": [...]}
```

### 3. `search_documents`
Direct vector search without expansion

```python
results = await search_documents(
    ctx=context,
    query="specific search terms",
    top_k=12
)
```

### 4. `get_chunk_window`
Get surrounding chunks for context

```python
result = await get_chunk_window(
    ctx=context,
    chunk_id="doc_123_chunk_5",
    window=2  # 2 chunks before and after
)
```

### 5. `get_document_metadata`
Get document-level information

```python
result = await get_document_metadata(
    ctx=context,
    document_id="doc_123"
)
```

### 6. `list_available_documents`
List all documents in the collection

```python
result = await list_available_documents(
    ctx=context,
    limit=100
)
```

## MCP Server Integration

Expose Vector agent capabilities via Model Context Protocol:

### Setup

1. **Standalone Server**:
```bash
python -m vector.agent.mcp_server
```

2. **Claude Desktop Integration**:

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (Mac) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "vector": {
      "command": "python",
      "args": ["-m", "vector.agent.mcp_server"],
      "env": {
        "OPENAI_API_KEY": "your-key-here"
      }
    }
  }
}
```

3. **Programmatic Usage**:
```python
from vector.agent import create_mcp_server

server = create_mcp_server()
if server:
    import asyncio
    asyncio.run(server.run())
```

## Multi-Agent Patterns

### Specialized Agents

```python
from vector.agent import SearchAgent, AnswerAgent, AgentDeps

# Create specialized agents
search_agent = SearchAgent(deps)
answer_agent = AnswerAgent(deps)

# Use independently
expansion = await search_agent.expand_query_with_context(
    session=session,
    user_message="permits"
)

answer = await answer_agent.generate_answer(
    session=session,
    user_message="What are the permit requirements?",
    max_tokens=500
)
```

### Custom Workflows

```python
# Structured retrieve-then-answer
result = await pydantic_agent.retrieve_and_answer(
    session=session,
    user_message="zoning question",
    top_k=15,
    window=2
)

# Tool-assisted chat (agent decides when to use tools)
result = await pydantic_agent.chat(
    session=session,
    user_message="complex question",
    max_tokens=800
)
```

## Migration Checklist

- [x] Install `pydantic-ai[openai]` and `httpx`
- [x] Update `requirements.txt` and `pyproject.toml`
- [x] Test existing code (should work unchanged)
- [ ] Gradually enable `use_tools=True` in chat calls
- [ ] Set up MCP server for external integrations
- [ ] Monitor token usage with new observability features
- [ ] Experiment with specialized agents for complex workflows

## Benefits

### Before (Classic)
- ✅ Simple retrieval pipeline
- ✅ Predictable behavior
- ❌ No tool use
- ❌ Limited observability
- ❌ No agent composition

### After (PydanticAI)
- ✅ All classic features still available
- ✅ Tool-based architecture
- ✅ Full observability (all tool calls tracked)
- ✅ Multi-agent composition
- ✅ MCP server integration
- ✅ Structured outputs
- ✅ Type-safe tool schemas

## Configuration

Control PydanticAI behavior:

```python
# Disable PydanticAI (use classic mode only)
agent = ResearchAgent(use_pydantic_ai=False)

# Enable but use classic by default
agent = ResearchAgent(use_pydantic_ai=True)
response = agent.chat(session_id, message)  # Classic mode

# Enable and use tools explicitly
response = agent.chat(session_id, message, use_tools=True)  # PydanticAI mode
```

## Troubleshooting

### Import Errors
```python
# If you see: ImportError: cannot import name 'Agent' from 'pydantic_ai'
pip install pydantic-ai[openai]
```

### Async Issues
```python
# PydanticAI is async-first. Use asyncio.run() in sync contexts:
import asyncio
result = asyncio.run(agent.chat(...))
```

### Tool Execution Errors
Check dependencies are properly injected in `AgentDeps`:
```python
deps = AgentDeps(
    search_service=search_service,  # Required
    config=config,                   # Required
    search_model=search_model,       # Optional but recommended
    answer_model=answer_model        # Optional but recommended
)
```

## Next Steps

1. **Read the docs**: Check `vector/agent/docs/` for detailed architecture
2. **Try examples**: Run example scripts to see PydanticAI in action
3. **Experiment with tools**: Create custom tools for your use case
4. **Set up MCP**: Integrate with Claude Desktop or other MCP clients
5. **Monitor usage**: Use the enhanced metrics to optimize performance

## Support

For issues or questions:
- Check `vector/agent/docs/ARCHITECTURE.md`
- Review tool definitions in `vector/agent/tools.py`
- See agent implementations in `vector/agent/agents.py`
