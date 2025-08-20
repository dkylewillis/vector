"""Collection naming convention manager for Vector."""

import json
import os
from typing import Dict, List, Optional
from ulid import ULID
from datetime import datetime

from ..config import Config


class CollectionManager:
    """Manages collection naming conventions and metadata for vector databases."""
    
    def __init__(self, config: Optional[Config] = None, metadata_file: Optional[str] = None):
        """Initialize collection manager.
        
        Args:
            config: Configuration object
            metadata_file: Override metadata file path (defaults to config)
        """
        self.config = config or Config()
        self.metadata_file = metadata_file or self.config.collections_metadata_file
        self.metadata = self._load_metadata()
        
    def _load_metadata(self) -> Dict:
        """Load collection metadata from JSON file."""
        if os.path.exists(self.metadata_file):
            with open(self.metadata_file, 'r') as f:
                return json.load(f)
        return {
            "collections": {},
            "display_name_to_id": {},
            "created_at": datetime.now().isoformat()
        }
    
    def _save_metadata(self):
        """Save collection metadata to JSON file."""
        self.metadata["updated_at"] = datetime.now().isoformat()
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2)
    
    def _generate_collection_name(self, modality: str) -> tuple[str, str]:
        """Generate a collection name following the c_<ulid>__<modality> pattern."""
        ulid_str = str(ULID())
        collection_name = f"c_{ulid_str}__{modality}"
        return collection_name, ulid_str
    
    def create_collection_name(self, display_name: str, modality: str, description: str = "") -> str:
        """
        Create a new collection name with metadata tracking.
        
        Args:
            display_name: Human-readable name for the collection
            modality: Data type ('chunks' or 'artifacts')
            description: Optional description
            
        Returns:
            The generated collection name
            
        Raises:
            ValueError: If display_name already exists or modality is invalid
        """
        # Validate modality
        valid_modalities = {"chunks", "artifacts"}
        if modality not in valid_modalities:
            raise ValueError(f"Invalid modality '{modality}'. Must be one of: {valid_modalities}")
        
        # Check for duplicate display name
        if display_name in self.metadata["display_name_to_id"]:
            raise ValueError(f"Display name '{display_name}' already exists")
        
        # Generate collection name
        collection_name, ulid_str = self._generate_collection_name(modality)
        
        # Store metadata
        self.metadata["collections"][collection_name] = {
            "display_name": display_name,
            "ulid": ulid_str,
            "modality": modality,
            "description": description,
            "created_at": datetime.now().isoformat(),
            "status": "active"
        }
        
        # Create reverse mapping
        self.metadata["display_name_to_id"][display_name] = collection_name
        
        # Save to file
        self._save_metadata()
        
        return collection_name
    
    def get_collection_by_display_name(self, display_name: str) -> Optional[str]:
        """Get collection name by display name."""
        return self.metadata["display_name_to_id"].get(display_name)
    
    def get_collection_metadata(self, collection_name: str) -> Optional[Dict]:
        """Get metadata for a specific collection."""
        return self.metadata["collections"].get(collection_name)
    
    def list_collections(self) -> List[Dict]:
        """List all collections with their metadata."""
        collections = []
        for name, metadata in self.metadata["collections"].items():
            collections.append({
                "collection_name": name,
                **metadata
            })
        return collections
    
    def rename_collection(self, old_display_name: str, new_display_name: str) -> bool:
        """
        Change a collection's display name.
        
        Args:
            old_display_name: Current display name
            new_display_name: New display name
            
        Returns:
            True if renamed, False if old name not found
            
        Raises:
            ValueError: If new display name already exists
        """
        # Check if new name already exists
        if new_display_name in self.metadata["display_name_to_id"]:
            raise ValueError(f"Display name '{new_display_name}' already exists")
        
        # Get collection name
        collection_name = self.get_collection_by_display_name(old_display_name)
        if not collection_name:
            return False
        
        # Update mappings
        self.metadata["collections"][collection_name]["display_name"] = new_display_name
        self.metadata["display_name_to_id"][new_display_name] = collection_name
        del self.metadata["display_name_to_id"][old_display_name]
        
        # Save changes
        self._save_metadata()
        return True

    def delete_collection_metadata(self, display_name: str) -> bool:
        """Remove collection metadata (call this after deleting from vector DB)."""
        collection_name = self.get_collection_by_display_name(display_name)
        if not collection_name:
            return False
        
        del self.metadata["collections"][collection_name]
        del self.metadata["display_name_to_id"][display_name]
        self._save_metadata()
        return True
