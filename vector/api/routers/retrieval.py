"""Retrieval and search endpoints.

Provides REST API for:
- Semantic search
- Context window retrieval
- Document filtering
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
import logging

from vector.api.deps import get_deps, AppDeps
from vector.api.schemas import (
    SearchRequest,
    SearchResponse,
    SearchResultResponse,
    WindowResponse,
    ChunkResponse
)
from vector.search.utils import get_chunk_window

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/retrieval", tags=["retrieval"])


@router.post("/search", response_model=SearchResponse)
def search(body: SearchRequest, deps: AppDeps = Depends(get_deps)):
    """Perform semantic search on indexed documents.
    
    Uses vector embeddings to find semantically similar content.
    Optionally includes surrounding chunks for additional context.
    
    Args:
        body: Search request with query, filters, and options
        
    Returns:
        SearchResponse with ranked results and metadata
        
    Raises:
        HTTPException: If search fails
    """
    try:
        logger.info(f"Search query: '{body.query}' (top_k={body.top_k}, window={body.window})")
        
        # Perform search using SearchService
        results = deps.search_service.search(
            query=body.query,
            top_k=body.top_k,
            document_ids=body.document_ids,
            window=body.window
        )
        
        # Filter by minimum score if specified
        if body.min_score is not None:
            results = [r for r in results if r.score >= body.min_score]
        
        # Convert to response models
        result_responses = []
        for r in results:
            result_responses.append(SearchResultResponse(
                id=r.id,
                score=r.score,
                text=r.text,
                filename=r.filename,
                type=r.type,
                chunk_id=r.chunk.chunk_id if r.chunk else None,
                chunk_index=r.chunk.chunk_index if r.chunk else None,
                document_id=r.chunk.document_id if r.chunk else None
            ))
        
        logger.info(f"Found {len(result_responses)} results")
        
        return SearchResponse(
            count=len(result_responses),
            results=result_responses,
            query=body.query,
            metadata={
                "top_k": body.top_k,
                "window": body.window,
                "min_score": body.min_score,
                "document_ids": body.document_ids
            }
        )
        
    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search", response_model=SearchResponse)
def search_get(
    query: str = Query(..., description="Search query text"),
    top_k: int = Query(12, ge=1, le=100, description="Number of results"),
    window: int = Query(0, ge=0, le=10, description="Context window size"),
    min_score: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum score"),
    document_ids: Optional[str] = Query(None, description="Comma-separated document IDs"),
    deps: AppDeps = Depends(get_deps)
):
    """Perform semantic search via GET request (convenience endpoint).
    
    Same as POST /search but using query parameters.
    
    Args:
        query: Search query text
        top_k: Number of results to return
        window: Number of surrounding chunks to include
        min_score: Optional minimum similarity score
        document_ids: Optional comma-separated list of document IDs to filter
        
    Returns:
        SearchResponse with ranked results
    """
    # Parse document IDs if provided
    doc_id_list = None
    if document_ids:
        doc_id_list = [d.strip() for d in document_ids.split(",") if d.strip()]
    
    # Delegate to POST handler
    request = SearchRequest(
        query=query,
        top_k=top_k,
        window=window,
        min_score=min_score,
        document_ids=doc_id_list
    )
    
    return search(request, deps)


@router.get("/context/{chunk_id}", response_model=WindowResponse)
def get_context_window(
    chunk_id: str,
    window: int = Query(2, ge=0, le=10, description="Number of chunks before/after"),
    collection: str = Query("chunks", description="Collection name"),
    deps: AppDeps = Depends(get_deps)
):
    """Get surrounding context for a specific chunk.
    
    Returns the target chunk plus surrounding chunks for additional context.
    Useful for expanding search results or examining chunk neighborhoods.
    
    Args:
        chunk_id: ID of the target chunk
        window: Number of chunks to include before and after (default: 2)
        collection: Collection name (default: "chunks")
        
    Returns:
        WindowResponse with list of chunks in order
        
    Raises:
        HTTPException: If chunk not found or retrieval fails
    """
    try:
        logger.info(f"Fetching context window for chunk: {chunk_id} (window={window})")
        
        # First, we need to find the chunk to get its document_id and chunk_index
        from vector.search.dsl import SearchRequest, FieldEquals
        
        # Search for the specific chunk
        search_request = SearchRequest(
            collection=collection,
            vector=None,  # Filter-only query
            top_k=1,
            filter=FieldEquals(key="chunk.chunk_id", value=chunk_id),
            include_payload=True
        )
        
        response = deps.store.search(search_request)
        
        if not response.hits:
            raise HTTPException(status_code=404, detail=f"Chunk not found: {chunk_id}")
        
        # Get document_id and chunk_index from the hit
        hit = response.hits[0]
        payload = hit.payload or {}
        document_id = payload.get("document_id")
        chunk_index = payload.get("chunk_index")
        
        if not document_id or chunk_index is None:
            raise HTTPException(
                status_code=500,
                detail="Chunk missing required metadata (document_id or chunk_index)"
            )
        
        # Get surrounding chunks
        context_hits = get_chunk_window(
            store=deps.store,
            collection=collection,
            document_id=document_id,
            center_index=chunk_index,
            window=window
        )
        
        # Convert hits to chunk responses
        chunks = []
        for ctx_hit in context_hits:
            ctx_payload = ctx_hit.payload or {}
            
            # Try to extract chunk data
            chunk_data = ctx_payload.get("chunk", {})
            if isinstance(chunk_data, str):
                import json
                chunk_data = json.loads(chunk_data)
            
            chunks.append(ChunkResponse(
                id=str(ctx_hit.id),
                chunk_id=chunk_data.get("chunk_id"),
                chunk_index=ctx_payload.get("chunk_index"),
                text=chunk_data.get("text", ""),
                document_id=ctx_payload.get("document_id", ""),
                filename=ctx_payload.get("filename", "")
            ))
        
        logger.info(f"Retrieved {len(chunks)} chunks in context window")
        
        return WindowResponse(
            count=len(chunks),
            chunks=chunks
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get context window: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
