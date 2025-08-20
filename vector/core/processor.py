"""Simplified document processor for Vector."""

import os
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional

from docling.document_converter import DocumentConverter
from docling.chunking import HybridChunker
from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer
from transformers import AutoTokenizer

from ..config import Config
from ..exceptions import ProcessingError, VectorError
from .embedder import Embedder
from .database import VectorDatabase
from .collection_manager import CollectionManager
from .models import Chunk, ChunkMetadata, DocumentResult

class DocumentProcessor:
    """Complete document processing and indexing service using Docling."""
    
    # Constants
    BATCH_SIZE = 100
    MAX_CHUNKS_PER_FILE = 10000
    SUPPORTED_EXTENSIONS = ['.pdf', '.docx', '.doc']
    DEFAULT_SOURCE_CATEGORIES = ['ordinances', 'manuals', 'checklists']

    def __init__(self, config: Config, collection_name: str, collection_manager: Optional[CollectionManager] = None):
        """Initialize the document processor.

        Args:
            config: Configuration object
            collection_name: Name of the vector collection (can be display name if collection_manager provided)
            collection_manager: Optional collection manager for name resolution
        """
        self.config = config
        self.collection_name = collection_name
        self.collection_manager = collection_manager
        
        # Initialize embedding and database components
        self.embedder = Embedder(config)
        self.vector_db = VectorDatabase(collection_name, config, collection_manager)
        
        # Initialize tokenizer and chunker
        model_name = config.embedder_model
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        
        self.tokenizer = HuggingFaceTokenizer(
            tokenizer=tokenizer,
            max_tokens=tokenizer.model_max_length,
        )
        
        self.chunker = HybridChunker(tokenizer=self.tokenizer)
        self.converter = DocumentConverter()
        
        # Track processed files by file hash
        self.processed_files = set()

    def process_and_index_files(self, files: List[str], force: bool = False, 
                               source: Optional[str] = None) -> str:
        """Process and index documents in one step.
        
        Args:
            files: List of file or directory paths to process
            force: Force reprocessing of existing documents
            source: Source type for documents
            
        Returns:
            Processing status message
        """
        try:
            # Ensure collection exists
            if not self.vector_db.collection_exists():
                vector_size = self.embedder.get_embedding_dimension()
                self.vector_db.create_collection(vector_size=vector_size)
                self.vector_db.ensure_indexes()
            
            # Process each file or directory
            total_processed = 0
            processed_paths = 0
            
            for path in files:
                try:
                    chunks = self.process_path(path, source, force)
                    if chunks:
                        # Process in batches to avoid timeouts
                        batch_size = self.BATCH_SIZE  # Process 100 chunks at a time
                        for i in range(0, len(chunks), batch_size):
                            batch_chunks = chunks[i:i + batch_size]
                            
                            # Embed batch
                            texts = [chunk.text for chunk in batch_chunks]
                            vectors = self.embedder.embed_texts(texts)
                            metadata = [chunk.metadata.model_dump() for chunk in batch_chunks]
                            
                            # Add to vector database
                            self.vector_db.add_documents(texts, vectors, metadata)
                            total_processed += len(batch_chunks)
                            
                            print(f"📦 Processed batch: {len(batch_chunks)} chunks (Total: {total_processed})")
                        
                        processed_paths += 1
                except Exception as e:
                    print(f"⚠️  Error processing {path}: {e}")
                    continue
            
            return f"✅ Processed {total_processed} chunks from {processed_paths} path(s)"
            
        except Exception as e:
            raise VectorError(f"File processing failed: {e}")

    def process_document(self, file_path: Path, source: Optional[str] = None) -> DocumentResult:
        """Convert file to DocumentResult - reusable document conversion.
        
        Args:
            file_path: Path to the file to convert
            source: Source category (ordinances, manuals, etc.)
            
        Returns:
            DocumentResult object with converted document and metadata
        """
        print(f"Converting: {file_path}")
        
        # Convert document using Docling
        doc = self.converter.convert(str(file_path)).document
        if not doc:
            raise ProcessingError(f"Failed to convert {file_path}")
        
        # Calculate metadata
        file_hash = self._calculate_file_hash(file_path)
        source_category = self._determine_source(file_path, source)
        
        return DocumentResult(
            document=doc,
            file_path=file_path,
            source_category=source_category,
            file_hash=file_hash
        )

    def chunk_document(self, doc_result: DocumentResult) -> List[Chunk]:
        """Convert DocumentResult to chunks - separated chunking logic.
        
        Args:
            doc_result: DocumentResult from process_document()
            
        Returns:
            List of Chunk objects with text and metadata
        """
        # Chunk the document
        chunks = self.chunker.chunk(doc_result.document)
        if not chunks:
            print(f"No chunks created for {doc_result.file_path.name}")
            return []

        # Process chunks and add metadata
        processed_chunks = []
        for chunk in chunks:
            contextualized_text = self.chunker.contextualize(chunk=chunk)
            metadata = chunk.meta.export_json_dict()

            chunk_metadata = ChunkMetadata(
                filename=doc_result.file_path.name,
                headings=metadata.get('headings', []),
                source=doc_result.source_category,
                file_path=str(doc_result.file_path),
                file_hash=doc_result.file_hash
            )
            
            chunk_obj = Chunk(
                text=contextualized_text,
                metadata=chunk_metadata
            )
            processed_chunks.append(chunk_obj)

        print(f"✅ Created {len(processed_chunks)} chunks from {doc_result.file_path.name}")
        return processed_chunks

    def process_path(self, path: str, source: Optional[str] = None, 
                    force: bool = False, recursive: bool = True) -> List[Chunk]:
        """Process a file or directory path and return chunks.

        Args:
            path: Path to file or directory to process
            source: Source category (ordinances, manuals, etc.)
            force: Force reprocessing if already processed
            recursive: Whether to process subdirectories (ignored for files)

        Returns:
            List of Chunk objects from processed file(s)
        """
        path_obj = Path(path)
        
        if not path_obj.exists():
            raise ProcessingError(f"Path not found: {path}")
        
        all_chunks = []
        processed_files = 0
        skipped_files = 0
        
        if path_obj.is_file():
            # Single file processing
            if self.is_supported_file(str(path_obj)):
                chunks = self._process_single_file(path_obj, source, force)
                if chunks:
                    all_chunks.extend(chunks)
                    processed_files += 1
                else:
                    skipped_files += 1
            else:
                raise ProcessingError(f"Unsupported file type: {path_obj}")
                
        elif path_obj.is_dir():
            # Directory processing
            print(f"Processing directory: {path_obj}")
            pattern = "**/*" if recursive else "*"
            
            for file_path in path_obj.glob(pattern):
                if file_path.is_file() and self.is_supported_file(str(file_path)):
                    try:
                        chunks = self._process_single_file(file_path, source, force)
                        if chunks:
                            all_chunks.extend(chunks)
                            processed_files += 1
                        else:
                            skipped_files += 1
                    except ProcessingError as e:
                        print(f"⚠️  Skipping {file_path.name}: {e}")
                        continue
        else:
            raise ProcessingError(f"Invalid path type: {path}")
        
        # Summary output for directories
        if path_obj.is_dir():
            if skipped_files > 0:
                print(f"✅ Processed {processed_files} files, skipped {skipped_files} already processed, created {len(all_chunks)} total chunks")
            else:
                print(f"✅ Processed {processed_files} files, created {len(all_chunks)} total chunks")
        
        return all_chunks
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate hash of file content for duplicate detection.
        
        Args:
            file_path: Path to the file
            
        Returns:
            SHA256 hash of file content
        """
        hash_sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            raise ProcessingError(f"Failed to calculate hash for {file_path}: {e}")

    def _is_file_processed(self, file_path: Path) -> bool:
        """Check if file has already been processed.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if file was already processed, False otherwise
        """
        file_hash = self._calculate_file_hash(file_path)
        
        # Check in-memory cache first
        if file_hash in self.processed_files:
            return True
        
        # Check for existing documents by file_hash in database
        try:
            # Ensure indexes exist before filtering
            self.vector_db.ensure_indexes()
            
            # Search for documents with this file hash
            scroll_result = self.vector_db.client.scroll(
                collection_name=self.vector_db.collection_name,
                scroll_filter={
                    "must": [
                        {"key": "file_hash", "match": {"value": file_hash}}
                    ]
                },
                limit=1,
                with_payload=True,
                with_vectors=False
            )
            
            if scroll_result[0]:  # If any documents found
                self.processed_files.add(file_hash)
                return True
        except Exception as e:
            # If database check fails, proceed with processing
            pass
        
        return False

    def _remove_existing_file_documents(self, file_path: Path) -> None:
        """Remove existing documents for a file when force reprocessing.
        
        Args:
            file_path: Path to the file
        """
        try:
            file_hash = self._calculate_file_hash(file_path)
            
            # Ensure indexes exist before filtering
            self.vector_db.ensure_indexes()
            
            # Find all points with this file hash
            scroll_result = self.vector_db.client.scroll(
                collection_name=self.vector_db.collection_name,
                scroll_filter={
                    "must": [
                        {"key": "file_hash", "match": {"value": file_hash}}
                    ]
                },
                limit=self.MAX_CHUNKS_PER_FILE,  # Assume no more than 10k chunks per file
                with_payload=False,
                with_vectors=False
            )
            
            points_to_delete = [point.id for point in scroll_result[0]]
            
            if points_to_delete:
                from qdrant_client.models import PointIdsList
                self.vector_db.client.delete(
                    collection_name=self.vector_db.collection_name,
                    points_selector=PointIdsList(points=points_to_delete)
                )
                print(f"🗑️  Removed {len(points_to_delete)} existing chunks for {file_path.name}")
                
            # Remove from processed files cache
            self.processed_files.discard(file_hash)
            
        except Exception as e:
            print(f"⚠️  Warning: Could not remove existing documents for {file_path.name}: {e}")

    def _process_single_file(self, file_path: Path, source: Optional[str] = None, 
                            force: bool = False) -> List[Chunk]:
        """Process a single file and return chunks (internal method).

        Args:
            file_path: Path object for the file to process
            source: Source category (ordinances, manuals, etc.)
            force: Force reprocessing if already processed

        Returns:
            List of Chunk objects with text and metadata
        """
        try:
            # Check if file was already processed (unless force is True)
            if not force and self._is_file_processed(file_path):
                print(f"⏭️  Skipping {file_path.name} (already processed)")
                return []
            
            # If force reprocessing, remove existing documents
            if force:
                self._remove_existing_file_documents(file_path)

            # Convert to DocumentResult first
            doc_result = self.process_document(file_path, source)
            
            # Then chunk it
            chunks = self.chunk_document(doc_result)
            
            # Mark file as processed
            self.processed_files.add(doc_result.file_hash)
            
            return chunks

        except Exception as e:
            raise ProcessingError(f"Failed to process {file_path}: {e}")

    def _determine_source(self, file_path: Path, source: Optional[str]) -> str:
        """Determine source category from file path or explicit source.

        Args:
            file_path: Path to the file
            source: Explicit source category

        Returns:
            Source category string
        """
        if source:
            return source

        # Try to determine from folder name
        folder_name = file_path.parent.name.lower()
        if folder_name in self.DEFAULT_SOURCE_CATEGORIES:
            return folder_name
        
        return 'other'

    def get_supported_extensions(self) -> List[str]:
        """Get list of supported file extensions."""
        return self.SUPPORTED_EXTENSIONS.copy()

    def is_supported_file(self, file_path: str) -> bool:
        """Check if file is supported for processing."""
        return Path(file_path).suffix.lower() in self.get_supported_extensions()
