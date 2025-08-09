"""Argument parser setup for RegScout CLI."""

import argparse


def create_parser():
    """Create and configure the main argument parser."""
    parser = argparse.ArgumentParser(
        description="RegScout CLI - Document processing and regulatory querying tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_get_examples_text()
    )

    # Global collection argument
    parser.add_argument(
        '--collection', '-c', type=str, default=None,
        help='Specify collection name (default: regscout_chunks)'
    )

    # Add subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    _add_process_parser(subparsers)
    _add_search_parser(subparsers)
    _add_ask_parser(subparsers)
    _add_info_parser(subparsers)
    _add_clear_parser(subparsers)
    _add_metadata_parser(subparsers)

    return parser


def _add_process_parser(subparsers):
    """Add process command parser."""
    parser = subparsers.add_parser(
        'process', 
        help='Process documents and add to knowledge base'
    )
    parser.add_argument(
        'files', 
        nargs='+', 
        help=('Files or directories to process (supports .txt, .md, .pdf, '
              '.docx). Directories are processed recursively.')
    )
    parser.add_argument(
        '--force', 
        action='store_true',
        help='Force reprocessing of files even if already in knowledge base'
    )
    parser.add_argument(
        '--source', 
        choices=['ordinances', 'manuals', 'checklists', 'other'],
        help='Override source category (default: auto-detect from folder name)'
    )


def _add_search_parser(subparsers):
    """Add search command parser."""
    parser = subparsers.add_parser('search', help='Search the knowledge base')
    parser.add_argument('question', help='Search query')
    parser.add_argument(
        '-k', '--top-k', 
        type=int, 
        default=5, 
        help='Number of results to return (default: 5)'
    )
    parser.add_argument(
        '--filename',
        help='Filter results by specific filename'
    )


def _add_ask_parser(subparsers):
    """Add ask command parser."""
    parser = subparsers.add_parser(
        'ask', 
        help='Ask AI a question with chunk context'
    )
    parser.add_argument('question', help='Question for AI')
    parser.add_argument(
        '--filename',
        help='Filter context by specific filename'
    )
    
    # Response length group - mutually exclusive
    length_group = parser.add_mutually_exclusive_group()
    length_group.add_argument(
        '--short', 
        action='store_const', 
        const='short',
        dest='response_length',
        help='Short, concise answer (150 tokens)'
    )
    length_group.add_argument(
        '--medium', 
        action='store_const', 
        const='medium',
        dest='response_length',
        help='Balanced detail level (500 tokens) [default]'
    )
    length_group.add_argument(
        '--long', 
        action='store_const', 
        const='long',
        dest='response_length',
        help='Comprehensive answer (1500 tokens)'
    )
    
    # Set default response length
    parser.set_defaults(response_length='medium')


def _add_info_parser(subparsers):
    """Add info command parser."""
    subparsers.add_parser('info', help='Show knowledge base information')


def _add_clear_parser(subparsers):
    """Add clear command parser."""
    subparsers.add_parser('clear', help='Clear the knowledge base')

def _add_metadata_parser(subparsers):
    """Add metadata command parser."""
    parser = subparsers.add_parser('metadata', help='Show collection metadata summary')
    parser.add_argument(
        '-c', '--collection',
        default='regscout_chunks',
        help='Collection name (default: regscout_chunks)'
    )


def _get_examples_text():
    """Get examples text for help."""
    return (
        "Examples:\n"
        "  %(prog)s process ordinance.pdf rules.txt          # Process specific files\n"
        "  %(prog)s --collection zoning process data/        # Process to specific collection\n"
        "  %(prog)s -c utilities process utilities/          # Process to utilities collection\n"
        "  %(prog)s process data/ --source ordinances        # Process with specific source category\n"
        "  %(prog)s process data/                             # Process all files in directory\n"
        "  %(prog)s process data/ --force                     # Process directory, include processed files\n"
        "  %(prog)s process data/ more_docs/                  # Process multiple directories\n"
        "  %(prog)s search \"setback requirements\"            # Search for relevant content\n"
        "  %(prog)s --collection zoning search \"setbacks\"   # Search in specific collection\n"
        "  %(prog)s ask \"What are the parking rules?\"       # Get AI-powered answers\n"
        "  %(prog)s ask --short \"What is setback?\"          # Get brief answer\n"
        "  %(prog)s ask --long \"Explain zoning rules\"       # Get comprehensive answer\n"
        "  %(prog)s -c drainage ask \"What are pipe requirements?\" # Ask using specific collection\n"
        "  %(prog)s info                                     # Show knowledge base status\n"
        "  %(prog)s --collection all info                   # Show info for all collections\n"
        "  %(prog)s clear                                    # Clear all chunks\n"
        "  %(prog)s --collection temp clear                 # Clear specific collection\n"
        "\n"
        "The tool uses local file storage and works offline (except for AI features).\n"
    )
