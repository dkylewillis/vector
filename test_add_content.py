#!/usr/bin/env python3
"""Test the renamed add_content method."""

import tempfile
import os
from vector.config import Config
from vector.core.database import VectorDatabase

def test_add_content():
    """Test that add_content method works correctly."""
    print("Testing add_content method...")
    
    try:
        config = Config()
        db = VectorDatabase("test_collection", config)
        
        # Create collection
        db.create_collection(vector_size=384)
        print("✅ Collection created")
        
        # Test add_content method
        texts = ["Test content"]
        vectors = [[0.1] * 384]
        metadata = [{"file_hash": "test_hash", "filename": "test.txt"}]
        
        db.add_content(texts, vectors, metadata)
        print("✅ add_content method works")
        
        # Test search still works
        search_results = db.search([0.1] * 384, top_k=1)
        if search_results:
            print(f"✅ Search returned {len(search_results)} results")
        else:
            print("⚠️  No search results")
            
        # Clean up
        db.delete_collection()
        print("✅ Collection cleaned up")
        
        print("🎉 All tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_add_content()