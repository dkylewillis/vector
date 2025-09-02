"""Document artifact processing for Vector."""

import json
import base64
import io
import asyncio
from typing import List, Optional, Dict, Tuple
from pathlib import Path
from datetime import datetime

from docling_core.types.doc.document import RefItem, TableItem, PictureItem, DoclingDocument, SectionHeaderItem

from .models import DocumentResult
from .embedder import Embedder
from .database import VectorDatabase
from ..config import Config
from .utils import extract_ref_id, image_to_hexhash
from .storage import StorageBackend, StorageFactory

import hashlib

from PIL import Image as PILImage


class ArtifactProcessor:
    """Handles document artifact (images, tables) processing and indexing."""
    
    def __init__(self, embedder: Optional[Embedder] = None, vector_db: Optional[VectorDatabase] = None, 
                 debug: bool = False, save_metadata: bool = False, 
                 generate_thumbnails: bool = True, thumbnail_size: Tuple[int, int] = (150, 150),
                 config: Optional[Config] = None, storage_backend: Optional[StorageBackend] = None):
        """Initialize artifact processor.
        
        Args:
            embedder: Embedder instance for creating embeddings
            vector_db: Vector database for storage
            debug: Enable debug output
            save_metadata: Save metadata to debug file
            generate_thumbnails: Whether to generate thumbnails for artifacts
            thumbnail_size: Max dimensions for thumbnails (width, height)
            config: Configuration instance
            storage_backend: Storage backend for documents and artifacts
        """
        self.embedder = embedder
        self.vector_db = vector_db
        self.debug = debug
        self.save_metadata = save_metadata
        self.generate_thumbnails = generate_thumbnails
        self.thumbnail_size = thumbnail_size
        self.config = config or Config()
        
        # Initialize storage backend
        self.storage_backend = storage_backend
        self._storage_initialized = False
        
    async def _ensure_storage_initialized(self) -> None:
        """Ensure storage backend is initialized."""
        if not self._storage_initialized and self.storage_backend:
            await self.storage_backend.initialize()
            self._storage_initialized = True
    
    async def process_document(self, doc_result: DocumentResult) -> None:
        """Process document with storage.
        
        Args:
            doc_result: Document result to process
        """
        await self._ensure_storage_initialized()
        
        # Save document if storage backend is available
        if self.storage_backend:
            doc_id = await self.storage_backend.get_document_storage().save_document(doc_result)
            print(f"📄 Saved document: {doc_id}")
        
        # Process artifacts
        await self.index_artifacts(doc_result)
    
    async def index_artifacts(self, doc_result: DocumentResult) -> None:
        """Index artifacts (images, tables) from a document.
        
        Args:
            doc_result: Document result with metadata
        """
        artifacts_processed = 0
        artifacts_stored = 0
        heading_stack = []  # Stack to track current heading hierarchy
        doc = doc_result.document
        
        for item, level in doc.iterate_items():
            
            if isinstance(item, SectionHeaderItem):
                # Update heading stack based on current level
                heading_stack = self._update_heading_stack(heading_stack, item, level)
                
            elif isinstance(item, PictureItem):
                # Step 1: Create metadata (always succeeds)
                metadata = await self._get_picture_metadata(item, doc_result, level, heading_stack.copy())
                artifacts_processed += 1
                
                # Step 2: Embed and store (can fail independently)
                if self._should_embed_and_store():
                    success = self._embed_and_store_picture(metadata['caption'], metadata)
                    if success:
                        artifacts_stored += 1
                
            elif isinstance(item, TableItem):
                # Step 1: Create metadata (always succeeds)
                metadata = await self._get_table_metadata(item, doc_result, level, heading_stack.copy())
                artifacts_processed += 1
                
                # Step 2: Embed and store (can fail independently)
                if self._should_embed_and_store():
                    table_text = self._extract_table_text(doc, item)
                    success = self._embed_and_store_table(table_text, metadata)
                    if success:
                        artifacts_stored += 1
        
        # Summary reporting
        if artifacts_processed > 0:
            print(f"📊 Indexed {artifacts_processed} artifacts from {doc_result.file_path.name}")
            if self._should_embed_and_store():
                print(f"💾 Stored {artifacts_stored}/{artifacts_processed} artifacts in vector database")

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
        return self.embedder is not None and self.vector_db is not None

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
                                         level: int, heading_stack: List[Dict]) -> Dict:
        """Get metadata for a picture artifact with storage backend."""
        doc = doc_result.document
        caption = item.caption_text(doc=doc) or "Image without description"
        headings = self._get_heading_context(heading_stack)
        
        metadata = {
            'ref_item': item.self_ref,  # Use Docling's ref_item ID
            'type': 'image',
            'caption': caption,
            'filename': doc_result.file_path.name,
            'source': doc_result.source_category,
            'file_path': str(doc_result.file_path),
            'file_hash': doc_result.file_hash,
            'level': level,
            'headings': headings,
            'has_thumbnail': False  # Default value
        }

        # Generate thumbnail and save artifact if enabled
        if self.generate_thumbnails:
            thumbnail_info = await self._generate_thumbnail(item, doc_result, "image")
            metadata.update(thumbnail_info)

        self._debug_print(f"Created image metadata with ref_item: {item.self_ref}")
        self._debug_save_metadata(metadata)

        return metadata

    async def _get_table_metadata(self, item: TableItem, doc_result: DocumentResult, 
                                       level: int, heading_stack: List[Dict]) -> Dict:
        """Get metadata for a table artifact with storage backend."""
        doc = doc_result.document
        table_text = self._extract_table_text(doc, item)
        caption = item.caption_text(doc=doc) or f"Table with {len(table_text)} content"
        headings = self._get_heading_context(heading_stack)

        metadata = {
            'ref_item': item.self_ref,  # Use Docling's ref_item ID
            'type': 'table',
            'caption': caption,
            'filename': doc_result.file_path.name,
            'source': doc_result.source_category,
            'file_path': str(doc_result.file_path),
            'file_hash': doc_result.file_hash,
            'level': level,
            'headings': headings,
            'has_thumbnail': False  # Default value
        }

        # Generate thumbnail and save artifact if enabled
        if self.generate_thumbnails:
            thumbnail_info = await self._generate_thumbnail(item, doc_result, "table")
            metadata.update(thumbnail_info)

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

    async def _generate_thumbnail(self, item, doc_result: DocumentResult, item_type: str) -> Dict:
        """Generate thumbnail for any artifact type.
        
        Args:
            item: Artifact item (PictureItem or TableItem)
            doc_result: Document result with metadata
            item_type: Type of item ("image" or "table")
            
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

            if self.storage_backend:
                # Save original artifact using storage backend
                artifact_id = await self.storage_backend.get_artifact_storage().save_artifact(
                    image_data, doc_result.file_hash, item.self_ref, item_type
                )

                # Save thumbnail as separate artifact
                thumbnail_buffer = io.BytesIO()
                thumbnail.save(thumbnail_buffer, format='PNG')
                thumbnail_data = thumbnail_buffer.getvalue()

                thumbnail_id = await self.storage_backend.get_artifact_storage().save_artifact(
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
            else:
                # Fallback to file system when no storage backend
                artifacts_dir = Path(self.config.artifacts_dir)
                thumbnails_dir = artifacts_dir / "thumbnails"
                thumbnails_dir.mkdir(parents=True, exist_ok=True)

                hexhash = image_to_hexhash(image)
                image_ref_id = extract_ref_id(item.self_ref)
                thumbnail_path = thumbnails_dir / f"{item_type}_{image_ref_id:06}_{hexhash}.png"
                thumbnail.save(thumbnail_path, "PNG")

                self._debug_print(f"Generated {item_type} thumbnail: {thumbnail_path}")

                return {
                    'thumbnail_path': str(thumbnail_path),
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

