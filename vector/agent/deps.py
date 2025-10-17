"""Dependency injection container for PydanticAI agents."""

from typing import Optional
from dataclasses import dataclass

from vector.search.service import SearchService
from ..config import Config


@dataclass
class AgentDeps:
    """Dependencies injected into agent tools and operations.
    
    This container provides access to all services needed by agent tools,
    enabling clean dependency injection and testability.
    
    Attributes:
        search_service: Service for vector search operations
        config: Application configuration
        search_model: Optional AI model for query expansion
        answer_model: Optional AI model for answer generation
        chunks_collection: Name of the chunks collection to search
    """
    
    search_service: SearchService
    config: Config
    search_model: Optional[object] = None
    answer_model: Optional[object] = None
    chunks_collection: str = "chunks"
    
    def __post_init__(self):
        """Validate dependencies after initialization."""
        if not self.search_service:
            raise ValueError("search_service is required")
        if not self.config:
            raise ValueError("config is required")
