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

    # Document management commands
    docs_parser = subparsers.add_parser("docs", help="List all documents")
    docs_parser.add_argument("--standalone", action="store_true", help="Show only standalone documents (not in collections)")
    docs_parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed information")

    add_to_collection_parser = subparsers.add_parser("add-to-collection", help="Add converted documents to a collection")
    add_to_collection_parser.add_argument("documents", nargs="+", help="Document filenames to add")
    add_to_collection_parser.add_argument("--collection", "-c", required=True, help="Collection display name")

    remove_from_collection_parser = subparsers.add_parser("remove-from-collection", help="Remove documents from a collection")
    remove_from_collection_parser.add_argument("documents", nargs="+", help="Document filenames to remove")
    remove_from_collection_parser.add_argument("--collection", "-c", required=True, help="Collection display name")

    # Convert command (file conversion only)
    convert_parser = subparsers.add_parser("convert", help="Convert documents to markdown/JSON and save to storage")
    convert_parser.add_argument("files", nargs="+", help="Files or directories to convert")
    convert_parser.add_argument("--output-dir", "-o", type=Path, help="Output directory for files (optional)")
    convert_parser.add_argument("--format", choices=["markdown", "json"], default="markdown", help="Output format")
    convert_parser.add_argument("--pipeline", choices=["pdf", "vlm"], default="pdf", help="Processing pipeline type")
    convert_parser.add_argument("--no-artifacts", action="store_true", help="Skip artifact processing")
    convert_parser.add_argument("--save-storage", action="store_true", default=True, help="Save to filesystem storage (default: True)")
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

        elif args.command == "docs":
            from .document_manager import DocumentManager
            
            collection_manager = CollectionManager(config)
            doc_manager = DocumentManager(config, collection_manager)
            
            if args.standalone:
                # Show standalone documents (converted but not in collections)
                standalone_docs = doc_manager.get_standalone_documents()
                
                if not standalone_docs:
                    print("📄 No standalone documents found.")
                    print("   (These are documents converted but not yet added to any collection)")
                    return
                
                print(f"📄 Standalone Documents ({len(standalone_docs)}):")
                for doc in standalone_docs:
                    print(f"  • {doc['filename']}")
                    if args.verbose:
                        print(f"    Source: {doc['source_category']}")
                        print(f"    Converted: {doc['processed_at'][:10] if doc['processed_at'] else 'unknown'}")
                        print(f"    Hash: {doc['file_hash'][:12]}...")
                        print(f"    Path: {doc['file_path']}")
                        print()
            else:
                # Show all documents with collection info
                all_docs = doc_manager.get_all_documents()
                
                if not all_docs:
                    print("📄 No documents found.")
                    return
                
                print(f"📄 All Documents ({len(all_docs)}):")
                for doc in all_docs:
                    collections_text = f"in {doc['collection_count']} collection{'s' if doc['collection_count'] != 1 else ''}"
                    print(f"  • {doc['filename']} ({collections_text})")
                    if args.verbose:
                        print(f"    Created: {doc['created_at'][:10] if doc['created_at'] else 'unknown'}")
                        print(f"    Source: {doc['source']}")
                        print(f"    Hash: {doc['file_hash'][:12] if doc['file_hash'] else 'unknown'}...")
                        print()

        elif args.command == "add-to-collection":
            from .document_manager import DocumentManager
            
            collection_manager = CollectionManager(config)
            doc_manager = DocumentManager(config, collection_manager)
            
            # Ensure all documents are tracked in metadata first
            for filename in args.documents:
                doc_manager.add_standalone_document_to_metadata(filename)
            
            result = doc_manager.add_documents_to_collection(args.documents, args.collection)
            print(result)

        elif args.command == "remove-from-collection":
            from .document_manager import DocumentManager
            
            collection_manager = CollectionManager(config)
            doc_manager = DocumentManager(config, collection_manager)
            
            # Convert filenames to display format expected by remove method
            document_displays = [filename for filename in args.documents]
            
            result = doc_manager.remove_documents_from_collection(document_displays, args.collection)
            print(result)

        elif args.command == "convert":
            # File conversion without indexing
            processor = DocumentProcessor(config)  # No collection needed
            
            # Create output directory if specified
            if args.output_dir:
                args.output_dir.mkdir(parents=True, exist_ok=True)
            
            pipeline_type = PipelineType.VLM if args.pipeline == "vlm" else PipelineType.PDF
            include_artifacts = not args.no_artifacts
            
            if args.verbose:
                print(f"🔧 Pipeline: {pipeline_type.value}")
                print(f"🔧 Format: {args.format}")
                if args.output_dir:
                    print(f"🔧 Output: {args.output_dir}")
                print(f"🔧 Artifacts: {'enabled' if include_artifacts else 'disabled'}")
                print(f"🔧 Save to storage: {'yes' if args.save_storage else 'no'}")
            
            # Convert files to specified format
            files_to_convert = []
            for file_path in args.files:
                path_obj = Path(file_path)
                if path_obj.is_file() and processor.is_supported_file(str(path_obj)):
                    files_to_convert.append(path_obj)
                elif path_obj.is_dir():
                    # Process directory recursively
                    for file_in_dir in path_obj.rglob("*"):
                        if file_in_dir.is_file() and processor.is_supported_file(str(file_in_dir)):
                            files_to_convert.append(file_in_dir)
                else:
                    print(f"⚠️  Skipping {file_path}: unsupported or not found")
            
            # Process each file
            for file_path in files_to_convert:
                try:
                    # Convert using normal pipeline but without vector storage
                    doc_results = processor.convert_documents([str(file_path)], pipeline_type, include_artifacts, False, None)
                    
                    if not doc_results:
                        print(f"⚠️  Failed to convert {file_path}")
                        continue
                    
                    doc_result = doc_results[0]
                    
                    # Handle artifacts if enabled and save-storage requested
                    if include_artifacts and args.save_storage:
                        import asyncio
                        asyncio.run(processor._handle_artifacts([doc_result], save_to_storage=True, save_to_vector=False))
                    
                    # Generate output files if output directory specified
                    if args.output_dir:
                        base_name = file_path.stem
                        if args.format == 'markdown':
                            output_file = args.output_dir / f"{base_name}.md"
                            # Save as markdown
                            from docling_core.types.doc import ImageRefMode
                            doc_result.document.save_as_markdown(
                                str(output_file), 
                                image_mode=ImageRefMode.REFERENCED
                            )
                            print(f"✅ Converted to markdown: {output_file}")
                        elif args.format == 'json':
                            output_file = args.output_dir / f"{base_name}.json"
                            # Save document data as JSON
                            import json
                            doc_data = {
                                'filename': file_path.name,
                                'source_category': doc_result.source_category,
                                'file_hash': doc_result.file_hash,
                                'content': doc_result.document.export_to_markdown()
                            }
                            with open(output_file, 'w', encoding='utf-8') as f:
                                json.dump(doc_data, f, indent=2, ensure_ascii=False)
                            print(f"✅ Converted to JSON: {output_file}")
                    
                    # Save to storage if requested (default: True)
                    if args.save_storage:
                        processor.save_document_results([doc_result])
                        print(f"💾 Saved {file_path.name} to storage")
                        
                except Exception as e:
                    print(f"❌ Failed to process {file_path.name}: {e}")
                    if args.verbose:
                        import traceback
                        traceback.print_exc()

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
