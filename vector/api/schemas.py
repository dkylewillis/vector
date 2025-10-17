"""Pydantic schemas for API request/response models."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ============================================================================
# VectorStore Schemas
# ============================================================================

class CreateCollectionRequest(BaseModel):
    """Request to create a new collection."""
    
    name: str = Field(..., description="Collection name")
    vector_size: int = Field(..., description="Vector dimension size")
    distance: str = Field("cosine", description="Distance metric (cosine, dot, euclidean)")


class UpsertPointRequest(BaseModel):
    """Request to upsert a point into a collection."""
    
    collection: str = Field(..., description="Collection name")
    point_id: str = Field(..., description="Unique point ID")
    vector: List[float] = Field(..., description="Vector embedding")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Point metadata")


class DeleteDocumentRequest(BaseModel):
    """Request to delete a document."""
    
    document_id: str = Field(..., description="Document ID to delete")
    collection: str = Field("chunks", description="Collection name")


# ============================================================================
# Search/Retrieval Schemas
# ============================================================================

class SearchRequest(BaseModel):
    """Request for semantic search."""
    
    query: str = Field(..., description="Search query text")
    top_k: int = Field(12, ge=1, le=100, description="Number of results to return")
    document_ids: Optional[List[str]] = Field(None, description="Filter by document IDs")
    window: int = Field(0, ge=0, le=10, description="Number of surrounding chunks to include")
    min_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Minimum similarity score")


class ChunkResponse(BaseModel):
    """Response model for a chunk."""
    
    id: str
    chunk_id: Optional[str] = None
    chunk_index: Optional[int] = None
    text: str
    document_id: str
    filename: str


class SearchResultResponse(BaseModel):
    """Response model for a search result."""
    
    id: str
    score: float
    text: str
    filename: str
    type: str
    chunk_id: Optional[str] = None
    chunk_index: Optional[int] = None
    document_id: Optional[str] = None


class SearchResponse(BaseModel):
    """Response for search endpoint."""
    
    count: int
    results: List[SearchResultResponse]
    query: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WindowResponse(BaseModel):
    """Response for chunk window endpoint."""
    
    count: int
    chunks: List[ChunkResponse]


# ============================================================================
# Ingestion Schemas
# ============================================================================

class IngestionResponse(BaseModel):
    """Response from document ingestion."""
    
    success: bool
    document_id: Optional[str] = None
    chunks_created: int = 0
    chunks_indexed: int = 0
    artifacts_generated: int = 0
    duration_seconds: float = 0.0
    errors: List[str] = Field(default_factory=list)


# ============================================================================
# Generic Responses
# ============================================================================

class SuccessResponse(BaseModel):
    """Generic success response."""
    
    ok: bool = True
    message: Optional[str] = None


class ErrorResponse(BaseModel):
    """Generic error response."""
    
    ok: bool = False
    error: str
    detail: Optional[str] = None


class CollectionListResponse(BaseModel):
    """Response with list of collections."""
    
    count: int
    collections: List[str]


class DocumentListResponse(BaseModel):
    """Response with list of documents."""
    
    count: int
    documents: List[Dict[str, Any]]
