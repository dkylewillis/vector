"""Web service layer for Vector application."""

import os
from typing import List, Tuple, Optional, Dict, Any
from pathlib import Path

from ..config import Config
from ..agent import ChatService
from ..stores.qdrant import QdrantVectorStore
from ..pipeline.ingestion import IngestionPipeline, IngestionConfig
from ..embedders.sentence_transformer import SentenceTransformerEmbedder
from ..models import Chunk, Artifact
from .registry import DocumentRegistry


class VectorWebService:
    """Web service for Vector operations."""

    def __init__(self, config=None):
        """Initialize web service with refactored components."""
        self.config = config or Config()

        try:
            # Initialize components with refactored architecture
            self.store = QdrantVectorStore(db_path=self.config.vector_db_path)
            self.registry = DocumentRegistry(config=self.config)
            # Use default embedder model
            self.embedder = SentenceTransformerEmbedder()
            
            # Initialize agent only if needed (lazy loading)
            self._agent = None
            
            # Create IngestionConfig for the pipeline
            ingestion_config = IngestionConfig(
                collection_name="chunks",
                generate_artifacts=True,
                use_vlm_pipeline=False
            )
            
            self.pipeline = IngestionPipeline(
                embedder=self.embedder,
                store=self.store,
                config=ingestion_config
            )
            print("✅ VectorWebService initialized successfully")
        except Exception as e:
            print(f"⚠️  Error initializing VectorWebService: {e}")
            import traceback
            traceback.print_exc()
            self.store = None
            self.registry = None
            self._agent = None
            self.pipeline = None
    
    @property
    def agent(self):
        """Lazy initialization of ChatService (only when needed for chat/search)."""
        if self._agent is None:
            try:
                print("🤖 Initializing ChatService...")
                self._agent = ChatService(
                    config=self.config,
                    chunks_collection="chunks"
                )
                print("✅ ChatService initialized")
            except Exception as e:
                print(f"⚠️  Error initializing ChatService: {e}")
                print("   Chat and AI features will be unavailable, but document upload/management will work.")
                import traceback
                traceback.print_exc()
        return self._agent

    def search_with_thumbnails(
        self,
        query: str,
        collection: str,
        top_k: int,
        search_type: str,
        documents: Optional[List[str]] = None,
        window: int = 0
    ) -> Tuple[str, List]:
        """Search with thumbnails.
        
        Note: search_type parameter is kept for compatibility but ignored.
        Always searches chunks only.
        """
        if not self.agent:
            return "Search functionality not available", []

        try:
            # Use the search service directly (refactored architecture)
            # Note: search_type parameter removed - always searches chunks
            results = self.agent.retriever.search_service.search(
                query=query,
                top_k=top_k,
                document_ids=self.get_selected_documents_by_name(documents),
                window=window
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

    def get_selected_documents_by_name(self, documents: List[str]) -> Optional[Dict[str, Any]]:
        """Get document details by ID."""
        if not self.registry:
            return None
        if not documents:
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
        return document_ids if document_ids else None

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
                file_path = Path(file_obj.name if hasattr(file_obj, 'name') else str(file_obj))
                file_name = file_path.name

                results.append(f"\n📄 Processing file {i}/{len(files)}: {file_name}")
                results.append("-" * 40)

                # Register document in registry first
                doc_record = self.registry.register_document(file_path, file_name)
                document_id = doc_record.document_id
                
                # Use ingestion pipeline to process the document
                ingestion_result = self.pipeline.ingest_file(
                    file_path=file_path,
                    document_id=document_id
                )

                if ingestion_result.success:
                    results.append(f"✅ Successfully processed: {file_name}")
                    results.append(f"   Document ID: {document_id}")
                    results.append(f"   Chunks indexed: {ingestion_result.chunks_indexed}")
                    results.append(f"   Artifacts: {ingestion_result.artifacts_generated}")
                    
                    # Update registry with processing results
                    doc_record.chunk_count = ingestion_result.chunks_indexed
                    doc_record.artifact_count = ingestion_result.artifacts_generated
                    doc_record.has_artifacts = ingestion_result.artifacts_generated > 0
                    doc_record.chunk_collection = collection
                    self.registry.update_document(doc_record)
                    
                    # Add tags if provided
                    if tags and tags.strip():
                        parsed_tags = [tag.strip().lower() for tag in tags.split(",") if tag.strip()]
                        self.registry.add_tags(document_id, parsed_tags)
                    
                    processed_document_ids.append(document_id)
                    success_count += 1
                else:
                    error_msg = f"❌ Ingestion failed: {', '.join(ingestion_result.errors)}"
                    results.append(error_msg)
                    error_count += 1

            except Exception as e:
                error_msg = f"❌ Error processing {file_name}: {str(e)}"
                results.append(error_msg)
                print(error_msg)  # Also log to console
                import traceback
                traceback.print_exc()
                error_count += 1

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

        if not self.store or not self.registry:
            return "Store or registry not available - cannot delete documents"

        results = []
        success_count = 0
        error_count = 0

        for doc_name in document_names:
            try:
                print(f"🗑️ Attempting to delete document: {doc_name}")
                
                # Get document ID from registry
                document_id = self.registry.get_id_by_display_name(doc_name)
                if not document_id:
                    results.append(f"❌ Document not found in registry: {doc_name}")
                    error_count += 1
                    continue
                
                # Delete from vector store using document_id filter
                from ..search.dsl import FieldEquals
                filter_expr = FieldEquals(key="document_id", value=document_id)
                
                deleted_count = self.store.delete(
                    collection_name=collection,
                    filter_expr=filter_expr
                )
                
                # Delete from registry
                self.registry.delete_document_record(document_id)
                
                results.append(f"✅ Successfully deleted: {doc_name} ({deleted_count} chunks)")
                success_count += 1
                
            except Exception as e:
                error_msg = f"❌ Error deleting document {doc_name}: {e}"
                print(error_msg)
                import traceback
                traceback.print_exc()
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

    def rename_document(self, display_name: str, new_name: str) -> Dict[str, Any]:
        """Rename a document.
        
        Args:
            display_name: Current display name of the document
            new_name: New display name for the document
            
        Returns:
            Dictionary with success status and message
        """
        try:
            # Get document ID
            document_id = self.registry.get_id_by_display_name(display_name)
            if not document_id:
                return {
                    "success": False,
                    "message": f"❌ Document '{display_name}' not found"
                }
            
            # Get document record
            doc_record = self.registry.get_document(document_id)
            if not doc_record:
                return {
                    "success": False,
                    "message": "❌ Document record not found"
                }
            
            # Strip any extension from the new name (we don't show extensions)
            if '.' in new_name:
                new_name = os.path.splitext(new_name)[0]
            
            # Attempt to rename
            success = self.registry.update_display_name(document_id, new_name)
            
            if success:
                # Get the actual name that was set (might have counter added)
                updated_doc = self.registry.get_document(document_id)
                actual_name = updated_doc.display_name
                
                if actual_name != new_name:
                    return {
                        "success": True,
                        "message": f"✅ Document renamed to: '{actual_name}'\n(Note: Name was modified to ensure uniqueness)"
                    }
                else:
                    return {
                        "success": True,
                        "message": f"✅ Document renamed successfully to: '{actual_name}'"
                    }
            else:
                return {
                    "success": False,
                    "message": "❌ Failed to rename document"
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"❌ Error renaming document: {str(e)}"
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
            
            doc_record = self.registry.get_document(document_id)
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
            List of document display names that have all of the selected tags
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
                    # Check if document has all of the selected tags (AND operation)
                    if all(tag in doc.tags for tag in selected_tags):
                        filtered_documents.append(doc.display_name)
                
            return filtered_documents
        except Exception as e:
            print(f"Error filtering documents by tags: {e}")
            return []

    # Chat Methods

    def start_chat_session(self, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """Start a new chat session.
        
        Args:
            system_prompt: Optional custom system prompt
            
        Returns:
            Dict with session_id and status
        """
        if not self.agent:
            return {"success": False, "error": "Agent not available"}
        
        try:
            session_id = self.agent.start_chat(system_prompt)
            return {
                "success": True,
                "session_id": session_id,
                "message": "Chat session started successfully"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def send_chat_message(
        self,
        session_id: str,
        message: str,
        response_length: str = 'medium',
        search_type: str = 'chunks',
        top_k: Optional[int] = None,
        documents: Optional[List[str]] = None,
        window: int = 0
    ) -> Dict[str, Any]:
        """Send a message in a chat session.
        
        Args:
            session_id: Chat session identifier (empty string will create new session)
            message: User message
            response_length: Response length (short/medium/long)
            search_type: Search type (always 'chunks', parameter kept for compatibility)
            top_k: Number of results to retrieve (uses config default if None)
            documents: Optional list of document names to filter
            window: Number of surrounding chunks to include (0 = disabled)
            
        Returns:
            Dict with assistant response, results, and metadata
        """
        if not self.agent:
            return {"success": False, "error": "Agent not available"}
        
        try:
            # Auto-create session if none exists
            auto_created = False
            if not session_id or not session_id.strip():
                session_result = self.start_chat_session()
                if not session_result.get('success'):
                    return {"success": False, "error": "Failed to create session"}
                session_id = session_result['session_id']
                auto_created = True
            
            # Get document IDs if document names provided
            document_ids = None
            if documents:
                document_ids = self.get_selected_documents_by_name(documents)
            
            # Use config default if top_k not specified
            if top_k is None:
                top_k = self.config.chat_default_top_k
            
            # Always search chunks only (search_type parameter ignored)
            result = self.agent.chat(
                session_id=session_id,
                user_message=message,
                response_length=response_length,
                top_k=top_k,
                document_ids=document_ids,
                window=window
            )
            
            # Get thumbnails from results
            thumbnails = []
            for search_result in result.get('results', []):
                if search_result.chunk:
                    chunk_thumbnails = self.get_thumbnails(search_result.chunk)
                    thumbnails.extend(chunk_thumbnails)
                if search_result.artifact:
                    artifact_thumbnails = self.get_thumbnails(search_result.artifact)
                    thumbnails.extend(artifact_thumbnails)
            
            return {
                "success": True,
                "session_id": result["session_id"],
                "assistant": result["assistant"],
                "message_count": result["message_count"],
                "results_count": len(result["results"]),
                "thumbnails": thumbnails,
                "auto_created": auto_created,
                "usage_metrics": result.get("usage_metrics", {})
            }
        except ValueError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": f"Chat error: {str(e)}"}

    def get_chat_session(self, session_id: str) -> Dict[str, Any]:
        """Get chat session information.
        
        Args:
            session_id: Chat session identifier
            
        Returns:
            Dict with session information
        """
        if not self.agent:
            return {"success": False, "error": "Agent not available"}
        
        try:
            session = self.agent.get_session(session_id)
            if not session:
                return {"success": False, "error": "Session not found"}
            
            # Return sanitized session info
            return {
                "success": True,
                "session_id": session.id,
                "message_count": len(session.messages),
                "created_at": session.created_at,
                "last_updated": session.last_updated,
                "has_summary": session.summary is not None,
                "messages": [
                    {"role": msg.role, "content": msg.content}
                    for msg in session.messages
                ]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
