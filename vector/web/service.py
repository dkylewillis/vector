"""Web service layer for Vector application."""

from typing import List, Tuple, Optional, Dict, Any
from pathlib import Path

from ..config import Config
from ..agent import ResearchAgent
from ..core.vector_store import VectorStore
from ..core.document_registry import VectorRegistry

from ..core.models import Chunk, Artifact


class VectorWebService:
    """Web service for Vector operations."""
    
    def __init__(self, config=None):
        """Initialize web service with refactored components."""
        self.config = config or Config()
        
        try:
            # Initialize components
            self.store = VectorStore(db_path=self.config.vector_db_path)
            self.registry = VectorRegistry()
            self.agent = ResearchAgent(
                config=self.config,
                chunks_collection="chunks",
                artifacts_collection="artifacts"
            )
            print("✅ VectorWebService initialized successfully")
        except Exception as e:
            print(f"⚠️  Error initializing VectorWebService: {e}")
            self.store = None
            self.registry = None
            self.agent = None
    
    def get_collections(self) -> List[str]:
        """Get available collections."""
        if not self.store:
            return ["placeholder"]
        try:
            return self.store.list_collections()
        except Exception as e:
            print(f"Error getting collections: {e}")
            return []
    
    def get_collection_documents(self, collection: str) -> List[str]:
        """Get documents in collection."""
        if not self.store:
            return []
        try:
            return self.store.list_documents(collection)
        except Exception as e:
            print(f"Error getting documents for collection {collection}: {e}")
            return []
    
    def search_with_thumbnails(self, query: str, collection: str, top_k: int, 
                             search_type: str, documents: Optional[List[str]] = None) -> Tuple[str, List]:
        """Search with thumbnails."""
        if not self.agent:
            return "Search functionality not available", []
        
        try:
            # Map collection name to search type if needed
            if collection == "artifacts":
                agent_search_type = "artifacts"
            elif collection == "chunks":
                agent_search_type = "chunks"
            else:
                agent_search_type = search_type or "both"
            
            results = self.agent.search(
                query=query,
                top_k=top_k,
                search_type=agent_search_type,
                document_ids=self.get_selected_documents_by_name(documents),
            )
            # Collect thumbnails from all results
            thumbnails = []
            for result in results:
                # Get thumbnails from chunk if present
                if result.chunk:
                    chunk_thumbnails = self.get_thumbnails(result.chunk)
                    thumbnails.extend(chunk_thumbnails)
                
                # Get thumbnails from artifact if present
                if result.artifact:
                    artifact_thumbnails = self.get_thumbnails(result.artifact)
                    thumbnails.extend(artifact_thumbnails)
            
            # Format results for display
            formatted_results = []
            for result in results:
                formatted_results.append(f"Score: {result.score:.3f}\n"
                                       f"Source: {result.filename}\n"
                                       f"Type: {result.type}\n"
                                       f"Text: {result.text[:200]}...\n\n")
            
            summary = f"Found {len(results)} results for '{query}'\n\n" + "".join(formatted_results)
            return summary, thumbnails
            
        except Exception as e:
            print(f"Error in search: {e}")
            return f"Search error: {str(e)}", []
    
    def ask_ai_with_thumbnails(self, question: str, collection: str, length: str,
                            search_type: str, documents: Optional[List[str]] = None) -> Tuple[str, List]:
        """Ask AI with thumbnails."""
        if not self.agent:
            return "AI functionality not available", []
        
        try:
            # Map collection name to search type if needed
            if collection == "artifacts":
                agent_search_type = "artifacts"
            elif collection == "chunks":
                agent_search_type = "chunks"
            else:
                agent_search_type = search_type or "both"
            
            response, results = self.agent.ask(
                question=question,
                response_length=length,
                search_type=agent_search_type,
                top_k=20,
                document_ids=self.get_selected_documents_by_name(documents)
            )

            # Collect thumbnails from search results
            thumbnails = []
            for result in results:
                # Get thumbnails from chunk if present
                if result.chunk:
                    chunk_thumbnails = self.get_thumbnails(result.chunk)
                    thumbnails.extend(chunk_thumbnails)
                
                # Get thumbnails from artifact if present
                if result.artifact:
                    artifact_thumbnails = self.get_thumbnails(result.artifact)
                    thumbnails.extend(artifact_thumbnails)
            
            # Return the AI response text
            response_text = response.response if hasattr(response, 'response') else str(response)
            return response_text, thumbnails
            
        except Exception as e:
            print(f"Error in AI ask: {e}")
            return f"AI error: {str(e)}", []

    ## TODO: REFACTOR!!
    ## NEED TO REFACTOR THESE AFTER CREATING NEW METHODS IN VECTOR STORE AND REGISTRY FOR SEARCHING BY ID##
    ## I DON'T LIKE HOW SEARCH_DOCUMENTS IS BEING USED FOR THIS AS IT RETURNS A LIST
    def get_selected_documents_by_name(self, documents: List[str]) -> Optional[Dict[str, Any]]:
        """Get document details by ID."""
        if not self.registry:
            return None
        document_ids = []
        for name in documents:
            try:
                doc = self.registry.search_documents(query=name, fields = ['display_name'])
                document_ids.append(doc[0].document_id)

            except Exception as e:
                print(f"Error getting document by name {name}: {e}")
        return document_ids
    
    
    def get_thumbnails(self, obj: Any) -> List[str]:
        """Return thumbnail image paths for an Artifact or Chunk."""
        thumbnails = []
        
        if isinstance(obj, Artifact):
            if getattr(obj, "image_file_path", None):
                thumbnails = [obj.image_file_path]
        elif isinstance(obj, Chunk):
            thumbnails = [
                artifact.image_file_path
                for artifact in getattr(obj, "artifacts", [])
                if getattr(artifact, "image_file_path", None)
            ]
        
        return thumbnails

    def process_documents(self, files: List, collection: str, source: Optional[str], force: bool) -> str:
        """Process documents (not implemented yet)."""
        return "Document processing not yet implemented in refactored version"
    
    def get_collection_info(self, collection: str) -> str:
        """Get collection info."""
        if not self.agent:
            return "Collection info not available"
        
        try:
            info = self.agent.get_collection_info()
            model_info = self.agent.get_model_info()
            return f"{info}\n\nModel Information:\n{model_info}"
        except Exception as e:
            return f"Error getting collection info: {e}"
    
    def get_metadata_summary(self, collection: str) -> str:
        """Get metadata summary (not implemented yet)."""
        return "Metadata summary not yet implemented in refactored version"
    
    def delete_documents(self, filenames: List[str], collection: str) -> str:
        """Delete documents (not implemented yet)."""
        return "Document deletion not yet implemented in refactored version"
    
    def list_collections(self) -> str:
        """List all collections."""
        if not self.store:
            return "Collection listing not available"
        
        try:
            collections = self.store.list_collections()
            if not collections:
                return "No collections found"
            
            result = "Available collections:\n"
            for collection in collections:
                result += f"• {collection}\n"
            return result
        except Exception as e:
            return f"Error listing collections: {e}"
    
    def create_collection(self, display_name: str, description: str) -> str:
        """Create collection."""
        if not self.store:
            return "Collection creation not available"
        
        try:
            # Use display_name as collection name, could be improved with validation
            collection_name = display_name.lower().replace(' ', '_')
            self.store.create_collection(collection_name, vector_size=384)  # Default embedding size
            return f"Collection '{collection_name}' created successfully"
        except Exception as e:
            return f"Error creating collection: {e}"
    
    def rename_collection(self, old_name: str, new_name: str) -> str:
        """Rename collection (not implemented yet)."""
        return "Collection renaming not yet implemented in refactored version"
    
    def delete_collection(self, collection_name: str) -> str:
        """Delete collection."""
        if not self.store:
            return "Collection deletion not available"
        
        try:
            self.store.delete_collection(collection_name)
            return f"Collection '{collection_name}' deleted successfully"
        except Exception as e:
            return f"Error deleting collection: {e}"
    
    def get_all_documents(self) -> List[str]:
        """Get all documents from registry by display name."""
        if not self.registry:
            return []
        
        try:
            documents = self.registry.list_documents()
            return [doc.display_name for doc in documents]
        except Exception as e:
            print(f"Error getting all documents: {e}")
            return []
            
    def get_registry_documents(self) -> List[str]:
        """Get documents from vector registry - alias for get_all_documents."""
        return self.get_all_documents()
    
    def get_document_details(self, documents: List[str]) -> str:
        """Get document details."""
        if not self.registry:
            return "Document details not available"
        
        try:
            if not documents:
                return "No documents selected"
            
            details = []
            all_docs = self.registry.list_documents()
            
            for display_name in documents:
                # Find document by display name
                doc_record = None
                for doc in all_docs:
                    if doc.display_name == display_name:
                        doc_record = doc
                        break
                
                if doc_record:
                    details.append(f"Document: {doc_record.display_name}")
                    details.append(f"  ID: {doc_record.document_id}")
                    details.append(f"  Original Path: {doc_record.original_path}")
                    details.append(f"  Extension: {doc_record.file_extension}")
                    details.append(f"  Registered: {doc_record.registered_date}")
                    details.append(f"  Last Updated: {doc_record.last_updated}")
                    details.append(f"  Chunks: {doc_record.chunk_count}")
                    details.append(f"  Artifacts: {doc_record.artifact_count}")
                    details.append(f"  Tags: {', '.join(doc_record.tags) if doc_record.tags else 'None'}")
                    details.append("")
                else:
                    details.append(f"Document '{display_name}' not found in registry")
                    details.append("")
            
            return "\n".join(details)
        except Exception as e:
            return f"Error getting document details: {e}"
    
    def delete_documents_permanently(self, documents: List[str]) -> str:
        """Delete documents permanently (not implemented yet)."""
        return "Permanent document deletion not yet implemented in refactored version"
    
    def get_available_documents_for_collection(self, collection: str) -> List[str]:
        """Get available documents for collection (not implemented yet)."""
        return []
    
    def add_documents_to_collection(self, documents: List[str], collection: str) -> str:
        """Add documents to collection (not implemented yet)."""
        return "Add documents functionality not yet implemented in refactored version"
    
    def remove_documents_from_collection(self, documents: List[str], collection: str) -> str:
        """Remove documents from collection (not implemented yet)."""
        return "Remove documents functionality not yet implemented in refactored version"