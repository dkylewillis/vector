"""Search utility functions built on top of the DSL.

This module provides higher-level search utilities that compose
DSL filters and requests for common use cases.
"""

from __future__ import annotations
from typing import List, TYPE_CHECKING

from .dsl import SearchRequest, And, FieldEquals, RangeFilter, Hit

if TYPE_CHECKING:
    from vector.ports import VectorStore


def get_chunk_window(
    store: "VectorStore",
    *,
    collection: str,
    document_id: str,
    center_index: int,
    window: int = 2,
) -> List[Hit]:
    """Retrieve a window of chunks around a center chunk using explicit chunk_index.
    
    This function uses filter-only search with explicit chunk_index metadata,
    making it provider-agnostic and avoiding parsing of chunk IDs.
    
    IMPORTANT: This function requires that chunks have explicit metadata:
    - document_id: str (the document identifier)
    - chunk_index: int (0-based position within the document)
    
    If your data doesn't have chunk_index yet, you'll need to backfill it
    or use the legacy VectorStore.get_chunk_window() method.
    
    Args:
        store: VectorStore instance to query
        collection: Name of the collection to search
        document_id: Document identifier to filter by
        center_index: The chunk_index of the center chunk
        window: Number of chunks to include before and after center (default: 2)
        
    Returns:
        List of Hit objects sorted by chunk_index, representing the window
        
    Example:
        >>> from vector.stores.factory import create_store
        >>> from vector.search.utils import get_chunk_window
        >>> 
        >>> store = create_store("qdrant", db_path="./qdrant_db")
        >>> # Get chunks 3-7 (center=5, window=2)
        >>> hits = get_chunk_window(
        ...     store,
        ...     collection="docs",
        ...     document_id="doc_123",
        ...     center_index=5,
        ...     window=2
        ... )
        >>> for hit in hits:
        ...     idx = hit.payload.get("chunk_index")
        ...     print(f"Chunk {idx}: {hit.payload.get('text', '')[:50]}...")
    """
    # Calculate the range
    start = max(0, center_index - window)
    end = center_index + window
    
    # Build the filter: document_id == X AND chunk_index BETWEEN start AND end
    flt = And(all=[
        FieldEquals(key="document_id", value=document_id),
        RangeFilter(key="chunk_index", gte=float(start), lte=float(end)),
    ])
    
    # Execute filter-only search (no vector)
    resp = store.search(SearchRequest(
        collection=collection,
        vector=None,              # Filter-only query
        top_k=(2 * window + 1),   # Request enough results for full window
        filter=flt,
        include_payload=True,
    ))
    
    # Sort results by chunk_index to ensure correct ordering
    sorted_hits = sorted(
        resp.hits,
        key=lambda h: (h.payload or {}).get("chunk_index", float('inf')),
    )
    
    return sorted_hits


def get_chunks_by_indices(
    store: "VectorStore",
    *,
    collection: str,
    document_id: str,
    indices: List[int],
) -> List[Hit]:
    """Retrieve specific chunks by their indices.
    
    This is useful when you know exactly which chunk indices you want,
    rather than a continuous window.
    
    Args:
        store: VectorStore instance to query
        collection: Name of the collection to search
        document_id: Document identifier to filter by
        indices: List of chunk_index values to retrieve
        
    Returns:
        List of Hit objects sorted by chunk_index
        
    Example:
        >>> # Get chunks 0, 5, and 10
        >>> hits = get_chunks_by_indices(
        ...     store,
        ...     collection="docs",
        ...     document_id="doc_123",
        ...     indices=[0, 5, 10]
        ... )
    """
    if not indices:
        return []
    
    # Build filter for specific indices
    min_idx = min(indices)
    max_idx = max(indices)
    
    flt = And(all=[
        FieldEquals(key="document_id", value=document_id),
        RangeFilter(key="chunk_index", gte=float(min_idx), lte=float(max_idx)),
    ])
    
    # Execute filter-only search
    resp = store.search(SearchRequest(
        collection=collection,
        vector=None,
        top_k=len(indices) * 2,  # Request extra in case of gaps
        filter=flt,
        include_payload=True,
    ))
    
    # Filter to only requested indices and sort
    target_indices = set(indices)
    matching_hits = [
        hit for hit in resp.hits
        if (hit.payload or {}).get("chunk_index") in target_indices
    ]
    
    sorted_hits = sorted(
        matching_hits,
        key=lambda h: (h.payload or {}).get("chunk_index", float('inf')),
    )
    
    return sorted_hits
