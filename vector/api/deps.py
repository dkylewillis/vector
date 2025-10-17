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

from vector.config import Config
from vector.stores.factory import create_store
from vector.stores.base import BaseVectorStore
from vector.search.service import SearchService
from vector.embedders.sentence_transformer import SentenceTransformerEmbedder
from vector.pipeline.ingestion import IngestionPipeline, IngestionConfig

logger = logging.getLogger(__name__)


@dataclass
class AppDeps:
    """Application dependencies container."""
    
    config: Config
    store: BaseVectorStore
    embedder: SentenceTransformerEmbedder
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
    
    # Load configuration
    config = Config()
    logger.info(f"Loaded configuration from {config.config_path}")
    
    # Create vector store
    store = create_store("qdrant", db_path=config.vector_db_path)
    logger.info(f"Connected to vector store at {config.vector_db_path}")
    
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
        config=config,
        store=store,
        embedder=embedder,
        search_service=search_service,
        ingestion=ingestion
    )
    
    logger.info("✓ All dependencies initialized successfully")
    return _singleton


def reset_deps() -> None:
    """Reset singleton dependencies (useful for testing)."""
    global _singleton
    _singleton = None
