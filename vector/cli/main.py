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
            self._agent = ResearchAgent(self.config, collection_name, self.collection_manager)
            self._current_collection = collection_name
        return self._agent
    
    def get_document_processor(self, collection_name: str) -> DocumentProcessor:
        """Get or create document processor for collection."""
        if self._document_processor is None or self._current_collection != collection_name:
            self._document_processor = DocumentProcessor(self.config, collection_name, self.collection_manager)
            self._current_collection = collection_name
        return self._document_processor
    
    def get_database(self, collection_name: str) -> VectorDatabase:
        """Get or create database for collection."""
        if self._database is None or self._current_collection != collection_name:
            self._database = VectorDatabase(collection_name, self.config, self.collection_manager)
            self._current_collection = collection_name
        return self._database
    
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
                agent = self.get_agent(collection_name)
                return agent.search(kwargs.get('question', ''), 
                                  kwargs.get('top_k', 5),
                                  kwargs.get('metadata_filter'))
            elif command == 'ask':
                agent = self.get_agent(collection_name)
                return agent.ask(kwargs.get('question', ''),
                               kwargs.get('response_length', 'medium'),
                               kwargs.get('metadata_filter'))
            elif command == 'process':
                doc_processor = self.get_document_processor(collection_name)
                return doc_processor.process_and_index_files(kwargs.get('files', []),
                                         kwargs.get('force', False),
                                         kwargs.get('source'))
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
            collections = self.collection_manager.list_collections()
            if not collections:
                return "📝 No collections found"
            
            result = "📚 Collections:\n"
            for collection in collections:
                result += f"   • {collection['display_name']}\n"
                result += f"     ID: {collection['collection_name']}\n"
                result += f"     Type: {collection['modality']}\n"
                if collection.get('description'):
                    result += f"     Description: {collection['description']}\n"
                result += f"     Created: {collection['created_at'][:10]}\n\n"
            
            return result.rstrip()
        except Exception as e:
            return f"❌ Error listing collections: {e}"
    
    def _create_collection(self, kwargs) -> str:
        """Create a new collection."""
        try:
            display_name = kwargs.get('display_name')
            modality = kwargs.get('modality')
            description = kwargs.get('description', '')
            
            if not display_name or not modality:
                return "❌ Both display_name and modality are required"
            
            # Create collection metadata
            collection_name = self.collection_manager.create_collection_name(
                display_name=display_name,
                modality=modality,
                description=description
            )
            
            # Also create the actual vector database collection
            try:
                # Use a default vector size - this will be updated when documents are first added
                vector_size = 1536  # OpenAI embedding size
                database = VectorDatabase(collection_name, self.config, self.collection_manager)
                database.create_collection(vector_size)
                
                return f"✅ Created collection '{display_name}' with ID: {collection_name}\n✅ Vector database collection created successfully"
            except Exception as e:
                # If database creation fails, clean up metadata
                self.collection_manager.delete_collection_metadata(display_name)
                return f"❌ Failed to create vector database collection: {e}"
            
        except ValueError as e:
            return f"❌ {e}"
        except Exception as e:
            return f"❌ Error creating collection: {e}"
    
    def _rename_collection(self, kwargs) -> str:
        """Rename a collection's display name."""
        try:
            old_name = kwargs.get('old_name')
            new_name = kwargs.get('new_name')
            
            if not old_name or not new_name:
                return "❌ Both old_name and new_name are required"
            
            success = self.collection_manager.rename_collection(old_name, new_name)
            if success:
                return f"✅ Renamed collection from '{old_name}' to '{new_name}'"
            else:
                return f"❌ Collection '{old_name}' not found"
        except ValueError as e:
            return f"❌ {e}"
        except Exception as e:
            return f"❌ Error renaming collection: {e}"
    
    def _delete_collection(self, kwargs) -> str:
        """Delete a collection and its metadata."""
        try:
            display_name = kwargs.get('display_name')
            force = kwargs.get('force', False)
            
            if not display_name:
                return "❌ display_name is required"
            
            # Get collection name first
            collection_name = self.collection_manager.get_collection_by_display_name(display_name)
            if not collection_name:
                return f"❌ Collection '{display_name}' not found"
            
            # Confirm deletion unless forced
            if not force:
                return (f"⚠️  This will permanently delete collection '{display_name}' ({collection_name}) "
                       "and all its data. Use --force to confirm.")
            
            # Delete from vector database using the proper delete_collection method
            # This will handle both vector data and metadata deletion through collection_manager
            try:
                database = VectorDatabase(collection_name, self.config, self.collection_manager)
                database.delete_collection()
                return f"✅ Deleted collection '{display_name}' and all its data"
            except Exception as e:
                # If database deletion fails, try to clean up metadata manually
                print(f"⚠️  Warning: Could not delete vector data: {e}")
                success = self.collection_manager.delete_collection_metadata(display_name)
                if success:
                    return f"⚠️  Deleted collection metadata for '{display_name}', but vector data deletion failed: {e}"
                else:
                    return f"❌ Error deleting collection: {e}"
        except Exception as e:
            return f"❌ Error deleting collection: {e}"
    


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
