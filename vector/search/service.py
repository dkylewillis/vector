"""SearchService - application logic for semantic search operations.

This module provides the main search service that combines embeddings and
vector store operations to deliver search functionality.
"""

from typing import List, Optional
from pydantic import BaseModel, Field
import json

from vector.models import Chunk, Artifact
from vector.ports import Embedder, VectorStore
from vector.search.dsl import SearchRequest, FieldIn
from vector.search.utils import get_chunk_window


class SearchResult(BaseModel):
    """A single search result with all relevant context."""
    
    id: str = Field(..., description="Unique identifier")
    score: float = Field(..., description="Similarity score")
    text: str = Field(..., description="The text content of the result")
    filename: str = Field(..., description="Source document/file name")
    type: str = Field(..., description="Type of result (e.g., 'chunk', 'artifact')")
    chunk: Optional[Chunk] = None
    artifact: Optional[Artifact] = None


class SearchService:
    """Service for semantic search operations.
    
    This service composes an Embedder and VectorStore to provide high-level
    search functionality. It handles query embedding, vector search, and
    context window expansion.
    
    Example:
        >>> from vector.search.service import SearchService
        >>> from vector.stores.factory import create_store
        >>> from vector.embedders.sentence_transformer import SentenceTransformerEmbedder
        >>> 
        >>> embedder = SentenceTransformerEmbedder()
        >>> store = create_store("qdrant", db_path="./qdrant_db")
        >>> service = SearchService(embedder=embedder, store=store)
        >>> 
        >>> results = service.search("zoning requirements", top_k=5)
        >>> for r in results:
        ...     print(f"{r.filename}: {r.text[:100]}")
    """
    
    def __init__(
        self,
        embedder: Embedder,
        store: VectorStore,
        chunks_collection: str = "chunks"
    ):
        """Initialize the search service.
        
        Args:
            embedder: Text embedder for query vectorization
            store: Vector store for similarity search
            chunks_collection: Name of the chunks collection (default: "chunks")
        """
        self.embedder = embedder
        self.store = store
        self.chunks_collection = chunks_collection
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        document_ids: Optional[List[str]] = None,
        window: int = 0
    ) -> List[SearchResult]:
        """Search for chunks matching the query.
        
        Args:
            query: The search query text
            top_k: Number of results to return (default: 5)
            document_ids: Optional list of document IDs to filter by
            window: Number of surrounding chunks to include for context (default: 0)
            
        Returns:
            List of SearchResult objects sorted by relevance
            
        Raises:
            ValueError: If query is empty
            
        Example:
            >>> # Search with document filter
            >>> results = service.search(
            ...     "setback requirements",
            ...     top_k=10,
            ...     document_ids=["doc_123", "doc_456"]
            ... )
            >>> 
            >>> # Search with context window
            >>> results = service.search(
            ...     "variance procedures",
            ...     top_k=5,
            ...     window=2  # Include 2 chunks before and after each match
            ... )
        """
        if not query.strip():
            raise ValueError("Search query cannot be empty")
        
        # Embed the query
        query_vector = self.embedder.embed_text(query)
        
        # Build the search request
        request = SearchRequest(
            collection=self.chunks_collection,
            vector=query_vector,
            top_k=top_k,
            filter=FieldIn(key="document_id", values=document_ids) if document_ids else None,
            include_payload=True
        )
        
        # Execute search
        response = self.store.search(request)
        
        # Process results
        results: List[SearchResult] = []
        for hit in response.hits:
            chunk_obj = None
            text = ""
            
            try:
                # Extract and validate chunk data from payload
                payload = hit.payload or {}
                chunk_data = payload.get("chunk", {}) or {}
                
                # Handle serialized JSON strings
                if isinstance(chunk_data, str):
                    chunk_data = json.loads(chunk_data)
                
                chunk_obj = Chunk.model_validate(chunk_data)
                
                # Populate chunk_index from payload if missing in chunk object
                if chunk_obj.chunk_index is None and "chunk_index" in payload:
                    chunk_obj.chunk_index = payload["chunk_index"]
                
                text = chunk_obj.text
                
                # If window is enabled, expand context with surrounding chunks
                if window > 0 and chunk_obj.chunk_id:
                    doc_id = payload.get("document_id")
                    if doc_id:
                        context_hits = get_chunk_window(
                            store=self.store,
                            collection=self.chunks_collection,
                            document_id=doc_id,
                            center_index=chunk_obj.chunk_index,
                            window=window
                        )
                        
                        if context_hits:
                            context_texts = []
                            for ctx_hit in context_hits:
                                try:
                                    ctx_payload = ctx_hit.payload or {}
                                    ctx_chunk_data = ctx_payload.get("chunk", {})
                                    if isinstance(ctx_chunk_data, str):
                                        ctx_chunk_data = json.loads(ctx_chunk_data)
                                    ctx_chunk = Chunk.model_validate(ctx_chunk_data)
                                    context_texts.append(ctx_chunk.text)
                                except Exception:
                                    pass
                            
                            if context_texts:
                                text = "\n\n".join(context_texts)
            
            except Exception as e:
                print(f"Warning: chunk validation failed ({hit.id}): {e}")
                text = (hit.payload or {}).get("text", "")
            
            results.append(SearchResult(
                id=str(hit.id),
                score=hit.score or 0.0,
                text=text,
                filename=(hit.payload or {}).get("document_id", "Unknown"),
                type="chunk",
                chunk=chunk_obj
            ))
        
        return results
