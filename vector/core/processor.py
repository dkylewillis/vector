"""Simplified document processor for Vector."""

import os
import hashlib
from pathlib import Path
from typing import List, Optional, Tuple
from enum import Enum
from ..config import Config
from ..exceptions import ProcessingError, VectorError
from .converter import DocumentConverter
from .chunking import DocumentChunker
from .embedder import Embedder
from .database import VectorDatabase
from .collection_manager import CollectionManager
from .artifacts import ArtifactProcessor
from .models import Chunk, ChunkMetadata, DocumentResult


class PipelineType(Enum):
    """Enum for document processing pipeline types."""
    VLM = "vlm"
    PDF = "pdf"


class DocumentProcessor:
    """Complete document processing and indexing service using Docling."""
    
    # Constants
    BATCH_SIZE = 100
    MAX_CHUNKS_PER_FILE = 10000
    SUPPORTED_EXTENSIONS = ['.pdf', '.docx', '.doc']
    DEFAULT_SOURCE_CATEGORIES = ['ordinances', 'manuals', 'checklists']

    def __init__(self, config: Config, collection_name: Optional[str] = None, collection_manager: Optional[CollectionManager] = None):
        """Initialize the document processor.

        Args:
            config: Configuration object
            collection_name: Name of the collection pair (display name). Optional for file conversion only.
            collection_manager: Optional collection manager for name resolution
        """
        self.config = config
        self.collection_name = collection_name
        self.collection_manager = collection_manager
        
        # Resolve collection pair if collection manager and collection_name are provided
        self.pair_info = None
        if collection_manager and collection_name:
            self.pair_info = collection_manager.get_pair_by_display_name(collection_name)
            if not self.pair_info:
                raise ValueError(f"Collection pair with display name '{collection_name}' not found")
        
        # Initialize core components
        self.embedder = Embedder(config)
        
        # Create vector databases only if we have collection info
        if self.pair_info:
            self.chunks_vector_db = VectorDatabase(self.pair_info['chunks_collection'], config, collection_manager)
            self.artifacts_vector_db = VectorDatabase(self.pair_info['artifacts_collection'], config, collection_manager)
        elif collection_name:
            # Fallback for when not using collection manager but collection_name provided
            self.chunks_vector_db = VectorDatabase(collection_name, config, collection_manager)
            self.artifacts_vector_db = self.chunks_vector_db  # Use same collection as fallback
        else:
            # File conversion only mode - no databases needed
            self.chunks_vector_db = None
            self.artifacts_vector_db = None
        
        self.chunker = DocumentChunker(config.embedder_model)
        
        # Initialize artifact processor only if we have databases
        if self.chunks_vector_db and self.artifacts_vector_db:
            self.artifact_processor = ArtifactProcessor(self.embedder, self.artifacts_vector_db)
        else:
            self.artifact_processor = None
        
        # Note: converter will be created per operation based on artifact needs
        
        # Track processed files by file hash (only used when databases are available)
        self.processed_files = set()

    def process_documents_to_chunks(self, doc_results: List[DocumentResult]) -> List[Tuple[Chunk, List[float]]]:
        """Process documents through chunking and embedding pipeline.
        
        Args:
            doc_results: List of DocumentResult objects
            
        Returns:
            List of tuples (chunk, embedding_vector)
        """
        # Use batch chunking from chunker
        chunks = self.chunker.chunk_documents_batch(doc_results)
        
        # Use batch embedding from embedder
        chunks_with_embeddings = self.embedder.embed_chunks_batch(chunks, batch_size=32)
        
        return chunks_with_embeddings

    def execute_processing_pipeline(self, files: List[str], pipeline_type: PipelineType, 
                                   include_artifacts: bool = True, force: bool = False, 
                                   source: Optional[str] = None) -> str:
        """Main pipeline: Convert → Chunk → Embed → Store.
        
        Args:
            files: List of file or directory paths to process
            pipeline_type: VLM or PDF pipeline
            include_artifacts: Whether to process artifacts (images, tables)
            force: Force reprocessing of existing documents
            source: Source type for documents
            
        Returns:
            Processing status message
        """
        try:
            # Step 1: Convert documents
            doc_results = self.convert_documents(files, pipeline_type, include_artifacts, force, source)
            
            # Step 2: Chunk and embed
            chunks_with_embeddings = self.process_documents_to_chunks(doc_results)
            
            # Step 3: Store in vector database
            self.store_chunks(chunks_with_embeddings)
            
            return f"✅ Pipeline completed for {len(doc_results)} documents"
        except Exception as e:
            raise ProcessingError(f"Pipeline failed: {e}")

    def convert_documents(self, files: List[str], pipeline_type: PipelineType, 
                         include_artifacts: bool, force: bool, source: Optional[str]) -> List[DocumentResult]:
        """Convert files using Docling, handle artifacts if needed.
        
        Args:
            files: List of file paths
            pipeline_type: VLM or PDF pipeline
            include_artifacts: Whether to process artifacts
            force: Force reprocessing
            source: Source type
            
        Returns:
            List of DocumentResult objects
        """
        results = []
        use_vlm = (pipeline_type == PipelineType.VLM)
        
        for file_path in files:
            path_obj = Path(file_path)
            if not path_obj.exists():
                print(f"⚠️  Skipping {file_path}: Path not found")
                continue
                
            if path_obj.is_dir():
                # Handle directories recursively
                for file_in_dir in path_obj.rglob("*"):
                    if file_in_dir.is_file() and self.is_supported_file(str(file_in_dir)):
                        doc_result = self._convert_single_document(file_in_dir, source, include_artifacts, use_vlm, force)
                        if doc_result:
                            results.append(doc_result)
            elif path_obj.is_file() and self.is_supported_file(str(path_obj)):
                doc_result = self._convert_single_document(path_obj, source, include_artifacts, use_vlm, force)
                if doc_result:
                    results.append(doc_result)
            else:
                print(f"⚠️  Skipping {file_path}: Unsupported file type")
                
        return results

    def convert_documents_to_files(self, files: List[str], pipeline_type: PipelineType, 
                                   include_artifacts: bool, output_dir: Path, 
                                   output_format: str, save_to_storage: bool = False, 
                                   source: Optional[str] = None, verbose: bool = False) -> List[str]:
        """Convert documents and save to files (without indexing).
        
        Args:
            files: List of file paths
            pipeline_type: VLM or PDF pipeline
            include_artifacts: Whether to process artifacts
            output_dir: Directory to save outputs
            output_format: 'markdown' or 'json'
            save_to_storage: Whether to save to filesystem storage
            source: Source type
            verbose: Enable verbose output
            
        Returns:
            List of result messages
        """
        results = []
        use_vlm = (pipeline_type == PipelineType.VLM)
        
        for file_path in files:
            path_obj = Path(file_path)
            if not path_obj.exists():
                results.append(f"❌ File not found: {file_path}")
                continue
                
            if path_obj.is_dir():
                # Handle directories recursively
                for file_in_dir in path_obj.rglob("*"):
                    if file_in_dir.is_file() and self.is_supported_file(str(file_in_dir)):
                        result = self._convert_single_document_to_file(
                            file_in_dir, source, include_artifacts, use_vlm, 
                            output_dir, output_format, save_to_storage, verbose
                        )
                        if result:
                            results.append(result)
            elif path_obj.is_file() and self.is_supported_file(str(path_obj)):
                result = self._convert_single_document_to_file(
                    path_obj, source, include_artifacts, use_vlm,
                    output_dir, output_format, save_to_storage, verbose
                )
                if result:
                    results.append(result)
            else:
                results.append(f"❌ Unsupported file type: {file_path}")
                
        return results

    def _convert_single_document_to_file(self, file_path: Path, source: Optional[str], 
                                        include_artifacts: bool, use_vlm: bool,
                                        output_dir: Path, output_format: str,
                                        save_to_storage: bool, verbose: bool) -> Optional[str]:
        """Convert a single document and save to file."""
        try:
            if verbose:
                print(f"🔄 Converting: {file_path.name}")
            
            # Use factory method from converter to get configured converter
            pipeline_type = PipelineType.VLM if use_vlm else PipelineType.PDF
            converter = DocumentConverter.create_for_pipeline(pipeline_type, include_artifacts)
            
            # Initialize storage if needed
            storage = None
            if save_to_storage:
                from .filesystem import FileSystemStorage
                storage = FileSystemStorage(self.config)
                if verbose:
                    print(f"💾 Using filesystem storage: {storage.base_path}")
            
            # Initialize artifact processor for storage-only mode
            artifact_processor = None
            if include_artifacts and storage:
                from .artifacts import ArtifactProcessor
                artifact_processor = ArtifactProcessor(storage=storage, save_only=True)
                if verbose:
                    print("🔧 ArtifactProcessor initialized for storage-only mode")
            
            # Convert to DocumentResult with metadata and artifact processing
            doc_result = converter.convert_to_document_result(
                file_path=file_path,
                source=source,
                artifact_processor=artifact_processor if include_artifacts else None,
                run_async=False  # Don't run async internally, handle it in CLI context
            )
            
            if verbose:
                print(f"   ✅ Converted: {file_path.name}")
            
            # Save to filesystem storage if requested
            if save_to_storage and storage:
                try:
                    doc_id = storage.save_document(doc_result)
                    if verbose:
                        print(f"   💾 Saved document with ID: {doc_id}")
                    
                    # Also save markdown to storage directory
                    if output_format == 'markdown':
                        markdown_content = doc_result.document.export_to_markdown()
                        storage.save_markdown(doc_result, markdown_content)
                        if verbose:
                            print(f"   💾 Saved markdown to storage: {file_path.stem}.md")
                except Exception as storage_error:
                    return f"❌ Failed to save to storage: {storage_error}"
            
            # Generate output filename
            base_name = file_path.stem
            if output_format == 'markdown':
                output_file = output_dir / f"{base_name}.md"
                # Save as markdown
                from docling_core.types.doc import ImageRefMode
                doc_result.document.save_as_markdown(
                    str(output_file), 
                    image_mode=ImageRefMode.REFERENCED
                )
                return f"✅ Converted to markdown: {output_file}"
            elif output_format == 'json':
                output_file = output_dir / f"{base_name}.json"
                # Save document data as JSON
                import json
                doc_data = {
                    'filename': file_path.name,
                    'source_category': doc_result.source_category,
                    'file_hash': doc_result.file_hash,
                    'content': doc_result.document.export_to_markdown()
                }
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(doc_data, f, indent=2, ensure_ascii=False)
                return f"✅ Converted to JSON: {output_file}"
            else:
                return f"❌ Unsupported format: {output_format}"
                
        except Exception as e:
            return f"❌ Failed to process {file_path.name}: {e}"

    def _convert_single_document(self, file_path: Path, source: Optional[str], 
                                include_artifacts: bool, use_vlm: bool, force: bool) -> Optional[DocumentResult]:
        """Convert a single document - simplified orchestration."""
        try:
            if not force and self._is_file_processed(file_path):
                print(f"⏭️  Skipping {file_path.name} (already processed)")
                return None
            
            if force:
                self._remove_existing_file_documents(file_path)
                
            # Use factory method from converter to get configured converter
            pipeline_type = PipelineType.VLM if use_vlm else PipelineType.PDF
            converter = DocumentConverter.create_for_pipeline(pipeline_type, include_artifacts)
            
            # Convert to DocumentResult with metadata and artifact processing
            doc_result = converter.convert_to_document_result(
                file_path=file_path,
                source=source,
                artifact_processor=self.artifact_processor if include_artifacts and self.artifact_processor else None
            )
            
            if self.chunks_vector_db:  # Only track if we have databases
                self.processed_files.add(doc_result.file_hash)
            return doc_result
        except Exception as e:
            print(f"⚠️  Error converting {file_path}: {e}")
            return None

    def chunk_and_embed(self, doc_results: List[DocumentResult]) -> List[tuple]:
        """Chunk documents and generate embeddings using batch processing.
        
        Args:
            doc_results: List of DocumentResult objects
            
        Returns:
            List of tuples (chunk, embedding_vector)
        """
        # Use batch chunking from chunker
        chunks = self.chunker.chunk_documents_batch(doc_results)
        
        # Use batch embedding from embedder
        chunks_with_embeddings = self.embedder.embed_chunks_batch(chunks, batch_size=32)
        
        return chunks_with_embeddings

    def store_chunks(self, chunks_with_embeddings: List[tuple]) -> None:
        """Store chunks and embeddings in vector database using batch processing.
        
        Args:
            chunks_with_embeddings: List of (chunk, embedding) tuples
        """
        if not chunks_with_embeddings:
            return
            
        # Ensure collections exist
        if not self.chunks_vector_db.collection_exists():
            vector_size = self.embedder.get_embedding_dimension()
            self.chunks_vector_db.create_collection(vector_size=vector_size)
            self.chunks_vector_db.ensure_indexes()
        
        if self.artifacts_vector_db != self.chunks_vector_db and not self.artifacts_vector_db.collection_exists():
            vector_size = self.embedder.get_embedding_dimension()
            self.artifacts_vector_db.create_collection(vector_size=vector_size)
            self.artifacts_vector_db.ensure_indexes()
        
        # Add document to collection pair metadata if we have pair info
        if self.pair_info and self.collection_manager and chunks_with_embeddings:
            doc_metadata = chunks_with_embeddings[0][0].metadata.model_dump()
            document_id = doc_metadata.get('file_hash', doc_metadata.get('filename', 'unknown'))
            self.collection_manager.add_document_to_pair(
                self.pair_info['pair_id'], 
                document_id, 
                {
                    'filename': doc_metadata.get('filename'),
                    'source': doc_metadata.get('source'),
                    'file_path': doc_metadata.get('file_path')
                }
            )
        
        # Use batch storage from database
        self.chunks_vector_db.store_chunks_batch(chunks_with_embeddings, batch_size=self.BATCH_SIZE)

    def _is_file_processed(self, file_path: Path) -> bool:
        """Check if file has already been processed.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if file was already processed, False otherwise
        """
        # If no database available, assume not processed
        if not self.chunks_vector_db:
            return False
            
        # Use a temporary converter instance to calculate hash
        temp_converter = DocumentConverter()
        file_hash = temp_converter._calculate_file_hash(file_path)
        
        # Check in-memory cache first
        if file_hash in self.processed_files:
            return True
        
        # Check for existing documents by file_hash in chunks database
        try:
            # Ensure indexes exist before filtering
            self.chunks_vector_db.ensure_indexes()
            
            # Search for documents with this file hash
            scroll_result = self.chunks_vector_db.client.scroll(
                collection_name=self.chunks_vector_db.collection_name,
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
        # If no database available, nothing to remove
        if not self.chunks_vector_db or not self.artifacts_vector_db:
            return
            
        try:
            # Use a temporary converter instance to calculate hash
            temp_converter = DocumentConverter()
            file_hash = temp_converter._calculate_file_hash(file_path)
            
            # Remove from both chunks and artifacts collections
            for db_name, vector_db in [("chunks", self.chunks_vector_db), ("artifacts", self.artifacts_vector_db)]:
                try:
                    # Ensure indexes exist before filtering
                    vector_db.ensure_indexes()
                    
                    # Find all points with this file hash
                    scroll_result = vector_db.client.scroll(
                        collection_name=vector_db.collection_name,
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
                        vector_db.client.delete(
                            collection_name=vector_db.collection_name,
                            points_selector=PointIdsList(points=points_to_delete)
                        )
                        if points_to_delete:  # Only log if we actually deleted something
                            print(f"🗑️  Removed {len(points_to_delete)} existing {db_name} for {file_path.name}")
                            
                except Exception as e:
                    print(f"⚠️  Warning: Could not remove existing {db_name} for {file_path.name}: {e}")
                    
            # Remove from processed files cache
            self.processed_files.discard(file_hash)
            
        except Exception as e:
            print(f"⚠️  Warning: Could not remove existing documents for {file_path.name}: {e}")

    def get_supported_extensions(self) -> List[str]:
        """Get list of supported file extensions."""
        return self.SUPPORTED_EXTENSIONS.copy()

    def is_supported_file(self, file_path: str) -> bool:
        """Check if file is supported for processing."""
        return Path(file_path).suffix.lower() in self.get_supported_extensions()
