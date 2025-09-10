"""Data models for Vector."""

from typing import List, Dict, Any, Optional
from pathlib import Path
from pydantic import BaseModel, Field
from docling_core.types import DoclingDocument


class ChunkMetadata(BaseModel):
    """Metadata for a document chunk."""
    chunk_ref: Optional[str] = None  # Docling ref_item if available
    filename: str
    headings: List[str] = Field(default_factory=list)
    source: str
    file_path: str
    file_hash: str
    # Artifact references using Docling ref_item IDs
    referenced_artifacts: List[str] = Field(default_factory=list)  # ref_item IDs
    nearby_artifacts: List[str] = Field(default_factory=list)     # ref_item IDs in same section



class Chunk(BaseModel):
    """A document chunk with text and metadata."""
    text: str
    metadata: ChunkMetadata


class ArtifactMetadata(BaseModel):
    """Metadata for figures and tables."""
    ref_item: str  # Docling's ref_item ID - required for artifacts
    type: str  # "image" | "table" 
    title: str
    label: str
    caption: str
    page: int
    doc_id: str
    source: str
    heading_path: List[str] = Field(default_factory=list)
    nearby_text: str
    # References back to chunks using ref_item IDs
    related_chunks: List[str] = Field(default_factory=list)
    # ...existing optional fields...


class Artifact(BaseModel):
    """A figure or table artifact with embedding text and metadata."""
    text: str  # Assembled text for embedding
    metadata: ArtifactMetadata


class DocumentResult(BaseModel):
    """Result from document processing."""
    document: DoclingDocument
    file_path: Path
    source_category: str
    file_hash: str
    
    class Config:
        arbitrary_types_allowed = True  # For Path and DoclingDocument types


class ProcessedArtifact(BaseModel):
    """A processed artifact with all extracted data."""
    ref_item: str
    artifact_type: str  # "image" | "table"
    raw_data: Optional[bytes] = None  # Original image/table data
    thumbnail_data: Optional[bytes] = None  # Generated thumbnail
    embedding: Optional[List[float]] = None  # Vector embedding
    metadata: Dict[str, Any]  # Extracted metadata
    caption: str  # Text for embedding
    
    class Config:
        arbitrary_types_allowed = True



