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
from ..exceptions import ProcessingError


class DocumentProcessor:
    """Simplified document processor using Docling."""

    def __init__(self, config: Config):
        """Initialize the document processor.

        Args:
            config: Configuration object
        """
        self.config = config
        
        # Initialize tokenizer and chunker
        model_name = config.embedder_model
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        
        self.tokenizer = HuggingFaceTokenizer(
            tokenizer=tokenizer,
            max_tokens=tokenizer.model_max_length,
        )
        
        self.chunker = HybridChunker(tokenizer=self.tokenizer)
        self.converter = DocumentConverter()

class DocumentProcessor:
    """Simplified document processor using Docling."""

    def __init__(self, config: Config):
        """Initialize the document processor.

        Args:
            config: Configuration object
        """
        self.config = config
        
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

    def _is_file_processed(self, file_path: Path, database=None) -> bool:
        """Check if file has already been processed.
        
        Args:
            file_path: Path to the file
            database: Optional database instance to check for existing documents
            
        Returns:
            True if file was already processed, False otherwise
        """
        file_hash = self._calculate_file_hash(file_path)
        
        # Check in-memory cache first
        if file_hash in self.processed_files:
            return True
        
        # If database is available, check for existing documents by file_hash
        if database:
            try:
                # Ensure indexes exist before filtering
                database.ensure_indexes()
                
                # Search for documents with this file hash
                scroll_result = database.client.scroll(
                    collection_name=database.collection_name,
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

    def _remove_existing_file_documents(self, file_path: Path, database=None) -> None:
        """Remove existing documents for a file when force reprocessing.
        
        Args:
            file_path: Path to the file
            database: Database instance to remove documents from
        """
        if not database:
            return
            
        try:
            file_hash = self._calculate_file_hash(file_path)
            
            # Ensure indexes exist before filtering
            database.ensure_indexes()
            
            # Find all points with this file hash
            scroll_result = database.client.scroll(
                collection_name=database.collection_name,
                scroll_filter={
                    "must": [
                        {"key": "file_hash", "match": {"value": file_hash}}
                    ]
                },
                limit=10000,  # Assume no more than 10k chunks per file
                with_payload=False,
                with_vectors=False
            )
            
            points_to_delete = [point.id for point in scroll_result[0]]
            
            if points_to_delete:
                from qdrant_client.models import PointIdsList
                database.client.delete(
                    collection_name=database.collection_name,
                    points_selector=PointIdsList(points=points_to_delete)
                )
                print(f"🗑️  Removed {len(points_to_delete)} existing chunks for {file_path.name}")
                
            # Remove from processed files cache
            self.processed_files.discard(file_hash)
            
        except Exception as e:
            print(f"⚠️  Warning: Could not remove existing documents for {file_path.name}: {e}")

    def process_file(self, file_path: str, source: Optional[str] = None, 
                    force: bool = False, database=None) -> List[Dict[str, Any]]:
        """Process a single file and return chunks.

        Args:
            file_path: Path to the file to process
            source: Source category (ordinances, manuals, etc.)
            force: Force reprocessing if already processed
            database: Optional database instance for duplicate checking

        Returns:
            List of chunk dictionaries with text and metadata
        """
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                raise ProcessingError(f"File not found: {file_path}")

            # Check if file was already processed (unless force is True)
            if not force and self._is_file_processed(file_path, database):
                print(f"⏭️  Skipping {file_path.name} (already processed)")
                return []
            
            # If force reprocessing, remove existing documents
            if force:
                self._remove_existing_file_documents(file_path, database)

            print(f"Processing: {file_path}")

            # Convert document using Docling
            doc = self.converter.convert(str(file_path)).document
            if not doc:
                raise ProcessingError(f"Failed to convert {file_path}")

            # Chunk the document
            chunks = self.chunker.chunk(doc)
            if not chunks:
                print(f"No chunks created for {file_path}")
                return []

            # Calculate file hash for duplicate detection
            file_hash = self._calculate_file_hash(file_path)

            # Process chunks and add metadata
            processed_chunks = []
            for chunk in chunks:
                contextualized_text = self.chunker.contextualize(chunk=chunk)
                metadata = chunk.meta.export_json_dict()

                # Determine source category
                source_category = self._determine_source(file_path, source)

                chunk_data = {
                    'text': contextualized_text,
                    'metadata': {
                        "filename": file_path.name,
                        "headings": metadata.get('headings', []),
                        "source": source_category,
                        "file_path": str(file_path),
                        "file_hash": file_hash  # Add file hash for duplicate detection
                    }
                }
                processed_chunks.append(chunk_data)

            # Mark file as processed
            self.processed_files.add(file_hash)
            
            print(f"✅ Created {len(processed_chunks)} chunks from {file_path.name}")
            return processed_chunks

        except Exception as e:
            raise ProcessingError(f"Failed to process {file_path}: {e}")

    def process_directory(self, directory_path: str, source: Optional[str] = None, 
                         force: bool = False, recursive: bool = True, database=None) -> List[Dict[str, Any]]:
        """Process all supported files in a directory.

        Args:
            directory_path: Path to the directory to process
            source: Source category (ordinances, manuals, etc.)
            force: Force reprocessing if already processed
            recursive: Whether to process subdirectories recursively
            database: Optional database instance for duplicate checking

        Returns:
            List of chunk dictionaries from all processed files
        """
        try:
            directory_path = Path(directory_path)
            if not directory_path.exists():
                raise ProcessingError(f"Directory not found: {directory_path}")
            
            if not directory_path.is_dir():
                raise ProcessingError(f"Path is not a directory: {directory_path}")

            print(f"Processing directory: {directory_path}")
            
            all_chunks = []
            processed_files = 0
            skipped_files = 0
            
            # Get all supported files in directory
            pattern = "**/*" if recursive else "*"
            for file_path in directory_path.glob(pattern):
                if file_path.is_file() and self.is_supported_file(str(file_path)):
                    try:
                        chunks = self.process_file(str(file_path), source, force, database)
                        if chunks:
                            all_chunks.extend(chunks)
                            processed_files += 1
                        else:
                            skipped_files += 1
                    except ProcessingError as e:
                        print(f"⚠️  Skipping {file_path.name}: {e}")
                        continue
            
            if skipped_files > 0:
                print(f"✅ Processed {processed_files} files, skipped {skipped_files} already processed, created {len(all_chunks)} total chunks")
            else:
                print(f"✅ Processed {processed_files} files, created {len(all_chunks)} total chunks")
            return all_chunks

        except Exception as e:
            raise ProcessingError(f"Failed to process directory {directory_path}: {e}")

    def process_path(self, path: str, source: Optional[str] = None, 
                    force: bool = False, database=None) -> List[Dict[str, Any]]:
        """Process a file or directory path.

        Args:
            path: Path to file or directory to process
            source: Source category (ordinances, manuals, etc.)
            force: Force reprocessing if already processed
            database: Optional database instance for duplicate checking

        Returns:
            List of chunk dictionaries from processed file(s)
        """
        path_obj = Path(path)
        
        if not path_obj.exists():
            raise ProcessingError(f"Path not found: {path}")
        
        if path_obj.is_file():
            return self.process_file(path, source, force, database)
        elif path_obj.is_dir():
            return self.process_directory(path, source, force, database=database)
        else:
            raise ProcessingError(f"Invalid path type: {path}")

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
        if folder_name in ['ordinances', 'manuals', 'checklists']:
            return folder_name
        
        return 'other'

    def get_supported_extensions(self) -> List[str]:
        """Get list of supported file extensions."""
        return ['.pdf', '.docx', '.doc']

    def is_supported_file(self, file_path: str) -> bool:
        """Check if file is supported for processing."""
        return Path(file_path).suffix.lower() in self.get_supported_extensions()
