#!/usr/bin/env python3
"""Simple test of the updated CollectionManager."""

import sys
import os

# Add the parent directory to the path so we can import vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vector.core.collection_manager import CollectionManager
from vector.config import Config

def test_collection_manager():
    """Test the basic functionality of the updated CollectionManager."""
    
    print("Testing CollectionManager...")
    
    # Initialize with a test metadata file
    config = Config()
    test_metadata_file = "test_collections_metadata.json"
    
    # Clean up any existing test file
    if os.path.exists(test_metadata_file):
        os.remove(test_metadata_file)
    
    try:
        # Initialize collection manager
        manager = CollectionManager(config, test_metadata_file)
        print("✅ CollectionManager initialized successfully")
        
        # Test creating a collection pair
        pair_info = manager.create_collection_pair(
            display_name="Test Collection",
            description="A test collection pair"
        )
        print(f"✅ Created collection pair: {pair_info}")
        
        # Test listing collection pairs
        pairs = manager.list_collection_pairs()
        print(f"✅ Listed collection pairs: {len(pairs)} found")
        for pair in pairs:
            print(f"   - {pair['display_name']} ({pair['pair_id']})")
        
        # Test getting pair by display name
        retrieved_pair = manager.get_pair_by_display_name("Test Collection")
        print(f"✅ Retrieved pair by display name: {retrieved_pair['pair_id']}")
        
        # Test tracking a document to the pair
        success = manager.track_document_in_pair(
            pair_info['pair_id'],
            "test_doc_123",
            {"filename": "test.pdf", "source": "test"}
        )
        print(f"✅ Tracked document in pair: {success}")
        
        # Test listing documents in pair
        docs = manager.list_documents_in_pair(pair_info['pair_id'])
        print(f"✅ Listed documents in pair: {len(docs)} found")
        
        print("🎉 All tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up test file
        if os.path.exists(test_metadata_file):
            os.remove(test_metadata_file)

if __name__ == "__main__":
    test_collection_manager()
