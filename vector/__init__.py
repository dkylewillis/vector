"""Vector - A Pythonic vector search and document processing library.

This library provides a clean, flat structure for semantic search, document
processing, and vector storage operations. It uses Protocol-based dependency
inversion (PEP 544) for maximum flexibility.

Main modules:
- vector.models: Domain models (Chunk, Artifact, DocumentRecord, etc.)
- vector.ports: Protocol interfaces (VectorStore, Embedder)
- vector.search: Search DSL, utilities, and SearchService
- vector.stores: Vector store implementations (Qdrant, etc.)
- vector.embedders: Text embedding implementations
- vector.pipeline: Document conversion and ingestion pipeline
"""

__version__ = "0.2.0"

# Export key interfaces and factories for convenience
from .ports import VectorStore, Embedder
from .models import (
    Chunk, 
    Artifact, 
    DocumentRecord, 
    ConvertedDocument,
    VectorDocument,
    DocumentSection,
    TableElement,
    ImageElement,
    HeaderElement
)
from .stores import create_store
from .search import SearchService, SearchRequest, SearchResponse
from .pipeline import IngestionPipeline, IngestionConfig, DocumentConverter, DocumentChunker

__all__ = [
    # Protocols
    "VectorStore",
    "Embedder",
    # Models
    "Chunk",
    "Artifact",
    "DocumentRecord",
    "ConvertedDocument",
    "VectorDocument",
    "DocumentSection",
    "TableElement",
    "ImageElement",
    "HeaderElement",
    # Factories
    "create_store",
    # Services
    "SearchService",
    "SearchRequest",
    "SearchResponse",
    # Pipeline
    "IngestionPipeline",
    "IngestionConfig",
    "DocumentConverter",
    "DocumentChunker",
]
