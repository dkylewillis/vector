"""Abstract storage interfaces for Vector documents and artifacts."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from datetime import datetime

from docling_core.types.doc.document import DoclingDocument
from ..models import DocumentResult


class DocumentStorage(ABC):
    """Abstract interface for document storage."""
    
    @abstractmethod
    async def save_document(self, doc_result: DocumentResult) -> str:
        """Save document and return document ID."""
        pass
    
    @abstractmethod
    async def load_document(self, doc_id: str) -> Optional[Tuple[DoclingDocument, Dict]]:
        """Load document by ID, return (document, metadata)."""
        pass
    
    @abstractmethod
    async def list_documents(self, filters: Optional[Dict] = None) -> List[Dict]:
        """List documents with optional filters."""
        pass
    
    @abstractmethod
    async def delete_document(self, doc_id: str) -> bool:
        """Delete document by ID."""
        pass


class ArtifactStorage(ABC):
    """Abstract interface for artifact storage."""
    
    @abstractmethod
    async def save_artifact(self, artifact_data: bytes, doc_id: str, 
                           ref_item: str, artifact_type: str, 
                           metadata: Optional[Dict] = None) -> str:
        """Save artifact and return artifact ID."""
        pass
    
    @abstractmethod
    async def load_artifact(self, artifact_id: str) -> Optional[Tuple[bytes, Dict]]:
        """Load artifact by ID, return (data, metadata)."""
        pass
    
    @abstractmethod
    async def list_artifacts(self, doc_id: Optional[str] = None, 
                            artifact_type: Optional[str] = None) -> List[Dict]:
        """List artifacts with optional filters."""
        pass
    
    @abstractmethod
    async def delete_artifact(self, artifact_id: str) -> bool:
        """Delete artifact by ID."""
        pass


class StorageBackend(ABC):
    """Abstract storage backend combining document and artifact storage."""
    
    @abstractmethod
    def get_document_storage(self) -> DocumentStorage:
        """Get document storage instance."""
        pass
    
    @abstractmethod
    def get_artifact_storage(self) -> ArtifactStorage:
        """Get artifact storage instance."""
        pass
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize storage backend."""
        pass
    
    @abstractmethod
    async def cleanup(self) -> Dict[str, int]:
        """Cleanup orphaned data."""
        pass
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        pass
