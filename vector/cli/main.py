"""Main CLI entry point for Vector."""

import argparse
import sys
from typing import Optional

from ..config import Config
from ..exceptions import VectorError, ValidationError, AIServiceError
from .parser import create_parser
from ..core.agent import ResearchAgent
from ..core.processor import DocumentProcessor
from ..core.database import VectorDatabase
from ..core.collection_manager import CollectionManager
from ..utils.formatting import CLIFormatter


class VectorCLI:
    """Main CLI coordinator for Vector."""
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize CLI with configuration."""
        self.config = config or Config()
        self.formatter = CLIFormatter()
        self.collection_manager = CollectionManager(self.config)
        self._agent = None
        self._document_processor = None
        self._database = None
        self._current_collection = None
    
    def get_agent(self, collection_name: str) -> ResearchAgent:
        """Get or create research agent for collection."""
        if self._agent is None or self._current_collection != collection_name:
            # For agents, we need the chunks collection from the pair
            resolved_collection = self._resolve_collection_name(collection_name, 'chunks')
            self._agent = ResearchAgent(self.config, resolved_collection, self.collection_manager)
            self._current_collection = collection_name
        return self._agent
    
    def get_document_processor(self, collection_name: str) -> DocumentProcessor:
        """Get or create document processor for collection."""
        if self._document_processor is None or self._current_collection != collection_name:
            # Document processor handles both collections internally
            self._document_processor = DocumentProcessor(self.config, collection_name, self.collection_manager)
            self._current_collection = collection_name
        return self._document_processor
    
    def get_database(self, collection_name: str) -> VectorDatabase:
        """Get or create database for collection."""
        if self._database is None or self._current_collection != collection_name:
            # For database operations, we typically work with chunks collection
            resolved_collection = self._resolve_collection_name(collection_name, 'chunks')
            self._database = VectorDatabase(resolved_collection, self.config, self.collection_manager)
            self._current_collection = collection_name
        return self._database
    
    def _resolve_collection_name(self, collection_name: str, collection_type: str = 'chunks') -> str:
        """Resolve display name to actual collection name for specified type.
        
        Args:
            collection_name: Display name or actual collection name
            collection_type: 'chunks' or 'artifacts'
            
        Returns:
            Actual collection name
        """
        if not self.collection_manager:
            return collection_name
            
        # If it's already a collection pair name, return as-is
        if collection_name.startswith('c_') and ('__chunks' in collection_name or '__artifacts' in collection_name):
            return collection_name
            
        # Try to get pair by display name
        pair_info = self.collection_manager.get_pair_by_display_name(collection_name)
        if pair_info:
            return pair_info[f'{collection_type}_collection']
            
        return collection_name
    
    def execute_command(self, command: str, collection_name: str = None, **kwargs) -> str:
        """Execute a command with automatic initialization."""
        try:
            collection_name = collection_name or self.config.default_collection
            
            # Handle special cases that don't need agent initialization
            if command == 'models':
                return self._list_available_models(kwargs.get('provider', 'openai'))
            elif command == 'collections':
                return self._handle_collections_command(kwargs)
            elif command == 'create-collection':
                return self._create_collection(kwargs)
            elif command == 'rename-collection':
                return self._rename_collection(kwargs)
            elif command == 'delete-collection':
                return self._delete_collection(kwargs)
            
            # Get agent for collection
            agent = self.get_agent(collection_name)
            
            # Execute command through appropriate service
            if command == 'search':
                search_type = kwargs.get('type', 'chunks')
                return self._handle_search(collection_name, kwargs.get('question', ''), 
                                         search_type, kwargs.get('top_k', 5), 
                                         kwargs.get('metadata_filter'))
            elif command == 'ask':
                agent = self.get_agent(collection_name)
                return agent.ask(kwargs.get('question', ''),
                               kwargs.get('response_length', 'medium'),
                               kwargs.get('metadata_filter'))
            elif command == 'process':
                doc_processor = self.get_document_processor(collection_name)
                # Convert --no-artifacts flag to index_artifacts boolean
                index_artifacts = not kwargs.get('no_artifacts', False)
                # Convert --use-pdf-pipeline flag to use_vlm_pipeline boolean (inverted)
                use_vlm_pipeline = not kwargs.get('use_pdf_pipeline', False)
                return doc_processor.process_and_index_files(kwargs.get('files', []),
                                         kwargs.get('force', False),
                                         kwargs.get('source'),
                                         index_artifacts,
                                         use_vlm_pipeline)
            elif command == 'info':
                database = self.get_database(collection_name)
                info = database.get_collection_info()
                return self.formatter.format_info(info)
            elif command == 'metadata':
                database = self.get_database(collection_name)
                summary = database.get_metadata_summary()
                return self.formatter.format_metadata_summary(summary)
            elif command == 'clear':
                database = self.get_database(collection_name)
                database.clear_collection()
                return f"✅ Collection '{collection_name}' cleared successfully (metadata preserved)"
            elif command == 'delete':
                database = self.get_database(collection_name)
                metadata_filter = {kwargs.get('key'): kwargs.get('value')}
                if not metadata_filter or not kwargs.get('key'):
                    raise VectorError("Metadata filter cannot be empty for safety")
                database.delete_documents(metadata_filter)
                filter_display = ", ".join([f"{k}={v}" for k, v in metadata_filter.items()])
                return f"✅ Deleted documents matching filter: {filter_display}"
            else:
                raise ValidationError(f"Unknown command: {command}")
                
        except AIServiceError:
            return self._show_api_key_help()
        except ValidationError as e:
            return f"❌ {e}"
        except VectorError as e:
            return f"❌ {e}"
        except Exception as e:
            return f"❌ Unexpected error: {e}"
    
    def _list_available_models(self, provider: str) -> str:
        """List available models for the specified provider."""
        try:
            from ..ai.factory import AIModelFactory
            
            # Check if provider is supported
            available_providers = AIModelFactory.get_available_providers()
            if provider not in available_providers:
                return f"❌ Unsupported provider: {provider}. Available providers: {', '.join(available_providers)}"
            
            # Create a model instance to get available models
            model = AIModelFactory.create_model(self.config, 'search')
            available_models = model.get_available_models()
            
            if not available_models:
                return f"📝 No models available for provider: {provider}"
            
            # Format the output
            result = f"🤖 Available models for {provider.upper()}:\n"
            for i, model_name in enumerate(available_models, 1):
                result += f"   {i:2d}. {model_name}\n"
            
            return result.rstrip()
            
        except AIServiceError as e:
            if "API key" in str(e):
                return self._show_api_key_help()
            return f"❌ Error accessing {provider} models: {e}"
        except Exception as e:
            return f"❌ Error listing models: {e}"
    
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
    
    def _handle_collections_command(self, kwargs) -> str:
        """Handle the collections list command."""
        try:
            pairs = self.collection_manager.list_collection_pairs()
            if not pairs:
                return "📝 No collection pairs found"
            
            result = "📚 Collection Pairs:\n"
            for pair in pairs:
                result += f"   • {pair['display_name']}\n"
                result += f"     Chunks: {pair['chunks_collection']}\n"
                result += f"     Artifacts: {pair['artifacts_collection']}\n"
                if pair.get('description'):
                    result += f"     Description: {pair['description']}\n"
                result += f"     Documents: {pair['document_count']}\n"
                result += f"     Created: {pair['created_at'][:10]}\n\n"
            
            return result.rstrip()
        except Exception as e:
            return f"❌ Error listing collection pairs: {e}"
    
    def _create_collection(self, kwargs) -> str:
        """Create a new collection pair."""
        try:
            display_name = kwargs.get('display_name')
            description = kwargs.get('description', '')
            
            if not display_name:
                return "❌ Display name is required"
            
            # Create collection pair
            pair_info = self.collection_manager.create_collection_pair(
                display_name=display_name,
                description=description
            )
            
            # Create the actual vector database collections
            try:
                # Use a default vector size - this will be updated when documents are first added
                vector_size = 384
                
                # Create chunks collection
                chunks_db = VectorDatabase(pair_info['chunks_collection'], self.config, self.collection_manager)
                chunks_db.create_collection(vector_size)
                
                # Create artifacts collection  
                artifacts_db = VectorDatabase(pair_info['artifacts_collection'], self.config, self.collection_manager)
                artifacts_db.create_collection(vector_size)
                
                return (f"✅ Created collection pair '{display_name}'\n"
                       f"   Chunks: {pair_info['chunks_collection']}\n"
                       f"   Artifacts: {pair_info['artifacts_collection']}")
            except Exception as e:
                # If database creation fails, clean up metadata
                self.collection_manager.delete_collection_pair(display_name)
                return f"❌ Failed to create vector database collections: {e}"
            
        except ValueError as e:
            return f"❌ {e}"
        except Exception as e:
            return f"❌ Error creating collection pair: {e}"
    
    def _rename_collection(self, kwargs) -> str:
        """Rename a collection pair's display name."""
        try:
            old_name = kwargs.get('old_name')
            new_name = kwargs.get('new_name')
            
            if not old_name or not new_name:
                return "❌ Both old_name and new_name are required"
            
            success = self.collection_manager.rename_collection_pair(old_name, new_name)
            if success:
                return f"✅ Renamed collection pair from '{old_name}' to '{new_name}'"
            else:
                return f"❌ Collection pair '{old_name}' not found"
        except ValueError as e:
            return f"❌ {e}"
        except Exception as e:
            return f"❌ Error renaming collection pair: {e}"
    
    def _delete_collection(self, kwargs) -> str:
        """Delete a collection pair and its metadata."""
        try:
            display_name = kwargs.get('display_name')
            force = kwargs.get('force', False)
            
            if not display_name:
                return "❌ display_name is required"
            
            # Get collection pair info first
            pair_info = self.collection_manager.get_pair_by_display_name(display_name)
            if not pair_info:
                return f"❌ Collection pair '{display_name}' not found"
            
            # Confirm deletion unless forced
            if not force:
                return (f"⚠️  This will permanently delete collection pair '{display_name}' "
                       f"({pair_info['chunks_collection']} & {pair_info['artifacts_collection']}) "
                       "and all its data. Use --force to confirm.")
            
            # Delete both collections from vector database
            try:
                # Delete chunks collection
                chunks_db = VectorDatabase(pair_info['chunks_collection'], self.config, self.collection_manager)
                if chunks_db.collection_exists():
                    chunks_db.delete_collection()
                
                # Delete artifacts collection
                artifacts_db = VectorDatabase(pair_info['artifacts_collection'], self.config, self.collection_manager)
                if artifacts_db.collection_exists():
                    artifacts_db.delete_collection()
                
                # Delete metadata
                self.collection_manager.delete_collection_pair(display_name)
                
                return f"✅ Deleted collection pair '{display_name}' and all its data"
            except Exception as e:
                # If database deletion fails, try to clean up metadata manually
                print(f"⚠️  Warning: Could not delete vector data: {e}")
                success = self.collection_manager.delete_collection_pair(display_name)
                if success:
                    return f"⚠️  Deleted collection pair metadata for '{display_name}', but vector data deletion failed: {e}"
                else:
                    return f"❌ Error deleting collection pair: {e}"
        except Exception as e:
            return f"❌ Error deleting collection pair: {e}"
    
    def _handle_search(self, collection_name: str, query: str, search_type: str, top_k: int, metadata_filter: str) -> str:
        """Handle search command with support for chunks, artifacts, or both.
        
        Args:
            collection_name: Name of the collection pair
            query: Search query
            search_type: 'chunks', 'artifacts', or 'both'
            top_k: Number of results to return
            metadata_filter: Optional metadata filter
            
        Returns:
            Formatted search results
        """
        try:
            if not query.strip():
                return "❌ Search query cannot be empty"
                
            from ..core.embedder import Embedder
            from ..core.database import VectorDatabase
            
            embedder = Embedder(self.config)
            query_vector = embedder.embed_text(query)
            
            # Get collection pair info
            pair_info = self.collection_manager.get_pair_by_display_name(collection_name)
            if not pair_info:
                return f"❌ Collection pair '{collection_name}' not found"
            
            results = []
            
            # Search chunks if requested
            if search_type in ['chunks', 'both']:
                try:
                    chunks_db = VectorDatabase(pair_info['chunks_collection'], self.config, self.collection_manager)
                    chunk_results = chunks_db.search(query_vector, top_k, metadata_filter)
                    for result in chunk_results:
                        results.append({
                            'type': 'chunk',
                            'score': result.score,
                            'text': result.text,
                            'metadata': result.metadata
                        })
                except Exception as e:
                    if search_type == 'chunks':
                        return f"❌ Error searching chunks: {e}"
                    else:
                        print(f"⚠️  Warning: Could not search chunks: {e}")
            
            # Search artifacts if requested
            if search_type in ['artifacts', 'both']:
                try:
                    artifacts_db = VectorDatabase(pair_info['artifacts_collection'], self.config, self.collection_manager)
                    artifact_results = artifacts_db.search(query_vector, top_k, metadata_filter)
                    for result in artifact_results:
                        results.append({
                            'type': 'artifact',
                            'score': result.score,
                            'text': result.text,
                            'metadata': result.metadata
                        })
                except Exception as e:
                    if search_type == 'artifacts':
                        return f"❌ Error searching artifacts: {e}"
                    else:
                        print(f"⚠️  Warning: Could not search artifacts: {e}")
            
            if not results:
                return f"🔍 No results found for '{query}'"
            
            # Sort results by score (descending) and limit to top_k
            results.sort(key=lambda x: x['score'], reverse=True)
            results = results[:top_k]
            
            # Format output
            output = []
            if search_type == 'both':
                output.append(f"🔍 Search Results ({search_type}):")
            else:
                output.append(f"🔍 Search Results:")
            output.append("")
            
            for i, result in enumerate(results, 1):
                result_type = result['type']
                score = result['score']
                metadata = result['metadata']
                text = result['text']
                
                if result_type == 'chunk':
                    output.append(f"Result {i} (Score: {score:.3f}) [CHUNK]")
                    output.append(f"📄 {metadata.get('filename', 'Unknown')}")
                    output.append(f"📂 Source: {metadata.get('source', 'Unknown')}")
                    output.append(f"📝 Content: {text[:200]}...")
                else:  # artifact
                    output.append(f"Result {i} (Score: {score:.3f}) [ARTIFACT]")
                    output.append(f"🖼️ Type: {metadata.get('type', 'unknown').title()}")
                    output.append(f"📄 {metadata.get('filename', 'Unknown')}")
                    output.append(f"📝 Caption: {metadata.get('caption', 'No caption')}")
                    headings = metadata.get('headings', [])
                    if headings:
                        output.append(f"📋 Context: {' > '.join(headings)}")
                
                output.append("-" * 50)
            
            return "\n".join(output)
            
        except Exception as e:
            return f"❌ Search error: {e}"


def main() -> int:
    """Main CLI entry point."""
    try:
        parser = create_parser()
        args = parser.parse_args()

        if not args.command:
            parser.print_help()
            return 0

        # Initialize CLI
        config = Config()
        cli = VectorCLI(config)

        # Execute command
        args_dict = vars(args)
        command = args_dict.pop('command')
        collection = args_dict.pop('collection', None)
        
        # Handle special case for global collection argument vs command-specific
        if collection is None and hasattr(args, 'collection'):
            collection = getattr(args, 'collection', None)
        
        result = cli.execute_command(
            command=command,
            collection_name=collection,
            **args_dict
        )
        
        if result:
            print(result)
        
        return 0

    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        return 0
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1
