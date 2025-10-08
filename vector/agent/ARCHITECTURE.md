# Research Agent Architecture

## Overview
The Research Agent has been refactored into a modular, testable architecture with clear separation of concerns.

## Module Structure

### `models.py` - Data Models
Pure Pydantic data models with no business logic:
- **ChatMessage**: Individual message with role and content
- **ChatSession**: Session with message history and optional summary
- **RetrievalResult**: Single search result with provenance
- **RetrievalBundle**: Complete retrieval operation with diagnostics

### `prompting.py` - Prompt Construction
Pure functions for building prompts (easily testable):
- `build_system_prompt()`: Default system prompt
- `build_expansion_prompt(history, message)`: Query expansion prompt
- `build_answer_prompt(session, message, retrieval)`: Final answer generation prompt
- `render_recent_messages(session, limit)`: Format conversation history
- `format_results_for_display(results)`: User-friendly result formatting

### `memory.py` - Conversation Memory
Policies for managing conversation history:
- **LLM Protocol**: Interface for language models
- **SummarizerPolicy**: Compacts history when it exceeds threshold
- **NoSummarizerPolicy**: No-op policy for testing or unlimited history

### `retrieval.py` - Search Orchestration
Handles retrieval with query expansion:
- **LLM Protocol**: Interface for language models
- **SearchBackend Protocol**: Interface for search implementations
- **Retriever**: Orchestrates query expansion and search with diagnostics

### `adapters.py` - Service Adapters
Adapts existing services to new protocols:
- **LLMAdapter**: Wraps AI models to match LLM protocol
- **SearchBackendAdapter**: Wraps SearchService to match SearchBackend protocol

### `agent.py` - Main Agent
Coordinates all components:
- **ResearchAgent**: Main entry point, manages sessions and orchestrates workflow

## Key Design Principles

### 1. **Dependency Injection**
All dependencies (embedder, vector store, LLM clients) are injectable:
```python
agent = ResearchAgent(
    config=custom_config,
    chunks_collection="custom_chunks",
    artifacts_collection="custom_artifacts"
)
```

### 2. **Protocol-Based Design**
Uses Python protocols instead of concrete types for maximum flexibility:
```python
class LLM(Protocol):
    def generate_response(self, prompt: str, ...) -> str: ...

class SearchBackend(Protocol):
    def search(self, query: str, ...) -> List[RetrievalResult]: ...
```

### 3. **Pure Functions**
Prompt building is pure and easily testable:
```python
# No side effects, easy to test
prompt = build_answer_prompt(session, message, retrieval)
```

### 4. **Structured Output**
All operations return structured data with diagnostics:
```python
retrieval = {
    "original_query": "...",
    "expanded_query": "...",
    "keyphrases": [...],
    "results": [...],
    "diagnostics": {
        "latency_ms": 45.2,
        "result_count": 12,
        "results_by_type": {"chunk": 8, "artifact": 4}
    }
}
```

### 5. **Graceful Degradation**
Query expansion failure doesn't break retrieval:
```python
try:
    expanded_query, keyphrases = self.expand_query(...)
except Exception:
    # Fallback to original query
    return user_message, []
```

## Workflow

```
User Message
    ↓
Add to Session
    ↓
Retriever.retrieve()
    ├─ expand_query() (optional, with search LLM)
    ├─ search_backend.search()
    └─ Return RetrievalBundle with diagnostics
    ↓
Build Answer Prompt (pure function)
    ↓
Generate Response (answer LLM)
    ↓
Add to Session
    ↓
SummarizerPolicy.compact() (if needed)
    ↓
Return Response Dict
```

## Testing Strategy

### Unit Tests
- **Prompting**: Test prompt templates with mock data
- **Memory**: Test summarization triggers and compaction
- **Retrieval**: Test query expansion and fallback
- **Adapters**: Test protocol compliance

### Integration Tests
- **End-to-End**: Full chat flow with mock LLMs and search
- **Error Handling**: Network failures, empty results, invalid inputs

### Example Test
```python
def test_query_expansion_fallback():
    """Query expansion failure should fall back to original query."""
    failing_llm = Mock(side_effect=Exception("LLM error"))
    backend = Mock(return_value=[...])
    retriever = Retriever(failing_llm, backend)
    
    result = retriever.retrieve(session, "test query", top_k=10)
    
    assert result.expanded_query == "test query"
    assert result.keyphrases == []
    backend.search.assert_called_with("test query", ...)
```

## Benefits

1. **Testability**: Pure functions and protocols enable comprehensive testing
2. **Flexibility**: Easy to swap implementations (different LLMs, search backends)
3. **Observability**: Structured diagnostics for debugging and monitoring
4. **Maintainability**: Clear boundaries between modules
5. **Resilience**: Graceful fallbacks for non-critical failures
6. **Performance**: Can optimize individual components independently

## Migration Notes

### Breaking Changes
- Removed `format_results()` method (use `retrieval.results` directly or `format_results_for_display()`)
- ChatSession now uses Pydantic models exclusively

### Compatible Changes
- `start_chat()`, `chat()`, `end_chat()` maintain same signatures
- Response format includes new `retrieval` field with diagnostics
- Session management remains unchanged

## Future Enhancements

1. **Token Budget Management**: Truncate context by relevance ranking
2. **Streaming Support**: Yield response chunks for real-time display
3. **Caching**: Cache expansion queries for identical inputs
4. **Dynamic System Prompts**: Per-session prompt editing
5. **Result Reranking**: Post-search reranking with cross-encoder
