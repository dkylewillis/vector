"""CLI commands for vector store CRUD operations."""

import argparse
import json
import sys
from typing import List, Optional
from pathlib import Path
from .vector_store import VectorStore
from .models import DocumentRecord


class VectorStoreCLI:
    """CLI handler for vector store operations."""
    
    def __init__(self, db_path: str = "./qdrant_db", url: Optional[str] = None, api_key: Optional[str] = None):
        self.vector_store = VectorStore(
            db_path=db_path,
            url=url,
            api_key=api_key
        )
    
    def create_collection(self, args):
        """Create a new vector collection."""
        from qdrant_client.models import Distance
        
        distance_map = {
            'cosine': Distance.COSINE,
            'euclid': Distance.EUCLID,
            'dot': Distance.DOT
        }
        
        self.vector_store.create_collection(
            args.name, 
            args.vector_size, 
            distance_map[args.distance]
        )
        print(f"[SUCCESS] Collection '{args.name}' created successfully")
    
    def delete_collection(self, args):
        """Delete a vector collection."""
        if not args.force:
            response = input(f"Are you sure you want to delete collection '{args.name}'? (y/N): ")
            if response.lower() not in ['y', 'yes']:
                print("Operation cancelled")
                return
        
        self.vector_store.delete_collection(args.name)
        print(f"[DELETED] Collection '{args.name}' deleted")
    
    def list_collections(self, args):
        """List all vector collections."""
        collections = self.vector_store.list_collections()
        
        if not collections:
            print("No collections found")
            return
        
        print("Collections:")
        for collection in collections:
            print(f"  * {collection}")
    
    def insert_point(self, args):
        """Insert a point into a collection."""
        try:
            vector_data = json.loads(args.vector)
            if not isinstance(vector_data, list):
                raise ValueError("Vector must be a list of numbers")
            
            payload_data = json.loads(args.payload) if args.payload else {}
            
            self.vector_store.insert(args.collection, args.point_id, vector_data, payload_data)
            print(f"[SUCCESS] Point '{args.point_id}' inserted into collection '{args.collection}'")
            
        except json.JSONDecodeError as e:
            print(f"[ERROR] JSON parsing error: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"[ERROR] Error inserting point: {e}", file=sys.stderr)
            sys.exit(1)
    
    def search(self, args):
        """Search for similar vectors in a collection."""
        try:
            vector_data = json.loads(args.query_vector)
            if not isinstance(vector_data, list):
                raise ValueError("Query vector must be a list of numbers")
            
            if args.document_ids:
                doc_ids = json.loads(args.document_ids)
                results = self.vector_store.search_documents(
                    vector_data, args.collection, args.top_k, doc_ids
                )
            else:
                results = self.vector_store.search(
                    vector_data, args.collection, args.top_k
                )
            
            if not results:
                print("No results found")
                return
            
            print(f"Search results for collection '{args.collection}':")
            for i, result in enumerate(results, 1):
                print(f"  {i}. ID: {result.id}, Score: {result.score:.4f}")
                if result.payload:
                    print(f"     Payload: {json.dumps(result.payload, indent=6)}")
            
        except json.JSONDecodeError as e:
            print(f"[ERROR] JSON parsing error: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"[ERROR] Error searching: {e}", file=sys.stderr)
            sys.exit(1)
    
    def delete_document(self, args):
        """Delete a document from a collection."""
        if not args.force:
            response = input(f"Are you sure you want to delete document '{args.document_id}' from collection '{args.collection}'? (y/N): ")
            if response.lower() not in ['y', 'yes']:
                print("Operation cancelled")
                return
        
        self.vector_store.delete_document(args.collection, args.document_id)
        print(f"[DELETED] Document '{args.document_id}' deleted from collection '{args.collection}'")
    
    def list_documents(self, args):
        """List all documents in a collection."""
        try:
            documents = self.vector_store.list_documents(args.collection)
            
            if not documents:
                print(f"No documents found in collection '{args.collection}'")
                return
            
            print(f"Documents in collection '{args.collection}':")
            for doc_id in documents:
                print(f"  * {doc_id}")
            
            print(f"\nTotal: {len(documents)} documents")
            
        except Exception as e:
            print(f"[ERROR] Error listing documents: {e}", file=sys.stderr)
            sys.exit(1)
    
    def collection_info(self, args):
        """Get information about a collection."""
        try:
            with self.vector_store.get_client() as client:
                if not client.collection_exists(args.collection):
                    print(f"[ERROR] Collection '{args.collection}' does not exist")
                    return
                
                info = client.get_collection(args.collection)
                print(f"Collection '{args.collection}' information:")
                print(f"  * Status: {info.status}")
                print(f"  * Vector size: {info.config.params.vectors.size}")
                print(f"  * Distance: {info.config.params.vectors.distance}")
                if hasattr(info, 'points_count'):
                    print(f"  * Points count: {info.points_count}")
                
        except Exception as e:
            print(f"[ERROR] Error getting collection info: {e}", file=sys.stderr)
            sys.exit(1)


def setup_parser():
    """Set up the argument parser with all commands and subcommands."""
    parser = argparse.ArgumentParser(
        prog="vector-core",
        description="Vector Core CLI - Manage vector stores and low-level operations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  vector-core create-collection chunks --vector-size 384
  vector-core list-collections
  vector-core search chunks "[0.1, 0.2, ...]" --top-k 5
  vector-core delete-collection chunks --force

For AI-powered search and questions, use 'vector-agent' instead.
        """
    )
    
    # Global options
    parser.add_argument('--db-path', default="./qdrant_db", 
                       help='Path to Qdrant database directory')
    parser.add_argument('--url', help='URL for remote Qdrant instance')
    parser.add_argument('--api-key', help='API key for remote Qdrant instance')
    
    # Create subparsers for commands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Create collection command
    create_parser = subparsers.add_parser('create-collection', 
                                         help='Create a new vector collection')
    create_parser.add_argument('name', help='Collection name')
    create_parser.add_argument('--vector-size', type=int, default=384,
                              help='Vector dimension size (default: 384)')
    create_parser.add_argument('--distance', choices=['cosine', 'euclid', 'dot'], 
                              default='cosine', help='Distance metric for vectors')
    
    # Delete collection command
    delete_parser = subparsers.add_parser('delete-collection',
                                         help='Delete a vector collection')
    delete_parser.add_argument('name', help='Collection name')
    delete_parser.add_argument('--force', action='store_true',
                              help='Skip confirmation prompt')
    
    # List collections command
    list_parser = subparsers.add_parser('list-collections',
                                       help='List all vector collections')
    
    # Insert point command
    insert_parser = subparsers.add_parser('insert-point',
                                         help='Insert a point into a collection')
    insert_parser.add_argument('collection', help='Collection name')
    insert_parser.add_argument('point_id', help='Point ID')
    insert_parser.add_argument('vector', help='Vector as JSON array of floats')
    insert_parser.add_argument('--payload', help='JSON payload for the point')
    
    # Search command
    search_parser = subparsers.add_parser('search',
                                         help='Search for similar vectors')
    search_parser.add_argument('collection', help='Collection name')
    search_parser.add_argument('query_vector', 
                              help='Query vector as JSON array of floats')
    search_parser.add_argument('--top-k', type=int, default=5,
                              help='Number of results to return')
    search_parser.add_argument('--document-ids',
                              help='JSON array of document IDs to filter by')
    
    # Delete document command
    delete_doc_parser = subparsers.add_parser('delete-document',
                                             help='Delete a document from collection')
    delete_doc_parser.add_argument('collection', help='Collection name')
    delete_doc_parser.add_argument('document_id', help='Document ID')
    delete_doc_parser.add_argument('--force', action='store_true',
                                  help='Skip confirmation prompt')
    
    # List documents command
    list_docs_parser = subparsers.add_parser('list-documents',
                                            help='List documents in collection')
    list_docs_parser.add_argument('collection', help='Collection name')
    
    # Collection info command
    info_parser = subparsers.add_parser('collection-info',
                                       help='Get collection information')
    info_parser.add_argument('collection', help='Collection name')
    
    return parser


def main():
    """Main CLI entry point."""
    parser = setup_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize CLI handler
    cli = VectorStoreCLI(
        db_path=args.db_path,
        url=args.url,
        api_key=args.api_key
    )
    
    # Route to appropriate command handler
    command_map = {
        'create-collection': cli.create_collection,
        'delete-collection': cli.delete_collection,
        'list-collections': cli.list_collections,
        'insert-point': cli.insert_point,
        'search': cli.search,
        'delete-document': cli.delete_document,
        'list-documents': cli.list_documents,
        'collection-info': cli.collection_info,
    }
    
    handler = command_map.get(args.command)
    if handler:
        handler(args)
    else:
        print(f"Unknown command: {args.command}", file=sys.stderr)
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()