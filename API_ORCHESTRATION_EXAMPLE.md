# API Endpoint for Retrieval Orchestration

## Quick Reference

Now that retrieval orchestration lives in `vector.retrieval`, you can easily add API endpoints for it.

## Example API Router

Create `vector/api/routers/orchestration.py`:

```python
"""Orchestrated retrieval endpoints with AI-powered query expansion."""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
import logging

from vector.api.deps import get_deps, AppDeps
from vector.retrieval import RetrievalOrchestrator
from vector.agent.models import ChatSession

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/orchestration", tags=["orchestration"])


class OrchestrationRequest(BaseModel):
    """Request for orchestrated retrieval."""
    query: str = Field(..., description="User's search query")
    top_k: int = Field(12, ge=1, le=100, description="Number of results")
    document_ids: Optional[List[str]] = Field(None, description="Filter by document IDs")
    window: int = Field(0, ge=0, le=10, description="Context window size")
    min_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Min similarity score")


class OrchestrationResponse(BaseModel):
    """Response from orchestrated retrieval."""
    original_query: str
    expanded_query: str
    keyphrases: List[str]
    result_count: int
    results: List[dict]
    diagnostics: dict
    metrics: dict


@router.post("/retrieve", response_model=OrchestrationResponse)
def orchestrated_retrieve(
    body: OrchestrationRequest,
    deps: AppDeps = Depends(get_deps)
):
    """Perform AI-powered orchestrated retrieval.
    
    This endpoint provides the full retrieval pipeline:
    - AI-powered query expansion using conversation context
    - Vector similarity search on document chunks
    - Optional score filtering
    - Context window expansion
    - Rich diagnostics and metrics
    
    Unlike the basic /retrieval/search endpoint, this uses AI to
    understand intent and expand queries for better results.
    
    Args:
        body: Orchestration request with query and options
        
    Returns:
        OrchestrationResponse with expanded query, results, and metrics
        
    Example:
        ```bash
        curl -X POST "http://localhost:8000/orchestration/retrieve" \\
          -H "Content-Type: application/json" \\
          -d '{
            "query": "height limits",
            "top_k": 10,
            "min_score": 0.5
          }'
        ```
    """
    try:
        logger.info(f"Orchestrated retrieval: '{body.query}' (top_k={body.top_k})")
        
        # Create orchestrator
        orchestrator = RetrievalOrchestrator(
            search_model=deps.search_model,
            search_service=deps.search_service
        )
        
        # Create minimal session for context
        # In a real app, you'd load the actual user session
        session = ChatSession(
            id="api",
            system_prompt="Document search assistant",
            messages=[]
        )
        
        # Perform orchestrated retrieval
        bundle, metrics = orchestrator.retrieve(
            session=session,
            user_message=body.query,
            top_k=body.top_k,
            document_ids=body.document_ids,
            window=body.window,
            min_score=body.min_score
        )
        
        # Convert results to dicts
        results = [r.model_dump() for r in bundle.results]
        
        logger.info(
            f"Retrieved {len(results)} results "
            f"(expanded: '{bundle.expanded_query}')"
        )
        
        return OrchestrationResponse(
            original_query=bundle.original_query,
            expanded_query=bundle.expanded_query,
            keyphrases=bundle.keyphrases,
            result_count=len(results),
            results=results,
            diagnostics=bundle.diagnostics,
            metrics=metrics.model_dump()
        )
        
    except Exception as e:
        logger.error(f"Orchestrated retrieval failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/retrieve", response_model=OrchestrationResponse)
def orchestrated_retrieve_get(
    query: str = Query(..., description="Search query text"),
    top_k: int = Query(12, ge=1, le=100, description="Number of results"),
    window: int = Query(0, ge=0, le=10, description="Context window size"),
    min_score: Optional[float] = Query(None, ge=0.0, le=1.0, description="Min score"),
    document_ids: Optional[str] = Query(None, description="Comma-separated doc IDs"),
    deps: AppDeps = Depends(get_deps)
):
    """Orchestrated retrieval via GET (convenience endpoint).
    
    Same as POST /orchestration/retrieve but using query parameters.
    
    Example:
        ```bash
        curl "http://localhost:8000/orchestration/retrieve?query=height%20limits&top_k=10"
        ```
    """
    # Parse document IDs if provided
    doc_id_list = None
    if document_ids:
        doc_id_list = [d.strip() for d in document_ids.split(",") if d.strip()]
    
    # Delegate to POST handler
    request = OrchestrationRequest(
        query=query,
        top_k=top_k,
        window=window,
        min_score=min_score,
        document_ids=doc_id_list
    )
    
    return orchestrated_retrieve(request, deps)


@router.post("/custom-pipeline", response_model=OrchestrationResponse)
def custom_pipeline_retrieve(
    body: OrchestrationRequest,
    deps: AppDeps = Depends(get_deps)
):
    """Retrieve using a custom pipeline configuration.
    
    This endpoint demonstrates how to build custom pipelines
    with different step configurations.
    
    Example: Retrieve without query expansion (direct search only)
    """
    try:
        from vector.retrieval import Pipeline, SearchStep, ScoreFilter, DiagnosticsStep
        
        # Build custom pipeline (no query expansion)
        pipeline = Pipeline()
        pipeline.add_step(SearchStep(
            deps.search_service,
            top_k=body.top_k,
            document_ids=body.document_ids,
            window=body.window
        ))
        if body.min_score:
            pipeline.add_step(ScoreFilter(body.min_score))
        pipeline.add_step(DiagnosticsStep())
        
        # Create orchestrator
        orchestrator = RetrievalOrchestrator(
            search_model=deps.search_model,
            search_service=deps.search_service
        )
        
        # Use custom pipeline
        session = ChatSession(id="api", system_prompt="", messages=[])
        bundle, metrics = orchestrator.retrieve(
            session=session,
            user_message=body.query,
            pipeline=pipeline  # Custom pipeline
        )
        
        return OrchestrationResponse(
            original_query=bundle.original_query,
            expanded_query=bundle.expanded_query,
            keyphrases=bundle.keyphrases,
            result_count=len(bundle.results),
            results=[r.model_dump() for r in bundle.results],
            diagnostics=bundle.diagnostics,
            metrics=metrics.model_dump()
        )
        
    except Exception as e:
        logger.error(f"Custom pipeline retrieval failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
```

## Register the Router

In `vector/api/app.py`:

```python
from vector.api.routers import ingestion, retrieval, vectorstore, orchestration

# Include routers
app.include_router(ingestion.router)
app.include_router(retrieval.router)  # Basic search
app.include_router(orchestration.router)  # AI-powered orchestration
app.include_router(vectorstore.router)
```

## Comparison: Basic Search vs Orchestration

### Basic Search (`/retrieval/search`)
- Direct vector similarity search
- No query expansion
- Faster, simpler
- Good for: Known queries, keyword matching

```bash
curl "http://localhost:8000/retrieval/search?query=height+limits&top_k=5"
```

### Orchestrated Retrieval (`/orchestration/retrieve`)
- AI-powered query expansion
- Conversation context awareness
- Richer diagnostics and metrics
- Good for: Complex queries, conversational interfaces

```bash
curl -X POST "http://localhost:8000/orchestration/retrieve" \\
  -H "Content-Type: application/json" \\
  -d '{"query": "height limits", "top_k": 10, "min_score": 0.5}'
```

## Example Responses

### Basic Search Response
```json
{
  "count": 5,
  "results": [
    {
      "id": "chunk_123",
      "score": 0.85,
      "text": "Maximum building height is 45 feet...",
      "filename": "zoning_code.pdf",
      "type": "chunk"
    }
  ],
  "query": "height limits",
  "metadata": {
    "top_k": 5,
    "window": 0
  }
}
```

### Orchestrated Response
```json
{
  "original_query": "height limits",
  "expanded_query": "building height limits, maximum height restrictions, vertical construction limits",
  "keyphrases": [
    "building height limits",
    "maximum height restrictions",
    "vertical construction limits"
  ],
  "result_count": 8,
  "results": [...],
  "diagnostics": {
    "query_expanded": true,
    "keyphrase_count": 3,
    "search_latency_ms": 125.4,
    "result_count": 8,
    "results_by_type": {"chunk": 8}
  },
  "metrics": {
    "total_tokens": 96,
    "prompt_tokens": 48,
    "completion_tokens": 48,
    "total_cost": 0.00012,
    "operations": [
      {
        "operation": "search",
        "model": "gpt-3.5-turbo",
        "total_tokens": 96
      }
    ]
  }
}
```

## Benefits

✅ **Separation of Concerns**: Basic search for simple use cases, orchestration for complex ones  
✅ **Flexibility**: Choose the right tool for each use case  
✅ **Transparency**: Full diagnostics and metrics in orchestrated mode  
✅ **Cost Visibility**: Track AI costs per operation  
✅ **Customization**: Build custom pipelines for specific needs  

## Next Steps

1. Add session management for multi-turn conversations
2. Implement caching for common queries
3. Add rate limiting and authentication
4. Build monitoring dashboards for metrics
5. Create webhooks for long-running retrievals
