# Pipeline Implementation Summary

## What Was Added

A simple, pluggable pipeline architecture for retrieval operations that makes it easy to add, remove, or reorder processing steps.

## New Files

### `vector/agent/pipeline.py` (~120 lines)
- **`RetrievalContext`** - Shared state passed through pipeline steps
- **`PipelineStep`** - Abstract base class for steps (just needs `__call__` method)
- **`Pipeline`** - Executes steps in sequence

### `vector/agent/steps.py` (~200 lines)
Concrete pipeline steps:
- **`QueryExpansionStep`** - Expands query using AI model and conversation history
- **`SearchStep`** - Performs vector similarity search
- **`ScoreFilter`** - Filters results by minimum score threshold
- **`DiagnosticsStep`** - Adds diagnostic metadata about results

### `vector/agent/PIPELINE_USAGE.md`
Complete usage guide with examples

### `vector/agent/example_pipeline.py`
Working examples of custom steps and pipelines

## Changes to Existing Files

### `vector/agent/retrieval.py`
**Removed:**
- `expand_query()` method (now `QueryExpansionStep`)
- Inline search logic (now `SearchStep`)
- `_convert_result()` helper (moved to `SearchStep`)

**Added:**
- `_build_pipeline()` - Builds default pipeline
- `custom_pipeline` parameter to `retrieve()` - Allows custom pipelines
- `min_score` parameter to `retrieve()` - Enables score filtering

**Result:** More modular, easier to extend

### `vector/agent/__init__.py`
Added exports for pipeline components

## How It Works

```
User Query
    ↓
RetrievalContext (session, user_message, query)
    ↓
QueryExpansionStep → Updates context.query
    ↓
SearchStep → Populates context.results
    ↓
ScoreFilter (optional) → Filters context.results
    ↓
DiagnosticsStep → Adds context.metadata
    ↓
RetrievalBundle (from context)
```

## Key Benefits

1. **Simple** - Just ~150 lines of framework code
2. **Clear** - Easy to understand the flow
3. **Flexible** - Add/remove/reorder steps easily
4. **Testable** - Test each step independently
5. **Extensible** - Create custom steps in minutes
6. **Backward Compatible** - Existing code still works

## Usage Comparison

### Before (Hard-coded)
```python
# Fixed pipeline, hard to customize
bundle, metrics = retriever.retrieve(session, message)
```

### After (With Default Pipeline)
```python
# Same as before, but now extensible
bundle, metrics = retriever.retrieve(session, message)

# Optional: Add score filtering
bundle, metrics = retriever.retrieve(session, message, min_score=0.4)
```

### After (With Custom Pipeline)
```python
# Full control over processing
pipeline = Pipeline()
pipeline.add_step(QueryExpansionStep(model))
pipeline.add_step(SearchStep(service, top_k=20))
pipeline.add_step(MyCustomStep())  # Your custom step!
pipeline.add_step(DiagnosticsStep())

bundle, metrics = retriever.retrieve(
    session, message, 
    custom_pipeline=pipeline
)
```

## Creating Custom Steps

Just inherit from `PipelineStep` and implement `__call__`:

```python
from vector.agent import PipelineStep, RetrievalContext

class MyCustomStep(PipelineStep):
    def __init__(self, my_param: str = "default"):
        self.my_param = my_param
    
    def __call__(self, context: RetrievalContext) -> RetrievalContext:
        # Modify context as needed
        context.add_metadata("my_step_ran", True)
        return context
```

## Future Step Ideas

- **HybridSearchStep** - Combine keyword + vector search
- **CrossEncoderReranker** - Use reranking model
- **CacheStep** - Cache repeated queries
- **TemporalFilter** - Filter by date
- **TypeBalancer** - Balance result types
- **DiversityReranker** - Promote document diversity
- **SummaryEnricher** - Add summaries to context

## Testing

Each step can be tested independently:

```python
def test_score_filter():
    # Create mock context with results
    context = RetrievalContext(
        session=mock_session,
        user_message="test",
        query="test",
        results=[
            RetrievalResult(..., score=0.8),
            RetrievalResult(..., score=0.3),
        ]
    )
    
    # Run step
    step = ScoreFilter(min_score=0.5)
    context = step(context)
    
    # Verify
    assert len(context.results) == 1
    assert context.results[0].score == 0.8
```

## Performance

- **Minimal overhead** - Just function calls
- **No magic** - Clear execution flow
- **Same performance** as before for default pipeline
- **Better maintainability** through modular design
