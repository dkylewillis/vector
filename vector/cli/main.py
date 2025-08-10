"""Main CLI entry point for Vector."""

import argparse
import sys
from typing import Optional

from ..config import Config
from ..exceptions import VectorError, ValidationError, AIServiceError
from .parser import create_parser
from ..core.agent import ResearchAgent
from ..utils.formatting import CLIFormatter


class VectorCLI:
    """Main CLI coordinator for Vector."""
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize CLI with configuration."""
        self.config = config or Config()
        self.formatter = CLIFormatter()
        self._agent = None
        self._current_collection = None
    
    def get_agent(self, collection_name: str) -> ResearchAgent:
        """Get or create research agent for collection."""
        if self._agent is None or self._current_collection != collection_name:
            self._agent = ResearchAgent(self.config, collection_name)
            self._current_collection = collection_name
        return self._agent
    
    def execute_command(self, command: str, collection_name: str = None, **kwargs) -> str:
        """Execute a command with automatic initialization."""
        try:
            collection_name = collection_name or self.config.default_collection
            
            # Handle special cases that don't need agent initialization
            if command == 'info' and collection_name == 'all':
                return self._list_all_collections()
            
            # Get agent for collection
            agent = self.get_agent(collection_name)
            
            # Execute command through agent
            if command == 'search':
                return agent.search(kwargs.get('question', ''), 
                                  kwargs.get('top_k', 5),
                                  kwargs.get('metadata_filter'))
            elif command == 'ask':
                return agent.ask(kwargs.get('question', ''),
                               kwargs.get('response_length', 'medium'),
                               kwargs.get('metadata_filter'))
            elif command == 'process':
                return agent.process_files(kwargs.get('files', []),
                                         kwargs.get('force', False),
                                         kwargs.get('source'))
            elif command == 'info':
                return agent.get_info()
            elif command == 'metadata':
                return agent.get_metadata_summary()
            elif command == 'clear':
                return agent.clear_collection()
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
    
    def _list_all_collections(self) -> str:
        """List all collections without initializing agent."""
        try:
            from ..core.database import VectorDatabase
            temp_db = VectorDatabase("temp", self.config)
            return self.formatter.format_collections_list(temp_db.client)
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
