from __future__ import annotations
from pathlib import Path
from typing import Dict, Optional, List, Literal, Union, Tuple, Any
from pydantic import BaseModel, Field, model_validator
import json
import io
from datetime import datetime, timezone
from PIL import Image as PILImage
from docling_core.types.doc.document import (
    DoclingDocument,
    RefItem,
    TextItem,
    TableItem,
    PictureItem,
    SectionHeaderItem,
)


# ============================================================================
# VectorDocument - Parser-agnostic document representation
# ============================================================================

class DocumentSection(BaseModel):
    """A logical section of the document."""
    section_id: str
    heading: Optional[str] = None
    level: int = 1  # Heading level (1 = h1, 2 = h2, etc.)
    text: str
    page_number: Optional[int] = None
    bbox: Optional[List[float]] = None  # [x0, y0, x1, y1]


class TableElement(BaseModel):
    """A table in the document."""
    table_id: str
    caption: Optional[str] = None
    data: List[List[str]]  # 2D array of cell values
    page_number: Optional[int] = None
    image_path: Optional[str] = None  # Path to rendered table image


class ImageElement(BaseModel):
    """An image in the document."""
    image_id: str
    caption: Optional[str] = None
    image_path: str  # Path to the image file
    page_number: Optional[int] = None
    bbox: Optional[List[float]] = None


class HeaderElement(BaseModel):
    """A heading/title in the document."""
    header_id: str
    text: str
    level: int  # 1-6 like HTML h1-h6
    page_number: Optional[int] = None


class VectorDocument(BaseModel):
    """Internal document representation independent of parsing library.
    
    This abstraction allows any document parser (Docling, Unstructured, 
    PyMuPDF, etc.) to be used as long as they convert to this format.
    """
    document_id: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Core content
    text: str  # Full document text
    sections: List[DocumentSection] = Field(default_factory=list)
    
    # Structured elements
    tables: List[TableElement] = Field(default_factory=list)
    images: List[ImageElement] = Field(default_factory=list)
    headers: List[HeaderElement] = Field(default_factory=list)
    
    # Original source info
    source_path: Optional[str] = None
    source_format: Optional[str] = None  # pdf, docx, html, etc.
    page_count: Optional[int] = None


def get_item_by_ref(doc: DoclingDocument, ref: str):
    """Find a document item by its reference string.
    
    Args:
        doc: DoclingDocument to search
        ref: Reference string to find (e.g., "#/table/0")
        
    Returns:
        The matching item or None if not found
    """
    for item, _ in doc.iterate_items():
        if getattr(item, "self_ref", None) == ref:
            return item
    return None


class DocumentRecord(BaseModel):
    """Pydantic model for document registry records."""
    
    document_id: str
    display_name: str
    original_path: str
    file_extension: str
    registered_date: datetime
    last_updated: datetime
    has_artifacts: bool = False
    artifact_count: int = 0
    chunk_count: int = 0
    chunk_collection: Optional[str] = None
    tags: List[str] = Field(default_factory=list)

    def add_tags(self, tags: List[str]) -> None:
        """Add tags to the document.
        
        Args:
            tags: List of tags to add (will be normalized to lowercase)
        """
        if not tags:
            return
        
        # Normalize to lowercase and remove duplicates
        normalized_tags = [tag.strip().lower() for tag in tags if tag.strip()]
        current_tags = set(self.tags)
        current_tags.update(normalized_tags)
        self.tags = list(current_tags)
        self.last_updated = datetime.now(timezone.utc)
    
    def remove_tags(self, tags: List[str]) -> None:
        """Remove tags from the document.
        
        Args:
            tags: List of tags to remove (will be normalized to lowercase)
        """
        if not tags:
            return
        
        # Normalize to lowercase for consistent removal
        normalized_tags = [tag.strip().lower() for tag in tags if tag.strip()]
        current_tags = set(self.tags)
        current_tags.difference_update(normalized_tags)
        self.tags = list(current_tags)
        self.last_updated = datetime.now(timezone.utc)

class Artifact(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    self_ref: str
    type: Literal["picture", "table"]                    # e.g., "#/table/0"
    image_file_path: Optional[str] = None    # relative path to PNG
    image_thumbnail_path: Optional[str] = None  # relative path to thumbnail PNG
    headings: Optional[List[str]] = Field(default_factory=list)
    before_text: Optional[str] = None
    after_text: Optional[str] = None
    caption: Optional[str] = None
    page_number: Optional[int] = None

    @classmethod
    def from_picture_item(
        cls,
        item: PictureItem,
        doc: DoclingDocument,
        headings: Optional[List[str]] = None,
        before_text: Optional[str] = None,
        after_text: Optional[str] = None
    ) -> "Artifact":
        """Create Artifact from PictureItem."""
        caption = item.caption_text(doc=doc) or "Image without description"
        
        return cls(
            self_ref=item.self_ref,
            type="picture",
            image_file_path="",  # Will be set later when saved
            headings=headings if headings is not None else [],
            before_text=before_text,
            after_text=after_text,
            caption=caption
        )
    
    @classmethod
    def from_table_item(
        cls,
        item: TableItem,
        doc: DoclingDocument,
        headings: Optional[List[str]] = None,
        before_text: Optional[str] = None,
        after_text: Optional[str] = None
    ) -> "Artifact":
        """Create Artifact from TableItem."""
        caption = item.caption_text(doc=doc) or "Table without description"
        
        return cls(
            self_ref=item.self_ref,
            type="table",
            image_file_path="",
            headings=headings if headings is not None else [],
            before_text=before_text,
            after_text=after_text,
            caption=caption,
        )

    def build_thumbnail_path(self, base_path: Union[str, Path]) -> str:
        """Build thumbnail path string from base path and self_ref.
        
        Args:
            base_path: Base directory path for thumbnails
            
        Returns:
            Full path string to the thumbnail file
            
        Example:
            For self_ref="#/table/0", returns "{base_path}/table_0_thumb.png"
        """
        base_path = Path(base_path)
        
        # Clean self_ref: remove '#/' and replace '/' with '_'
        # "#/table/0" -> "table_0"
        clean_ref = self.self_ref.lstrip('#/').replace('/', '_')
        
        # Build thumbnail filename
        thumbnail_filename = f"{clean_ref}_thumb.png"
        
        return str(base_path / thumbnail_filename)


class Chunk(BaseModel):
    chunk_id: str
    chunk_index: Optional[int] = None  # Position of chunk in document (0-based), optional for backward compatibility
    text: str
    page_number: Optional[int] = None
    headings: List[str] = Field(default_factory=list)
    doc_items: List[str] = Field(default_factory=list)  # links to artifacts
    artifacts: List[Artifact] = Field(default_factory=list)  # auto-filtered from doc_items



class ConvertedDocument(BaseModel):
    doc: DoclingDocument
    
    @classmethod
    def load_converted_document(cls, filename: Union[str, Path]) -> ConvertedDocument:
        """Load an already-converted document from filesystem storage.

        Args:
            filename: Path to the JSON file containing the DoclingDocument

        Returns:
            ConvertedDocument object reconstructed from storage
        """
        try:
            doc = DoclingDocument.load_from_json(filename)
            return cls(doc=doc)
        except Exception as e:
            raise ValueError(f"Failed to load document from {filename}: {e}")
        
    def get_chunks(self) -> List[Chunk]:
        from vector.pipeline import DocumentChunker
        return DocumentChunker().chunk_document(self.doc)

    def get_artifacts(self) -> List[Artifact]:
        """Process artifacts and return structured data.
        
        Returns:
            List of processed artifacts with all extracted data
        """
        artifacts = []
        heading_stack = []
        items = list(self.doc.iterate_items())
        
        for idx, (item, level) in enumerate(items):
            if isinstance(item, SectionHeaderItem):
                heading_stack = self._update_heading_stack(heading_stack, item, level)
            elif isinstance(item, (PictureItem, TableItem)):
                artifact = self._process_artifact_item(item, level, heading_stack.copy(), items, idx)
                if artifact:
                    artifacts.append(artifact)
        
        return artifacts
    
    def _process_artifact_item(
        self,
        item: Union[PictureItem, TableItem],
        level: int,
        heading_stack: List[Dict],
        items: List,
        idx: int
    ) -> Optional[Artifact]:
        """Process a picture or table item into an Artifact."""
        
        # Get context text
        before_text = self._get_context_text(items, idx, direction="before", max_chars=200)
        after_text = self._get_context_text(items, idx, direction="after", max_chars=200)
        headings = self._get_heading_context(heading_stack)
        
        # Use appropriate factory method based on item type
        if isinstance(item, PictureItem):
            return Artifact.from_picture_item(
                item=item,
                doc=self.doc,
                headings=headings,
                before_text=before_text,
                after_text=after_text
            )
        elif isinstance(item, TableItem):
            return Artifact.from_table_item(
                item=item,
                doc=self.doc,
                headings=headings,
                before_text=before_text,
                after_text=after_text
            )
        else:
            return None
    
    def _get_context_text(self, items: List[Tuple], current_idx: int, direction: str, max_chars: int = 200) -> Optional[str]:
        """Extract context text before or after the current item."""
        context_parts = []
        chars_collected = 0
        
        range_func = range(current_idx - 1, -1, -1) if direction == "before" else range(current_idx + 1, len(items))
        
        for i in range_func:
            item, _ = items[i]
            if isinstance(item, TextItem) and item.text:
                text = item.text.strip()
                if text:
                    if direction == "before":
                        context_parts.insert(0, text)
                    else:
                        context_parts.append(text)
                    chars_collected += len(text)
                    if chars_collected >= max_chars:
                        break
        
        if context_parts:
            full_context = " ".join(context_parts)
            return full_context[:max_chars] if len(full_context) > max_chars else full_context
        return None

    def _update_heading_stack(self, heading_stack: List[Dict], item: SectionHeaderItem, level: int) -> List[Dict]:
        """Update heading stack with new section header."""
        heading_info = {
            "text": item.text.strip() if hasattr(item, 'text') else "",
            "level": level,
            "ref": item.self_ref
        }
        
        # Remove headings at the same or deeper level
        heading_stack = [h for h in heading_stack if h['level'] < level]
        heading_stack.append(heading_info)
        
        return heading_stack

    def _get_heading_context(self, heading_stack: List[Dict]) -> List[str]:
        """Get hierarchical heading context."""
        return [heading["text"] for heading in heading_stack if heading["text"]]

    def _extract_table_text(self, doc: DoclingDocument, item: TableItem) -> str:
        """Extract table text content."""
        try:
            return item.text.strip() if hasattr(item, 'text') and item.text else item.export_to_markdown(doc=doc)
        except Exception:
            return ""
