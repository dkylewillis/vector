# Research Agent Architecture

## Overview
The Research Agent uses a modular, pipeline-based architecture with clear separation of concerns. The retrieval system is built on a pluggable pipeline pattern that makes it easy to add, remove, or reorder processing steps.

## Module Structure

### `models.py` - Data Models
Pure Pydantic data models with no business logic:
- **ChatMessage**: Individual message with role and content
- **ChatSession**: Session with message history and optional summary
- **RetrievalResult**: Single search result with provenance
- **RetrievalBundle**: Complete retrieval operation with diagnostics
- **UsageMetrics**: Token usage and performance metrics from AI operations
- **AggregatedUsageMetrics**: Combined metrics with breakdown by operation

### `prompting.py` - Prompt Construction
Pure functions for building prompts (easily testable):
- `build_system_prompt()`: Default system prompt
- `build_expansion_prompt(history, message)`: Query expansion prompt
- `build_answer_prompt(session, message, retrieval)`: Final answer generation prompt
- `render_recent_messages(session, limit)`: Format conversation history

### `memory.py` - Conversation Memory
Policies for managing conversation history:
- **SummarizerPolicy**: Compacts history when it exceeds threshold
- **NoSummarizerPolicy**: No-op policy for testing or unlimited history

### `pipeline.py` - Retrieval Pipeline Framework
Simple, pluggable pipeline architecture (~120 lines):
- **RetrievalContext**: Shared state container passed through pipeline steps
- **PipelineStep**: Abstract base class for pipeline steps (just needs `__call__`)
- **Pipeline**: Sequential step executor with error handling

### `steps.py` - Pipeline Steps
Concrete retrieval pipeline steps (~200 lines):
- **QueryExpansionStep**: Expands query using AI model and conversation history
- **SearchStep**: Performs vector similarity search
- **ScoreFilter**: Filters results by minimum score threshold
- **DiagnosticsStep**: Adds result metadata and diagnostics

### `retrieval.py` - Search Orchestration
Pipeline-based retrieval orchestration:
- **Retriever**: Builds and executes retrieval pipelines with configurable steps

### `agent.py` - Main Agent
Coordinates all components:
- **ResearchAgent**: Main entry point, manages sessions and orchestrates workflow

## Key Design Principles

### 1. **Pluggable Pipeline Architecture**
Retrieval uses a simple pipeline pattern for maximum flexibility:
```python
# Default pipeline
retrieval, metrics = retriever.retrieve(session, message)

# Custom pipeline
pipeline = Pipeline()
pipeline.add_step(QueryExpansionStep(model))
pipeline.add_step(SearchStep(service, top_k=20))
pipeline.add_step(ScoreFilter(min_score=0.5))
pipeline.add_step(DiagnosticsStep())

retrieval, metrics = retriever.retrieve(session, message, custom_pipeline=pipeline)
```

### 2. **Dependency Injection**
All dependencies (embedder, vector store, LLM clients) are injectable:
```python
agent = ResearchAgent(
    config=custom_config,
    chunks_collection="custom_chunks",
    artifacts_collection="custom_artifacts"
)
```

### 3. **Pure Functions**
Prompt building is pure and easily testable:
```python
# No side effects, easy to test
prompt = build_answer_prompt(session, message, retrieval)
```

### 4. **Structured Output with Metrics**
All operations return structured data with comprehensive metrics:
```python
response = {
    "session_id": "...",
    "assistant": "...",
    "results": [...],
    "retrieval": {
        "original_query": "...",
        "expanded_query": "...",
        "keyphrases": [...],
        "results": [...],
        "diagnostics": {
            "latency_ms": 45.2,
            "result_count": 12,
            "search_type": "both",
            "window": 2,
            "results_by_type": {"chunk": 8, "table": 4}
        }
    },
    "usage_metrics": {
        "total_prompt_tokens": 1234,
        "total_completion_tokens": 567,
        "total_tokens": 1801,
        "total_latency_ms": 2345.67,
        "breakdown": [
            {"operation": "search", "model_name": "gpt-4o-mini", ...},
            {"operation": "answer", "model_name": "gpt-4o-mini", ...}
        ]
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
    context.add_metadata("query_expanded", False)
    return context  # Pipeline continues
```

### 6. **Easy Extensibility**
Adding new pipeline steps is simple:
```python
class DiversityReranker(PipelineStep):
    def __call__(self, context: RetrievalContext) -> RetrievalContext:
        # Rerank results to promote diversity
        context.results = self._rerank(context.results)
        context.add_metadata("reranked_for_diversity", True)
        return context

# Use it
pipeline.add_step(DiversityReranker(weight=0.3))
```

## Workflow

```
User Message
    ↓
Add to Session
    ↓
Retriever.retrieve() → Pipeline Execution
    ↓
┌─────────────────────────────────┐
│   Retrieval Pipeline            │
│                                 │
│  RetrievalContext               │
│  (session, query, results, ...) │
│         ↓                       │
│  QueryExpansionStep             │
│  → Expand query with AI         │
│  → Update context.query         │
│         ↓                       │
│  SearchStep                     │
│  → Vector similarity search     │
│  → Populate context.results     │
│         ↓                       │
│  ScoreFilter (optional)         │
│  → Filter by min_score          │
│         ↓                       │
│  DiagnosticsStep                │
│  → Add metadata & metrics       │
│         ↓                       │
│  Return RetrievalBundle +       │
│  AggregatedUsageMetrics         │
└─────────────────────────────────┘
    ↓
Build Answer Prompt (pure function)
    ↓
Generate Response (answer LLM)
    ↓
Combine Metrics
    ├─ Search operation metrics
    └─ Answer operation metrics
    ↓
Add Response to Session
    ↓
SummarizerPolicy.compact() (if needed)
    ↓
Return Response Dict with Full Metrics
```

## Pipeline Architecture Details

### Pipeline Flow
1. **RetrievalContext** is created with initial state
2. Each **PipelineStep** processes context sequentially
3. Steps can:
   - Modify `context.query` (e.g., expand query)
   - Add/filter `context.results` (e.g., search, filter)
   - Add `context.metadata` (e.g., diagnostics)
   - Track `context.usage_metrics` (e.g., AI token usage)
4. Final **RetrievalBundle** and **AggregatedUsageMetrics** are returned

### Default Pipeline Steps
1. **QueryExpansionStep**: Uses AI model to expand query based on conversation history
2. **SearchStep**: Performs vector similarity search with configurable parameters
3. **ScoreFilter**: (Optional) Removes results below minimum score threshold
4. **DiagnosticsStep**: Adds metadata about result counts and types

### Custom Pipeline Example
```python
# Build custom pipeline with reranking and caching
pipeline = Pipeline()
pipeline.add_step(CacheCheckStep(cache_service))  # Check cache first
pipeline.add_step(QueryExpansionStep(model))
pipeline.add_step(SearchStep(service, top_k=20))
pipeline.add_step(CrossEncoderReranker(reranker_model))  # Rerank with better model
pipeline.add_step(ScoreFilter(min_score=0.4))
pipeline.add_step(TypeBalancer(min_per_type=2))  # Ensure type diversity
pipeline.add_step(DiagnosticsStep())
pipeline.add_step(CacheStoreStep(cache_service))  # Store in cache

retrieval, metrics = retriever.retrieve(session, message, custom_pipeline=pipeline)
```

## Testing Strategy

### Unit Tests
- **Prompting**: Test prompt templates with mock data
- **Memory**: Test summarization triggers and compaction
- **Pipeline Steps**: Test each step independently with mock contexts
- **Retrieval**: Test pipeline building and execution
- **Metrics**: Test aggregation and breakdown

### Integration Tests
- **End-to-End**: Full chat flow with mock LLMs and search
- **Custom Pipelines**: Test different pipeline configurations
- **Error Handling**: Network failures, empty results, invalid inputs

### Example Tests
```python
def test_score_filter_step():
    """ScoreFilter should remove results below threshold."""
    context = RetrievalContext(
        session=mock_session,
        user_message="test",
        query="test",
        results=[
            RetrievalResult(score=0.8, ...),
            RetrievalResult(score=0.3, ...),
            RetrievalResult(score=0.6, ...),
        ]
    )
    
    step = ScoreFilter(min_score=0.5)
    context = step(context)
    
    assert len(context.results) == 2
    assert all(r.score >= 0.5 for r in context.results)
    assert context.metadata["filtered_by_score"] == 1

def test_pipeline_execution_with_failure():
    """Pipeline should continue even if a step fails."""
    failing_step = Mock(side_effect=Exception("Step failed"))
    pipeline = Pipeline([failing_step, DiagnosticsStep()])
    
    context = RetrievalContext(mock_session, "test", "test")
    result = pipeline.run(context)
    
    # Pipeline continued despite failure
    assert "result_count" in result.metadata
    assert "FailingStep_error" in result.metadata

def test_metrics_aggregation():
    """Metrics should aggregate across pipeline steps."""
    context = RetrievalContext(mock_session, "test", "test")
    context.add_usage(UsageMetrics(
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150,
        operation="search"
    ))
    
    aggregated = AggregatedUsageMetrics.from_operations(context.usage_metrics)
    
    assert aggregated.total_tokens == 150
    assert len(aggregated.operations) == 1
    assert aggregated.operations[0].operation == "search"
```

## Benefits

1. **Testability**: Pure functions and isolated pipeline steps enable comprehensive testing
2. **Flexibility**: Easy to add/remove/reorder pipeline steps without touching core logic
3. **Observability**: Structured diagnostics and metrics for debugging and monitoring
4. **Maintainability**: Clear boundaries between modules, ~150 lines for pipeline framework
5. **Resilience**: Graceful fallbacks for non-critical failures in pipeline steps
6. **Performance**: Can optimize individual pipeline steps independently
7. **Extensibility**: Create custom steps in minutes, no need to modify existing code
8. **Transparency**: Full metrics breakdown shows token usage by operation (search, answer, etc.)

## Recent Improvements

### Pipeline Architecture (October 2025)
- ✅ Introduced pluggable pipeline pattern for retrieval
- ✅ Created `pipeline.py` with RetrievalContext, PipelineStep, and Pipeline classes
- ✅ Implemented concrete steps in `steps.py` (QueryExpansion, Search, ScoreFilter, Diagnostics)
- ✅ Refactored `retrieval.py` to use pipeline pattern
- ✅ Enables easy A/B testing of different retrieval strategies

### Metrics Enhancement (October 2025)
- ✅ Fixed metrics display in web interface
- ✅ Return `AggregatedUsageMetrics` from retriever with full breakdown
- ✅ Web UI now shows detailed token usage by operation (search vs answer)
- ✅ Includes model names and latency per operation

## Migration Notes

### Breaking Changes
- None for external API - `start_chat()`, `chat()`, `end_chat()` maintain same signatures

### New Features
- `retrieve()` accepts `custom_pipeline` parameter for advanced use cases
- `retrieve()` accepts `min_score` parameter for score-based filtering
- Response includes `usage_metrics` with full breakdown by operation

### Compatible Changes
- ChatSession uses Pydantic models exclusively
- Response format includes `retrieval.diagnostics` with search metadata
- Session management remains unchanged

## Future Enhancements

### Planned Pipeline Steps
1. **HybridSearchStep**: Combine keyword (BM25) + vector search
2. **CrossEncoderReranker**: Rerank results with more powerful reranking model
3. **CacheStep**: Cache query results for repeated queries
4. **TemporalFilter**: Filter by document date/time
5. **TypeBalancer**: Ensure minimum representation of each result type (chunks, tables, figures)
6. **DiversityReranker**: Promote document diversity in results
7. **SummaryEnricher**: Add document summaries to context
8. **CitationLinker**: Add citation relationships between documents

### Other Improvements
1. **Token Budget Management**: Truncate context by relevance ranking
2. **Streaming Support**: Yield response chunks for real-time display
3. **Dynamic System Prompts**: Per-session prompt editing
4. **Multi-Collection Search**: Search across multiple collections simultaneously
5. **Faceted Search**: Filter by metadata attributes

## Documentation

- **[PIPELINE_USAGE.md](PIPELINE_USAGE.md)**: Comprehensive pipeline usage guide
- **[PIPELINE_SUMMARY.md](PIPELINE_SUMMARY.md)**: Implementation details and benefits
- **[PIPELINE_DIAGRAM.md](PIPELINE_DIAGRAM.md)**: Visual architecture diagrams
- **[PIPELINE_QUICKREF.md](PIPELINE_QUICKREF.md)**: Quick reference card
- **[example_pipeline.py](example_pipeline.py)**: Working code examples
- **[METRICS_FIX.md](../../METRICS_FIX.md)**: Details on metrics display fix
