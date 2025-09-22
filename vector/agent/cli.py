"""Agent CLI for search operations."""

import argparse
import sys

from ..config import Config
from ..exceptions import VectorError, AIServiceError
from .agent import ResearchAgent


def main():
    """Main entry point for vector-agent CLI."""
    parser = argparse.ArgumentParser(
        prog="vector-agent", 
        description="Vector research agent CLI for search"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands", required=True)

    # Ask command
    ask_parser = subparsers.add_parser("ask", help="Ask a question and get relevant context")
    ask_parser.add_argument("question", help="Question to ask")
    ask_parser.add_argument("--chunks-collection", "-c", default="chunks", help="Chunks collection name")
    ask_parser.add_argument("--artifacts-collection", "-a", default="artifacts", help="Artifacts collection name")
    ask_parser.add_argument("--type", choices=["chunks", "artifacts", "both"], default="both", 
                           help="Search type for context")
    ask_parser.add_argument("--length", choices=["short", "medium", "long"], default="medium", 
                           help="Response length")
    ask_parser.add_argument("--top-k", "-k", type=int, default=20, help="Number of results for context")
    ask_parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")

    # Search command
    search_parser = subparsers.add_parser("search", help="Search chunks or artifacts")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--chunks-collection", "-c", default="chunks", help="Chunks collection name")
    search_parser.add_argument("--artifacts-collection", "-a", default="artifacts", help="Artifacts collection name")
    search_parser.add_argument("--top-k", "-k", type=int, default=5, help="Number of results to return")
    search_parser.add_argument("--type", choices=["chunks", "artifacts", "both"], default="both", 
                              help="Search type")
    search_parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")

    # Collection info command  
    collection_parser = subparsers.add_parser("collection-info", help="Show collection information")
    collection_parser.add_argument("--chunks-collection", "-c", default="chunks", help="Chunks collection name")
    collection_parser.add_argument("--artifacts-collection", "-a", default="artifacts", help="Artifacts collection name")

    # Model info command
    model_parser = subparsers.add_parser("model-info", help="Show AI model configuration")
    model_parser.add_argument("--chunks-collection", "-c", default="chunks", help="Chunks collection name")
    model_parser.add_argument("--artifacts-collection", "-a", default="artifacts", help="Artifacts collection name")

    args = parser.parse_args()

    try:
        config = Config()
        
        # Initialize agent
        agent = ResearchAgent(
            config=config,
            chunks_collection=args.chunks_collection,
            artifacts_collection=args.artifacts_collection
        )
        
        if args.command == "ask":
            if args.verbose:
                print(f"🤖 Asking question about collections: {args.chunks_collection}, {args.artifacts_collection}")
                print(f"🔧 Search type: {args.type}")
                print(f"🔧 Top-k: {args.top_k}")
            
            response, search_results = agent.ask(
                question=args.question,
                response_length=args.length,
                search_type=args.type,
                top_k=args.top_k
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
                print(f"� Searching collections: {args.chunks_collection}, {args.artifacts_collection}")
                print(f"🔧 Search type: {args.type}")
                print(f"🔧 Top-k: {args.top_k}")
            
            if args.type == "chunks":
                results = agent.search_chunks(
                    query=args.query,
                    top_k=args.top_k
                )
            elif args.type == "artifacts":
                results = agent.search_artifacts(
                    query=args.query,
                    top_k=args.top_k
                )
            else:  # both
                results = agent.search(
                    query=args.query,
                    top_k=args.top_k,
                    search_type="both"
                )
            
            formatted_results = agent.format_results(results)
            print(formatted_results)

        elif args.command == "collection-info":
            info = agent.get_collection_info()
            print(info)

        elif args.command == "model-info":
            info = agent.get_model_info()
            print(info)

    except KeyboardInterrupt:
        print("\n❌ Cancelled by user")
        sys.exit(1)
    except (VectorError, AIServiceError) as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    except ValueError as e:
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
