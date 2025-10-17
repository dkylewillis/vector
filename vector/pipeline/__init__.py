"""Document processing pipeline components.

This module provides the complete document ingestion pipeline:
- DocumentConverter: Convert various formats to structured documents
- DoclingAdapter: Adapter for Docling parser (implements DocumentConverter protocol)
- DocumentChunker: Chunk documents into semantic pieces
- IngestionPipeline: Process and index documents into the vector store
"""

from .converter import DocumentConverter
from .docling_adapter import DoclingAdapter
from .chunker import DocumentChunker
from .ingestion import IngestionPipeline, IngestionConfig, IngestionResult

__all__ = [
    "DocumentConverter",
    "DoclingAdapter",
    "DocumentChunker",
    "IngestionPipeline",
    "IngestionConfig",
    "IngestionResult",
]
