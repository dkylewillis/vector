#!/usr/bin/env python3
"""RegScout CLI - Document processing and regulatory querying tool."""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from src.cli.parsers import create_parser
from src.cli.commands import RegScoutCommands
from config import Config

# Load environment variables
load_dotenv()


def main():
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Initialize commands
    config = Config('./config/settings.yaml')
    commands = RegScoutCommands(config)
    collection_name = args.collection or "regscout_chunks"

    try:
        # Route to appropriate command
        if args.command == 'process':
            commands.process(args.files, args.force, collection_name)
        elif args.command == 'search':
            commands.search(args.question, args.top_k, collection_name, args.filename)
        elif args.command == 'ask':
            commands.ask(args.question, args.response_length, collection_name, args.filename)
        elif args.command == 'info':
            commands.info(collection_name)
        elif args.command == 'clear':
            commands.clear(collection_name)
        elif args.command == 'metadata':
            commands.metadata_summary(collection_name)

    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
