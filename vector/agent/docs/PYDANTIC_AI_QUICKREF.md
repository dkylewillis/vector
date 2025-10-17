# PydanticAI Quick Reference

## Import Patterns

```python
# Classic API (backward compatible)
from vector.agent import ResearchAgent, ChatSession

# PydanticAI agents
from vector.agent import (
    PydanticResearchAgent,
    SearchAgent,
    AnswerAgent,
    AgentDeps
)

# Tools
from vector.agent.tools import (
    retrieve_chunks,
    expand_query,
    search_documents,
    get_chunk_window,
    get_document_metadata
)

# MCP Server
from vector.agent import create_mcp_server, MCP_AVAILABLE
```

## Common Workflows

### 1. Simple Chat (Classic Mode)
```python
agent = ResearchAgent()
session_id = agent.start_chat()
response = agent.chat(session_id, "What are the zoning rules?")
```

### 2. Tool-Enabled Chat
```python
agent = ResearchAgent(use_pydantic_ai=True)
session_id = agent.start_chat()
response = agent.chat(
    session_id,
    "What are the zoning rules?",
    use_tools=True  # Agent can use all tools
)
```

### 3. Direct PydanticAI Usage
```python
from vector.agent import PydanticResearchAgent, AgentDeps
import asyncio

# Setup deps (see migration guide)
deps = AgentDeps(...)
agent = PydanticResearchAgent(deps)

async def query():
    result = await agent.chat(session, "question")
    return result

asyncio.run(query())
```

### 4. Custom Tool Workflow
```python
from vector.agent.tools import expand_query, search_documents
import asyncio

async def custom_search(ctx, session, query):
    # Expand query
    expansion = await expand_query(ctx, session, query)
    
    # Search with expanded query
    results = await search_documents(
        ctx,
        query=expansion['expanded_query'],
        top_k=20
    )
    
    return results
```

### 5. MCP Server
```bash
# Run standalone
python -m vector.agent.mcp_server

# Or programmatically
python -c "
from vector.agent import create_mcp_server
import asyncio

server = create_mcp_server()
asyncio.run(server.run())
"
```

## Tool Signatures

```python
# retrieve_chunks: Full pipeline
await retrieve_chunks(
    ctx: RunContext[AgentDeps],
    session: ChatSession,
    user_message: str,
    top_k: int = 12,
    document_ids: Optional[List[str]] = None,
    window: int = 0,
    min_score: Optional[float] = None
) -> RetrievalBundle

# expand_query: Query expansion
await expand_query(
    ctx: RunContext[AgentDeps],
    session: ChatSession,
    user_message: str
) -> dict  # {expanded_query, keyphrases, expanded}

# search_documents: Direct search
await search_documents(
    ctx: RunContext[AgentDeps],
    query: str,
    top_k: int = 12,
    document_ids: Optional[List[str]] = None,
    window: int = 0
) -> List[RetrievalResult]

# get_chunk_window: Context expansion
await get_chunk_window(
    ctx: RunContext[AgentDeps],
    chunk_id: str,
    window: int = 2
) -> dict  # {chunks, success, error?}

# get_document_metadata: Doc info
await get_document_metadata(
    ctx: RunContext[AgentDeps],
    document_id: str
) -> dict  # {filename, type, metadata, success}
```

## Agent Methods

```python
# ResearchAgent (main agent with backward compatibility)
agent = ResearchAgent(
    config=None,
    chunks_collection="chunks",
    use_pydantic_ai=True  # Enable PydanticAI
)

# Chat method
response = agent.chat(
    session_id: str,
    user_message: str,
    response_length: str = 'medium',  # short/medium/long
    top_k: int = 12,
    document_ids: Optional[List[str]] = None,
    window: int = 0,
    use_tools: bool = False  # Enable PydanticAI agent
) -> Dict[str, Any]

# PydanticResearchAgent (pure PydanticAI)
agent = PydanticResearchAgent(deps)

# Full tool-assisted chat
await agent.chat(
    session: ChatSession,
    user_message: str,
    max_tokens: int = 800,
    top_k: int = 12,
    document_ids: Optional[List[str]] = None,
    window: int = 0
) -> Dict[str, Any]

# Structured retrieve-then-answer
await agent.retrieve_and_answer(
    session: ChatSession,
    user_message: str,
    max_tokens: int = 800,
    top_k: int = 12,
    document_ids: Optional[List[str]] = None,
    window: int = 0
) -> Dict[str, Any]

# SearchAgent (specialized for query expansion)
search_agent = SearchAgent(deps)
expansion = await search_agent.expand_query_with_context(
    session: ChatSession,
    user_message: str
) -> QueryExpansionResult

# AnswerAgent (specialized for answer generation)
answer_agent = AnswerAgent(deps)
answer = await answer_agent.generate_answer(
    session: ChatSession,
    user_message: str,
    max_tokens: int = 800
) -> AnswerResult
```

## Response Format

### Classic Mode
```python
{
    "session_id": "uuid",
    "assistant": "response text",
    "results": [...],  # RetrievalResult objects
    "retrieval": {...},  # RetrievalBundle
    "message_count": 10,
    "summary_present": False,
    "usage_metrics": {
        "total_tokens": 1234,
        "total_prompt_tokens": 800,
        "total_completion_tokens": 434,
        "operations": [...]  # Breakdown by operation
    },
    "agent_type": "classic"
}
```

### PydanticAI Mode
```python
{
    "session_id": "uuid",
    "assistant": "response text",
    "results": [...],
    "retrieval": {...},
    "expansion": {...},  # Query expansion details
    "message_count": 10,
    "summary_present": False,
    "usage_metrics": {...},
    "agent_type": "pydantic_ai",
    "tool_calls": [  # NEW: Full tool trace
        {
            "tool": "search_documents",
            "args": {"query": "...", "top_k": 12},
            "result": [...]
        }
    ]
}
```

## Configuration

```python
# Environment variables
OPENAI_API_KEY=your-key

# Config object
from vector.config import Config
config = Config()
config.ai_search_model_name = "gpt-3.5-turbo"
config.ai_answer_model_name = "gpt-4"

# AgentDeps
deps = AgentDeps(
    search_service=search_service,
    config=config,
    search_model=search_model,
    answer_model=answer_model,
    chunks_collection="chunks"
)
```

## Testing

```python
# Test classic mode
def test_classic():
    agent = ResearchAgent()
    session_id = agent.start_chat()
    response = agent.chat(session_id, "test")
    assert response['agent_type'] == 'classic'

# Test PydanticAI mode
def test_pydantic_ai():
    agent = ResearchAgent(use_pydantic_ai=True)
    session_id = agent.start_chat()
    response = agent.chat(session_id, "test", use_tools=True)
    assert response['agent_type'] == 'pydantic_ai'
    assert 'tool_calls' in response

# Test async PydanticAI agent
async def test_pydantic_agent():
    deps = AgentDeps(...)
    agent = PydanticResearchAgent(deps)
    session = ChatSession(id="test", system_prompt="", messages=[])
    result = await agent.chat(session, "test")
    assert 'assistant' in result
```

## CLI Usage

```bash
# Classic agent CLI (unchanged)
vector-agent chat

# MCP server
python -m vector.agent.mcp_server

# Or add to package scripts
# Already configured in pyproject.toml
```

## Troubleshooting

```python
# Check PydanticAI availability
from vector.agent import MCP_AVAILABLE
print(f"MCP Available: {MCP_AVAILABLE}")

# Check agent mode
agent = ResearchAgent()
print(f"PydanticAI enabled: {agent.use_pydantic_ai}")
print(f"PydanticAI agent: {agent.pydantic_agent is not None}")

# Force classic mode
agent = ResearchAgent(use_pydantic_ai=False)
response = agent.chat(session_id, message)  # Always classic

# Debug tool calls
response = agent.chat(session_id, message, use_tools=True)
print(f"Tool calls: {len(response.get('tool_calls', []))}")
for call in response.get('tool_calls', []):
    print(f"  Tool: {call['tool']}")
    print(f"  Args: {call['args']}")
```

## Best Practices

1. **Start with classic mode**: Test your queries work before enabling tools
2. **Enable tools selectively**: Use `use_tools=True` when you need dynamic retrieval
3. **Monitor token usage**: PydanticAI provides detailed breakdowns
4. **Use async for performance**: Direct PydanticAI usage is fully async
5. **Compose agents**: Use specialized agents for complex workflows
6. **Set up MCP**: Expose capabilities to other AI applications

## Examples

See `vector/agent/docs/example_pipeline.py` for complete working examples.
