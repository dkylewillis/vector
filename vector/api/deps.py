"""Dependency injection for FastAPI application.

Provides singleton instances of core services:
- Config: Configuration management
- VectorStore: Vector database operations
- Embedder: Text embedding generation
- SearchService: Semantic search operations
- IngestionPipeline: Document ingestion
"""

from dataclasses import dataclass
from typing import Optional
import logging

from vector.settings import settings
from vector.stores.factory import create_store
from vector.stores.base import BaseVectorStore
from vector.search.service import SearchService
from vector.embedders.sentence_transformer import SentenceTransformerEmbedder
from vector.pipeline.ingestion import IngestionPipeline, IngestionConfig

logger = logging.getLogger(__name__)


@dataclass
class AppDeps:
    """Application dependencies container."""
    
    embedder: SentenceTransformerEmbedder
    store: BaseVectorStore
    search_service: SearchService
    ingestion: IngestionPipeline


# Global singleton instance
_singleton: Optional[AppDeps] = None


def get_deps() -> AppDeps:
    """Get or create application dependencies (singleton pattern).
    
    Returns:
        AppDeps instance with all initialized services
    """
    global _singleton
    
    if _singleton:
        return _singleton
    
    logger.info("Initializing application dependencies...")
    
    # Create vector store using settings
    store = create_store("qdrant", db_path=settings.qdrant_local_path)
    logger.info(f"Connected to vector store at {settings.qdrant_local_path}")
    
    # Create embedder
    embedder = SentenceTransformerEmbedder()
    logger.info("Initialized embedder")
    
    # Create search service
    search_service = SearchService(
        embedder=embedder,
        store=store,
        chunks_collection="chunks"
    )
    logger.info("Initialized search service")
    
    # Create ingestion pipeline
    ingestion = IngestionPipeline(
        embedder=embedder,
        store=store,
        config=IngestionConfig(
            collection_name="chunks",
            batch_size=32,
            generate_artifacts=True,
            use_vlm_pipeline=False
        )
    )
    logger.info("Initialized ingestion pipeline")
    
    _singleton = AppDeps(
        embedder=embedder,
        store=store,
        search_service=search_service,
        ingestion=ingestion
    )
    
    logger.info("✓ All dependencies initialized successfully")
    return _singleton


def reset_deps() -> None:
    """Reset singleton dependencies (useful for testing)."""
    global _singleton
    _singleton = None
