"""Search module - provider-agnostic search DSL and utilities.

This module provides the core search functionality including:
- DSL for building flexible search queries and filters
- Utility functions for common search patterns
- SearchService for high-level search operations
"""

from .dsl import (
    SearchRequest,
    SearchResponse,
    Hit,
    FilterExpr,
    And,
    Or,
    Not,
    FieldEquals,
    FieldIn,
    RangeFilter,
)
from .utils import get_chunk_window, get_chunks_by_indices
from .service import SearchService, SearchResult

__all__ = [
    # DSL
    "SearchRequest",
    "SearchResponse",
    "Hit",
    "FilterExpr",
    "And",
    "Or",
    "Not",
    "FieldEquals",
    "FieldIn",
    "RangeFilter",
    # Utils
    "get_chunk_window",
    "get_chunks_by_indices",
    # Service
    "SearchService",
    "SearchResult",
]
