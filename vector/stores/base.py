"""Base abstract interface for vector store providers.

This module defines a minimal, stable interface that all vector store
implementations must follow, allowing the application to remain
decoupled from specific provider implementations.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Union
from vector.search.dsl import SearchRequest, SearchResponse


class DistanceType(str, Enum):
    """Distance metric for vector similarity."""
    COSINE = "cosine"
    DOT = "dot"
    EUCLIDEAN = "euclidean"


class BaseVectorStore(ABC):
    """Abstract base class for vector store providers.
    
    All vector store implementations (Qdrant, Pinecone, Faiss, etc.)
    must implement this interface.
    """
    
    @abstractmethod
    def create_collection(
        self,
        collection_name: str,
        vector_size: int,
        distance: DistanceType = DistanceType.COSINE
    ) -> None:
        """Create a new collection with the specified configuration.
        
        Args:
            collection_name: Name of the collection to create
            vector_size: Dimension of the vectors
            distance: Distance metric to use for similarity
        """
        pass
    
    @abstractmethod
    def delete_collection(self, name: str) -> None:
        """Delete a collection.
        
        Args:
            name: Name of the collection to delete
        """
        pass
    
    @abstractmethod
    def list_collections(self) -> List[str]:
        """List all available collections.
        
        Returns:
            List of collection names
        """
        pass
    
    @abstractmethod
    def upsert(
        self,
        collection_name: str,
        point_id: Union[str, int],
        vector: List[float],
        payload: Dict[str, Any]
    ) -> None:
        """Insert or update a point in the collection.
        
        Args:
            collection_name: Name of the collection
            point_id: Unique identifier for the point
            vector: The vector to store
            payload: Metadata to attach to the point
        """
        pass
    
    @abstractmethod
    def delete(
        self,
        collection_name: str,
        filter_expr: Any
    ) -> int:
        """Delete points from a collection matching the filter.
        
        Args:
            collection_name: Name of the collection
            filter_expr: Filter expression (from search.dsl) to select points to delete
            
        Returns:
            Number of points deleted
        """
        pass
    
    @abstractmethod
    def search(self, request: SearchRequest) -> SearchResponse:
        """Execute a search query using the provider-agnostic DSL.
        
        This is the main entry point for all search operations, supporting
        both vector similarity search and filter-only queries.
        
        Args:
            request: Search request with query parameters and filters
            
        Returns:
            Search response with matching hits
        """
        pass
