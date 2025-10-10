# Pipeline Quick Reference

## 🚀 Quick Start

```python
from vector.agent import Retriever

# Use default pipeline (automatic)
bundle, metrics = retriever.retrieve(session, message)
```

## 📋 Common Patterns

### Add Score Filtering
```python
bundle, metrics = retriever.retrieve(
    session, message,
    min_score=0.4  # Only results with score >= 0.4
)
```

### Custom Pipeline
```python
from vector.agent import Pipeline, QueryExpansionStep, SearchStep

pipeline = Pipeline()
pipeline.add_step(QueryExpansionStep(model))
pipeline.add_step(SearchStep(service, top_k=20))

bundle, metrics = retriever.retrieve(
    session, message,
    custom_pipeline=pipeline
)
```

## 🔧 Built-in Steps

| Step | Purpose | Parameters |
|------|---------|------------|
| `QueryExpansionStep` | Expand query using AI | `ai_model` |
| `SearchStep` | Vector similarity search | `search_service`, `top_k`, `search_type`, `window` |
| `ScoreFilter` | Filter by minimum score | `min_score` |
| `DiagnosticsStep` | Add result metadata | None |

## ✨ Create Custom Step

```python
from vector.agent import PipelineStep, RetrievalContext

class MyStep(PipelineStep):
    def __init__(self, my_param="default"):
        self.my_param = my_param
    
    def __call__(self, context: RetrievalContext) -> RetrievalContext:
        # Modify context
        context.add_metadata("my_key", "my_value")
        return context
```

## 📦 RetrievalContext

```python
context.session         # ChatSession with history
context.user_message    # Original user message
context.query          # Current query (modifiable)
context.results        # List[RetrievalResult]
context.metadata       # Dict[str, Any]
context.usage_metrics  # List[UsageMetrics]

# Helper methods
context.add_metadata(key, value)
context.add_usage(metrics)
```

## 🎯 Common Use Cases

### Diversity Reranking
```python
class DiversityReranker(PipelineStep):
    def __call__(self, context):
        # Penalize repeated documents
        # Return context with reranked results
```

### Type Balancing
```python
class TypeBalancer(PipelineStep):
    def __call__(self, context):
        # Ensure minimum results per type
        # Return context with balanced results
```

### Result Caching
```python
class CacheStep(PipelineStep):
    def __call__(self, context):
        # Check cache, return if hit
        # Otherwise continue pipeline
```

## 📚 Documentation

- **[PIPELINE_USAGE.md](PIPELINE_USAGE.md)** - Comprehensive usage guide
- **[PIPELINE_SUMMARY.md](PIPELINE_SUMMARY.md)** - Implementation details
- **[PIPELINE_DIAGRAM.md](PIPELINE_DIAGRAM.md)** - Visual architecture
- **[example_pipeline.py](example_pipeline.py)** - Working examples

## ⚡ Performance

- **Minimal overhead** - Just function calls
- **Same speed** as original implementation
- **Easy to profile** - Test each step individually
- **Modular testing** - Unit test each step

## 🎨 Builder Pattern

```python
pipeline = (
    Pipeline()
    .add_step(QueryExpansionStep(model))
    .add_step(SearchStep(service, top_k=20))
    .add_step(ScoreFilter(0.5))
    .add_step(DiagnosticsStep())
)
```

## 🔍 Debugging

```python
# Each step can add metadata
class DebugStep(PipelineStep):
    def __call__(self, context):
        print(f"Query: {context.query}")
        print(f"Results: {len(context.results)}")
        context.add_metadata("debug_checkpoint", True)
        return context
```

## ✅ Testing

```python
def test_score_filter():
    context = RetrievalContext(
        session=mock_session,
        user_message="test",
        query="test",
        results=[
            RetrievalResult(..., score=0.8),
            RetrievalResult(..., score=0.3),
        ]
    )
    
    step = ScoreFilter(min_score=0.5)
    context = step(context)
    
    assert len(context.results) == 1
    assert context.results[0].score == 0.8
```
