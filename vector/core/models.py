"""Data models for Vector."""

from typing import List, Dict, Any, Optional
from pathlib import Path
from pydantic import BaseModel, Field
from docling_core.types import DoclingDocument


class ChunkMetadata(BaseModel):
    """Metadata for a document chunk."""
    filename: str
    headings: List[str] = Field(default_factory=list)
    source: str
    file_path: str
    file_hash: str


class Chunk(BaseModel):
    """A document chunk with text and metadata."""
    text: str
    metadata: ChunkMetadata


class ArtifactMetadata(BaseModel):
    """Metadata for figures and tables."""
    type: str  # "figure" | "table"
    title: str
    label: str
    caption: str
    page: int
    doc_id: str
    source: str
    heading_path: List[str] = Field(default_factory=list)
    nearby_text: str
    image_path: Optional[str] = None
    thumb_path: Optional[str] = None
    table_html: Optional[str] = None
    ocr_text: Optional[str] = None
    width_px: Optional[int] = None
    height_px: Optional[int] = None


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



