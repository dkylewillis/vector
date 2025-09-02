"""Test 2: Load document and artifacts from storage system."""

import asyncio
from pathlib import Path
from vector.core.storage import StorageFactory
from vector.config import Config


async def test_load_from_storage():
    """Test loading document and artifacts from storage."""
    
    print("🚀 Test 2: Load Document from Storage")
    print("=" * 50)
    
    # Initialize configuration and storage
    config = Config()
    print(f"🔧 Using storage backend: {config.storage_backend}")
    
    # Create storage backend
    storage_backend = await StorageFactory.create_backend(config)
    print(f"✅ Storage backend initialized: {type(storage_backend).__name__}")
    
    # Document ID to load (from test 1)
    doc_id = "gsmm_75_85_test"
    
    print(f"\n📥 Loading document: {doc_id}")
    loaded_doc_data = await storage_backend.get_document_storage().load_document(doc_id)
    
    if loaded_doc_data:
        loaded_doc, loaded_metadata = loaded_doc_data
        print(f"✅ Document loaded successfully!")
        print(f"   Filename: {loaded_metadata.get('filename') or loaded_metadata.get('file_path', 'Unknown')}")
        print(f"   Source: {loaded_metadata.get('source') or loaded_metadata.get('source_category', 'Unknown')}")
        print(f"   File Hash: {loaded_metadata.get('file_hash', 'Unknown')}")
        print(f"   Saved at: {loaded_metadata.get('created_at', 'Unknown')}")
        print(f"   Document type: {type(loaded_doc).__name__}")
        
        # Test that the document is usable
        print(f"\n🧪 Testing loaded document:")
        try:
            # Try to iterate through items to verify it's a valid DoclingDocument
            item_count = 0
            for item, level in loaded_doc.iterate_items():
                item_count += 1
                if item_count >= 5:  # Just test first 5 items
                    break
            print(f"   ✅ Document has {item_count}+ items and is functional")
        except Exception as e:
            print(f"   ❌ Error testing document: {e}")
    else:
        print(f"❌ Failed to load document with ID: {doc_id}")
        print(f"💡 Make sure to run test_storage_save.py first!")
        return
    
    # Load some artifacts
    print(f"\n🖼️ Loading artifacts for document...")
    artifacts = await storage_backend.get_artifact_storage().list_artifacts()
    doc_artifacts = [a for a in artifacts if a.get('doc_hash') == doc_id or a.get('doc_id') == doc_id]
    
    print(f"📊 Found {len(doc_artifacts)} artifacts for this document")
    
    if doc_artifacts:
        # Try to load a few artifacts
        print(f"\n🔍 Testing artifact loading:")
        for i, artifact_info in enumerate(doc_artifacts[:3]):  # Test first 3
            artifact_id = artifact_info['artifact_id']
            artifact_type = artifact_info.get('artifact_type', 'unknown')
            
            try:
                artifact_data = await storage_backend.get_artifact_storage().load_artifact(artifact_id)
                if artifact_data:
                    data, metadata = artifact_data
                    print(f"   ✅ Loaded {artifact_type} artifact: {len(data)} bytes")
                else:
                    print(f"   ❌ Failed to load artifact: {artifact_id} (returned None)")
            except Exception as e:
                print(f"   ❌ Error loading artifact {artifact_id}: {e}")
                import traceback
                traceback.print_exc()
    
    # Get current storage statistics
    stats = await storage_backend.get_stats()
    print(f"\n📊 Current Storage Statistics:")
    print(f"  Backend Type: {stats['backend_type']}")
    print(f"  Documents: {stats['total_documents']}")
    print(f"  Artifacts: {stats['total_artifacts']}")
    print(f"  Storage Size: {stats['storage_size_mb']} MB")
    
    print(f"\n✅ Load test completed!")


if __name__ == "__main__":
    asyncio.run(test_load_from_storage())
