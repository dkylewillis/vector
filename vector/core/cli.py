"""Core CLI for document processing operations."""

import argparse
import sys
from pathlib import Path
from typing import List

from ..config import Config
from ..exceptions import ProcessingError, VectorError
from .processor import DocumentProcessor, PipelineType
from .collection_manager import CollectionManager


def main():
    """Main entry point for vector-core CLI."""
    parser = argparse.ArgumentParser(
        prog="vector-core", 
        description="Vector core document processing CLI"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands", required=True)

    # Process command
    process_parser = subparsers.add_parser("process", help="Convert, chunk, embed, and index documents")
    process_parser.add_argument("files", nargs="+", help="Files or directories to process")
    process_parser.add_argument("--collection", "-c", help="Collection display name")
    process_parser.add_argument("--source", "-s", help="Source category (ordinances, manuals, checklists, other)")
    process_parser.add_argument("--pipeline", choices=["pdf", "vlm"], default="pdf", help="Processing pipeline type")
    process_parser.add_argument("--no-artifacts", action="store_true", help="Skip artifact processing for faster processing")
    process_parser.add_argument("--force", "-f", action="store_true", help="Force reprocessing and replace existing data")
    process_parser.add_argument("--from-storage", action="store_true", help="Load converted docs from storage by filename")
    process_parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")

    # Collections management
    collections_parser = subparsers.add_parser("collections", help="List collection pairs")
    collections_parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed information")

    create_collection_parser = subparsers.add_parser("create-collection", help="Create new collection pair")
    create_collection_parser.add_argument("name", help="Display name for the collection pair")
    create_collection_parser.add_argument("--description", "-d", default="", help="Description for the collection pair")

    rename_collection_parser = subparsers.add_parser("rename-collection", help="Rename collection pair")
    rename_collection_parser.add_argument("old_name", help="Current display name")
    rename_collection_parser.add_argument("new_name", help="New display name")

    delete_collection_parser = subparsers.add_parser("delete-collection", help="Delete collection pair")
    delete_collection_parser.add_argument("name", help="Display name of collection to delete")
    delete_collection_parser.add_argument("--force", action="store_true", help="Skip confirmation prompt")

    # Convert command (file conversion only)
    convert_parser = subparsers.add_parser("convert", help="Convert documents to markdown/JSON without indexing")
    convert_parser.add_argument("files", nargs="+", help="Files or directories to convert")
    convert_parser.add_argument("--output-dir", "-o", type=Path, required=True, help="Output directory")
    convert_parser.add_argument("--format", choices=["markdown", "json"], default="markdown", help="Output format")
    convert_parser.add_argument("--pipeline", choices=["pdf", "vlm"], default="pdf", help="Processing pipeline type")
    convert_parser.add_argument("--no-artifacts", action="store_true", help="Skip artifact processing")
    convert_parser.add_argument("--save-storage", action="store_true", help="Also save to filesystem storage")
    convert_parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")

    args = parser.parse_args()

    try:
        config = Config()
        
        if args.command == "process":
            # Initialize collection manager if collection specified
            collection_manager = None
            if args.collection:
                collection_manager = CollectionManager(config)
                # Check if collection exists, create if not
                if not collection_manager.get_pair_by_display_name(args.collection):
                    print(f"📁 Creating new collection pair: {args.collection}")
                    collection_manager.create_collection_pair(args.collection, "")
            
            # Initialize processor
            processor = DocumentProcessor(
                config, 
                collection_name=args.collection, 
                collection_manager=collection_manager
            )
            
            # Set pipeline type and options
            include_artifacts = not args.no_artifacts
            pipeline_type = PipelineType.VLM if args.pipeline == "vlm" else PipelineType.PDF
            
            if args.verbose:
                print(f"🔧 Pipeline: {pipeline_type.value}")
                print(f"🔧 Artifacts: {'enabled' if include_artifacts else 'disabled'}")
                print(f"🔧 Collection: {args.collection or 'none'}")
            
            # Execute processing pipeline
            result = processor.execute_processing_pipeline(
                files=args.files,
                pipeline_type=pipeline_type,
                include_artifacts=include_artifacts,
                force=args.force,
                source=args.source,
                from_storage=args.from_storage
            )
            print(result)

        elif args.command == "collections":
            collection_manager = CollectionManager(config)
            pairs = collection_manager.list_collection_pairs()
            
            if not pairs:
                print("📁 No collection pairs found.")
                return
            
            print("📁 Collection Pairs:")
            for pair_info in pairs:
                display_name = pair_info.get('display_name', 'Unknown')
                doc_count = pair_info.get('document_count', 0)
                status = pair_info.get('status', 'unknown')
                created = pair_info.get('created_at', 'unknown')[:10]  # Date only
                
                print(f"  • {display_name} ({doc_count} documents, {status}, created: {created})")
                
                if args.verbose:
                    print(f"    Chunks: {pair_info.get('chunks_collection', 'unknown')}")
                    print(f"    Artifacts: {pair_info.get('artifacts_collection', 'unknown')}")
                    print(f"    Description: {pair_info.get('description', 'none')}")
                    print()

        elif args.command == "create-collection":
            collection_manager = CollectionManager(config)
            try:
                pair_info = collection_manager.create_collection_pair(args.name, args.description)
                print(f"✅ Created collection pair: {args.name}")
                print(f"   Chunks: {pair_info['chunks_collection']}")
                print(f"   Artifacts: {pair_info['artifacts_collection']}")
            except ValueError as e:
                print(f"❌ Error: {e}")
                sys.exit(1)

        elif args.command == "rename-collection":
            collection_manager = CollectionManager(config)
            success = collection_manager.rename_collection_pair(args.old_name, args.new_name)
            if success:
                print(f"✅ Renamed collection: {args.old_name} → {args.new_name}")
            else:
                print(f"❌ Collection '{args.old_name}' not found")
                sys.exit(1)

        elif args.command == "delete-collection":
            collection_manager = CollectionManager(config)
            
            if not args.force:
                response = input(f"⚠️  Delete collection '{args.name}' and all its documents? (y/N): ")
                if response.lower() != 'y':
                    print("❌ Cancelled")
                    return
            
            success = collection_manager.delete_collection_pair(args.name)
            if success:
                print(f"🗑️  Deleted collection pair: {args.name}")
            else:
                print(f"❌ Collection '{args.name}' not found")
                sys.exit(1)

        elif args.command == "convert":
            # File conversion without indexing
            processor = DocumentProcessor(config)  # No collection needed
            
            # Ensure output directory exists
            args.output_dir.mkdir(parents=True, exist_ok=True)
            
            pipeline_type = PipelineType.VLM if args.pipeline == "vlm" else PipelineType.PDF
            include_artifacts = not args.no_artifacts
            
            if args.verbose:
                print(f"🔧 Pipeline: {pipeline_type.value}")
                print(f"🔧 Format: {args.format}")
                print(f"🔧 Output: {args.output_dir}")
                print(f"🔧 Artifacts: {'enabled' if include_artifacts else 'disabled'}")
            
            # Process each file
            for file_path in args.files:
                path_obj = Path(file_path)
                if path_obj.is_file() and processor.is_supported_file(str(path_obj)):
                    result = processor._convert_single_document_to_file(
                        file_path=path_obj,
                        source=None,
                        include_artifacts=include_artifacts,
                        use_vlm=(pipeline_type == PipelineType.VLM),
                        output_dir=args.output_dir,
                        output_format=args.format,
                        save_to_storage=args.save_storage,
                        verbose=args.verbose
                    )
                    print(result)
                elif path_obj.is_dir():
                    # Process directory recursively
                    for file_in_dir in path_obj.rglob("*"):
                        if file_in_dir.is_file() and processor.is_supported_file(str(file_in_dir)):
                            result = processor._convert_single_document_to_file(
                                file_path=file_in_dir,
                                source=None,
                                include_artifacts=include_artifacts,
                                use_vlm=(pipeline_type == PipelineType.VLM),
                                output_dir=args.output_dir,
                                output_format=args.format,
                                save_to_storage=args.save_storage,
                                verbose=args.verbose
                            )
                            print(result)
                else:
                    print(f"⚠️  Skipping {file_path}: unsupported or not found")

    except KeyboardInterrupt:
        print("\n❌ Cancelled by user")
        sys.exit(1)
    except (ProcessingError, VectorError) as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        if args.verbose if hasattr(args, 'verbose') else False:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
