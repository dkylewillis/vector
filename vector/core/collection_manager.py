"""Collection naming convention manager for Vector."""

import json
import os
from typing import Dict, List, Optional, Tuple, Any
from ulid import new as new_ulid
from datetime import datetime

from ..config import Config


class CollectionManager:
    """Manages collection naming conventions and metadata for vector databases."""
    
    def __init__(self, config: Optional[Config] = None, metadata_file: Optional[str] = None):
        """Initialize collection manager."""
        self.config = config or Config()
        self.metadata_file = metadata_file or self.config.collections_metadata_file
        self.metadata = self._load_metadata()
        
    def _load_metadata(self) -> Dict:
        """Load collection metadata from JSON file."""
        if os.path.exists(self.metadata_file):
            with open(self.metadata_file, 'r') as f:
                return json.load(f)
        return {
            "collection_pairs": {},  # pair_id -> {chunks_collection, artifacts_collection, metadata}
            "display_name_to_pair": {},  # display_name -> pair_id
            "documents": {},  # document_id -> {in_collections, metadata}
            "created_at": datetime.now().isoformat()
        }
    
    def _save_metadata(self):
        """Save collection metadata to JSON file."""
        self.metadata["updated_at"] = datetime.now().isoformat()
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2)
    
    def save_metadata(self):
        """Public method to save metadata (for use by other managers)."""
        self._save_metadata()
    
    def _generate_collection_pair(self, base_name: str) -> Tuple[str, str, str]:
        """Generate a paired collection (chunks + artifacts) with shared ULID."""
        ulid_str = str(new_ulid())
        pair_id = f"cp_{ulid_str}"
        chunks_collection = f"c_{ulid_str}__chunks"
        artifacts_collection = f"c_{ulid_str}__artifacts"
        return chunks_collection, artifacts_collection, pair_id
    
    def create_collection_pair(self, display_name: str, description: str = "") -> Dict[str, str]:
        """
        Create a new paired collection (chunks + artifacts).
        
        Args:
            display_name: Human-readable name for the collection pair
            description: Optional description
            
        Returns:
            Dict with 'chunks_collection' and 'artifacts_collection' names
            
        Raises:
            ValueError: If display_name already exists
        """
        # Check for duplicate display name
        if display_name in self.metadata["display_name_to_pair"]:
            raise ValueError(f"Display name '{display_name}' already exists")
        
        # Generate collection pair
        chunks_collection, artifacts_collection, pair_id = self._generate_collection_pair(display_name)
        
        # Extract ULID from pair_id (remove cp_ prefix)
        ulid_str = pair_id[3:]  # Remove "cp_" prefix
        
        # Store metadata
        self.metadata["collection_pairs"][pair_id] = {
            "display_name": display_name,
            "ulid": ulid_str,
            "chunks_collection": chunks_collection,
            "artifacts_collection": artifacts_collection,
            "description": description,
            "created_at": datetime.now().isoformat(),
            "status": "active",
            "document_count": 0
        }
        
        # Create reverse mapping
        self.metadata["display_name_to_pair"][display_name] = pair_id
        
        # Save to file
        self._save_metadata()
        
        return {
            "chunks_collection": chunks_collection,
            "artifacts_collection": artifacts_collection,
            "pair_id": pair_id
        }
    
    def track_document_in_pair(self, pair_id: str, document_id: str, document_metadata: Dict = None) -> bool:
        """
        Track that a document exists in a collection pair (metadata only).
        
        Args:
            pair_id: Collection pair ID
            document_id: Unique document identifier (file hash)
            document_metadata: Optional document metadata
            
        Returns:
            True if tracked, False if pair doesn't exist
        """
        if pair_id not in self.metadata["collection_pairs"]:
            return False
        
        # Find existing document by file hash or create new one
        doc_ulid_key = None
        for key, doc_info in self.metadata["documents"].items():
            if doc_info.get("file_hash") == document_id:
                doc_ulid_key = key
                break
                
        # If document doesn't exist, create new one
        if doc_ulid_key is None:
            doc_ulid = f"doc_{str(new_ulid())}"
            doc_ulid_key = doc_ulid
            self.metadata["documents"][doc_ulid_key] = {
                "ulid": doc_ulid[4:],  # Store just the ULID part without doc_ prefix
                "file_hash": document_id,  # Store the original file hash for reference
                "in_collections": {},
                "metadata": document_metadata or {}
            }
        
        # Ensure in_collections is a dictionary (fix legacy list format)
        if isinstance(self.metadata["documents"][doc_ulid_key]["in_collections"], list):
            # Convert from legacy list format to dictionary format
            old_collections = self.metadata["documents"][doc_ulid_key]["in_collections"]
            self.metadata["documents"][doc_ulid_key]["in_collections"] = {}
            # Re-add any existing collections with timestamps
            for collection_id in old_collections:
                self.metadata["documents"][doc_ulid_key]["in_collections"][collection_id] = {
                    "added_at": datetime.now().isoformat()
                }
        
        # Check if document is already in this specific pair
        if pair_id in self.metadata["documents"][doc_ulid_key]["in_collections"]:
            # Document already exists in this pair, no need to add again
            return True
            
        # Add document to this pair
        self.metadata["documents"][doc_ulid_key]["in_collections"][pair_id] = {
            "added_at": datetime.now().isoformat()
        }
        
        # Update document count for this pair
        self.metadata["collection_pairs"][pair_id]["document_count"] += 1
        
        self._save_metadata()
        return True
    
    def get_collections_for_document(self, document_id: str) -> Optional[List[Dict[str, str]]]:
        """Get collection names for a document (may be in multiple pairs)."""
        # Find document by file hash
        document_info = None
        for doc_key, doc_data in self.metadata["documents"].items():
            if doc_data.get("file_hash") == document_id:
                document_info = doc_data
                break
                
        if document_info is None:
            return None
            
        collections = []
        
        for pair_id in document_info.get("in_collections", {}):
            if pair_id in self.metadata["collection_pairs"]:
                pair_info = self.metadata["collection_pairs"][pair_id]
                collections.append({
                    "chunks_collection": pair_info["chunks_collection"],
                    "artifacts_collection": pair_info["artifacts_collection"],
                    "pair_id": pair_id,
                    "display_name": pair_info["display_name"]
                })
        
        return collections if collections else None
    
    def get_pair_by_display_name(self, display_name: str) -> Optional[Dict]:
        """Get collection pair by display name."""
        pair_id = self.metadata["display_name_to_pair"].get(display_name)
        if not pair_id:
            return None
            
        pair_info = self.metadata["collection_pairs"][pair_id].copy()
        pair_info["pair_id"] = pair_id
        return pair_info
    
    def list_collection_pairs(self) -> List[Dict]:
        """List all collection pairs."""
        pairs = []
        for pair_id, pair_info in self.metadata["collection_pairs"].items():
            pair_data = pair_info.copy()
            pair_data["pair_id"] = pair_id
            pairs.append(pair_data)
        return pairs
    
    def rename_collection_pair(self, old_name: str, new_name: str) -> bool:
        """Rename a collection pair."""
        if new_name in self.metadata["display_name_to_pair"]:
            raise ValueError(f"Display name '{new_name}' already exists")
            
        pair_id = self.metadata["display_name_to_pair"].get(old_name)
        if not pair_id:
            return False
            
        # Update display name in pair info
        self.metadata["collection_pairs"][pair_id]["display_name"] = new_name
        
        # Update mapping
        del self.metadata["display_name_to_pair"][old_name]
        self.metadata["display_name_to_pair"][new_name] = pair_id
        
        self._save_metadata()
        return True
    
    def delete_collection_pair(self, display_name: str) -> bool:
        """Delete a collection pair and all its documents."""
        pair_id = self.metadata["display_name_to_pair"].get(display_name)
        if not pair_id:
            return False
            
        # Remove from collection_pairs
        del self.metadata["collection_pairs"][pair_id]
        
        # Remove from display_name_to_pair
        del self.metadata["display_name_to_pair"][display_name]
        
        # Remove this pair from all documents
        for document_id in list(self.metadata["documents"].keys()):
            doc_info = self.metadata["documents"][document_id]
            if pair_id in doc_info.get("in_collections", {}):
                del doc_info["in_collections"][pair_id]
                # If document has no more collection pairs, remove it entirely
                if not doc_info.get("in_collections"):
                    del self.metadata["documents"][document_id]
        
        self._save_metadata()
        return True
    
    def get_total_documents(self) -> int:
        """Get total number of unique documents across all pairs."""
        return len(self.metadata["documents"])
    
    def get_document_pairs(self, document_id: str) -> Optional[List[str]]:
        """Get list of pair IDs that contain a specific document."""
        # Find document by file hash
        for doc_key, doc_data in self.metadata["documents"].items():
            if doc_data.get("file_hash") == document_id:
                return list(doc_data.get("in_collections", {}).keys())
        return None

    def list_documents_in_pair(self, pair_id: str) -> List[Dict[str, Any]]:
        """List all documents in a collection pair."""
        if pair_id not in self.metadata["collection_pairs"]:
            return []
        
        documents = []
        for doc_key, doc_data in self.metadata["documents"].items():
            if pair_id in doc_data.get("in_collections", {}):
                documents.append({
                    "document_id": doc_data.get("file_hash"),
                    "ulid": doc_data.get("ulid"),
                    "metadata": doc_data.get("metadata", {}),
                    "added_at": doc_data["in_collections"][pair_id].get("added_at")
                })
        return documents
    
    # New public API methods for document operations
    
    def get_metadata(self) -> Dict:
        """Get a copy of the current metadata.
        
        Returns:
            Copy of metadata dictionary
        """
        return self.metadata.copy()
    
    def get_document_by_filename(self, filename: str) -> Optional[Tuple[str, Dict]]:
        """Find document by filename across all collections.
        
        Args:
            filename: Original filename to search for
            
        Returns:
            Tuple of (document_id, document_info) if found, None otherwise
        """
        from .document_utils import DocumentUtils
        return DocumentUtils.find_document_by_filename(self.metadata, filename)
    
    def get_document_by_hash(self, file_hash: str) -> Optional[Tuple[str, Dict]]:
        """Find document by file hash.
        
        Args:
            file_hash: File hash to search for
            
        Returns:
            Tuple of (document_id, document_info) if found, None otherwise
        """
        from .document_utils import DocumentUtils
        return DocumentUtils.find_document_by_hash(self.metadata, file_hash)
    
    def get_all_documents(self) -> List[Dict[str, Any]]:
        """Get all active documents across all collections.
        
        Returns:
            List of document information dictionaries
        """
        from .document_utils import DocumentUtils
        documents = []
        
        for doc_id, doc_info in self.metadata.get('documents', {}).items():
            if doc_info.get('status', 'active') == 'active':
                collections = DocumentUtils.ensure_collections_dict_format(
                    doc_info.get('in_collections', {})
                )
                collection_count = len(collections)
                
                documents.append({
                    'id': doc_id,
                    'filename': doc_info.get('metadata', {}).get('filename', doc_id),
                    'collection_count': collection_count,
                    'display_name': f"{doc_info.get('metadata', {}).get('filename', doc_id)} ({DocumentUtils.get_collection_count_display(collection_count)})",
                    'created_at': doc_info.get('created_at'),
                    'source': doc_info.get('metadata', {}).get('source'),
                    'file_hash': doc_info.get('file_hash'),
                    'ulid': doc_info.get('ulid')
                })
        
        return sorted(documents, key=lambda x: x['filename'])
    
    def add_document_to_collection(self, filename: str, collection_id: str) -> bool:
        """Add a document to a collection (metadata only).
        
        Args:
            filename: Document filename
            collection_id: Collection pair ID
            
        Returns:
            True if added successfully, False otherwise
        """
        doc_info = self.get_document_by_filename(filename)
        if not doc_info:
            return False
        
        doc_id, doc_data = doc_info
        
        # Ensure collections are in dict format
        from .document_utils import DocumentUtils
        collections = DocumentUtils.ensure_collections_dict_format(
            doc_data.get('in_collections', {})
        )
        
        # Check if already in collection
        if collection_id in collections:
            return True  # Already added
        
        # Add to collection
        from datetime import datetime
        collections[collection_id] = {"added_at": datetime.now().isoformat()}
        self.metadata['documents'][doc_id]['in_collections'] = collections
        
        # Update document count for the collection
        if collection_id in self.metadata["collection_pairs"]:
            self.metadata["collection_pairs"][collection_id]["document_count"] += 1
        
        self._save_metadata()
        return True
    
    def remove_document_from_collection(self, filename: str, collection_id: str) -> bool:
        """Remove a document from a collection (metadata only).
        
        Args:
            filename: Document filename
            collection_id: Collection pair ID
            
        Returns:
            True if removed successfully, False otherwise
        """
        doc_info = self.get_document_by_filename(filename)
        if not doc_info:
            return False
        
        doc_id, doc_data = doc_info
        
        # Ensure collections are in dict format
        from .document_utils import DocumentUtils
        collections = DocumentUtils.ensure_collections_dict_format(
            doc_data.get('in_collections', {})
        )
        
        # Remove from collection if present
        if collection_id in collections:
            del collections[collection_id]
            self.metadata['documents'][doc_id]['in_collections'] = collections
            
            # Update document count for the collection
            if collection_id in self.metadata["collection_pairs"]:
                self.metadata["collection_pairs"][collection_id]["document_count"] = max(0, 
                    self.metadata["collection_pairs"][collection_id]["document_count"] - 1)
            
            self._save_metadata()
            return True
        
        return False
    
    def delete_document_permanently(self, filename: str) -> bool:
        """Permanently delete a document from all collections (metadata only).
        
        Args:
            filename: Document filename
            
        Returns:
            True if deleted successfully, False otherwise
        """
        doc_info = self.get_document_by_filename(filename)
        if not doc_info:
            return False
        
        doc_id, doc_data = doc_info
        
        # Update document counts for all collections this document was in
        from .document_utils import DocumentUtils
        collections = DocumentUtils.ensure_collections_dict_format(
            doc_data.get('in_collections', {})
        )
        
        for collection_id in collections.keys():
            if collection_id in self.metadata["collection_pairs"]:
                self.metadata["collection_pairs"][collection_id]["document_count"] = max(0,
                    self.metadata["collection_pairs"][collection_id]["document_count"] - 1)
        
        # Remove document from metadata
        del self.metadata['documents'][doc_id]
        self._save_metadata()
        return True
    
    def get_documents_not_in_collection(self, collection_name: str) -> List[str]:
        """Get documents that are not in the specified collection.
        
        Args:
            collection_name: Display name of the collection
            
        Returns:
            List of filenames not in the collection
        """
        collection_pair = self.get_pair_by_display_name(collection_name)
        if not collection_pair:
            return []
        
        collection_id = f"cp_{collection_pair['ulid']}"
        available_documents = []
        
        from .document_utils import DocumentUtils
        for doc_id, doc_info in self.metadata.get('documents', {}).items():
            if doc_info.get('status', 'active') == 'active':
                if not DocumentUtils.is_document_in_collection(doc_info, collection_id):
                    filename = doc_info.get('metadata', {}).get('filename', doc_id)
                    available_documents.append(filename)
        
        return sorted(available_documents)
    
    def fix_document_counts(self) -> Dict[str, Dict[str, int]]:
        """Fix document count discrepancies in collection metadata.
        
        Returns:
            Dictionary with collection names and their count corrections
        """
        corrections = {}
        
        for pair_id, pair_info in self.metadata["collection_pairs"].items():
            # Count actual documents in this collection
            actual_count = 0
            for doc_data in self.metadata["documents"].values():
                if pair_id in doc_data.get("in_collections", {}):
                    actual_count += 1
            
            stored_count = pair_info.get("document_count", 0)
            display_name = pair_info.get("display_name", pair_id)
            
            if stored_count != actual_count:
                corrections[display_name] = {
                    "stored_count": stored_count,
                    "actual_count": actual_count,
                    "correction": actual_count - stored_count
                }
                
                # Fix the count
                self.metadata["collection_pairs"][pair_id]["document_count"] = actual_count
        
        if corrections:
            self._save_metadata()
            
        return corrections