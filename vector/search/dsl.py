"""Provider-agnostic search DSL for vector store operations.

This module defines a domain-specific language (DSL) for constructing
flexible, composable search queries and filters that work across different
vector store backends.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel


# ============================================================================
# Filter AST (provider-agnostic)
# ============================================================================

class FilterExpr(BaseModel):
    """Base class for all filter expressions."""
    pass


class And(FilterExpr):
    """Logical AND - all conditions must be true."""
    all: List[FilterExpr]


class Or(FilterExpr):
    """Logical OR - at least one condition must be true."""
    any: List[FilterExpr]


class Not(FilterExpr):
    """Logical NOT - negates the inner expression."""
    expr: FilterExpr


class FieldEquals(FilterExpr):
    """Field equality filter - field must equal the specified value."""
    key: str
    value: Union[str, int, float, bool]


class FieldIn(FilterExpr):
    """Field IN filter - field value must be in the specified list."""
    key: str
    values: List[Union[str, int, float, bool]]


class RangeFilter(FilterExpr):
    """Range filter for numeric/comparable fields.
    
    Supports gt (>), gte (>=), lt (<), and lte (<=) comparisons.
    """
    key: str
    gt: Optional[float] = None
    gte: Optional[float] = None
    lt: Optional[float] = None
    lte: Optional[float] = None


# ============================================================================
# Search Request/Response
# ============================================================================

class SearchRequest(BaseModel):
    """Flexible search request supporting both vector and filter-only queries.
    
    Attributes:
        collection: Name of the collection to search
        vector: Query vector for similarity search (None for filter-only)
        top_k: Maximum number of results to return
        filter: Optional filter expression to constrain results
        include_payload: Whether to include point payload in results
        include_vector: Whether to include vector in results (not all providers support this)
    """
    collection: str
    vector: Optional[List[float]] = None  # Optional: filter-only if None
    top_k: int = 10
    filter: Optional[FilterExpr] = None
    include_payload: bool = True
    include_vector: bool = False  # Not all providers support this


class Hit(BaseModel):
    """A single search result hit.
    
    Attributes:
        id: Unique identifier for the point
        score: Similarity score (None for filter-only queries)
        payload: Point metadata/payload
        vector: The vector itself (if requested and supported)
    """
    id: Union[str, int]
    score: Optional[float] = None
    payload: Optional[Dict[str, Any]] = None
    vector: Optional[List[float]] = None


class SearchResponse(BaseModel):
    """Search response containing matching hits.
    
    Attributes:
        hits: List of matching results
    """
    hits: List[Hit]
