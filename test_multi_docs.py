#!/usr/bin/env python3

from vector.core.pipeline import VectorPipeline

def test_multiple_documents():
    """Test loading multiple documents to check for ID conflicts."""
    
    print("=== Testing Multiple Documents (ID Conflict Prevention) ===\n")
    
    pipeline = VectorPipeline()
    
    # Same document loaded twice to simulate different docs
    filename = r'data/converted_documents/bf9345120a19ee4110d3221c40a1636580e1c96429f2d12e2cd09dbc82429d85/docling_document.json'
    
    try:
        print("Loading Document 1...")
        doc_id_1 = pipeline.run(filename, collection_name="multi_doc_test")
        print(f"✅ Document 1 completed: {doc_id_1}\n")
        
        print("Loading Document 2 (same file, different processing)...")
        doc_id_2 = pipeline.run(filename, collection_name="multi_doc_test")
        print(f"✅ Document 2 completed: {doc_id_2}\n")
        
        # Check collection stats
        with pipeline.store.get_client() as client:
            collection_info = client.get_collection("multi_doc_test")
            print(f"📊 Collection 'multi_doc_test' stats:")
            print(f"   - Total points: {collection_info.points_count}")
            print(f"   - Expected: 48 (24 chunks × 2 documents)")
            
            if collection_info.points_count == 48:
                print("✅ No ID conflicts detected!")
            else:
                print("❌ Possible ID conflicts - expected 48 points but got {collection_info.points_count}")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def test_id_patterns():
    """Show the ID patterns generated for different documents."""
    
    print("\n=== Testing ID Pattern Generation ===\n")
    
    pipeline = VectorPipeline()
    filename = r'data/converted_documents/bf9345120a19ee4110d3221c40a1636580e1c96429f2d12e2cd09dbc82429d85/docling_document.json'
    
    # Load document and check the first few IDs
    try:
        converted_doc = pipeline.convert(filename)
        chunks, artifacts = pipeline.chunk(converted_doc)
        
        print(f"Generated chunk IDs would be:")
        import hashlib
        file_hash = hashlib.md5(str(filename).encode()).hexdigest()[:8]
        
        for i in range(min(5, len(chunks))):  # Show first 5
            point_id = f"{file_hash}_{i:04d}"
            print(f"   Chunk {i}: {point_id}")
        
        if len(chunks) > 5:
            print(f"   ... and {len(chunks) - 5} more")
            
        print(f"\n🔍 Document prefix: '{file_hash}' (based on file path hash)")
        print("   This ensures each document gets unique IDs even in the same collection")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_id_patterns()
    test_multiple_documents()