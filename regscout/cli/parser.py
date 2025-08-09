"""Command line argument parser for RegScout."""

import argparse
from typing import List


def create_parser() -> argparse.ArgumentParser:
    """Create the main argument parser for RegScout CLI."""
    parser = argparse.ArgumentParser(
        prog='regscout',
        description='RegScout - AI-Powered Document Processing & Search',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  regscout search "zoning requirements" --collection coweta
  regscout ask "What are the fire safety requirements?" --length long
  regscout process documents/*.pdf --source ordinances
  regscout info --collection all
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
        help='Collection name or "all" to list all collections',
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
    
    return parser
