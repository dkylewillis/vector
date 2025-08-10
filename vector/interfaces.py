"""Core interfaces and base classes for Vector."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Protocol
from dataclasses import dataclass


@dataclass
class SearchResult:
    """Standardized search result structure."""
    score: float
    text: str
    metadata: Dict[str, Any]
    
    @property
    def filename(self) -> str:
        """Get filename from metadata."""
        return self.metadata.get('filename', 'Unknown')
    
    @property
    def source(self) -> str:
        """Get source from metadata."""
        return self.metadata.get('source', 'Unknown')
    
    @property
    def chunk_info(self) -> str:
        """Get chunk information if available."""
        if 'chunk_index' in self.metadata:
            chunk_idx = self.metadata['chunk_index']
            total_chunks = self.metadata.get('total_chunks', '?')
            return f" (chunk {chunk_idx + 1}/{total_chunks})"
        return ""


class AIModel(Protocol):
    """Protocol for AI model implementations."""
    
    def generate_response(self, prompt: str, context: str = "", **kwargs) -> str:
        """Generate a response from the AI model."""
        ...


class VectorDB(Protocol):
    """Protocol for vector database implementations."""
    
    def search(self, query_vector: List[float], top_k: int = 5, 
               metadata_filter: Optional[Dict] = None) -> List[SearchResult]:
        """Search for similar vectors."""
        ...
    
    def add_documents(self, texts: List[str], vectors: List[List[float]], 
                     metadata: List[Dict[str, Any]]) -> None:
        """Add documents to the database."""
        ...


class Embedder(Protocol):
    """Protocol for text embedding implementations."""
    
    def embed_text(self, text: str) -> List[float]:
        """Embed a single text."""
        ...
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts."""
        ...


class CommandHandler(ABC):
    """Base class for command handlers."""
    
    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """Execute the command with given arguments."""
        pass
    
    def validate_args(self, **kwargs) -> bool:
        """Validate command arguments. Override if needed."""
        return True


class ResultFormatter(ABC):
    """Base class for result formatters."""
    
    @abstractmethod
    def format_search_results(self, results: List[SearchResult]) -> str:
        """Format search results for display."""
        pass
    
    @abstractmethod
    def format_info(self, info: Dict[str, Any]) -> str:
        """Format knowledge base info for display."""
        pass
    
    @abstractmethod
    def format_metadata_summary(self, summary: Dict[str, Any]) -> str:
        """Format metadata summary for display."""
        pass
