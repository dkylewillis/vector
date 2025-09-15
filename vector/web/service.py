"""Web service that uses core and agent modules directly."""

import sys
import io
from typing import Optional, Dict, Any, List, Tuple

from ..config import Config
from ..core import CollectionManager, DocumentProcessor, DocumentManager
from ..core.processor import PipelineType
from ..agent import ResearchAgent
from ..exceptions import VectorError, AIServiceError
from ..utils.thumbnails import ThumbnailPathResolver


class VectorWebService:
    """Simplified web service that uses core and agent modules directly."""
    
    def __init__(self, config: Config):
        """Initialize web service with configuration."""
        self.config = config
        self.collection_manager = CollectionManager(config)
        self.document_manager = DocumentManager(config, self.collection_manager)
        self.thumbnail_resolver = ThumbnailPathResolver(config)
        self._agents = {}  # Cache agents by collection name
        self._document_processors = {}  # Cache processors by collection name
    
    def get_agent(self, collection_name: str) -> ResearchAgent:
        """Get or create research agent for collection."""
        if collection_name not in self._agents:
            self._agents[collection_name] = ResearchAgent(
                config=self.config,
                collection_name=collection_name,
                collection_manager=self.collection_manager
            )
        return self._agents[collection_name]
    
    def get_document_processor(self, collection_name: str) -> DocumentProcessor:
        """Get or create document processor for collection."""
        if collection_name not in self._document_processors:
            self._document_processors[collection_name] = DocumentProcessor(
                config=self.config,
                collection_name=collection_name,
                collection_manager=self.collection_manager
            )
        return self._document_processors[collection_name]
    
    def get_collections(self) -> List[str]:
        """Get all available collection display names."""
        try:
            pairs = self.collection_manager.list_collection_pairs()
            return [pair['display_name'] for pair in pairs] if pairs else [self.config.default_collection]
        except Exception as e:
            print(f"Error getting collections: {e}")
            return [self.config.default_collection]
    
    def get_metadata_options(self, collection_name: str) -> tuple:
        """Get available metadata options for filters."""
        try:
            agent = self.get_agent(collection_name)
            # Get pair info to access the chunks database directly
            pair = self.collection_manager.get_pair_by_display_name(collection_name)
            if not pair:
                return [], [], []
            
            # Access the database directly for metadata
            summary = agent.chunks_db.get_metadata_summary()
            
            filenames = list(summary.get('filenames', {}).keys())
            sources = list(summary.get('sources', {}).keys())
            headings = list(summary.get('headings', {}).keys())
            
            return filenames, sources, headings
        except Exception as e:
            print(f"Error getting metadata options: {e}")
            return [], [], []
    
    def get_collection_documents(self, collection_name: str) -> List[str]:
        """Get list of all documents in the collection."""
        try:
            agent = self.get_agent(collection_name)
            # Get pair info to access the chunks database directly
            pair = self.collection_manager.get_pair_by_display_name(collection_name)
            if not pair:
                return []
            
            # Access the database directly for metadata
            summary = agent.chunks_db.get_metadata_summary()
            
            # Get filenames and format them with document counts
            filenames = summary.get('filenames', {})
            document_list = []
            for filename, count in filenames.items():
                document_list.append(f"{filename} ({count} chunks)")
            
            return sorted(document_list)
        except Exception as e:
            print(f"Error getting collection documents: {e}")
            return []
    
    def search(self, query: str, collection_name: str, top_k: int = 5, 
               metadata_filter: Optional[Dict] = None) -> str:
        """Search for documents."""
        try:
            if not query.strip():
                return "Search query cannot be empty."
            
            agent = self.get_agent(collection_name)
            return agent.search(query, top_k, metadata_filter, 'both')
        except Exception as e:
            return f"Search error: {e}"
    
    def ask_ai(self, question: str, collection_name: str, response_length: str = 'medium',
               metadata_filter: Optional[Dict] = None) -> str:
        """Ask AI a question about documents."""
        try:
            if not question.strip():
                return "Question cannot be empty."
            
            agent = self.get_agent(collection_name)
            response, search_results = agent.ask(question, response_length, metadata_filter, 'chunks')
            return response
        except AIServiceError:
            return self._show_api_key_help()
        except Exception as e:
            return f"AI error: {e}"
    
    def process_documents(self, files: List, collection_name: str, source: Optional[str] = None,
                         force: bool = False) -> str:
        """Process uploaded documents."""
        try:
            if not files:
                return "No files selected."
            
            processor = self.get_document_processor(collection_name)
            
            # Capture output
            old_stdout = sys.stdout
            sys.stdout = captured = io.StringIO()
            
            try:
                file_paths = [file.name for file in files]
                source_value = None if source == "auto" else source
                
                result = processor.execute_processing_pipeline(
                    files=file_paths,
                    pipeline_type=PipelineType.PDF,  # Default to PDF pipeline
                    include_artifacts=True,
                    force=force,
                    source=source_value
                )
                
                output = captured.getvalue()
                return output + "\n" + result if output else result
            finally:
                sys.stdout = old_stdout
                
        except Exception as e:
            return f"Processing error: {e}"
    
    def get_collection_info(self, collection_name: str) -> str:
        """Get collection information."""
        try:
            agent = self.get_agent(collection_name)
            info = agent.chunks_db.get_collection_info()
            
            # Get metadata summary to count unique documents
            metadata_summary = agent.chunks_db.get_metadata_summary()
            document_count = len(metadata_summary.get('filenames', {}))
            
            # Format info
            result = f"📊 Collection Information: {collection_name}\n"
            result += f"Documents: {document_count}\n"
            result += f"Chunks: {info.get('points_count', 0)}\n"
            result += f"Vector size: {info.get('config', {}).get('size', 'unknown')}\n"
            
            # Add pair info if available
            pair = self.collection_manager.get_pair_by_display_name(collection_name)
            if pair:
                result += f"Chunks collection: {pair['chunks_collection']}\n"
                result += f"Artifacts collection: {pair['artifacts_collection']}\n"
                result += f"Created: {pair.get('created_at', 'unknown')}\n"
                if pair.get('description'):
                    result += f"Description: {pair['description']}\n"
            
            return result
        except Exception as e:
            return f"Error getting collection info: {e}"
    
    def get_metadata_summary(self, collection_name: str) -> str:
        """Get metadata summary for collection."""
        try:
            agent = self.get_agent(collection_name)
            summary = agent.chunks_db.get_metadata_summary()
            
            # Format summary
            result = f"📋 Metadata Summary for {collection_name}\n\n"
            
            # Files
            filenames = summary.get('filenames', {})
            result += f"📁 Files: {len(filenames)}\n"
            for filename, count in list(filenames.items())[:10]:  # Show top 10
                result += f"  • {filename} ({count} chunks)\n"
            if len(filenames) > 10:
                result += f"  ... and {len(filenames) - 10} more files\n"
            
            result += "\n"
            
            # Sources
            sources = summary.get('sources', {})
            result += f"📋 Sources: {len(sources)}\n"
            for source, count in sources.items():
                result += f"  • {source}: {count} chunks\n"
            
            result += "\n"
            
            # Headings
            headings = summary.get('headings', {})
            result += f"🏷️ Headings: {len(headings)}\n"
            for heading, count in list(headings.items())[:15]:  # Show top 15
                result += f"  • {heading} ({count} chunks)\n"
            if len(headings) > 15:
                result += f"  ... and {len(headings) - 15} more headings\n"
            
            result += f"\n📊 Total: {sum(filenames.values())} chunks"
            
            return result
        except Exception as e:
            return f"Error getting metadata summary: {e}"
    
    def delete_documents(self, filenames: List[str], collection_name: str) -> str:
        """Delete documents by filename."""
        try:
            if not filenames:
                return "No files selected for deletion."
            
            agent = self.get_agent(collection_name)
            
            # Get the collection pair info
            pair = self.collection_manager.get_pair_by_display_name(collection_name)
            if not pair:
                return f"❌ Collection '{collection_name}' not found"
            
            deleted_count = 0
            results = []
            
            for filename in filenames:
                try:
                    metadata_filter = {'filename': filename}
                    
                    # Delete from both chunks and artifacts databases
                    chunks_deleted = agent.chunks_db.delete_documents(metadata_filter)
                    artifacts_deleted = agent.artifacts_db.delete_documents(metadata_filter)
                    
                    total_deleted = chunks_deleted + artifacts_deleted
                    if total_deleted > 0:
                        results.append(f"✅ {filename}: Deleted {total_deleted} items ({chunks_deleted} chunks, {artifacts_deleted} artifacts)")
                        deleted_count += 1
                        
                        # Update the collection manager metadata
                        # Find the document by filename in the metadata
                        pair_id = pair['pair_id']
                        for doc_key, doc_data in self.collection_manager.metadata["documents"].items():
                            if doc_data.get("metadata", {}).get("filename") == filename:
                                # Remove this document from the pair
                                if pair_id in doc_data.get("in_collections", {}):
                                    del doc_data["in_collections"][pair_id]
                                    # If document is not in any other collections, remove it entirely
                                    if not doc_data.get("in_collections"):
                                        del self.collection_manager.metadata["documents"][doc_key]
                                    # Update the document count for the pair
                                    if self.collection_manager.metadata["collection_pairs"][pair_id]["document_count"] > 0:
                                        self.collection_manager.metadata["collection_pairs"][pair_id]["document_count"] -= 1
                                    break
                        
                        # Save the updated metadata
                        self.collection_manager._save_metadata()
                    else:
                        # Even if no vector items were deleted, check if we need to clean up metadata
                        pair_id = pair['pair_id']
                        metadata_updated = False
                        for doc_key, doc_data in self.collection_manager.metadata["documents"].items():
                            if doc_data.get("metadata", {}).get("filename") == filename:
                                if pair_id in doc_data.get("in_collections", {}):
                                    del doc_data["in_collections"][pair_id]
                                    if not doc_data.get("in_collections"):
                                        del self.collection_manager.metadata["documents"][doc_key]
                                    if self.collection_manager.metadata["collection_pairs"][pair_id]["document_count"] > 0:
                                        self.collection_manager.metadata["collection_pairs"][pair_id]["document_count"] -= 1
                                    metadata_updated = True
                                    break
                        
                        if metadata_updated:
                            self.collection_manager._save_metadata()
                            results.append(f"✅ {filename}: Removed from collection metadata")
                            deleted_count += 1
                        else:
                            results.append(f"⚠️ {filename}: No matching documents found")
                        
                except Exception as e:
                    results.append(f"❌ {filename}: Error - {e}")
            
            summary = f"📊 Summary: {deleted_count}/{len(filenames)} files deleted successfully\n\n"
            return summary + "\n".join(results)
        except Exception as e:
            return f"Deletion error: {e}"
    
    def create_collection(self, display_name: str, description: str = "") -> str:
        """Create a new collection pair."""
        try:
            if not display_name or not display_name.strip():
                return "❌ Display name is required"
            
            pair_info = self.collection_manager.create_collection_pair(
                display_name=display_name.strip(),
                description=description.strip()
            )
            
            return f"✅ Created collection: {display_name}"
        except ValueError as e:
            return f"❌ {e}"
        except Exception as e:
            return f"❌ Error creating collection: {e}"
    
    def rename_collection(self, old_name: str, new_name: str) -> str:
        """Rename a collection's display name."""
        try:
            if not old_name or not old_name.strip():
                return "❌ Current display name is required"
            
            if not new_name or not new_name.strip():
                return "❌ New display name is required"
            
            success = self.collection_manager.rename_collection_pair(
                old_name.strip(), 
                new_name.strip()
            )
            
            if success:
                return f"✅ Renamed collection from '{old_name}' to '{new_name}'"
            else:
                return f"❌ Collection '{old_name}' not found"
        except ValueError as e:
            return f"❌ {e}"
        except Exception as e:
            return f"❌ Error renaming collection: {e}"
    
    def delete_collection(self, collection_name: str) -> str:
        """Delete a collection and all its data."""
        try:
            if not collection_name or not collection_name.strip():
                return "❌ Collection display name is required"
            
            success = self.collection_manager.delete_collection_pair(collection_name.strip())
            
            if success:
                return f"✅ Deleted collection: {collection_name}"
            else:
                return f"❌ Collection '{collection_name}' not found"
        except Exception as e:
            return f"❌ Error deleting collection: {e}"
    
    def list_collections(self) -> str:
        """List all collections with metadata."""
        try:
            pairs = self.collection_manager.list_collection_pairs()
            
            if not pairs:
                return "📁 No collection pairs found."
            
            result = "📚 Collections:\n"
            for pair in pairs:
                display_name = pair['display_name']
                doc_count = pair.get('document_count', 0)
                status = pair.get('status', 'unknown')
                created = pair.get('created_at', 'unknown')[:10]  # Date only
                
                result += f"  • {display_name} ({doc_count} documents, {status}, created: {created})\n"
                
                if pair.get('description'):
                    result += f"    Description: {pair['description']}\n"
            
            return result.rstrip()
        except Exception as e:
            return f"❌ Error listing collections: {e}"
    
    def _show_api_key_help(self) -> str:
        """Show API key setup instructions."""
        return (
            "❌ OpenAI API key not found!\n"
            "   Please set your API key using one of these methods:\n"
            "   1. Create a .env file with: OPENAI_API_KEY=your_key_here\n"
            "   2. Set environment variable: set OPENAI_API_KEY=your_key_here\n"
            "   3. Add api_key to config.yaml under ai_model section\n"
            "   Get your API key from: https://platform.openai.com/api-keys"
        )
    
    def search_with_thumbnails(self, query: str, collection_name: str, top_k: int = 5, 
                              metadata_filter: Optional[Dict] = None, search_type: str = 'both') -> Tuple[str, List[str]]:
        """Search for documents and return results with thumbnails."""
        try:
            if not query.strip():
                return "Search query cannot be empty.", []
            
            agent = self.get_agent(collection_name)
            
            # Get raw search results (unformatted)
            search_results = agent.search(query, top_k, metadata_filter, search_type, format_results=False)
            
            # Format search results for display
            search_text = agent.formatter.format_search_results(search_results)
            
            # Extract thumbnail file paths (now only returns valid paths, no None values)
            thumbnails = self.thumbnail_resolver.extract_thumbnails_from_search_results(search_results)
            
            return search_text, thumbnails
        except Exception as e:
            return f"Search error: {e}", []
    
    def ask_ai_with_thumbnails(self, question: str, collection_name: str, response_length: str = 'medium',
                              metadata_filter: Optional[Dict] = None, search_type: str = 'both') -> Tuple[str, List[str]]:
        """Ask AI a question and return response with thumbnails."""
        try:
            if not question.strip():
                return "Question cannot be empty.", []
            
            agent = self.get_agent(collection_name)
            response, search_results = agent.ask(question, response_length, metadata_filter, search_type)
            
            # Extract thumbnail file paths from the search results used for context
            thumbnails = self.thumbnail_resolver.extract_thumbnails_from_search_results(search_results)
            
            return response, thumbnails
        except AIServiceError:
            return self._show_api_key_help(), []
        except Exception as e:
            return f"AI error: {e}", []
    
    # Document Management Methods (delegated to core DocumentManager)
    
    def get_all_documents(self) -> List[str]:
        """Get all available documents across all collections."""
        try:
            documents = self.document_manager.get_all_documents()
            return [doc['display_name'] for doc in documents]
        except Exception as e:
            return [f"Error loading documents: {e}"]
    
    def get_document_details(self, selected_documents: List[str]) -> str:
        """Get detailed information about selected documents."""
        return self.document_manager.get_document_details(selected_documents)
    
    def delete_documents_permanently(self, selected_documents: List[str]) -> str:
        """Permanently delete documents from the system."""
        return self.document_manager.delete_documents_permanently(selected_documents)
    
    def get_available_documents_for_collection(self, collection_name: str) -> List[str]:
        """Get documents that are not in the specified collection."""
        return self.document_manager.get_available_documents_for_collection(collection_name)
    
    def add_documents_to_collection(self, selected_documents: List[str], collection_name: str) -> str:
        """Add selected documents to the specified collection."""
        return self.document_manager.add_documents_to_collection(selected_documents, collection_name)
    
    def remove_documents_from_collection(self, selected_documents: List[str], collection_name: str) -> str:
        """Remove selected documents from the specified collection."""
        return self.document_manager.remove_documents_from_collection(selected_documents, collection_name)