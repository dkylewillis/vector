#!/usr/bin/env python3
"""
Test script for the delete_document method in VectorStore.
This script will:
1. Create a test collection
2. Add documents with doc_id payload
3. Test the delete_document method
4. Verify deletion worked
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

    def test_delete_document():
        """Test the delete_document functionality."""
        print("=== Testing delete_document Method ===\n")
        
        # Initialize vector store
        vector_store = VectorStore()
        collection_name = "text_chunks"  # Using the hardcoded collection name from delete_document
        vector_size = 384
        
        print(f"1. Creating collection '{collection_name}'...")
        vector_store.create_collection(collection_name, vector_size)
        
        print(f"2. Current collections: {vector_store.list_collections()}\n")
        
        # Create test documents with doc_id payload (note: using doc_id, not document_id)
        test_documents = [
            {
                "point_id": str(uuid.uuid4()),
                "doc_id": "test_doc_001",  # Using doc_id to match the filter in delete_document
                "content": "This is the first test document for deletion testing.",
                "chunk_number": 1
            },
            {
                "point_id": str(uuid.uuid4()),
                "doc_id": "test_doc_001",  # Same doc_id - multiple chunks
                "content": "This is the second chunk of the first test document.",
                "chunk_number": 2
            },
            {
                "point_id": str(uuid.uuid4()),
                "doc_id": "test_doc_002",  # Different doc_id
                "content": "This is a document that should NOT be deleted.",
                "chunk_number": 1
            },
            {
                "point_id": str(uuid.uuid4()),
                "doc_id": "test_doc_003",  # Another different doc_id
                "content": "This is another document that should remain.",
                "chunk_number": 1
            }
        ]
        
        print("3. Adding test documents...")
        for doc in test_documents:
            vector = generate_dummy_vector(vector_size)
            payload = {k: v for k, v in doc.items() if k != "point_id"}
            
            vector_store.insert(
                collection_name=collection_name,
                point_id=doc["point_id"],
                vectors=vector,
                payload=payload
            )
        
        print(f"\n4. Added {len(test_documents)} documents to collection.\n")
        
        # Search to verify all documents are there
        print("5. Verifying all documents are present...")
        query_vector = generate_dummy_vector(vector_size)
        all_results = vector_store.search(
            query_vector=query_vector,
            collection=collection_name,
            top_k=10
        )
        
        print(f"Found {len(all_results)} documents before deletion:")
        for i, result in enumerate(all_results, 1):
            doc_id = result.payload.get("doc_id", "N/A")
            content = result.payload.get("content", "N/A")[:50] + "..."
            print(f"  {i}. Doc ID: {doc_id}, Content: {content}")
        
        print("\n6. Testing delete_document method...")
        target_doc_id = "test_doc_001"
        print(f"Deleting document with doc_id: {target_doc_id}")
        
        # Test the delete_document method
        vector_store.delete_document(collection_name, target_doc_id)
        
        print("\n7. Verifying deletion...")
        after_results = vector_store.search(
            query_vector=query_vector,
            collection=collection_name,
            top_k=10
        )
        
        print(f"Found {len(after_results)} documents after deletion:")
        remaining_doc_ids = set()
        for i, result in enumerate(after_results, 1):
            doc_id = result.payload.get("doc_id", "N/A")
            content = result.payload.get("content", "N/A")[:50] + "..."
            remaining_doc_ids.add(doc_id)
            print(f"  {i}. Doc ID: {doc_id}, Content: {content}")
        
        # Verify the deletion worked correctly
        print(f"\n8. Deletion verification:")
        if target_doc_id not in remaining_doc_ids:
            print(f"✅ SUCCESS: Document '{target_doc_id}' was successfully deleted")
            print(f"✅ All chunks with doc_id '{target_doc_id}' were removed")
        else:
            print(f"❌ FAILURE: Document '{target_doc_id}' is still present")
        
        expected_remaining = {"test_doc_002", "test_doc_003"}
        actual_remaining = remaining_doc_ids
        
        if expected_remaining == actual_remaining:
            print(f"✅ SUCCESS: Only expected documents remain: {actual_remaining}")
        else:
            print(f"❌ FAILURE: Unexpected documents remain")
            print(f"   Expected: {expected_remaining}")
            print(f"   Actual: {actual_remaining}")
        
        # Test edge case: try to delete non-existent document
        print(f"\n9. Testing edge case - deleting non-existent document...")
        vector_store.delete_document(collection_name, "non_existent_doc")
        
        # Cleanup
        print(f"\n10. Cleaning up...")
        vector_store.delete_collection(collection_name)
        print(f"Collection '{collection_name}' deleted.")
        
        print(f"\nFinal collections: {vector_store.list_collections()}")
        print("\n=== delete_document Test Complete ===")

    if __name__ == "__main__":
        test_delete_document()
        
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running from the correct directory.")
except Exception as e:
    print(f"Unexpected error: {e}")
    import traceback
    traceback.print_exc()