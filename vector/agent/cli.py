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
        description="Vector Agent CLI - AI-powered search and question answering operations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  vector-agent search "building permits" --type chunks --top-k 10
  vector-agent delete --document-id abc123 --force
  vector-agent delete --name "My Document" --no-cleanup
  vector-agent model-info
  vector-agent collection-info

For low-level vector operations, use 'vector-core' instead.
        """
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands", required=True)

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

    # Delete document command
    delete_parser = subparsers.add_parser("delete", help="Delete a document and all its data")
    delete_group = delete_parser.add_mutually_exclusive_group(required=True)
    delete_group.add_argument("--document-id", help="Document ID to delete")
    delete_group.add_argument("--name", help="Document name to delete")
    delete_parser.add_argument("--no-cleanup", action="store_true", help="Don't delete saved files, only vector data")
    delete_parser.add_argument("--force", action="store_true", help="Skip confirmation prompt")
    delete_parser.add_argument("--chunks-collection", "-c", default="chunks", help="Chunks collection name")
    delete_parser.add_argument("--artifacts-collection", "-a", default="artifacts", help="Artifacts collection name")

    args = parser.parse_args()

    try:
        config = Config()
        
        # Initialize agent
        agent = ResearchAgent(
            config=config,
            chunks_collection=args.chunks_collection,
            artifacts_collection=args.artifacts_collection
        )
        
        if args.command == "search":
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

        elif args.command == "delete":
            # Import pipeline only when needed to avoid dependency issues
            from ..core.pipeline import VectorPipeline
            pipeline = VectorPipeline()
            
            cleanup_files = not args.no_cleanup
            
            if args.document_id:
                if not args.force:
                    response = input(f"Are you sure you want to delete document '{args.document_id}'? (y/N): ")
                    if response.lower() not in ['y', 'yes']:
                        print("❌ Operation cancelled")
                        sys.exit(0)
                
                success = pipeline.delete_document(args.document_id, cleanup_files=cleanup_files)
                if not success:
                    sys.exit(1)
                    
            elif args.name:
                if not args.force:
                    response = input(f"Are you sure you want to delete document '{args.name}'? (y/N): ")
                    if response.lower() not in ['y', 'yes']:
                        print("❌ Operation cancelled")
                        sys.exit(0)
                
                success = pipeline.delete_document_by_name(args.name, cleanup_files=cleanup_files)
                if not success:
                    sys.exit(1)

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
