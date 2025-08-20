"""Command line argument parser for Vector."""

import argparse
from typing import List


def create_parser() -> argparse.ArgumentParser:
    """Create the main argument parser for Vector CLI."""
    parser = argparse.ArgumentParser(
        prog='vector',
        description='Vector - AI-Powered Document Processing & Search',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  vector search "zoning requirements" --collection documents
  vector ask "What are the fire safety requirements?" --length long
  vector process documents/*.pdf --source manuals
  vector delete filename "old_document.pdf" --collection documents
  vector delete source "outdated_manuals" --collection documents
  vector info --collection documents
  vector models --provider openai
  vector collections
  vector create-collection "Legal Docs Q1" chunks --description "Q1 legal documents"
  vector rename-collection "Legal Docs Q1" "Legal Documents Q1 2024"
  vector delete-collection "Old Collection" --force
        """
    )
    
    # Subcommands
    subparsers = parser.add_subparsers(
        dest='command',
        help='Available commands',
        metavar='COMMAND'
    )
    
    # Search command
    search_parser = subparsers.add_parser(
        'search',
        help='Search documents for relevant content'
    )
    search_parser.add_argument(
        'question',
        help='Search query'
    )
    search_parser.add_argument(
        '--collection', '-c',
        help='Collection name (default: from config)',
        default=None
    )
    search_parser.add_argument(
        '--top-k', '-k',
        type=int,
        default=5,
        help='Number of results to return (default: 5)'
    )
    search_parser.add_argument(
        '--metadata-filter',
        help='JSON string for metadata filtering'
    )
    search_parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    # Ask command
    ask_parser = subparsers.add_parser(
        'ask',
        help='Ask AI a question about the documents'
    )
    ask_parser.add_argument(
        'question',
        help='Question to ask'
    )
    ask_parser.add_argument(
        '--collection', '-c',
        help='Collection name (default: from config)',
        default=None
    )
    ask_parser.add_argument(
        '--length', '-l',
        choices=['short', 'medium', 'long'],
        default='medium',
        help='Response length (default: medium)'
    )
    ask_parser.add_argument(
        '--metadata-filter',
        help='JSON string for metadata filtering'
    )
    ask_parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    # Process command
    process_parser = subparsers.add_parser(
        'process',
        help='Process and index documents'
    )
    process_parser.add_argument(
        'files',
        nargs='+',
        help='Files or directories to process'
    )
    process_parser.add_argument(
        '--collection', '-c',
        help='Collection name (default: from config)',
        default=None
    )
    process_parser.add_argument(
        '--source', '-s',
        choices=['ordinances', 'manuals', 'checklists', 'other'],
        help='Source type for documents'
    )
    process_parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='Force reprocessing of existing documents'
    )
    process_parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    # Info command
    info_parser = subparsers.add_parser(
        'info',
        help='Show collection information'
    )
    info_parser.add_argument(
        '--collection', '-c',
        help='Collection name (default: from config)',
        default=None
    )
    info_parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    # Metadata command
    metadata_parser = subparsers.add_parser(
        'metadata',
        help='Show metadata summary'
    )
    metadata_parser.add_argument(
        '--collection', '-c',
        help='Collection name (default: from config)',
        default=None
    )
    metadata_parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    # Delete command
    delete_parser = subparsers.add_parser(
        'delete',
        help='Delete documents matching metadata filter'
    )
    delete_parser.add_argument(
        'key',
        help='Metadata key to filter by (e.g., filename, source)'
    )
    delete_parser.add_argument(
        'value',
        help='Metadata value to match'
    )
    delete_parser.add_argument(
        '--collection', '-c',
        help='Collection name (default: from config)',
        default=None
    )
    delete_parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    # Clear command
    clear_parser = subparsers.add_parser(
        'clear',
        help='Clear collection (with confirmation)'
    )
    clear_parser.add_argument(
        '--collection', '-c',
        help='Collection name (default: from config)',
        default=None
    )
    clear_parser.add_argument(
        '--force',
        action='store_true',
        help='Skip confirmation prompt'
    )
    clear_parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    # Models command
    models_parser = subparsers.add_parser(
        'models',
        help='List available AI models'
    )
    models_parser.add_argument(
        '--provider', '-p',
        choices=['openai'],
        default='openai',
        help='AI provider to list models for (default: openai)'
    )
    models_parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    # Collections command
    collections_parser = subparsers.add_parser(
        'collections',
        help='List all collections'
    )
    collections_parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    # Create collection command
    create_collection_parser = subparsers.add_parser(
        'create-collection',
        help='Create a new collection with display name'
    )
    create_collection_parser.add_argument(
        'display_name',
        help='Human-readable name for the collection'
    )
    create_collection_parser.add_argument(
        'modality',
        choices=['chunks', 'artifacts'],
        help='Type of data to store (chunks or artifacts)'
    )
    create_collection_parser.add_argument(
        '--description', '-d',
        help='Optional description for the collection',
        default=''
    )
    create_collection_parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    # Rename collection command
    rename_collection_parser = subparsers.add_parser(
        'rename-collection',
        help='Rename a collection\'s display name'
    )
    rename_collection_parser.add_argument(
        'old_name',
        help='Current display name of the collection'
    )
    rename_collection_parser.add_argument(
        'new_name',
        help='New display name for the collection'
    )
    rename_collection_parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    # Delete collection command
    delete_collection_parser = subparsers.add_parser(
        'delete-collection',
        help='Delete a collection and all its data'
    )
    delete_collection_parser.add_argument(
        'display_name',
        help='Display name of the collection to delete'
    )
    delete_collection_parser.add_argument(
        '--force',
        action='store_true',
        help='Skip confirmation prompt'
    )
    delete_collection_parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    
    return parser
