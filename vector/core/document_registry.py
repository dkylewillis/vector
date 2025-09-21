import json
from pathlib import Path
from typing import List, Dict, Optional, Union
from datetime import datetime, timezone
from .models import Chunk, Artifact, DocumentRecord

class VectorRegistry:
    """Registry for managing processed documents and their lifecycle."""
    
    def __init__(self, registry_path: str = "vector_registry"):
        """Initialize the registry with a storage location.
        
        Args:
            registry_path: Path to directory where registry files are stored
        """
        self.registry_path = Path(registry_path)
        self.registry_path.mkdir(parents=True, exist_ok=True)
    
    def register_document(self, file_path: Path, document_name: str) -> DocumentRecord:
        """Register a new document in the registry.
        
        Args:
            file_path: Original file path
            document_name: Document name used for identification
            
        Returns:
            Created DocumentRecord instance
        """
        document_record = DocumentRecord.create_new(file_path, document_name)
        
        self._save_document_record(document_name, document_record)
        print(f"✅ Registered document: {document_name}")
        return document_record
        
    def get_document_info(self, document_id: str) -> Optional[DocumentRecord]:
        """Get information about a registered document.
        
        Args:
            document_id: Document identifier
            
        Returns:
            DocumentRecord instance or None if not found
        """
        record_path = self.registry_path / f"{document_id}.json"
        
        if record_path.exists():
            try:
                with open(record_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Parse datetime strings back to datetime objects
                    data['registered_date'] = datetime.fromisoformat(data['registered_date'])
                    data['last_updated'] = datetime.fromisoformat(data['last_updated'])
                    return DocumentRecord(**data)
            except Exception as e:
                print(f"Error reading document record for {document_id}: {e}")
        
        return None
        
    def update_document(self, document_record: DocumentRecord) -> bool:
        """Update a document record.
        
        Args:
            document_record: DocumentRecord instance to save
            
        Returns:
            True if successful, False otherwise
        """
        document_record.last_updated = datetime.now(timezone.utc)
        return self._save_document_record(document_record.document_id, document_record)
    
    def list_documents(self, status: Optional[str] = None, 
                      sort_by: str = "registered_date", 
                      reverse: bool = True) -> List[DocumentRecord]:
        """List all registered documents with optional filtering.
        
        Args:
            status: Optional status filter ("registered", "processing", "completed", "failed")
            sort_by: Field to sort by
            reverse: Sort in descending order if True
            
        Returns:
            List of DocumentRecord instances
        """
        documents = []
        
        if not self.registry_path.exists():
            return documents
        
        # Read all JSON files in registry directory
        for record_file in self.registry_path.glob("*.json"):
            try:
                with open(record_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Parse datetime strings back to datetime objects
                    data['registered_date'] = datetime.fromisoformat(data['registered_date'])
                    data['last_updated'] = datetime.fromisoformat(data['last_updated'])
                    document_record = DocumentRecord(**data)
                    
                    # Apply status filter if specified
                    if status is None or document_record.status == status:
                        documents.append(document_record)
                        
            except Exception as e:
                print(f"Error reading record file {record_file}: {e}")
        
        # Sort documents
        try:
            documents.sort(key=lambda x: getattr(x, sort_by, ''), reverse=reverse)
        except Exception:
            # Fallback to registered_date if sort_by field doesn't exist
            documents.sort(key=lambda x: x.registered_date, reverse=True)
        
        return documents
        
    def search_documents(self, query: str, fields: List[str] = None) -> List[DocumentRecord]:
        """Search registered documents.
        
        Args:
            query: Search query string
            fields: List of fields to search in (default: display_name, tags, notes)
            
        Returns:
            List of matching DocumentRecord instances
        """
        if fields is None:
            fields = ["display_name", "tags", "notes", "original_path"]
        
        query_lower = query.lower()
        matching_docs = []
        
        for doc in self.list_documents():
            for field in fields:
                field_value = getattr(doc, field, "")
                if isinstance(field_value, list):
                    field_value = " ".join(field_value)
                
                if query_lower in str(field_value).lower():
                    matching_docs.append(doc)
                    break
        
        return matching_docs
    
    def add_tags(self, document_id: str, tags: List[str]) -> bool:
        """Add tags to a document.
        
        Args:
            document_id: Document identifier
            tags: List of tags to add
            
        Returns:
            True if successful, False otherwise
        """
        document_record = self.get_document_info(document_id)
        if document_record is None:
            return False
        
        document_record.add_tags(tags)
        return self.update_document(document_record)
    
    def remove_tags(self, document_id: str, tags: List[str]) -> bool:
        """Remove tags from a document.
        
        Args:
            document_id: Document identifier
            tags: List of tags to remove
            
        Returns:
            True if successful, False otherwise
        """
        document_record = self.get_document_info(document_id)
        if document_record is None:
            return False
        
        document_record.remove_tags(tags)
        return self.update_document(document_record)
    
    def delete_document_record(self, document_id: str) -> bool:
        """Delete a document record from the registry.
        
        Args:
            document_id: Document identifier
            
        Returns:
            True if successful, False otherwise
        """
        record_path = self.registry_path / f"{document_id}.json"
        
        try:
            if record_path.exists():
                record_path.unlink()
                print(f"✅ Deleted document record: {document_id}")
                return True
            else:
                print(f"Document record {document_id} not found")
                return False
        except Exception as e:
            print(f"Error deleting document record {document_id}: {e}")
            return False
    
    def _save_document_record(self, document_id: str, document_record: DocumentRecord) -> bool:
        """Internal method to save document record to file.
        
        Args:
            document_id: Document identifier
            document_record: DocumentRecord instance to save
            
        Returns:
            True if successful, False otherwise
        """
        record_path = self.registry_path / f"{document_id}.json"
        
        try:
            with open(record_path, 'w', encoding='utf-8') as f:
                # Convert to dict and ensure datetime fields are ISO format strings
                data = document_record.model_dump()
                data['registered_date'] = data['registered_date'].isoformat()
                data['last_updated'] = data['last_updated'].isoformat()
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving document record for {document_id}: {e}")
            return False