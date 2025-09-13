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