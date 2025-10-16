"""Factory for creating vector store providers.

This module provides a factory function that selects the appropriate
vector store implementation based on configuration or environment variables.
"""

import os
from typing import Optional

from .base import BaseVectorStore
from .qdrant import QdrantVectorStore


def create_store(
    provider: Optional[str] = None,
    *,
    db_path: Optional[str] = None,
    url: Optional[str] = None,
    api_key: Optional[str] = None
) -> BaseVectorStore:
    """Create a vector store instance based on the specified provider.
    
    The provider is selected in the following order:
    1. The `provider` parameter if explicitly provided
    2. The VECTOR_STORE_PROVIDER environment variable
    3. Default to "qdrant" if neither is set
    
    Args:
        provider: Provider name ("qdrant", "faiss", "pinecone", etc.)
        db_path: Path to local database (for providers that support it)
        url: URL for remote instance (for providers that support it)
        api_key: API key for authentication
        
    Returns:
        A BaseVectorStore implementation
        
    Raises:
        ValueError: If the provider is not recognized
        NotImplementedError: If the provider is recognized but not yet implemented
        
    Examples:
        >>> # Use default Qdrant with local database
        >>> store = create_store(db_path="./qdrant_db")
        
        >>> # Use remote Qdrant
        >>> store = create_store(provider="qdrant", url="http://localhost:6333")
        
        >>> # Use environment variable
        >>> os.environ["VECTOR_STORE_PROVIDER"] = "qdrant"
        >>> store = create_store(db_path="./qdrant_db")
    """
    # Determine provider name
    name = (provider or os.getenv("VECTOR_STORE_PROVIDER") or "qdrant").lower()
    
    # Create appropriate provider instance
    if name == "qdrant":
        return QdrantVectorStore(db_path=db_path, url=url, api_key=api_key)
    
    if name == "faiss":
        raise NotImplementedError("FAISS provider not implemented yet.")
    
    if name == "pinecone":
        raise NotImplementedError("Pinecone provider not implemented yet.")
    
    if name == "weaviate":
        raise NotImplementedError("Weaviate provider not implemented yet.")
    
    if name == "milvus":
        raise NotImplementedError("Milvus provider not implemented yet.")
    
    raise ValueError(f"Unknown vector store provider: {name}")
