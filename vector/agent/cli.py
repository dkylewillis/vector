"""Agent CLI for search and Q&A operations."""

import argparse
import sys
from typing import Dict, Any, Optional

from ..config import Config
from ..exceptions import VectorError, AIServiceError
from ..core.collection_manager import CollectionManager
from .agent import ResearchAgent


def parse_filter_args(filter_strings: list) -> Optional[Dict[str, Any]]:
    """Parse filter arguments from command line."""
    if not filter_strings:
        return None
    
    filters = {}
    for filter_str in filter_strings:
        try:
            key, value = filter_str.split("=", 1)
            # Handle multiple values for the same key
            if key in filters:
                if not isinstance(filters[key], list):
                    filters[key] = [filters[key]]
                filters[key].append(value)
            else:
                filters[key] = value
        except ValueError:
            print(f"⚠️  Invalid filter format: {filter_str} (expected key=value)")
            continue
    
    return filters if filters else None


def main():
    """Main entry point for vector-agent CLI."""
    parser = argparse.ArgumentParser(
        prog="vector-agent", 
        description="Vector research agent CLI for search and Q&A"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands", required=True)

    # Ask command
    ask_parser = subparsers.add_parser("ask", help="Ask a question against a collection")
    ask_parser.add_argument("question", help="Question to ask")
    ask_parser.add_argument("--collection", "-c", required=True, help="Collection display name")
    ask_parser.add_argument("--length", choices=["short", "medium", "long"], default="medium", 
                           help="Response length")
    ask_parser.add_argument("--type", choices=["chunks", "artifacts", "both"], default="both", 
                           help="Search type for context")
    ask_parser.add_argument("--filter", action="append", help="Metadata filter (key=value)")
    ask_parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")

    # Search command
    search_parser = subparsers.add_parser("search", help="Search chunks or artifacts")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--collection", "-c", required=True, help="Collection display name")
    search_parser.add_argument("--top-k", "-k", type=int, default=5, help="Number of results to return")
    search_parser.add_argument("--type", choices=["chunks", "artifacts", "both"], default="both", 
                              help="Search type")
    search_parser.add_argument("--filter", action="append", help="Metadata filter (key=value)")
    search_parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")

    # Model info command
    model_parser = subparsers.add_parser("model-info", help="Show AI model configuration")
    model_parser.add_argument("--collection", "-c", required=True, help="Collection display name")

    # Collection info command  
    collection_parser = subparsers.add_parser("collection-info", help="Show collection information")
    collection_parser.add_argument("--collection", "-c", required=True, help="Collection display name")

    args = parser.parse_args()

    try:
        config = Config()
        collection_manager = CollectionManager(config)
        
        # Verify collection exists
        pair = collection_manager.get_pair_by_display_name(args.collection)
        if not pair:
            print(f"❌ Collection '{args.collection}' not found")
            print("\n📁 Available collections:")
            pairs = collection_manager.list_collection_pairs()
            for pair_info in pairs:
                display_name = pair_info.get('display_name', 'Unknown')
                doc_count = pair_info.get('document_count', 0)
                print(f"  • {display_name} ({doc_count} documents)")
            sys.exit(1)
        
        # Initialize agent
        agent = ResearchAgent(
            config=config, 
            collection_name=args.collection, 
            collection_manager=collection_manager
        )
        
        if args.command == "ask":
            if args.verbose:
                print(f"🤖 Asking question about collection: {args.collection}")
                print(f"🔧 Response length: {args.length}")
                print(f"🔧 Search type: {args.type}")
            
            # Parse filters
            metadata_filter = parse_filter_args(args.filter or [])
            if metadata_filter and args.verbose:
                print(f"🔧 Filters: {metadata_filter}")
            
            response, search_results = agent.ask(
                question=args.question,
                response_length=args.length,
                metadata_filter=metadata_filter,
                search_type=args.type
            )
            
            print(response)
            
            if args.verbose:
                print(f"\n📊 Context Results: {len(search_results)} documents used")
                print("🔍 Context Sources:")
                for i, result in enumerate(search_results[:5], 1):  # Show first 5 sources
                    print(f"   {i}. {result.filename} (Score: {result.score:.3f}, Type: {result.type})")
                if len(search_results) > 5:
                    print(f"   ... and {len(search_results) - 5} more results")

        elif args.command == "search":
            if args.verbose:
                print(f"🔍 Searching collection: {args.collection}")
                print(f"🔧 Search type: {args.type}")
                print(f"🔧 Top-k: {args.top_k}")
            
            # Parse filters
            metadata_filter = parse_filter_args(args.filter or [])
            if metadata_filter and args.verbose:
                print(f"🔧 Filters: {metadata_filter}")
            
            if args.type == "chunks":
                result = agent.search_chunks(
                    query=args.query,
                    top_k=args.top_k,
                    metadata_filter=metadata_filter
                )
            elif args.type == "artifacts":
                result = agent.search_artifacts(
                    query=args.query,
                    top_k=args.top_k,
                    metadata_filter=metadata_filter
                )
            else:  # both
                result = agent.search(
                    query=args.query,
                    top_k=args.top_k,
                    metadata_filter=metadata_filter,
                    search_type="both"
                )
            
            print(result)

        elif args.command == "model-info":
            info = agent.get_model_info()
            print(info)

        elif args.command == "collection-info":
            info = agent.get_collection_info()
            print(info)
            
            if args.verbose if hasattr(args, 'verbose') else True:
                # Show additional collection details
                pair_info = collection_manager.get_pair_by_display_name(args.collection)
                print(f"\n📊 Collection Details:")
                print(f"   Display Name: {pair_info.get('display_name', 'unknown')}")
                print(f"   ULID: {pair_info.get('ulid', 'unknown')}")
                print(f"   Document Count: {pair_info.get('document_count', 0)}")
                print(f"   Status: {pair_info.get('status', 'unknown')}")
                print(f"   Created: {pair_info.get('created_at', 'unknown')}")
                if pair_info.get('description'):
                    print(f"   Description: {pair_info.get('description')}")

    except KeyboardInterrupt:
        print("\n❌ Cancelled by user")
        sys.exit(1)
    except (VectorError, AIServiceError) as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        if hasattr(args, 'verbose') and args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
