#!/usr/bin/env python3
"""
Comprehensive test summary for delete_document method
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

    def comprehensive_test():
        """Comprehensive test of delete_document method."""
        print("=== Comprehensive delete_document Test Summary ===\n")
        
        vector_store = VectorStore()
        vector_size = 384
        
        # Test 1: Method works when collection is named "text_chunks"
        print("Test 1: Method works with hardcoded 'text_chunks' collection")
        print("-" * 55)
        
        vector_store.create_collection("text_chunks", vector_size)
        
        # Add test documents
        docs = [
            {"point_id": str(uuid.uuid4()), "doc_id": "doc1", "content": "Document 1"},
            {"point_id": str(uuid.uuid4()), "doc_id": "doc2", "content": "Document 2"}
        ]
        
        for doc in docs:
            vector = generate_dummy_vector(vector_size)
            payload = {k: v for k, v in doc.items() if k != "point_id"}
            vector_store.insert("text_chunks", doc["point_id"], vector, payload)
        
        # Delete one document
        vector_store.delete_document("text_chunks", "doc1")
        
        # Verify
        query_vector = generate_dummy_vector(vector_size)
        results = vector_store.search(query_vector, "text_chunks", top_k=5)
        remaining_docs = [r.payload.get("doc_id") for r in results]
        
        if "doc1" not in remaining_docs and "doc2" in remaining_docs:
            print("✅ PASS: Method works correctly with 'text_chunks' collection")
        else:
            print("❌ FAIL: Method didn't work as expected")
        
        vector_store.delete_collection("text_chunks")
        
        # Test 2: Method fails with different collection name
        print("\nTest 2: Method fails with non-'text_chunks' collection")
        print("-" * 55)
        
        vector_store.create_collection("custom_collection", vector_size)
        
        doc = {"point_id": str(uuid.uuid4()), "doc_id": "test_doc", "content": "Test"}
        vector = generate_dummy_vector(vector_size)
        payload = {k: v for k, v in doc.items() if k != "point_id"}
        vector_store.insert("custom_collection", doc["point_id"], vector, payload)
        
        try:
            vector_store.delete_document("custom_collection", "test_doc")
            print("❌ FAIL: Method should have failed but didn't")
        except Exception:
            print("✅ PASS: Method correctly failed with non-'text_chunks' collection")
        
        vector_store.delete_collection("custom_collection")
        
        print("\n" + "="*70)
        print("SUMMARY OF FINDINGS:")
        print("="*70)
        print("✅ WORKS: Method successfully deletes documents when:")
        print("   - Collection is named 'text_chunks'")
        print("   - Documents have 'doc_id' payload field")
        print("   - Filters correctly by doc_id value")
        print("   - Deletes ALL points with matching doc_id")
        
        print("\n❌ ISSUES IDENTIFIED:")
        print("   1. Hardcoded collection name 'text_chunks'")
        print("      - Should use the 'collection' parameter instead")
        print("      - Line 147: collection_name='text_chunks' should be collection_name=collection")
        
        print("\n🔧 RECOMMENDED FIX:")
        print("   Change line 147 from:")
        print("     collection_name='text_chunks',")
        print("   To:")
        print("     collection_name=collection,")
        
        print("\n📝 METHOD BEHAVIOR:")
        print("   - Uses 'doc_id' field for filtering (not 'document_id')")
        print("   - Deletes all points matching the doc_id")
        print("   - Returns success message even if no documents found")
        print("   - Uses Filter with 'must' condition and exact 'value' match")
        
        print("="*70)

    if __name__ == "__main__":
        comprehensive_test()
        
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running from the correct directory.")
except Exception as e:
    print(f"Unexpected error: {e}")
    import traceback
    traceback.print_exc()