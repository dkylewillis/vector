"""Protocol-based ports for dependency inversion (PEP 544).

This module defines the core interfaces that all implementations must follow,
using Python's Protocol feature for structural (duck) typing. This approach
keeps the codebase Pythonic and flexible while maintaining clear contracts.
"""

from typing import Protocol, List, Dict, Any, Union, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .search.dsl import SearchRequest, SearchResponse


class VectorStore(Protocol):
    """Protocol for vector store implementations.
    
    Any class that implements these methods can be used as a vector store,
    without needing to inherit from a base class or register with an ABC.
    This is structural typing - if it walks like a duck and quacks like a duck...
    """
    
    def search(self, request: "SearchRequest") -> "SearchResponse":
        """Execute a search query using the provider-agnostic DSL.
        
        Args:
            request: Search request with query parameters and filters
            
        Returns:
            Search response with matching hits
        """
        ...
    
    def create_collection(
        self,
        collection_name: str,
        vector_size: int,
        distance: str = "cosine"
    ) -> None:
        """Create a new collection with the specified configuration.
        
        Args:
            collection_name: Name of the collection to create
            vector_size: Dimension of the vectors
            distance: Distance metric ("cosine", "dot", or "euclidean")
        """
        ...
    
    def delete_collection(self, name: str) -> None:
        """Delete a collection.
        
        Args:
            name: Name of the collection to delete
        """
        ...
    
    def list_collections(self) -> List[str]:
        """List all available collections.
        
        Returns:
            List of collection names
        """
        ...
    
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
        ...


class Embedder(Protocol):
    """Protocol for text embedding implementations.
    
    Implementations can use any embedding model (OpenAI, SentenceTransformers,
    HuggingFace, etc.) as long as they provide these methods.
    """
    
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text.
        
        Args:
            text: Text string to embed
            
        Returns:
            List of float values representing the embedding
        """
        ...
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts (batch processing).
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            List of embeddings, each as a list of float values
        """
        ...
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of the embeddings produced by this embedder.
        
        Returns:
            Integer dimension of embeddings (e.g., 384, 1536)
        """
        ...
