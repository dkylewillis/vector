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
from .filesystem import FileSystemStorage as FS


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
        
        # Initialize artifact processor (pure processing, no storage)
        if self.embedder:
            self.artifact_processor = ArtifactProcessor(self.embedder, debug=False)
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
                                source: Optional[str] = None, from_storage: bool = False) -> str:
        """Main pipeline: Convert → Chunk → Embed → Store.
        
        Args:
            files: List of file or directory paths to process OR filenames if from_storage=True
            pipeline_type: VLM or PDF pipeline (ignored if from_storage=True)
            include_artifacts: Whether to process artifacts (images, tables)
            force: Force reprocessing of existing documents
            source: Source type for documents
            from_storage: If True, load documents from storage by filename instead of converting
            
        Returns:
            Processing status message
        """
        try:
            if from_storage:
                # Step 1: Load documents from storage instead of converting
                doc_results = self.load_documents_from_storage(files)
            else:
                # Step 1: Convert documents
                doc_results = self.convert_documents(files, pipeline_type, include_artifacts, force, source)
            
            # Step 2: Chunk and embed
            chunks_with_embeddings = self.process_documents_to_chunks(doc_results)
            
            # Step 3: Store in vector database
            self.store_chunks(chunks_with_embeddings)

            # Step 4: Process and store artifacts (if enabled and we have databases)
            if include_artifacts and doc_results and self.artifacts_vector_db:
                import asyncio
                asyncio.run(self._handle_artifacts(doc_results, save_to_storage= True, save_to_vector=True))

            # Step 5: Save Document Results (skip if from_storage since already saved)
            if not from_storage:
                self.save_document_results(doc_results)

            return f"✅ Pipeline completed for {len(doc_results)} documents"
        except Exception as e:
            raise ProcessingError(f"Pipeline failed: {e}")

    def load_documents_from_storage(self, filenames: List[str]) -> List[DocumentResult]:
        """Load already-converted documents from filesystem storage.
        
        Args:
            filenames: List of original filenames to load
            
        Returns:
            List of DocumentResult objects reconstructed from storage
        """
        storage = FS(self.config)
        doc_results = []
        
        for filename in filenames:
            try:
                loaded_doc_and_metadata = storage.load_document_by_filename(filename)
                if loaded_doc_and_metadata:
                    loaded_doc, metadata = loaded_doc_and_metadata
                    # Reconstruct DocumentResult from stored data
                    doc_result = DocumentResult(
                        document=loaded_doc,
                        file_path=Path(metadata['file_path']),
                        source_category=metadata['source_category'],
                        file_hash=metadata['file_hash']
                    )
                    doc_results.append(doc_result)
                    print(f"📂 Loaded from storage: {filename}")
                else:
                    print(f"⚠️  Document not found in storage: {filename}")
            except Exception as e:
                print(f"❌ Error loading {filename} from storage: {e}")
        
        return doc_results
        
    def save_document_results(self, doc_results: List[DocumentResult]) -> None:
        for doc_result in doc_results:
            try:
                # Save to filesystem storage
                storage = FS(self.config)
                doc_id = storage.save_document(doc_result)
                print(f"   💾 Saved document with ID: {doc_id}")
                
                # Also save markdown to storage directory
                markdown_content = doc_result.document.export_to_markdown()
                storage.save_markdown(doc_result, markdown_content)
                print(f"   💾 Saved markdown to storage: {doc_result.file_path.stem}.md")
            except Exception as e:
                print(f"❌ Failed to save {doc_result.file_path.name} to storage: {e}")

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
            
            # Note: Artifact processing is deferred - converter only converts documents
            # Artifacts will be handled separately if needed
            
            # Convert to DocumentResult with metadata
            doc_result = converter.convert_to_document_result(
                file_path=file_path,
                source=source,
                artifact_processor=None,  # Artifacts processed separately in the pipeline
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
        
        # Store chunks in vector database (auto-tracking will handle collection metadata)
        self.chunks_vector_db.store_chunks_batch(chunks_with_embeddings, batch_size=self.BATCH_SIZE)

    async def _handle_artifacts(self, doc_results: List[DocumentResult], 
                              save_to_storage: bool = False, save_to_vector: bool = True) -> None:
        """Orchestrate artifact processing and storage.
        
        Args:
            doc_results: List of document results to process
            save_to_storage: Whether to save artifacts to filesystem storage
            save_to_vector: Whether to save artifacts to vector database
        """
        if not self.artifact_processor:
            return
            
        for doc_result in doc_results:
            try:
                # 1. Process artifacts (pure processing)
                processed_artifacts = await self.artifact_processor.process_artifacts(doc_result)
                
                if not processed_artifacts:
                    continue
                
                print(f"📊 Indexed {len(processed_artifacts)} artifacts from {doc_result.file_path.name}")
                
                # 2. Storage decisions (orchestration)
                artifacts_stored = 0
                
                if save_to_storage:
                    # Save original and thumbnail to filesystem
                    storage = FS(self.config)
                    for artifact in processed_artifacts:
                        try:
                            if artifact.raw_data:
                                storage.save_artifact(artifact.raw_data, doc_result.file_hash, 
                                                     artifact.ref_item, artifact.artifact_type)
                            if artifact.thumbnail_data:
                                storage.save_artifact(artifact.thumbnail_data, doc_result.file_hash, 
                                                     artifact.ref_item, "thumbnail")
                        except Exception as e:
                            print(f"⚠️  Error saving artifact {artifact.ref_item} to storage: {e}")
                
                if save_to_vector and self.artifacts_vector_db:
                    # Ensure artifacts collection exists
                    if not self.artifacts_vector_db.collection_exists():
                        vector_size = self.embedder.get_embedding_dimension()
                        self.artifacts_vector_db.create_collection(vector_size=vector_size)
                        self.artifacts_vector_db.ensure_indexes()
                    
                    # Prepare data for vector storage
                    texts = []
                    embeddings = []
                    metadata_list = []
                    
                    for artifact in processed_artifacts:
                        if artifact.embedding:  # Only store artifacts with embeddings
                            text = (
                                f'Headings: {" > ".join(artifact.metadata.get("headings", []))}\n'
                                f'Before Text: {artifact.metadata.get("before_text", "")}\n'
                                f'Caption: {artifact.caption}\n'
                                f'After Text: {artifact.metadata.get("after_text", "")}'
                            )
                            texts.append(text)
                            embeddings.append(artifact.embedding)
                            metadata_list.append(artifact.metadata)
                            artifacts_stored += 1
                    
                    if texts:
                        self.artifacts_vector_db.add_artifacts(texts, embeddings, metadata_list)
                
                if save_to_vector and artifacts_stored > 0:
                    print(f"💾 Stored {artifacts_stored}/{len(processed_artifacts)} artifacts in vector database")
                    
            except Exception as e:
                print(f"⚠️  Error processing artifacts for {doc_result.file_path.name}: {e}")

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
            
            # Search for documents with this file hash using proper Filter model
            from qdrant_client.models import Filter
            scroll_filter = Filter(
                must=[
                    {"key": "file_hash", "match": {"value": file_hash}}
                ]
            )
            scroll_result = self.chunks_vector_db.client.scroll(
                collection_name=self.chunks_vector_db.collection_name,
                scroll_filter=scroll_filter,
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
                    
                    # Find all points with this file hash using proper Filter model
                    from qdrant_client.models import Filter
                    scroll_filter = Filter(
                        must=[
                            {"key": "file_hash", "match": {"value": file_hash}}
                        ]
                    )
                    scroll_result = vector_db.client.scroll(
                        collection_name=vector_db.collection_name,
                        scroll_filter=scroll_filter,
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
