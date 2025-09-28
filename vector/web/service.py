"""Web service layer for Vector application."""

from typing import List, Tuple, Optional, Dict, Any
from pathlib import Path

from ..config import Config
from ..agent import ResearchAgent
from ..core.vector_store import VectorStore
from ..core.document_registry import VectorRegistry
from ..core.pipeline import VectorPipeline

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
            self.pipeline = VectorPipeline()
            print("✅ VectorWebService initialized successfully")
        except Exception as e:
            print(f"⚠️  Error initializing VectorWebService: {e}")
            self.store = None
            self.registry = None
            self.agent = None

    def search_with_thumbnails(
        self,
        query: str,
        collection: str,
        top_k: int,
        search_type: str,
        documents: Optional[List[str]] = None
    ) -> Tuple[str, List]:
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
                formatted_results.append(
                    f"Score: {result.score:.3f}\n"
                    f"Source: {result.filename}\n"
                    f"Type: {result.type}\n"
                    f"Text: {result.text[:200]}...\n\n"
                )

            summary = f"Found {len(results)} results for '{query}'\n\n" + "".join(formatted_results)
            return summary, thumbnails

        except Exception as e:
            print(f"Error in search: {e}")
            return f"Search error: {str(e)}", []

    def ask_ai_with_thumbnails(
        self,
        question: str,
        collection: str,
        length: str,
        search_type: str,
        documents: Optional[List[str]] = None
    ) -> Tuple[str, List]:
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

    def get_selected_documents_by_name(self, documents: List[str]) -> Optional[Dict[str, Any]]:
        """Get document details by ID."""
        if not self.registry:
            return None
        document_ids = []
        for name in documents:
            try:
                doc_id = self.registry.get_id_by_display_name(name)
                if doc_id:
                    document_ids.append(doc_id)
                else:
                    print(f"Document with display name '{name}' not found.")

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

    def process_documents(
        self,
        files: List,
        collection: str,
        tags: Optional[str] = None
    ) -> str:
        """Process documents using the pipeline."""
        if not files:
            return "No files provided for processing"

        if not self.pipeline:
            return "Document pipeline not available"

        results = []
        success_count = 0
        error_count = 0
        processed_document_ids = []

        results.append(f"🚀 Starting processing of {len(files)} file(s)...")
        if tags and tags.strip():
            results.append(f"🏷️  Tags to add: {tags}")
        results.append("=" * 50)

        for i, file_obj in enumerate(files, 1):
            try:
                # Get the file path from the file object
                file_path = file_obj.name if hasattr(file_obj, 'name') else str(file_obj)
                file_name = (
                    file_path.split('/')[-1]
                    if '/' in file_path
                    else file_path.split('\\')[-1]
                )

                results.append(f"\n📄 Processing file {i}/{len(files)}: {file_name}")
                results.append("-" * 40)

                # Use pipeline to process the document
                document_id = self.pipeline.run(file_path)

                results.append(f"✅ Successfully processed: {file_name}")
                results.append(f"   Document ID: {document_id}")
                
                # Store document ID for tagging
                processed_document_ids.append(document_id)
                success_count += 1

            except Exception as e:
                error_msg = f"❌ Error processing {file_name}: {str(e)}"
                results.append(error_msg)
                print(error_msg)  # Also log to console
                error_count += 1

        # Add tags to successfully processed documents
        if tags and tags.strip() and processed_document_ids:
            results.append(f"\n🏷️  Adding tags to {len(processed_document_ids)} processed documents...")
            
            # Get document display names for the processed documents
            processed_display_names = []
            for doc_id in processed_document_ids:
                try:
                    doc_record = self.registry.get_document(doc_id)
                    if doc_record:
                        processed_display_names.append(doc_record.display_name)
                except Exception as e:
                    print(f"Error getting display name for {doc_id}: {e}")
            
            if processed_display_names:
                try:
                    tag_result = self.add_document_tags(processed_display_names, tags)
                    results.append(f"📋 Tag Result: {tag_result.get('message', 'Tags added')}")
                except Exception as e:
                    results.append(f"⚠️  Error adding tags: {str(e)}")

        # Summary
        results.append("\n" + "=" * 50)
        results.append("📊 Processing Summary:")
        results.append(f"   ✅ Successfully processed: {success_count}")
        results.append(f"   ❌ Failed: {error_count}")
        results.append(f"   📁 Total files: {len(files)}")

        if success_count > 0:
            results.append("\n🎉 Documents are now available for search and AI queries!")

        return "\n".join(results)

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

    def delete_documents(self, document_names: List[str], collection: str) -> str:
        """Delete documents from the system."""
        if not document_names:
            return "No documents specified for deletion"

        if not self.pipeline:
            return "Document pipeline not available - cannot delete documents"

        results = []
        success_count = 0
        error_count = 0

        for doc in document_names:
            try:
                print(f"🗑️ Attempting to delete document: {doc}")
                success = self.pipeline.delete_document_by_name(doc)
                if success:
                    results.append(f"✅ Successfully deleted: {doc}")
                    success_count += 1
                else:
                    results.append(f"❌ Failed to delete: {doc}")
                    error_count += 1
            except Exception as e:
                error_msg = f"❌ Error deleting document {doc}: {e}"
                print(error_msg)
                results.append(error_msg)
                error_count += 1

        # Create summary message
        summary = f"Deletion Summary: {success_count} succeeded, {error_count} failed\n\n"
        detailed_results = "\n".join(results)

        return f"{summary}{detailed_results}"

    def get_registry_documents(self) -> List[str]:
        """Get documents from vector registry by display name."""
        if not self.registry:
            return []

        try:
            documents = self.registry.list_documents()
            return [doc.display_name for doc in documents]
        except Exception as e:
            print(f"Error getting all documents: {e}")
            return []

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

    def add_document_tags(self, document_display_names: List[str], tags_str: str) -> Dict[str, Any]:
        """Add tags to multiple documents.
        
        Args:
            document_display_names: List of document display names
            tags_str: Comma-separated string of tags to add
            
        Returns:
            Dict with success status and message
        """
        if not document_display_names:
            return {"success": False, "message": "No documents selected"}
        
        if not tags_str.strip():
            return {"success": False, "message": "No tags provided"}
        
        # Parse tags from comma-separated string
        tags = [tag.strip().lower() for tag in tags_str.split(",") if tag.strip()]
        
        if not tags:
            return {"success": False, "message": "No valid tags provided"}
        
        results = []
        successful_count = 0
        
        for display_name in document_display_names:
            # Get document ID from display name
            document_id = self.registry.get_id_by_display_name(display_name)
            if not document_id:
                results.append(f"❌ Document not found: {display_name}")
                continue
            
            # Add tags
            if self.registry.add_tags(document_id, tags):
                results.append(f"✅ Added tags to: {display_name}")
                successful_count += 1
            else:
                results.append(f"❌ Failed to add tags to: {display_name}")
        
        message = f"Added tags to {successful_count}/{len(document_display_names)} documents.\n\n"
        message += f"Tags added: {', '.join(tags)}\n\n"
        message += "\n".join(results)
        
        return {
            "success": successful_count > 0,
            "message": message
        }

    def remove_document_tags(self, document_display_names: List[str], tags_str: str) -> Dict[str, Any]:
        """Remove tags from multiple documents.
        
        Args:
            document_display_names: List of document display names
            tags_str: Comma-separated string of tags to remove
            
        Returns:
            Dict with success status and message
        """
        if not document_display_names:
            return {"success": False, "message": "No documents selected"}
        
        if not tags_str.strip():
            return {"success": False, "message": "No tags provided"}
        
        # Parse tags from comma-separated string
        tags = [tag.strip().lower() for tag in tags_str.split(",") if tag.strip()]
        
        if not tags:
            return {"success": False, "message": "No valid tags provided"}
        
        results = []
        successful_count = 0
        
        for display_name in document_display_names:
            # Get document ID from display name
            document_id = self.registry.get_id_by_display_name(display_name)
            if not document_id:
                results.append(f"❌ Document not found: {display_name}")
                continue
            
            # Remove tags
            if self.registry.remove_tags(document_id, tags):
                results.append(f"✅ Removed tags from: {display_name}")
                successful_count += 1
            else:
                results.append(f"❌ Failed to remove tags from: {display_name}")
        
        message = f"Removed tags from {successful_count}/{len(document_display_names)} documents.\n\n"
        message += f"Tags removed: {', '.join(tags)}\n\n"
        message += "\n".join(results)
        
        return {
            "success": successful_count > 0,
            "message": message
        }

    def get_document_tags(self, document_display_names: List[str]) -> str:
        """Get current tags for selected documents.
        
        Args:
            document_display_names: List of document display names
            
        Returns:
            Formatted string showing tags for each document
        """
        if not document_display_names:
            return "No documents selected"
        
        results = []
        
        for display_name in document_display_names:
            document_id = self.registry.get_id_by_display_name(display_name)
            if not document_id:
                results.append(f"❌ {display_name}: Document not found")
                continue
            
            doc_record = self.registry.get_document_info(document_id)
            if doc_record and doc_record.tags:
                tags_str = ", ".join(doc_record.tags)
                results.append(f"📄 {display_name}: {tags_str}")
            else:
                results.append(f"📄 {display_name}: No tags")
        
        return "\n".join(results)

    def get_all_tags(self) -> List[str]:
        """Get all unique tags from all documents in the registry.
        
        Returns:
            List of all unique tags sorted alphabetically
        """
        if not self.registry:
            return []
        
        try:
            all_tags = set()
            documents = self.registry.list_documents()
            
            for doc in documents:
                if doc.tags:
                    all_tags.update(doc.tags)
            
            return sorted(list(all_tags))
        except Exception as e:
            print(f"Error getting all tags: {e}")
            return []

    def get_documents_by_tags(self, selected_tags: Optional[List[str]] = None) -> List[str]:
        """Get documents filtered by tags.
        
        Args:
            selected_tags: List of tags to filter by. If None or empty, returns all documents.
            
        Returns:
            List of document display names that have any of the selected tags
        """
        if not self.registry:
            return []
        
        try:
            documents = self.registry.list_documents()
            
            if not selected_tags:
                return [doc.display_name for doc in documents]
            
            filtered_documents = []
            for doc in documents:
                if doc.tags:
                    # Check if document has any of the selected tags
                    if any(tag in doc.tags for tag in selected_tags):
                        filtered_documents.append(doc.display_name)
                
            return filtered_documents
        except Exception as e:
            print(f"Error filtering documents by tags: {e}")
            return []
