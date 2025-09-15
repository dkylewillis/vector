"""Document utility functions shared across the vector core modules."""

import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any


class DocumentUtils:
    """Centralized utility functions for document operations."""
    
    @staticmethod
    def calculate_file_hash(file_path: Path) -> str:
        """Calculate SHA-256 hash of a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Hexadecimal hash string
        """
        hash_sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            raise ValueError(f"Failed to calculate hash for {file_path}: {e}")
    
    @staticmethod
    def find_document_by_filename(metadata: Dict, filename: str) -> Optional[Tuple[str, Dict]]:
        """Find document in metadata by filename.
        
        Args:
            metadata: Collection metadata dictionary
            filename: Original filename to search for
            
        Returns:
            Tuple of (document_id, document_info) if found, None otherwise
        """
        for doc_id, doc_info in metadata.get('documents', {}).items():
            if doc_info.get('metadata', {}).get('filename') == filename:
                return doc_id, doc_info
        return None
    
    @staticmethod
    def find_document_by_hash(metadata: Dict, file_hash: str) -> Optional[Tuple[str, Dict]]:
        """Find document in metadata by file hash.
        
        Args:
            metadata: Collection metadata dictionary
            file_hash: File hash to search for
            
        Returns:
            Tuple of (document_id, document_info) if found, None otherwise
        """
        for doc_id, doc_info in metadata.get('documents', {}).items():
            if doc_info.get('file_hash') == file_hash:
                return doc_id, doc_info
        return None
    
    @staticmethod
    def validate_file_exists(file_path: str) -> bool:
        """Check if file exists and is readable.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if file exists and is readable, False otherwise
        """
        try:
            path_obj = Path(file_path)
            return path_obj.exists() and path_obj.is_file()
        except Exception:
            return False
    
    @staticmethod
    def extract_filename_from_display(doc_display: str) -> str:
        """Extract filename from document display format.
        
        Args:
            doc_display: Display string like "file.pdf (15 chunks)" or "file.pdf (in 2 collections)"
            
        Returns:
            Clean filename without display suffix
        """
        if ' (' in doc_display:
            return doc_display.split(' (')[0]
        return doc_display
    
    @staticmethod
    def get_collection_count_display(collection_count: int) -> str:
        """Generate display string for collection count.
        
        Args:
            collection_count: Number of collections
            
        Returns:
            Formatted display string
        """
        return f"in {collection_count} collection{'s' if collection_count != 1 else ''}"
    
    @staticmethod
    def ensure_collections_dict_format(collections_data: Any) -> Dict:
        """Ensure collections data is in dictionary format (not legacy list).
        
        Args:
            collections_data: Collections data (could be list or dict)
            
        Returns:
            Dictionary format collections data
        """
        if isinstance(collections_data, list):
            # Convert from legacy list format to dictionary format
            from datetime import datetime
            return {
                collection_id: {"added_at": datetime.now().isoformat()}
                for collection_id in collections_data
            }
        elif isinstance(collections_data, dict):
            return collections_data
        else:
            return {}
    
    @staticmethod
    def is_document_in_collection(doc_info: Dict, collection_id: str) -> bool:
        """Check if document is in a specific collection.
        
        Args:
            doc_info: Document information dictionary
            collection_id: Collection ID to check
            
        Returns:
            True if document is in collection, False otherwise
        """
        collections = DocumentUtils.ensure_collections_dict_format(
            doc_info.get('in_collections', {})
        )
        return collection_id in collections