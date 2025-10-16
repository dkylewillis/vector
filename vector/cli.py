"""CLI commands for vector store CRUD operations.

This is the new flat-structure CLI that replaces vector.core.cli.
It uses the refactored stores, embedders, and search modules.
"""

import argparse
import json
import sys
from typing import Optional
from pathlib import Path

from vector.stores.factory import create_store
from vector.stores.base import DistanceType


class VectorStoreCLI:
    """CLI handler for vector store operations using the flat structure."""
    
    def __init__(self, db_path: str = "./qdrant_db", url: Optional[str] = None, api_key: Optional[str] = None):
        """Initialize CLI with a vector store instance.
        
        Args:
            db_path: Path to local Qdrant database
            url: URL for remote Qdrant instance (optional)
            api_key: API key for remote authentication (optional)
        """
        self.store = create_store(
            provider="qdrant",
            db_path=db_path,
            url=url,
            api_key=api_key
        )
        self.db_path = db_path
        self.url = url
        self.api_key = api_key
    
    def create_collection(self, args):
        """Create a new vector collection."""
        distance_map = {
            'cosine': DistanceType.COSINE,
            'euclid': DistanceType.EUCLIDEAN,
            'dot': DistanceType.DOT
        }
        
        self.store.create_collection(
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
        
        self.store.delete_collection(args.name)
        print(f"[DELETED] Collection '{args.name}' deleted")
    
    def list_collections(self, args):
        """List all vector collections."""
        collections = self.store.list_collections()
        
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
            
            self.store.upsert(args.collection, args.point_id, vector_data, payload_data)
            print(f"[SUCCESS] Point '{args.point_id}' inserted into collection '{args.collection}'")
            
        except json.JSONDecodeError as e:
            print(f"[ERROR] JSON parsing error: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"[ERROR] Error inserting point: {e}", file=sys.stderr)
            sys.exit(1)
    
    def search(self, args):
        """Search for similar vectors in a collection using the new DSL."""
        try:
            from vector.search.dsl import SearchRequest, FieldIn
            
            vector_data = json.loads(args.query_vector)
            if not isinstance(vector_data, list):
                raise ValueError("Query vector must be a list of numbers")
            
            # Build search request using the DSL
            filter_expr = None
            if args.document_ids:
                doc_ids = json.loads(args.document_ids)
                filter_expr = FieldIn(key="document_id", values=doc_ids)
            
            request = SearchRequest(
                collection=args.collection,
                vector=vector_data,
                top_k=args.top_k,
                filter=filter_expr,
                include_payload=True
            )
            
            response = self.store.search(request)
            
            if not response.hits:
                print("No results found")
                return
            
            print(f"Search results for collection '{args.collection}':")
            for i, hit in enumerate(response.hits, 1):
                print(f"  {i}. ID: {hit.id}, Score: {hit.score:.4f}")
                if hit.payload:
                    print(f"     Payload: {json.dumps(hit.payload, indent=6)}")
            
        except json.JSONDecodeError as e:
            print(f"[ERROR] JSON parsing error: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"[ERROR] Error searching: {e}", file=sys.stderr)
            sys.exit(1)
    
    def delete_document(self, args):
        """Delete a document from a collection."""
        from vector.search.dsl import SearchRequest, FieldEquals
        
        if not args.force:
            response = input(f"Are you sure you want to delete document '{args.document_id}' from collection '{args.collection}'? (y/N): ")
            if response.lower() not in ['y', 'yes']:
                print("Operation cancelled")
                return
        
        # Use DSL to find and delete document points
        filter_expr = FieldEquals(key="document_id", value=args.document_id)
        request = SearchRequest(
            collection=args.collection,
            vector=None,  # Filter-only query
            top_k=10000,  # Get all matching points
            filter=filter_expr,
            include_payload=False
        )
        
        response = self.store.search(request)
        
        # Note: The base Protocol doesn't have a delete method
        # This would need to be implemented in the Qdrant adapter
        # For now, print a message
        print(f"[INFO] Found {len(response.hits)} points for document '{args.document_id}'")
        print(f"[WARNING] Deletion by document_id requires extending the Protocol interface")
        print(f"[WORKAROUND] You can manually delete the collection and recreate it")
    
    def list_documents(self, args):
        """List all documents in a collection."""
        try:
            from vector.search.dsl import SearchRequest
            
            # Get all points (filter-only query)
            request = SearchRequest(
                collection=args.collection,
                vector=None,
                top_k=10000,
                filter=None,
                include_payload=True
            )
            
            response = self.store.search(request)
            
            # Extract unique document IDs
            document_ids = set()
            for hit in response.hits:
                if hit.payload and "document_id" in hit.payload:
                    document_ids.add(hit.payload["document_id"])
            
            if not document_ids:
                print(f"No documents found in collection '{args.collection}'")
                return
            
            print(f"Documents in collection '{args.collection}':")
            for doc_id in sorted(document_ids):
                print(f"  * {doc_id}")
            
            print(f"\nTotal: {len(document_ids)} documents")
            
        except Exception as e:
            print(f"[ERROR] Error listing documents: {e}", file=sys.stderr)
            sys.exit(1)
    
    def collection_info(self, args):
        """Get information about a collection."""
        # Note: This requires direct Qdrant client access
        # The Protocol interface doesn't expose collection info
        try:
            from qdrant_client import QdrantClient
            
            # Create a direct client (this is temporary until we extend the Protocol)
            if hasattr(self.store, '_client'):
                # QdrantVectorStore has a _client context manager
                with self.store._client() as client:
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
            else:
                print("[WARNING] Collection info requires direct Qdrant client access")
                
        except Exception as e:
            print(f"[ERROR] Error getting collection info: {e}", file=sys.stderr)
            sys.exit(1)
    
    def ingest_file(self, args):
        """Ingest a document file into the vector store."""
        from vector.pipeline import IngestionPipeline, IngestionConfig
        from vector.embedders.sentence_transformer import SentenceTransformerEmbedder
        
        print(f"[INFO] Initializing ingestion pipeline...")
        
        # Create embedder and store
        embedder = SentenceTransformerEmbedder()
        store = create_store(
            provider="qdrant",
            db_path=self.db_path,
            url=self.url,
            api_key=self.api_key
        )
        
        # Create pipeline config
        config = IngestionConfig(
            batch_size=args.batch_size,
            collection_name=args.collection,
            generate_artifacts=not args.no_artifacts
        )
        
        # Create pipeline
        pipeline = IngestionPipeline(embedder, store, config)
        
        # Ensure collection exists
        try:
            existing_collections = store.list_collections()
            if args.collection not in existing_collections:
                print(f"[INFO] Creating collection '{args.collection}'...")
                vector_size = embedder.get_embedding_dimension()
                store.create_collection(
                    collection_name=args.collection,
                    vector_size=vector_size,
                    distance=DistanceType.COSINE
                )
        except Exception as e:
            print(f"[WARNING] Could not check/create collection: {e}")
        
        # Ingest file
        print(f"[INFO] Ingesting file: {args.file_path}")
        result = pipeline.ingest_file(
            file_path=Path(args.file_path),
            document_id=args.document_id
        )
        
        # Display results
        if result.success:
            print(f"[SUCCESS] Ingestion completed successfully!")
            print(f"  Document ID: {result.document_id}")
            print(f"  Chunks created: {result.chunks_created}")
            print(f"  Chunks indexed: {result.chunks_indexed}")
            print(f"  Artifacts generated: {result.artifacts_generated}")
            print(f"  Duration: {result.duration_seconds:.2f}s")
        else:
            print(f"[ERROR] Ingestion failed!")
            for error in result.errors:
                print(f"  Error: {error}", file=sys.stderr)
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
    
    # Ingest file command
    ingest_file_parser = subparsers.add_parser('ingest-file',
                                               help='Ingest a document file into the vector store')
    ingest_file_parser.add_argument('file_path', help='Path to the document file')
    ingest_file_parser.add_argument('--document-id', help='Document ID (defaults to filename)')
    ingest_file_parser.add_argument('--collection', default='chunks',
                                    help='Target collection name (default: chunks)')
    ingest_file_parser.add_argument('--batch-size', type=int, default=32,
                                    help='Embedding batch size (default: 32)')
    ingest_file_parser.add_argument('--no-artifacts', action='store_true',
                                    help='Disable artifact generation')
    
    return parser


def main():
    """Main CLI entry point for the flat structure."""
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
        'ingest-file': cli.ingest_file,
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
