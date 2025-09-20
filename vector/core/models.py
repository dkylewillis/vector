from __future__ import annotations
from pathlib import Path
from typing import Dict, Optional, List, Literal, Union, Tuple
from pydantic import BaseModel, Field
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

class Artifact(BaseModel):
    model_config = {"arbitrary_types_allowed": True}
    
    artifact_id: str
    type: Literal["picture", "table"]
    ref_item: str                     # e.g., "#/table/0"
    file_ref: str                     # relative path to PNG
    headings: List[str] = Field(default_factory=list)
    image: Optional[PILImage.Image] = None  # Loaded image (not serialized)
    before_text: Optional[str] = None
    after_text: Optional[str] = None
    caption: Optional[str] = None
    page_number: Optional[int] = None

class Chunk(BaseModel):
    chunk_id: str
    text: str
    page_number: Optional[int] = None
    headings: List[str] = Field(default_factory=list)
    doc_items: List[str] = Field(default_factory=list)  # links to artifacts
    picture_items: List[str] = Field(default_factory=list)  # ref_item IDs
    table_items: List[str] = Field(default_factory=list)  # ref_item IDs


class DocumentMetadataRecord(BaseModel):
    doc_id: str                          # same ID used in vector store
    display_name: str                     # alias for UI (human-friendly name)
    source_file_name: str
    artifacts_collection: Optional[str] = None
    chunks_collection: Optional[str] = None
    aliases: Optional[List[str]] = Field(default_factory=list)
    description: Optional[str] = None
    tags: Optional[List[str]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class FileInfo(BaseModel):
    filename: str
    size: Optional[int] = None
    format: str                       # e.g., "pdf", "docx"
    hash: str


class DocumentMetadata(BaseModel):
    page_count: int
    conversion_date: str              # ISO string
    pipeline_options: dict = Field(default_factory=dict)


class ConvertedDocument(BaseModel):
    doc: DoclingDocument
    
    # ---- Helpers ----
    def get_images(self) -> List[Artifact]:
        return []
    
    def get_image_by_ref(self, ref_item: str) -> Optional[Artifact]:
        return None

    def get_tables(self) -> List[Artifact]:
        return []
    
    def get_table_by_ref(self, ref_item: str) -> Optional[Artifact]:
        return None
    
    def get_chunks(self) -> List[Chunk]:
        from .chunker import DocumentChunker
        return DocumentChunker().chunk_document(self.doc)
    
    def embed(self) -> None:
        pass
    
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
            elif isinstance(item, PictureItem):
                artifact = self._process_picture_item(item, level, heading_stack.copy(), items, idx)
                if artifact:
                    artifacts.append(artifact)
            elif isinstance(item, TableItem):
                artifact = self._process_table_item(item, level, heading_stack.copy(), items, idx)
                if artifact:
                    artifacts.append(artifact)
        
        return artifacts
    
    def _process_picture_item(
        self,
        item: PictureItem,
        level: int,
        heading_stack: List[Dict],
        items: List,
        idx: int
    ) -> Optional[Artifact]:
        """Process a picture item into an Artifact."""
        
        # Get context text
        before_text = self._get_context_text(items, idx, direction="before", max_chars=200)
        after_text = self._get_context_text(items, idx, direction="after", max_chars=200)
        
        # Get caption
        caption = item.caption_text(doc=self.doc) or "Image without description"

        # Extract image
        image = item.get_image(doc=self.doc)
        
        return Artifact(
            artifact_id=item.self_ref,
            type="picture",
            ref_item=item.self_ref,
            file_ref="",  # Will be set later when saved
            image=image,
            headings=self._get_heading_context(heading_stack),
            before_text=before_text,
            after_text=after_text,
            caption=caption
        )
    def _process_table_item(
        self,
        item: TableItem,
        level: int,
        heading_stack: List[Dict],
        items: List,
        idx: int
    ) -> Optional[Artifact]:
        """Process a table item into a ProcessedArtifact."""
        
        # Get context text
        before_text = self._get_context_text(items, idx, direction="before", max_chars=200)
        after_text = self._get_context_text(items, idx, direction="after", max_chars=200)
        
        # Extract table text
        table_text = self._extract_table_text(self.doc, item)
        
        # Extract image if available
        image = item.get_image(doc=self.doc)
        
        # Get caption
        caption = item.caption_text(doc=self.doc) or f"Table with {len(table_text)} content"
        
        return Artifact(
            artifact_id=item.self_ref,
            type="table",
            ref_item=item.self_ref,
            file_ref="",  # Will be set later when saved
            headings=self._get_heading_context(heading_stack),
            before_text=before_text,
            after_text=after_text,
            caption=caption,
            image=image
        )
    
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
