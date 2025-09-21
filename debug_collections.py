#!/usr/bin/env python3
"""
Debug script to check Qdrant collections and test collection existence.
"""

from vector.core.vector_store import VectorStore

def debug_collections():
    print("🔍 Debugging Qdrant Collections")
    print("=" * 40)
    
    store = VectorStore()
    
    # List all collections
    print("📋 Listing all collections:")
    try:
        collections = store.list_collections()
        if collections:
            for i, col in enumerate(collections, 1):
                print(f"  {i}. {col}")
        else:
            print("  No collections found")
        print(f"Total: {len(collections)} collections")
    except Exception as e:
        print(f"❌ Error listing collections: {e}")
        return
    
    # Check specific collection
    target_collection = "text_chunks"
    print(f"\n🎯 Checking '{target_collection}' collection:")
    
    try:
        with store.get_client() as client:
            exists = client.collection_exists(target_collection)
            print(f"  collection_exists('{target_collection}'): {exists}")
            
            if exists:
                # Get collection info
                info = client.get_collection(target_collection)
                print(f"  Collection info:")
                print(f"    Points count: {info.points_count}")
                print(f"    Vector size: {info.config.params.vectors.size}")
                print(f"    Distance: {info.config.params.vectors.distance}")
            else:
                print(f"  ❌ Collection '{target_collection}' not found!")
                print(f"  Available collections: {collections}")
    except Exception as e:
        print(f"❌ Error checking collection: {e}")
    
    # Test what happens during insert
    print(f"\n🧪 Testing insert behavior:")
    try:
        test_vector = [0.1] * 384  # Typical embedding size
        test_payload = {"test": "data"}
        
        print(f"  Attempting to insert test point into '{target_collection}'...")
        store.insert(target_collection, "test_point", test_vector, test_payload)
        
    except Exception as e:
        print(f"❌ Error during insert test: {e}")

if __name__ == "__main__":
    debug_collections()