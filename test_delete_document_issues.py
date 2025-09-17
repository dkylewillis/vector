#!/usr/bin/env python3
"""
Additional tests for delete_document method to identify potential issues.
"""

import sys
import os
import numpy as np
import uuid

# Add the vector core directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'vector', 'core'))

try:
    from vector_store import VectorStore
    
    def generate_dummy_vector(size: int = 384) -> list[float]:
        """Generate a random dummy vector of specified size."""
        return np.random.rand(size).tolist()

    def test_delete_document_issues():
        """Test for potential issues in delete_document method."""
        print("=== Testing delete_document Issues ===\n")
        
        vector_store = VectorStore()
        
        # Issue 1: Method uses hardcoded collection name
        print("1. Testing hardcoded collection name issue...")
        collection_name = "my_custom_collection"
        vector_size = 384
        
        print(f"Creating collection: {collection_name}")
        vector_store.create_collection(collection_name, vector_size)
        
        # Add a document to the custom collection
        test_doc = {
            "point_id": str(uuid.uuid4()),
            "doc_id": "test_doc_in_custom_collection",
            "content": "This document is in a custom collection"
        }
        
        vector = generate_dummy_vector(vector_size)
        payload = {k: v for k, v in test_doc.items() if k != "point_id"}
        
        vector_store.insert(
            collection_name=collection_name,
            point_id=test_doc["point_id"],
            vectors=vector,
            payload=payload
        )
        
        print(f"Added document to {collection_name}")
        
        # Try to delete from custom collection - this will fail because method hardcodes "text_chunks"
        print(f"Attempting to delete from {collection_name} (this will show the issue)...")
        try:
            vector_store.delete_document(collection_name, "test_doc_in_custom_collection")
            print("❌ The method didn't use the provided collection name!")
        except Exception as e:
            print(f"Error occurred: {e}")
        
        # Verify the document is still there in our custom collection
        query_vector = generate_dummy_vector(vector_size)
        results = vector_store.search(query_vector, collection_name, top_k=5)
        print(f"Documents still in {collection_name}: {len(results)}")
        
        # Clean up
        vector_store.delete_collection(collection_name)
        
        print("\n" + "="*60)
        print("IDENTIFIED ISSUES:")
        print("1. The delete_document method ignores the 'collection' parameter")
        print("   and hardcodes 'text_chunks' in the client.delete() call")
        print("2. This means it will only work with a collection named 'text_chunks'")
        print("3. The method should use the collection parameter instead")
        print("="*60)

    if __name__ == "__main__":
        test_delete_document_issues()
        
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running from the correct directory.")
except Exception as e:
    print(f"Unexpected error: {e}")
    import traceback
    traceback.print_exc()