"""Document artifact processing for Vector."""

import json
import base64
import io
import asyncio
from typing import List, Optional, Dict, Tuple
from pathlib import Path
from datetime import datetime

from docling_core.types.doc.document import RefItem, TextItem, TableItem, PictureItem, DoclingDocument, SectionHeaderItem

from .models import DocumentResult, ProcessedArtifact
from .embedder import Embedder
from ..config import Config
from .utils import extract_ref_id, image_to_hexhash

import hashlib

from PIL import Image as PILImage


class ArtifactProcessor:
    """Pure artifact processing - extracts and processes artifacts without storage logic.
    
    Handles:
    - Artifact extraction from documents
    - Metadata generation
    - Thumbnail generation
    - Embedding generation
    
    Does NOT handle storage - that's handled by DocumentProcessor orchestration.
    """
    
    def __init__(self, embedder: Optional[Embedder] = None, debug: bool = False, 
                 generate_thumbnails: bool = True, thumbnail_size: Tuple[int, int] = (150, 150)):
        """Initialize artifact processor.
        
        Args:
            embedder: Optional embedder for generating vector embeddings
            debug: Enable debug logging
            generate_thumbnails: Whether to generate thumbnail images
            thumbnail_size: Size for generated thumbnails
        """
        self.embedder = embedder
        self.debug = debug
        self.generate_thumbnails = generate_thumbnails
        self.thumbnail_size = thumbnail_size
        
    async def process_artifacts(self, doc_result: DocumentResult) -> List[ProcessedArtifact]:
        """Process artifacts and return structured data - doesn't save anything.
        
        Args:
            doc_result: Document to process
            
        Returns:
            List of processed artifacts with all extracted data
        """
        processed_artifacts = []
        heading_stack = []
        doc = doc_result.document
        
        # Convert to list for bidirectional access
        items = list(doc.iterate_items())
        
        self._debug_print(f"Processing artifacts from {doc_result.file_path.name}")
        
        for idx, (item, level) in enumerate(items):
            if isinstance(item, SectionHeaderItem):
                heading_stack = self._update_heading_stack(heading_stack, item, level)
                    
            elif isinstance(item, PictureItem):
                try:
                    artifact = await self._process_picture_item(item, doc_result, level, heading_stack.copy(), items, idx)
                    if artifact:
                        processed_artifacts.append(artifact)
                        self._debug_print(f"Processed image artifact: {artifact.ref_item}")
                except Exception as e:
                    self._debug_print(f"Error processing picture {item.self_ref}: {e}")
                    
            elif isinstance(item, TableItem):
                try:
                    artifact = await self._process_table_item(item, doc_result, level, heading_stack.copy(), items, idx)
                    if artifact:
                        processed_artifacts.append(artifact)
                        self._debug_print(f"Processed table artifact: {artifact.ref_item}")
                except Exception as e:
                    self._debug_print(f"Error processing table {item.self_ref}: {e}")
        
        self._debug_print(f"Processed {len(processed_artifacts)} artifacts from {doc_result.file_path.name}")
        return processed_artifacts
    
    async def _process_picture_item(self, item: PictureItem, doc_result: DocumentResult, 
                                   level: int, heading_stack: List[Dict], items: List, idx: int) -> Optional[ProcessedArtifact]:
        """Process a picture item into a ProcessedArtifact."""
        doc = doc_result.document
        
        # Get context text
        before_text = self._get_context_text(items, idx, direction="before", max_chars=200)
        after_text = self._get_context_text(items, idx, direction="after", max_chars=200)
        
        # Extract metadata
        metadata = self._get_picture_metadata(item, doc_result, level, heading_stack, before_text, after_text)
        
        # Get caption for embedding
        caption = item.caption_text(doc=doc) or "Image without description"
        
        # Generate embedding if embedder available
        embedding = None
        if self.embedder:
            embedding = self.embedder.embed_text(caption)
        
        # Extract raw image data
        raw_data = None
        thumbnail_data = None
        try:
            if hasattr(item, 'image') and item.image:
                raw_data = item.image.export_as_bytes()
                
                # Generate thumbnail if requested
                if self.generate_thumbnails and raw_data:
                    thumbnail_data = self._generate_thumbnail_bytes(raw_data)
        except Exception as e:
            self._debug_print(f"Error extracting image data: {e}")
        
        return ProcessedArtifact(
            ref_item=item.self_ref,
            artifact_type="image",
            raw_data=raw_data,
            thumbnail_data=thumbnail_data,
            embedding=embedding,
            metadata=metadata,
            caption=caption
        )
    
    async def _process_table_item(self, item: TableItem, doc_result: DocumentResult, 
                                 level: int, heading_stack: List[Dict], items: List, idx: int) -> Optional[ProcessedArtifact]:
        """Process a table item into a ProcessedArtifact."""
        doc = doc_result.document
        
        # Get context text
        before_text = self._get_context_text(items, idx, direction="before", max_chars=200)
        after_text = self._get_context_text(items, idx, direction="after", max_chars=200)
        
        # Extract table text and metadata
        table_text = self._extract_table_text(doc, item)
        metadata = self._get_table_metadata(item, doc_result, level, heading_stack, before_text, after_text, table_text)
        
        # Get caption for embedding
        caption = item.caption_text(doc=doc) or f"Table with {len(table_text)} content"
        full_text = f"{caption}\n{table_text}" if table_text else caption
        
        # Generate embedding if embedder available
        embedding = None
        if self.embedder:
            embedding = self.embedder.embed_text(full_text)
        
        return ProcessedArtifact(
            ref_item=item.self_ref,
            artifact_type="table",
            raw_data=table_text.encode('utf-8') if table_text else None,
            thumbnail_data=None,  # Tables don't have thumbnails
            embedding=embedding,
            metadata=metadata,
            caption=full_text
        )
    
    def _generate_thumbnail_bytes(self, image_data: bytes) -> Optional[bytes]:
        """Generate thumbnail bytes from image data."""
        try:
            image = PILImage.open(io.BytesIO(image_data))
            image.thumbnail(self.thumbnail_size, PILImage.Resampling.LANCZOS)
            
            # Convert to bytes
            output = io.BytesIO()
            image.save(output, format='JPEG', quality=85)
            return output.getvalue()
        except Exception as e:
            self._debug_print(f"Error generating thumbnail: {e}")
            return None
    
    def _get_context_text(self, items: List[Tuple], current_idx: int, direction: str, max_chars: int = 200) -> Optional[str]:
        """Extract context text before or after the current item."""
        context_parts = []
        chars_collected = 0
        
        if direction == "before":
            for i in range(current_idx - 1, -1, -1):
                item, level = items[i]
                if isinstance(item, TextItem):
                    text = item.text.strip()
                    if text:
                        context_parts.insert(0, text)
                        chars_collected += len(text)
                        if chars_collected >= max_chars:
                            break
        else:  # direction == "after"
            for i in range(current_idx + 1, len(items)):
                item, level = items[i]
                if isinstance(item, TextItem):
                    text = item.text.strip()
                    if text:
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
    
    def _get_picture_metadata(self, item: PictureItem, doc_result: DocumentResult, 
                             level: int, heading_stack: List[Dict], before_text: str = None, after_text: str = None) -> Dict:
        """Get metadata for a picture artifact."""
        doc = doc_result.document
        caption = item.caption_text(doc=doc) or "Image without description"
        headings = self._get_heading_context(heading_stack)
        
        return {
            'ref_item': item.self_ref,
            'type': 'image',
            'caption': caption,
            'filename': doc_result.file_path.name,
            'source': doc_result.source_category,
            'file_path': str(doc_result.file_path),
            'file_hash': doc_result.file_hash,
            'level': level,
            'headings': headings,
            'before_text': before_text,
            'after_text': after_text
        }
    
    def _get_table_metadata(self, item: TableItem, doc_result: DocumentResult, 
                           level: int, heading_stack: List[Dict], before_text: str = None, 
                           after_text: str = None, table_text: str = None) -> Dict:
        """Get metadata for a table artifact."""
        doc = doc_result.document
        caption = item.caption_text(doc=doc) or f"Table with {len(table_text or '')} content"
        headings = self._get_heading_context(heading_stack)

        return {
            'ref_item': item.self_ref,
            'type': 'table',
            'caption': caption,
            'table_text': table_text,
            'filename': doc_result.file_path.name,
            'source': doc_result.source_category,
            'file_path': str(doc_result.file_path),
            'file_hash': doc_result.file_hash,
            'level': level,
            'headings': headings,
            'before_text': before_text,
            'after_text': after_text
        }
    
    def _extract_table_text(self, doc: DoclingDocument, item: TableItem) -> str:
        """Extract table text content."""
        try:
            if hasattr(item, 'text') and item.text:
                return item.text.strip()
            else:
                return item.export_to_markdown(doc=doc)
        except Exception as e:
            self._debug_print(f"Error extracting table text: {e}")
            return ""
    
    def _debug_print(self, message: str):
        """Print debug message if debug mode enabled."""
        if self.debug:
            print(f"🔧 {message}")
