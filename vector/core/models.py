"""Data models for Vector."""

from typing import List, Dict, Any, Optional, Literal
from pathlib import Path
from pydantic import BaseModel, Field
from docling_core.types import DoclingDocument


class ChunkMetadata(BaseModel):
    """Metadata for a document chunk."""
    doc_items: List[str] = Field(default_factory=list)  # List of Docling ref_items if available
    type: Literal["chunk"] = "chunk"
    filename: str
    headings: List[str] = Field(default_factory=list)
    source: str
    file_path: str
    file_hash: str
    # Artifact references using Docling ref_item IDs
    picture_items: List[str] = Field(default_factory=list)  # ref_item IDs
    table_items: List[str] = Field(default_factory=list)  # ref_item IDs

class Chunk(BaseModel):
    """A document chunk with text and metadata."""
    text: str
    metadata: ChunkMetadata


class DocumentResult(BaseModel):
    """Result from document processing."""
    document: DoclingDocument
    file_path: Path
    source_category: str
    file_hash: str
    
    class Config:
        arbitrary_types_allowed = True  # For Path and DoclingDocument types


class BaseArtifactMetadata(BaseModel):
    """Base metadata for all artifact types."""
    ref_item: str
    type: str  # "image" | "table"
    caption: str
    filename: str
    source: str
    file_path: str
    file_hash: str
    level: int
    headings: List[str] = Field(default_factory=list)
    before_text: Optional[str] = None
    after_text: Optional[str] = None


class PictureMetadata(BaseArtifactMetadata):
    """Metadata specific to picture artifacts."""
    type: Literal["image"] = "image"


class TableMetadata(BaseArtifactMetadata):
    """Metadata specific to table artifacts."""
    type: Literal["table"] = "table"
    table_text: Optional[str] = None


class ProcessedArtifact(BaseModel):
    """A processed artifact with all extracted data."""
    ref_item: str
    artifact_type: str  # "image" | "table"
    raw_data: Optional[bytes] = None  # Original image/table data
    thumbnail_data: Optional[bytes] = None  # Generated thumbnail
    embedding: Optional[List[float]] = None  # Vector embedding
    metadata: BaseArtifactMetadata  # Structured metadata
    caption: str  # Text for embedding
    
    class Config:
        arbitrary_types_allowed = True


class ChunkEmbeddingData(BaseModel):
    """Structured data for chunk embedding and storage."""
    text: str  # The chunk text
    embedding: List[float]
    metadata: ChunkMetadata
    
    @classmethod
    def from_chunk_and_embedding(cls, chunk: Chunk, embedding: List[float]) -> 'ChunkEmbeddingData':
        """Create embedding data from a chunk and its embedding."""
        return cls(
            text=chunk.text,
            embedding=embedding,
            metadata=chunk.metadata
        )


class ArtifactEmbeddingData(BaseModel):
    """Structured data for artifact embedding and storage."""
    text: str  # The full text used for embedding
    embedding: List[float]
    metadata: BaseArtifactMetadata
    
    @classmethod
    def from_processed_artifact(cls, artifact: 'ProcessedArtifact') -> Optional['ArtifactEmbeddingData']:
        """Create embedding data from a processed artifact."""
        if not artifact.embedding:
            return None
            
        # Consistent text formatting for artifacts
        text = cls._format_artifact_text(artifact)
        
        return cls(
            text=text,
            embedding=artifact.embedding,
            metadata=artifact.metadata
        )
    
    @staticmethod
    def _format_artifact_text(artifact: 'ProcessedArtifact') -> str:
        """Standardized text formatting for artifacts."""
        return (
            f'Headings: {" > ".join(artifact.metadata.headings or [])}\n'
            f'Before Text: {artifact.metadata.before_text or ""}\n'
            f'Caption: {artifact.caption}\n'
            f'After Text: {artifact.metadata.after_text or ""}'
        )


class StorageResult(BaseModel):
    """Result from storage operations."""
    processed_count: int
    stored_count: int
    errors: List[str] = Field(default_factory=list)
    
    def add_error(self, error: str) -> None:
        """Add an error message."""
        self.errors.append(error)
    
    def merge(self, other: 'StorageResult') -> 'StorageResult':
        """Merge with another storage result."""
        return StorageResult(
            processed_count=self.processed_count + other.processed_count,
            stored_count=self.stored_count + other.stored_count,
            errors=self.errors + other.errors
        )


class ChunkSearchResult(BaseModel):
    """Search result for chunk data using consistent models."""
    score: float
    text: str
    metadata: ChunkMetadata
    type: Literal["chunk"] = "chunk"
    
    @property
    def filename(self) -> str:
        """Get filename from metadata."""
        return self.metadata.filename
    
    @property
    def source(self) -> str:
        """Get source from metadata."""
        return self.metadata.source


class ArtifactSearchResult(BaseModel):
    """Search result for artifact data using consistent models."""
    score: float
    text: str
    metadata: BaseArtifactMetadata
    type: str  # "image" | "table"
    
    @property
    def filename(self) -> str:
        """Get filename from metadata."""
        return self.metadata.filename
    
    @property
    def source(self) -> str:
        """Get source from metadata."""
        return self.metadata.source


# Union type for search results
SearchResultType = ChunkSearchResult | ArtifactSearchResult



