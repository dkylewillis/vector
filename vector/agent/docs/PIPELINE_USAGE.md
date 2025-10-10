# Pipeline Usage Guide

The retrieval pipeline is a simple, pluggable architecture that allows you to easily add, remove, or reorder processing steps.

## Basic Usage

The `Retriever` uses a default pipeline automatically:

```python
from vector.agent import Retriever

# Standard retrieval (uses default pipeline)
bundle, metrics = retriever.retrieve(
    session=session,
    user_message="What is machine learning?",
    top_k=12,
    search_type="both",
    window=2
)
```

## Default Pipeline Steps

1. **QueryExpansionStep** - Expands query using AI model and conversation history
2. **SearchStep** - Performs vector similarity search
3. **ScoreFilter** - (Optional) Filters results by minimum score
4. **DiagnosticsStep** - Adds metadata about results

## Adding Score Filtering

```python
# Add score filtering to default pipeline
bundle, metrics = retriever.retrieve(
    session=session,
    user_message="What is machine learning?",
    min_score=0.4  # Only return results with score >= 0.4
)
```

## Custom Pipeline

Create your own pipeline with custom steps:

```python
from vector.agent import Pipeline, QueryExpansionStep, SearchStep, ScoreFilter, DiagnosticsStep

# Build custom pipeline
custom_pipeline = Pipeline()
custom_pipeline.add_step(QueryExpansionStep(search_model))
custom_pipeline.add_step(SearchStep(search_service, top_k=20))
custom_pipeline.add_step(ScoreFilter(min_score=0.5))
custom_pipeline.add_step(DiagnosticsStep())

# Use custom pipeline
bundle, metrics = retriever.retrieve(
    session=session,
    user_message="What is machine learning?",
    custom_pipeline=custom_pipeline
)
```

## Creating Custom Steps

Create a new step by inheriting from `PipelineStep`:

```python
from vector.agent import PipelineStep, RetrievalContext

class DiversityReranker(PipelineStep):
    """Reranks results to promote document diversity."""
    
    def __init__(self, diversity_weight: float = 0.3):
        self.diversity_weight = diversity_weight
    
    def __call__(self, context: RetrievalContext) -> RetrievalContext:
        """Rerank results."""
        # Track document frequency
        doc_counts = {}
        reranked = []
        
        for result in sorted(context.results, key=lambda r: r.score, reverse=True):
            doc_id = result.doc_id
            doc_counts[doc_id] = doc_counts.get(doc_id, 0) + 1
            
            # Apply diversity penalty
            diversity_penalty = doc_counts[doc_id] * self.diversity_weight
            adjusted_score = result.score * (1 - diversity_penalty)
            
            reranked.append((result, adjusted_score))
        
        # Sort by adjusted score
        reranked.sort(key=lambda x: x[1], reverse=True)
        context.results = [r for r, _ in reranked]
        
        context.add_metadata("reranked_for_diversity", True)
        return context
```

Then use it in a pipeline:

```python
pipeline = Pipeline()
pipeline.add_step(QueryExpansionStep(search_model))
pipeline.add_step(SearchStep(search_service, top_k=20))
pipeline.add_step(DiversityReranker(diversity_weight=0.2))  # Your custom step!
pipeline.add_step(DiagnosticsStep())

bundle, metrics = retriever.retrieve(
    session=session,
    user_message="What is machine learning?",
    custom_pipeline=pipeline
)
```

## Pipeline Context

The `RetrievalContext` object flows through all steps and contains:

- **session** - Chat session with conversation history
- **user_message** - Original user message
- **query** - Current query (can be modified by steps)
- **results** - List of RetrievalResult objects
- **metadata** - Dictionary for storing step metadata
- **usage_metrics** - List of UsageMetrics from AI operations

Steps can modify any of these fields and add metadata:

```python
def __call__(self, context: RetrievalContext) -> RetrievalContext:
    # Modify query
    context.query = "expanded: " + context.query
    
    # Filter results
    context.results = [r for r in context.results if r.score > 0.5]
    
    # Add metadata
    context.add_metadata("my_step_ran", True)
    context.add_metadata("filtered_count", 10)
    
    # Track AI usage
    context.add_usage(UsageMetrics(...))
    
    return context
```

## Examples of Future Steps

Here are ideas for additional steps you could add:

- **HybridSearchStep** - Combine keyword + vector search
- **CrossEncoderReranker** - Use a reranking model for better relevance
- **CacheStep** - Cache results for repeated queries
- **TemporalFilter** - Filter by document date
- **TypeBalancer** - Ensure minimum representation of each result type
- **SummaryEnricher** - Add document summaries to context
- **CitationLinker** - Add citation relationships between documents

## Benefits

✅ **Easy to understand** - Just a sequence of callable steps  
✅ **Easy to extend** - Create a class with `__call__`  
✅ **Easy to test** - Test each step independently  
✅ **Easy to configure** - Pass parameters to constructors  
✅ **Easy to experiment** - Create different pipelines for A/B testing  
✅ **Minimal code** - ~150 lines for entire framework  
