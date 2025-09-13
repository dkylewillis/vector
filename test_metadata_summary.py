"""Test script for get_metadata_summary method."""

import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from vector.config import Config
from vector.core.database import VectorDatabase
from vector.core.collection_manager import CollectionManager


def test_get_metadata_summary():
    """Test the get_metadata_summary method."""
    print("🧪 Testing get_metadata_summary method...")
    
    try:
        # Initialize configuration and collection manager
        config = Config()
        collection_manager = CollectionManager(config)
        
        # Get available collections
        print("\n📁 Available collections:")
        pairs = collection_manager.list_collection_pairs()
        
        if not pairs:
            print("❌ No collection pairs found. Please create some collections first.")
            return
        
        for i, pair in enumerate(pairs, 1):
            display_name = pair['display_name']
            chunks_collection = pair['chunks_collection']
            doc_count = pair.get('document_count', 0)
            print(f"   {i}. {display_name} ({chunks_collection}) - {doc_count} documents")
        
        # Test with the first available collection
        test_collection = pairs[0]
        display_name = test_collection['display_name']
        chunks_collection = test_collection['chunks_collection']
        
        print(f"\n🔍 Testing with collection: {display_name}")
        print(f"   Chunks collection: {chunks_collection}")
        
        # Create database instance
        db = VectorDatabase(chunks_collection, config, collection_manager)
        
        # Test if collection exists
        if not db.collection_exists():
            print(f"❌ Collection '{chunks_collection}' does not exist in Qdrant")
            return
        
        print(f"✅ Collection exists in Qdrant")
        
        # Get metadata summary
        print("\n📊 Getting metadata summary...")
        summary = db.get_metadata_summary()
        
        # Display results
        print(f"✅ Metadata summary retrieved successfully!")
        print(f"   Type: {type(summary)}")
        print(f"   Keys: {list(summary.keys())}")
        
        # Check each metadata field
        filenames = summary.get('filenames', [])
        sources = summary.get('sources', [])
        headings = summary.get('headings', [])
        total_docs = summary.get('total_documents', 0)
        
        print(f"\n📋 Summary details:")
        print(f"   📁 Filenames: {len(filenames)} (type: {type(filenames)})")
        if filenames:
            print(f"      First 5: {filenames[:5]}")
        
        print(f"   📂 Sources: {len(sources)} (type: {type(sources)})")
        if sources:
            print(f"      All: {sources}")
        
        print(f"   🏷️  Headings: {len(headings)} (type: {type(headings)})")
        if headings:
            print(f"      First 10: {headings[:10]}")
        
        print(f"   📊 Total documents: {total_docs}")
        
        # Test data format consistency
        print(f"\n🧪 Data format validation:")
        
        # Check if all fields are lists (as expected from the database method)
        expected_format = True
        
        if not isinstance(filenames, list):
            print(f"   ❌ filenames is not a list: {type(filenames)}")
            expected_format = False
        else:
            print(f"   ✅ filenames is a list with {len(filenames)} items")
        
        if not isinstance(sources, list):
            print(f"   ❌ sources is not a list: {type(sources)}")
            expected_format = False
        else:
            print(f"   ✅ sources is a list with {len(sources)} items")
        
        if not isinstance(headings, list):
            print(f"   ❌ headings is not a list: {type(headings)}")
            expected_format = False
        else:
            print(f"   ✅ headings is a list with {len(headings)} items")
        
        if not isinstance(total_docs, int):
            print(f"   ❌ total_documents is not an int: {type(total_docs)}")
            expected_format = False
        else:
            print(f"   ✅ total_documents is an int: {total_docs}")
        
        if expected_format:
            print(f"\n🎉 All data formats are as expected!")
        else:
            print(f"\n⚠️  Some data formats are unexpected")
        
        # Test with display name resolution
        print(f"\n🔍 Testing with display name resolution...")
        db_by_display = VectorDatabase(display_name, config, collection_manager)
        summary_by_display = db_by_display.get_metadata_summary()
        
        # Compare results
        if summary == summary_by_display:
            print(f"✅ Display name resolution works correctly")
        else:
            print(f"❌ Display name resolution gives different results")
            print(f"   Direct: {len(summary.get('filenames', []))} filenames")
            print(f"   Display: {len(summary_by_display.get('filenames', []))} filenames")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


def test_collection_access():
    """Test basic collection access without metadata."""
    print("\n🧪 Testing basic collection access...")
    
    try:
        config = Config()
        collection_manager = CollectionManager(config)
        
        # Get first available collection
        pairs = collection_manager.list_collection_pairs()
        if not pairs:
            print("❌ No collections available for testing")
            return
        
        test_collection = pairs[0]
        chunks_collection = test_collection['chunks_collection']
        
        # Test database connection
        db = VectorDatabase(chunks_collection, config, collection_manager)
        
        # Test collection existence
        exists = db.collection_exists()
        print(f"✅ Collection exists check: {exists}")
        
        if exists:
            # Test collection info
            info = db.get_collection_info()
            print(f"✅ Collection info retrieved:")
            print(f"   Name: {info.get('name', 'unknown')}")
            print(f"   Status: {info.get('status', 'unknown')}")
            print(f"   Points: {info.get('points_count', 0)}")
            print(f"   Vectors: {info.get('vectors_count', 0)}")
        
    except Exception as e:
        print(f"❌ Collection access test failed: {e}")


if __name__ == "__main__":
    print("🚀 Starting metadata summary tests...\n")
    
    # Test collection access first
    test_collection_access()
    
    # Test metadata summary
    test_get_metadata_summary()
    
    print(f"\n✅ Test completed!")