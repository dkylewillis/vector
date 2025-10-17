# Vector Retrieval Pipeline Guide

## Overview

The `vector.retrieval` module provides a clean, composable pipeline for RAG (Retrieval-Augmented Generation) operations, now separated from chat agent concerns.

---

## Quick Start

### Basic Search Pipeline

```python
from vector.retrieval import Pipeline, SearchStep, ScoreFilter, DiagnosticsStep
from vector.search.service import SearchService
from vector.stores.factory import create_store
from vector.embedders.sentence_transformer import SentenceTransformerEmbedder
from vector.agent.models import ChatSession

# Setup dependencies
embedder = SentenceTransformerEmbedder()
store = create_store("qdrant", db_path="./qdrant_db")
search_service = SearchService(embedder, store)

# Build pipeline
pipeline = Pipeline()
pipeline.add_step(SearchStep(search_service, top_k=12))
pipeline.add_step(ScoreFilter(min_score=0.5))
pipeline.add_step(DiagnosticsStep())

# Create context
session = ChatSession(id="test", system_prompt="You are a helpful assistant")
from vector.retrieval import RetrievalContext
context = RetrievalContext(
    session=session,
    user_message="What are the zoning requirements?",
    query="zoning requirements"
)

# Run pipeline
result = pipeline.run(context)

# Access results
print(f"Found {len(result.results)} results")
for r in result.results:
    print(f"  {r.filename}: {r.score:.4f} - {r.text[:100]}")

# Access metadata
print(f"Metadata: {result.metadata}")
```

---

## Core Components

### 1. Pipeline

Orchestrates a sequence of steps:

```python
from vector.retrieval import Pipeline

pipeline = Pipeline()
pipeline.add_step(step1)  # Chainable
pipeline.add_step(step2)
pipeline.add_step(step3)

result = pipeline.run(context)
```

### 2. RetrievalContext

Shared state passed through all steps:

```python
from vector.retrieval import RetrievalContext

context = RetrievalContext(
    session=chat_session,      # ChatSession with history
    user_message="...",         # Original user message
    query="...",                # Current query (modifiable)
    results=[],                 # Retrieved results (populated)
    metadata={},                # Step metadata (enriched)
    usage_metrics=[]            # AI usage tracking
)

# Steps can modify context
context.add_metadata("key", "value")
context.add_usage(usage_metrics)
```

### 3. PipelineStep

Abstract base for custom steps:

```python
from vector.retrieval import PipelineStep, RetrievalContext

class MyCustomStep(PipelineStep):
    def __call__(self, context: RetrievalContext) -> RetrievalContext:
        # Do something with context
        context.add_metadata("custom_step", "executed")
        return context
```

---

## Built-in Steps

### SearchStep

Performs vector similarity search:

```python
from vector.retrieval import SearchStep

step = SearchStep(
    search_service=search_service,
    top_k=12,                    # Number of results
    document_ids=["doc1"],       # Optional filter
    window=2                     # Context window (chunks before/after)
)
```

**What it does:**
- Embeds the query
- Searches vector store for similar chunks
- Optionally includes surrounding chunks for context
- Populates `context.results` with `RetrievalResult` objects

### QueryExpansionStep

Expands queries using AI and conversation history:

```python
from vector.retrieval import QueryExpansionStep
from vector.ai.factory import create_model

ai_model = create_model("openai", model_name="gpt-3.5-turbo")
step = QueryExpansionStep(ai_model)
```

**What it does:**
- Uses recent chat history (last 6 messages)
- Generates search keyphrases via AI
- Updates `context.query` with expanded terms
- Tracks AI usage in `context.usage_metrics`

**Metadata added:**
- `query_expanded` (bool)
- `keyphrases` (list)
- `expanded_query` (str)

### ScoreFilter

Filters results by minimum score:

```python
from vector.retrieval import ScoreFilter

step = ScoreFilter(min_score=0.5)
```

**What it does:**
- Removes results with `score < min_score`
- Tracks how many were filtered

**Metadata added:**
- `score_threshold` (float)
- `filtered_by_score` (int)

### DiagnosticsStep

Adds diagnostic metadata:

```python
from vector.retrieval import DiagnosticsStep

step = DiagnosticsStep()
```

**What it does:**
- Counts results
- Breaks down results by type (chunk/artifact)
- Summarizes query expansion

**Metadata added:**
- `result_count` (int)
- `results_by_type` (dict)
- `keyphrase_count` (int) - if query was expanded

---

## Complete Example: RAG Pipeline

```python
from vector.retrieval import (
    Pipeline,
    RetrievalContext,
    QueryExpansionStep,
    SearchStep,
    ScoreFilter,
    DiagnosticsStep
)
from vector.ai.factory import create_model
from vector.search.service import SearchService
from vector.agent.models import ChatSession

# Setup
ai_model = create_model("openai", model_name="gpt-3.5-turbo")
search_service = SearchService(embedder, store)

# Build pipeline with all steps
pipeline = Pipeline()
pipeline.add_step(QueryExpansionStep(ai_model))      # Expand query
pipeline.add_step(SearchStep(search_service, top_k=20))  # Search
pipeline.add_step(ScoreFilter(min_score=0.6))        # Filter
pipeline.add_step(DiagnosticsStep())                 # Add metadata

# Create session with history
session = ChatSession(id="user123", system_prompt="You are a helpful assistant")
session.add("user", "What is the zoning code?")
session.add("assistant", "The zoning code is ABC-123.")
session.add("user", "What are the setback requirements?")

# Run retrieval
context = RetrievalContext(
    session=session,
    user_message="What are the setback requirements?",
    query="setback requirements"
)

result = pipeline.run(context)

# Use results
print(f"Query: {result.query}")  # May be expanded
print(f"Found {len(result.results)} results")
print(f"Metadata: {result.metadata}")

for r in result.results:
    print(f"\n[{r.score:.4f}] {r.filename}")
    print(f"  {r.text[:200]}")

# Check usage
total_tokens = sum(m.total_tokens for m in result.usage_metrics)
print(f"\nTotal tokens used: {total_tokens}")
```

---

## Migration from `vector.agent`

The pipeline was moved from `vector.agent` to `vector.retrieval` for better separation of concerns.

### Old Import (still works)
```python
from vector.agent.pipeline import Pipeline, PipelineStep, RetrievalContext
from vector.agent.steps import SearchStep, ScoreFilter
```

### New Import (recommended)
```python
from vector.retrieval import Pipeline, PipelineStep, RetrievalContext, SearchStep, ScoreFilter
```

**Both work!** The old imports re-export from the new module for backward compatibility.

---

## Custom Steps

Create your own steps by extending `PipelineStep`:

```python
from vector.retrieval import PipelineStep, RetrievalContext

class DocumentFilterStep(PipelineStep):
    """Filter results to specific documents."""
    
    def __init__(self, allowed_docs: list):
        self.allowed_docs = set(allowed_docs)
    
    def __call__(self, context: RetrievalContext) -> RetrievalContext:
        original = len(context.results)
        context.results = [
            r for r in context.results 
            if r.doc_id in self.allowed_docs
        ]
        
        context.add_metadata("document_filter_applied", True)
        context.add_metadata("filtered_by_document", original - len(context.results))
        
        return context

# Use it
pipeline.add_step(DocumentFilterStep(["doc1", "doc2"]))
```

### Another Example: Deduplication

```python
class DeduplicationStep(PipelineStep):
    """Remove duplicate results based on text similarity."""
    
    def __call__(self, context: RetrievalContext) -> RetrievalContext:
        seen_texts = set()
        unique_results = []
        
        for r in context.results:
            # Simple dedup by text prefix
            prefix = r.text[:100]
            if prefix not in seen_texts:
                seen_texts.add(prefix)
                unique_results.append(r)
        
        duplicates = len(context.results) - len(unique_results)
        context.results = unique_results
        context.add_metadata("duplicates_removed", duplicates)
        
        return context
```

---

## Error Handling

The pipeline catches step errors and continues:

```python
pipeline = Pipeline()
pipeline.add_step(SearchStep(search_service))
pipeline.add_step(BrokenStep())  # This step raises an exception
pipeline.add_step(DiagnosticsStep())  # This still runs

result = pipeline.run(context)

# Check for errors
if "BrokenStep_error" in result.metadata:
    print(f"Error: {result.metadata['BrokenStep_error']}")
```

---

## Best Practices

### 1. Order Matters
```python
# ✅ Good: Expand → Search → Filter → Diagnostics
pipeline.add_step(QueryExpansionStep(ai_model))
pipeline.add_step(SearchStep(search_service))
pipeline.add_step(ScoreFilter(min_score=0.5))
pipeline.add_step(DiagnosticsStep())

# ❌ Bad: Filter before search (nothing to filter!)
pipeline.add_step(ScoreFilter(min_score=0.5))
pipeline.add_step(SearchStep(search_service))
```

### 2. Diagnostics Last
Always add `DiagnosticsStep()` last to capture final state.

### 3. Reuse Pipelines
Create pipelines once and reuse:

```python
# Setup once
search_pipeline = Pipeline()
search_pipeline.add_step(SearchStep(search_service, top_k=12))
search_pipeline.add_step(ScoreFilter(min_score=0.5))

# Use many times
for query in queries:
    context = RetrievalContext(session, query, query)
    result = search_pipeline.run(context)
    # Process result...
```

### 4. Monitor Usage
Track AI usage for cost monitoring:

```python
result = pipeline.run(context)

total_tokens = sum(m.total_tokens for m in result.usage_metrics)
total_cost = sum(
    (m.prompt_tokens * 0.0001 + m.completion_tokens * 0.0002)
    for m in result.usage_metrics
)

print(f"Tokens: {total_tokens}, Cost: ${total_cost:.4f}")
```

---

## Integration with FastAPI

The retrieval pipeline works seamlessly with the FastAPI endpoints:

```python
# In your API route handler
from vector.retrieval import Pipeline, SearchStep, DiagnosticsStep

@router.post("/advanced-search")
def advanced_search(query: str, deps: AppDeps = Depends(get_deps)):
    # Build pipeline
    pipeline = Pipeline()
    pipeline.add_step(SearchStep(deps.search_service, top_k=20))
    pipeline.add_step(ScoreFilter(min_score=0.6))
    pipeline.add_step(DiagnosticsStep())
    
    # Run
    session = ChatSession(id="api", system_prompt="")
    context = RetrievalContext(session, query, query)
    result = pipeline.run(context)
    
    # Return
    return {
        "results": [r.model_dump() for r in result.results],
        "metadata": result.metadata
    }
```

---

## Summary

The `vector.retrieval` module provides:

✅ **Clean pipeline orchestration** for RAG operations  
✅ **Composable steps** (search, filter, expand, diagnose)  
✅ **Extensible** (create custom steps easily)  
✅ **Production-ready** (error handling, metadata, usage tracking)  
✅ **Backward compatible** (old `vector.agent` imports still work)  

Perfect for building sophisticated retrieval systems without coupling to chat agents!
