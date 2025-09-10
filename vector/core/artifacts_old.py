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
        """Initialize artifact processor.
        
        Args:
            embedder: Embedder instance for creating embeddings
            vector_db: Vector database for storage
            debug: Enable debug output
            save_metadata: Save metadata to debug file
            generate_thumbnails: Whether to generate thumbnails for artifacts
            thumbnail_size: Max dimensions for thumbnails (width, height)
            config: Configuration instance
            storage: Filesystem storage instance
            save_only: If True, only save artifacts to storage without embedding/storing in vector DB
        """
        self.embedder = embedder
        self.vector_db = vector_db
        self.debug = debug
        self.save_metadata = save_metadata
        self.generate_thumbnails = generate_thumbnails
        self.thumbnail_size = thumbnail_size
        self.config = config or Config()
        self.save_only = save_only
        
        # Initialize storage
        self.storage = storage or FileSystemStorage(self.config)
        
    async def index_artifacts(self, doc_result: DocumentResult) -> None:
        """Index artifacts (images, tables) from a document."""
        if self.save_only:
            self._debug_print("Running in save-only mode - artifacts will be saved to storage without embedding")
        elif self._should_embed_and_store():
            self._debug_print("Running in full mode - artifacts will be embedded and stored in vector database")
        else:
            self._debug_print("Running in storage-only mode - artifacts will be saved to storage")
            
        artifacts_processed = 0
        artifacts_stored = 0
        heading_stack = []
        doc = doc_result.document
        
        # Convert to list for bidirectional access
        items = list(doc.iterate_items())
        
        for idx, (item, level) in enumerate(items):
            
            if isinstance(item, SectionHeaderItem):
                heading_stack = self._update_heading_stack(heading_stack, item, level)
                    
            elif isinstance(item, PictureItem):
                # Get before_text (200 chars before current item)
                before_text = self._get_context_text(items, idx, direction="before", max_chars=200)
                
                # Get after_text (200 chars after current item)  
                after_text = self._get_context_text(items, idx, direction="after", max_chars=200)
                
                # Pass context to metadata creation
                metadata = await self._get_picture_metadata(item, doc_result, level, heading_stack.copy(), 
                                                          before_text=before_text, after_text=after_text)
                
                # Generate thumbnail separately if enabled
                if self.generate_thumbnails:
                    thumbnail_info = await self._generate_thumbnail(item, doc_result, "image", extra_metadata=metadata)
                    metadata.update(thumbnail_info)
                    artifacts_processed += 1
                
                if self._should_embed_and_store():
                    success = self._embed_and_store_picture(metadata['caption'], metadata)
                    if success:
                        artifacts_stored += 1
                    
            elif isinstance(item, TableItem):
                # Same logic for tables
                before_text = self._get_context_text(items, idx, direction="before", max_chars=200)
                after_text = self._get_context_text(items, idx, direction="after", max_chars=200)
                
                # Pass context to metadata creation
                metadata = await self._get_table_metadata(item, doc_result, level, heading_stack.copy(),
                                                        before_text=before_text, after_text=after_text)
                
                # Generate thumbnail separately if enabled
                if self.generate_thumbnails:
                    thumbnail_info = await self._generate_thumbnail(item, doc_result, "table", extra_metadata=metadata)
                    metadata.update(thumbnail_info)

                artifacts_processed += 1
                
                if self._should_embed_and_store():
                    table_text = self._extract_table_text(doc, item)
                    success = self._embed_and_store_table(table_text, metadata)
                    if success:
                        artifacts_stored += 1

        # Summary reporting
        if artifacts_processed > 0:
            print(f"📊 Indexed {artifacts_processed} artifacts from {doc_result.file_path.name}")
            if self.save_only:
                print(f"💾 Saved {artifacts_processed} artifacts to storage (save-only mode)")
            elif self._should_embed_and_store():
                print(f"💾 Stored {artifacts_stored}/{artifacts_processed} artifacts in vector database")

    async def save_artifacts_only(self, doc_result: DocumentResult) -> None:
        """Save artifacts to storage without embedding or vector storage.
        
        Args:
            doc_result: Document result containing artifacts to save
        """
        # Temporarily set save_only mode
        original_save_only = self.save_only
        self.save_only = True
        try:
            await self.index_artifacts(doc_result)
        finally:
            self.save_only = original_save_only

    def _get_context_text(self, items: List[Tuple], current_idx: int, direction: str, max_chars: int = 200) -> Optional[str]:
        """Extract context text before or after the current item.
        
        Args:
            items: List of (item, level) tuples
            current_idx: Index of current item
            direction: "before" or "after"
            max_chars: Maximum characters to collect
            
        Returns:
            Context text or None if not enough content
        """
        text_buffer = ""
        
        if direction == "before":
            # Collect text from items before current index (backwards)
            for i in range(current_idx - 1, -1, -1):
                item, level = items[i]
                item_text = self._extract_item_text(item)
                if item_text:
                    # Add to beginning since we're going backwards
                    text_buffer = item_text + " " + text_buffer
                    if len(text_buffer) >= max_chars:
                        break
                        
        elif direction == "after":
            # Collect text from items after current index (forwards)
            for i in range(current_idx + 1, len(items)):
                item, level = items[i]
                item_text = self._extract_item_text(item)
                if item_text:
                    text_buffer += item_text + " "
                    if len(text_buffer) >= max_chars:
                        break
        
        # Trim to max_chars and clean up
        if text_buffer:
            text_buffer = text_buffer.strip()
            if len(text_buffer) > max_chars:
                if direction == "before":
                    text_buffer = text_buffer[-max_chars:]  # Keep end
                else:
                    text_buffer = text_buffer[:max_chars]   # Keep beginning
            return text_buffer
        
        return None

    def _extract_item_text(self, item) -> Optional[str]:
        """Extract text from any document item type."""
        # ✅ Check if item is TextItem
        if isinstance(item, TextItem) and item.text:
            return item.text
        
        # ✅ Check if item is SectionHeaderItem  
        elif isinstance(item, SectionHeaderItem) and item.text:
            return item.text
        
        # Check for other text-containing items
        elif hasattr(item, 'text') and item.text:
            return item.text
        
        # Try caption text for picture/table items
        elif hasattr(item, 'caption_text') and callable(item.caption_text):
            try:
                return item.caption_text()
            except:
                return None
                
        return None
    
    def _update_heading_stack(self, heading_stack: List[Dict], header_item: SectionHeaderItem, level: int) -> List[Dict]:
        """Update the heading stack based on the current header level.
        
        Args:
            heading_stack: Current stack of headings
            header_item: New header item
            level: Nesting level of the header
            
        Returns:
            Updated heading stack
        """
        # Create header info
        header_info = {
            'text': header_item.text or '',
            'level': level,
            'hierarchy_level': getattr(header_item, 'hierarchy_level', level)  # Use hierarchy_level if available
        }
        
        # Remove headers at same or deeper levels
        heading_stack = [h for h in heading_stack if h['hierarchy_level'] < header_info['hierarchy_level']]
        
        # Add current header
        heading_stack.append(header_info)
        
        return heading_stack

    def _should_embed_and_store(self) -> bool:
        """Check if embedding and storage should be performed."""
        return not self.save_only and self.embedder is not None and self.vector_db is not None

    def _debug_print(self, message: str) -> None:
        """Print debug message if debug mode is enabled."""
        if self.debug:
            print(f"🐛 {message}")

    def _get_heading_context(self, heading_stack: List[Dict]) -> List[str]:
        """Get the current heading context as a list of heading texts.
        
        Args:
            heading_stack: Current heading stack
            
        Returns:
            List of heading texts from root to current
        """
        return [h['text'] for h in heading_stack if h['text']]

    def _debug_save_metadata(self, metadata: Dict) -> None:
        """Save artifact metadata to debug file."""
        if not self.save_metadata:
            return
            
        debug_file = Path('artifacts_debug.txt')
        with open(debug_file, 'a', encoding='utf-8') as f:
            f.write(f"TIMESTAMP: {datetime.now().isoformat()}\n")
            f.write(f"{json.dumps(metadata, indent=2)}\n")
            f.write("-" * 80 + "\n")

    async def _get_picture_metadata(self, item: PictureItem, doc_result: DocumentResult, 
                                        level: int, heading_stack: List[Dict], before_text: str = None, after_text: str = None) -> Dict:
        """Get metadata for a picture artifact."""
        doc = doc_result.document
        caption = item.caption_text(doc=doc) or "Image without description"
        headings = self._get_heading_context(heading_stack)
        
        metadata = {
            'ref_item': item.self_ref,
            'type': 'image',
            'caption': caption,
            'filename': doc_result.file_path.name,
            'source': doc_result.source_category,
            'file_path': str(doc_result.file_path),
            'file_hash': doc_result.file_hash,
            'level': level,
            'headings': headings,
            'has_thumbnail': False,  # Default value
            'before_text': before_text,
            'after_text': after_text
        }

        self._debug_print(f"Created image metadata with ref_item: {item.self_ref}")
        self._debug_save_metadata(metadata)

        return metadata

    async def _get_table_metadata(self, item: TableItem, doc_result: DocumentResult, 
                                    level: int, heading_stack: List[Dict], before_text: str = None, after_text: str = None) -> Dict:
        """Get metadata for a table artifact."""
        doc = doc_result.document
        table_text = self._extract_table_text(doc, item)
        caption = item.caption_text(doc=doc) or f"Table with {len(table_text)} content"
        headings = self._get_heading_context(heading_stack)

        metadata = {
            'ref_item': item.self_ref,
            'type': 'table',
            'caption': caption,
            'table_text': table_text,  # Include table text in metadata
            'filename': doc_result.file_path.name,
            'source': doc_result.source_category,
            'file_path': str(doc_result.file_path),
            'file_hash': doc_result.file_hash,
            'level': level,
            'headings': headings,
            'has_thumbnail': False,  # Default value
            'before_text': before_text,
            'after_text': after_text
        }

        self._debug_print(f"Created table metadata with ref_item: {item.self_ref}")
        self._debug_save_metadata(metadata)

        return metadata

    def _embed_and_store_picture(self, caption: str, metadata: Dict) -> bool:
        """Embed and store picture caption in vector database.
        
        Args:
            caption: Caption text to embed
            metadata: Associated metadata
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self._debug_print(f"Embedding image: {caption[:50]}...")
            vector = self.embedder.embed_texts([caption])[0]
            
            self._debug_print(f"Storing image vector (dim: {len(vector)})")
            self.vector_db.add_documents([caption], [vector], [metadata])
            
            self._debug_print("✅ Image successfully stored")
            return True
            
        except Exception as e:
            print(f"❌ Failed to store image '{caption[:50]}...': {e}")
            if self.debug:
                import traceback
                traceback.print_exc()
            return False

    def _embed_and_store_table(self, table_text: str, metadata: Dict) -> bool:
        """Embed and store table content in vector database.

        Args:
            table_text: Text content of the table
            metadata: Associated metadata
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self._debug_print(f"Embedding table: {table_text[:50]}...")
            vector = self.embedder.embed_texts([table_text])[0]
            
            self._debug_print(f"Storing table vector (dim: {len(vector)})")
            self.vector_db.add_documents([table_text], [vector], [metadata])
            
            self._debug_print("✅ Table successfully stored")
            return True
            
        except Exception as e:
            print(f"❌ Failed to store table '{metadata.get('caption', 'Unknown')[:50]}...': {e}")
            if self.debug:
                import traceback
                traceback.print_exc()
            return False

    def _extract_table_text(self, doc: DoclingDocument, table_item: TableItem) -> str:
        """Extract text content from a table item.
        
        Args:
            table_item: Table item to extract text from
            
        Returns:
            Text representation of the table
        """
        # This is a placeholder - you'd implement actual table text extraction
        # based on the table structure in DoclingDocument
        return f"Table content: {table_item.export_to_markdown(doc=doc) or 'No description'}"

    async def _generate_thumbnail(self, item, doc_result: DocumentResult, item_type: str, extra_metadata: Dict = None) -> Dict:
        """Generate thumbnail for any artifact type.
        
        Args:
            item: Artifact item (PictureItem or TableItem)
            doc_result: Document result with metadata
            item_type: Type of item ("image" or "table")
            extra_metadata: Additional metadata to include (like before_text/after_text)
            
        Returns:
            Dict with thumbnail information
        """
        try:
            # Extract raw image data (works for both types)
            image_data = self._extract_image_data(item, doc_result.document)
            if not image_data:
                return {'has_thumbnail': False}

            # Create thumbnail
            image = PILImage.open(io.BytesIO(image_data))
            thumbnail = image.copy()
            thumbnail.thumbnail(self.thumbnail_size, PILImage.Resampling.LANCZOS)

            # Save original artifact using storage
            artifact_id = await self.storage.save_artifact(
                image_data, doc_result.file_hash, item.self_ref, item_type, metadata=extra_metadata
            )

            # Save thumbnail as separate artifact
            thumbnail_buffer = io.BytesIO()
            thumbnail.save(thumbnail_buffer, format='PNG')
            thumbnail_data = thumbnail_buffer.getvalue()

            thumbnail_id = await self.storage.save_artifact(
                thumbnail_data, doc_result.file_hash, item.self_ref, f"{item_type}_thumbnail",
                metadata={'original_artifact_id': artifact_id}
            )

            self._debug_print(f"Generated {item_type} thumbnail and saved to storage: {thumbnail_id}")

            return {
                'artifact_id': artifact_id,
                'thumbnail_id': thumbnail_id,
                'thumbnail_size': {"width": thumbnail.width, "height": thumbnail.height},
                'has_thumbnail': True
            }

        except Exception as e:
            self._debug_print(f"Failed to generate {item_type} thumbnail: {e}")
            return {'has_thumbnail': False}

    def _extract_image_data(self, item, doc: DoclingDocument) -> Optional[bytes]:
        """Extract raw image data from any artifact item.
        
        Args:
            item: Artifact item (PictureItem or TableItem)
            doc: Docling document
            
        Returns:
            Raw image bytes or None if not available
        """
        try:
            # Try nested image object
            if hasattr(item, 'image') and item.image:
                
                try:
                    pil_img = getattr(item.image, 'pil_image', None)
                except Exception as e:
                    pil_img = None
                    
                # Verify it's actually a PIL Image
                if isinstance(pil_img, PILImage.Image):
                    # Convert PIL Image to bytes    
                    buffer = io.BytesIO()
                    pil_img.save(buffer, format='PNG')
                    return buffer.getvalue()
                
                # Check for URI
                if hasattr(item.image, 'uri'):
                    uri = item.image.uri
                    
                    if isinstance(uri, Path):
                        artifacts_dir = Path(self.config.artifacts_dir)
                        image_path = artifacts_dir / uri
                        try:
                            with open(image_path, 'rb') as f:
                                return f.read()
                        except Exception as e:
                            self._debug_print(f"Error loading image from {image_path}: {e}")
            return None
            
        except Exception as e:
            self._debug_print(f"Error extracting image data for {item.self_ref}: {e}")
            return None

