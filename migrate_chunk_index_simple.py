"""Simple migration script to add chunk_index to existing chunks in vector store."""

import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from vector.stores.factory import create_store
from vector.search.dsl import SearchRequest


def extract_chunk_index_from_id(chunk_id: str) -> int:
    """Extract index from chunk_id like 'chunk_0' -> 0"""
    if chunk_id and chunk_id.startswith('chunk_'):
        try:
            return int(chunk_id.split('_')[-1])
        except (ValueError, IndexError):
            pass
    return None


def migrate_collection(collection_name="chunks"):
    print(f"Migrating collection: {collection_name}")
    
    store = create_store("qdrant", db_path="./qdrant_db")
    
    # Check collection exists
    collections = store.list_collections()
    if collection_name not in collections:
        print(f"Error: Collection '{collection_name}' not found")
        return
    
    print(f"Found collection")
    
    # Fetch all chunks
    print("Fetching all chunks...")
    request = SearchRequest(
        collection=collection_name,
        vector=None,
        top_k=10000,
        include_payload=True
    )
    
    response = store.search(request)
    total = len(response.hits)
    print(f"Retrieved {total} chunks")
    
    if total == 0:
        print("No chunks found")
        return
    
    # Process each chunk
    updated = 0
    skipped = 0
    errors = 0
    
    print("Processing chunks...")
    
    # Use single client connection for all operations
    with store._client() as client:
        for i, hit in enumerate(response.hits):
            if i % 100 == 0:
                print(f"  Progress: {i}/{total}")
            
            point_id = str(hit.id)
            payload = hit.payload or {}
            
            # Skip if already has chunk_index
            if 'chunk_index' in payload and payload['chunk_index'] is not None:
                skipped += 1
                continue
            
            # Extract chunk data
            chunk_json = payload.get('chunk')
            if not chunk_json:
                errors += 1
                continue
            
            try:
                # Parse chunk
                if isinstance(chunk_json, str):
                    chunk_data = json.loads(chunk_json)
                else:
                    chunk_data = chunk_json
                
                # Get chunk_index
                chunk_index = chunk_data.get('chunk_index')
                if chunk_index is None:
                    # Try to extract from chunk_id
                    chunk_id = chunk_data.get('chunk_id', '')
                    chunk_index = extract_chunk_index_from_id(chunk_id)
                
                if chunk_index is None:
                    errors += 1
                    continue
                
                # Update payload
                updated_payload = {**payload, 'chunk_index': chunk_index}
                
                # Get vector and upsert
                points = client.retrieve(
                    collection_name=collection_name,
                    ids=[point_id],
                    with_vectors=True
                )
                
                if points and len(points) > 0:
                    vector = points[0].vector
                    
                    # Upsert directly using client
                    from qdrant_client.models import PointStruct
                    client.upsert(
                        collection_name=collection_name,
                        points=[
                            PointStruct(
                                id=point_id,
                                vector=vector,
                                payload=updated_payload
                            )
                        ]
                    )
                    updated += 1
                else:
                    errors += 1
                        
            except Exception as e:
                print(f"  Error processing {point_id[:8]}: {e}")
                errors += 1
    
    print(f"\nMigration complete!")
    print(f"  Total: {total}")
    print(f"  Already had chunk_index: {skipped}")
    print(f"  Updated: {updated}")
    print(f"  Errors: {errors}")


if __name__ == "__main__":
    migrate_collection("chunks")
