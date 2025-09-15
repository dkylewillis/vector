"""Document management for Vector - handles documents independently from collections."""

import os
import shutil
import json
import asyncio
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from datetime import datetime

from ..config import Config
from .collection_manager import CollectionManager
from .database import VectorDatabase
from .document_utils import DocumentUtils


class DocumentManager:
    """Manages documents independently from collections."""
    
    def __init__(self, config: Optional[Config] = None, collection_manager: Optional[CollectionManager] = None):
        """Initialize document manager."""
        self.config = config or Config()
        self.collection_manager = collection_manager or CollectionManager(self.config)
        self.converted_docs_path = Path(self.config.artifacts_dir) / "converted_documents"
        self.converted_docs_path.mkdir(parents=True, exist_ok=True)
    
    def get_all_documents(self) -> List[Dict[str, Any]]:
        """Get all available documents across all collections."""
        return self.collection_manager.get_all_documents()
    
    def get_document_details(self, document_ids: List[str]) -> str:
        """Get detailed information about selected documents."""
        if not document_ids:
            return "No documents selected."
        
        details = []
        
        for doc_display in document_ids:
            # Extract filename from display format
            filename = DocumentUtils.extract_filename_from_display(doc_display)
            
            # Find document by filename using CollectionManager API
            doc_info = self.collection_manager.get_document_by_filename(filename)
            if doc_info:
                doc_id, doc_data = doc_info
                details.append(f"📄 **{filename}**")
                details.append(f"   - Document ID: {doc_id}")
                details.append(f"   - ULID: {doc_data.get('ulid', 'unknown')}")
                details.append(f"   - Status: {doc_data.get('status', 'active')}")
                details.append(f"   - Created: {doc_data.get('created_at', 'unknown')}")
                details.append(f"   - File Hash: {doc_data.get('file_hash', 'unknown')}")
                details.append(f"   - Source: {doc_data.get('metadata', {}).get('source', 'unknown')}")
                
                # Get collection names
                collections = DocumentUtils.ensure_collections_dict_format(
                    doc_data.get('in_collections', {})
                )
                if collections:
                    collection_names = []
                    for coll_id in collections.keys():
                        # Get collection display name
                        for pair in self.collection_manager.list_collection_pairs():
                            if f"cp_{pair['ulid']}" == coll_id:
                                collection_names.append(pair['display_name'])
                                break
                    details.append(f"   - Collections: {', '.join(collection_names) if collection_names else 'None'}")
                else:
                    details.append("   - Collections: None")
                
                # File path info
                file_path = doc_data.get('file_path', '')
                details.append(f"   - File Path: {file_path}")
                
                if file_path and DocumentUtils.validate_file_exists(file_path):
                    details.append("   - Files: ✅ Available")
                else:
                    details.append("   - Files: ❌ Missing")
                
                details.append("")
        
        return "\n".join(details) if details else "No matching documents found."
    
    def delete_documents_permanently(self, document_ids: List[str]) -> str:
        """Permanently delete documents from the system."""
        if not document_ids:
            return "No documents selected for deletion."
        
        results = []
        
        for doc_display in document_ids:
            # Extract filename from display format
            filename = DocumentUtils.extract_filename_from_display(doc_display)
            
            # Find document using CollectionManager API
            doc_info = self.collection_manager.get_document_by_filename(filename)
            if doc_info:
                doc_id, doc_data = doc_info
                results.append(f"🗑️  **{filename}**")
                
                # Remove from all collections in vector database
                collections = DocumentUtils.ensure_collections_dict_format(
                    doc_data.get('in_collections', {})
                )
                
                for coll_id in collections.keys():
                    try:
                        # Get collection pair info
                        pairs = self.collection_manager.list_collection_pairs()
                        pair_info = None
                        for pair in pairs:
                            if f"cp_{pair['ulid']}" == coll_id:
                                pair_info = pair
                                break
                        
                        if pair_info:
                            # Remove from chunks collection
                            removed_chunks = self._remove_document_from_vector_db(
                                pair_info['chunks_collection'], doc_data.get('file_hash', '')
                            )
                            if removed_chunks > 0:
                                results.append(f"   - ✅ Removed {removed_chunks} chunks from {pair_info['chunks_collection']}")
                            
                            # Remove from artifacts collection
                            removed_artifacts = self._remove_document_from_vector_db(
                                pair_info['artifacts_collection'], doc_data.get('file_hash', '')
                            )
                            if removed_artifacts > 0:
                                results.append(f"   - ✅ Removed {removed_artifacts} artifacts from {pair_info['artifacts_collection']}")
                        
                    except Exception as e:
                        results.append(f"   - ❌ Error removing from collection {coll_id}: {e}")
                
                # Delete converted files - use proper converted documents path
                file_hash = doc_data.get('file_hash', '')
                if file_hash:
                    converted_file_dir = self.converted_docs_path / file_hash
                    if converted_file_dir.exists():
                        try:
                            shutil.rmtree(converted_file_dir)
                            results.append(f"   - ✅ Deleted converted files: {converted_file_dir}")
                        except Exception as e:
                            results.append(f"   - ❌ Error deleting converted files: {e}")
                
                # Also try to delete the original file if it exists and is safe to delete
                file_path_str = doc_data.get('file_path', '')
                if file_path_str and DocumentUtils.validate_file_exists(file_path_str):
                    try:
                        file_path = Path(file_path_str)
                        # Only delete if it's in our data directory (safety check)
                        if str(file_path).startswith(str(self.config.data_dir)):
                            file_path.unlink()
                            results.append(f"   - ✅ Deleted original file: {file_path}")
                        else:
                            results.append(f"   - ⚠️  Original file not in data directory, skipped deletion: {file_path}")
                    except Exception as e:
                        results.append(f"   - ❌ Error deleting original file: {e}")
                
                # Remove from metadata using CollectionManager API
                if self.collection_manager.delete_document_permanently(filename):
                    results.append(f"   - ✅ Removed from metadata")
                else:
                    results.append(f"   - ❌ Error removing from metadata")
            else:
                results.append(f"❌ Document not found: {filename}")
        
        return "\n".join(results)
    
    def get_available_documents_for_collection(self, collection_name: str) -> List[str]:
        """Get documents that are not in the specified collection."""
        return self.collection_manager.get_documents_not_in_collection(collection_name)
    
    def add_documents_to_collection(self, document_filenames: List[str], collection_name: str) -> str:
        """Add selected documents to the specified collection."""
        if not document_filenames or not collection_name:
            return "No documents or collection specified."
        
        # Get collection pair info
        collection_pair = self.collection_manager.get_pair_by_display_name(collection_name)
        if not collection_pair:
            return f"Collection '{collection_name}' not found."
        
        collection_id = f"cp_{collection_pair['ulid']}"
        results = []
        
        # Process documents that need to be added
        documents_to_process = []
        
        for filename in document_filenames:
            # Find document by filename using CollectionManager API
            doc_info = self.collection_manager.get_document_by_filename(filename)
            if doc_info:
                doc_id, doc_data = doc_info
                
                # Check if already in collection
                if not DocumentUtils.is_document_in_collection(doc_data, collection_id):
                    # Add to metadata first
                    if self.collection_manager.add_document_to_collection(filename, collection_id):
                        documents_to_process.append((filename, doc_id, doc_data))
                        results.append(f"✅ Added {filename} to {collection_name} metadata")
                    else:
                        results.append(f"❌ Failed to add {filename} to metadata")
                else:
                    results.append(f"⚠️  {filename} already in {collection_name}")
            else:
                results.append(f"❌ Document not found: {filename}")
        
        # Process documents through the vector database pipeline
        if documents_to_process:
            try:
                processed_count = self._process_documents_to_collection(
                    documents_to_process, collection_pair
                )
                results.append(f"✅ Added {processed_count} documents to {collection_name} vector database")
            except Exception as e:
                results.append(f"❌ Error processing documents: {e}")
                # Revert metadata changes on error
                for filename, doc_id, doc_data in documents_to_process:
                    self.collection_manager.remove_document_from_collection(filename, collection_id)
        
        return "\n".join(results)
    
    def remove_documents_from_collection(self, document_displays: List[str], collection_name: str) -> str:
        """Remove selected documents from the specified collection."""
        if not document_displays or not collection_name:
            return "No documents or collection specified."
        
        # Get collection pair info
        collection_pair = self.collection_manager.get_pair_by_display_name(collection_name)
        if not collection_pair:
            return f"Collection '{collection_name}' not found."
        
        collection_id = f"cp_{collection_pair['ulid']}"
        results = []
        
        for doc_display in document_displays:
            # Extract filename from display format
            filename = DocumentUtils.extract_filename_from_display(doc_display)
            
            # Find document by filename
            doc_info = self.collection_manager.get_document_by_filename(filename)
            if doc_info:
                doc_id, doc_data = doc_info
                
                # Check if document is in collection
                if DocumentUtils.is_document_in_collection(doc_data, collection_id):
                    # Remove from vector databases first
                    try:
                        removed_chunks = self._remove_document_from_vector_db(
                            collection_pair['chunks_collection'], doc_data.get('file_hash', '')
                        )
                        removed_artifacts = self._remove_document_from_vector_db(
                            collection_pair['artifacts_collection'], doc_data.get('file_hash', '')
                        )
                        
                        results.append(f"✅ {filename}")
                        if removed_chunks > 0:
                            results.append(f"   - Removed {removed_chunks} chunks")
                        if removed_artifacts > 0:
                            results.append(f"   - Removed {removed_artifacts} artifacts")
                        
                        # Remove from metadata
                        if self.collection_manager.remove_document_from_collection(filename, collection_id):
                            results.append(f"   - Removed from metadata")
                        else:
                            results.append(f"   - ❌ Error removing from metadata")
                        
                    except Exception as e:
                        results.append(f"❌ Error removing {filename}: {e}")
                else:
                    results.append(f"⚠️  {filename} not in {collection_name}")
            else:
                results.append(f"❌ Document not found: {filename}")
        
        return "\n".join(results)
    
    def get_document_collections(self, filename: str) -> List[str]:
        """Get list of collection names that contain the specified document."""
        doc_info = self.collection_manager.get_document_by_filename(filename)
        if not doc_info:
            return []
        
        doc_id, doc_data = doc_info
        collections = DocumentUtils.ensure_collections_dict_format(
            doc_data.get('in_collections', {})
        )
        
        # Convert collection IDs to display names
        collection_names = []
        for coll_id in collections.keys():
            for pair in self.collection_manager.list_collection_pairs():
                if f"cp_{pair['ulid']}" == coll_id:
                    collection_names.append(pair['display_name'])
                    break
        
        return collection_names
    
    def _remove_document_from_vector_db(self, collection_name: str, file_hash: str) -> int:
        """Remove all document chunks/artifacts from a collection by file hash.
        
        Args:
            collection_name: Name of the collection
            file_hash: File hash to remove
            
        Returns:
            Number of points removed
        """
        try:
            db = VectorDatabase(collection_name, self.config, self.collection_manager)
            db.ensure_indexes()
            
            # Create filter for the file hash
            from qdrant_client.models import Filter
            scroll_filter = Filter(
                must=[{"key": "file_hash", "match": {"value": file_hash}}]
            )
            
            # Get all points with this file hash
            scroll_result = db.client.scroll(
                collection_name=collection_name,
                scroll_filter=scroll_filter,
                limit=10000,  # Large limit to get all matching points
                with_payload=False,
                with_vectors=False
            )
            
            points_to_delete = [point.id for point in scroll_result[0]]
            
            if points_to_delete:
                from qdrant_client.models import PointIdsList
                db.client.delete(
                    collection_name=collection_name,
                    points_selector=PointIdsList(points=points_to_delete)
                )
                return len(points_to_delete)
            
            return 0
            
        except Exception as e:
            print(f"Warning: Could not remove documents from {collection_name}: {e}")
            return 0
    
    def _process_documents_to_collection(self, documents_to_process: List[tuple], 
                                       collection_pair: dict) -> int:
        """Process converted documents and add them to vector databases.
        
        Args:
            documents_to_process: List of (filename, doc_id, doc_info) tuples
            collection_pair: Collection pair info containing collection names
            
        Returns:
            Number of documents successfully processed
        """
        from .processor import DocumentProcessor
        from .filesystem import FileSystemStorage
        
        # Initialize processor for this collection
        processor = DocumentProcessor(
            self.config, 
            collection_name=collection_pair['display_name'],
            collection_manager=self.collection_manager
        )
        
        # Initialize filesystem storage to load converted documents
        storage = FileSystemStorage(self.config)
        
        processed_count = 0
        
        for filename, doc_id, doc_info in documents_to_process:
            try:
                # Load the converted document from storage
                doc_and_metadata = storage.load_document_by_filename(filename)
                if not doc_and_metadata:
                    print(f"   ❌ Could not load {filename} from storage")
                    continue
                
                loaded_doc, metadata = doc_and_metadata
                
                # Create DocumentResult from loaded data
                from .models import DocumentResult
                from pathlib import Path
                doc_result = DocumentResult(
                    document=loaded_doc,
                    file_path=Path(metadata['file_path']),
                    source_category=metadata['source_category'],
                    file_hash=metadata['file_hash']
                )
                
                # Process through chunking and embedding pipeline
                chunks_with_embeddings = processor.process_documents_to_chunks([doc_result])
                
                # Store chunks in vector database
                processor.store_chunks(chunks_with_embeddings)
                
                # Process and store artifacts if they exist
                if hasattr(processor, '_handle_artifacts'):
                    asyncio.run(processor._handle_artifacts([doc_result], save_to_storage=False, save_to_vector=True))
                
                processed_count += 1
                print(f"   ✅ Processed {filename} into vector database")
                
            except Exception as e:
                print(f"   ❌ Error processing {filename}: {e}")
                continue
        
        return processed_count
    
    def get_standalone_documents(self) -> List[Dict[str, Any]]:
        """Get documents that have been converted but aren't in any collection yet."""
        from .filesystem import FileSystemStorage
        
        storage = FileSystemStorage(self.config)
        all_converted_docs = storage.list_documents()
        
        standalone_docs = []
        
        for converted_doc in all_converted_docs:
            filename = converted_doc.get('original_filename')
            if not filename:
                continue
                
            # Check if this document is tracked in collection metadata
            doc_info = self.collection_manager.get_document_by_filename(filename)
            if not doc_info:
                standalone_docs.append({
                    'filename': filename,
                    'doc_id': converted_doc.get('doc_id'),
                    'source_category': converted_doc.get('source_category', 'unknown'),
                    'file_hash': converted_doc.get('file_hash'),
                    'processed_at': converted_doc.get('processed_at'),
                    'file_path': converted_doc.get('file_path')
                })
        
        return sorted(standalone_docs, key=lambda x: x['filename'])
    
    def add_standalone_document_to_metadata(self, filename: str) -> bool:
        """Add a standalone converted document to the metadata system.
        
        This is useful when you have converted documents that aren't tracked
        in the collection metadata yet.
        """
        from .filesystem import FileSystemStorage
        
        storage = FileSystemStorage(self.config)
        doc_and_metadata = storage.load_document_by_filename(filename)
        
        if not doc_and_metadata:
            return False
        
        loaded_doc, metadata = doc_and_metadata
        doc_id = metadata['doc_id']
        
        # Check if already in metadata
        if self.collection_manager.get_document_by_filename(filename):
            return True  # Already exists
        
        # Add to metadata using CollectionManager's tracking method
        return self.collection_manager.track_document_in_pair(
            "standalone", doc_id, {
                'filename': filename,
                'source': metadata['source_category'],
                'file_path': metadata['file_path'],
                'processed_at': metadata.get('processed_at', datetime.now().isoformat())
            }
        )