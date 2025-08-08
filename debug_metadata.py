#!/usr/bin/env python3
"""Debug script to check metadata filtering issues."""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent / "src"))

from src.data_pipeline.vector_database import VectorDatabase
from src.data_pipeline.embedder import Embedder

# Initialize components
db = VectorDatabase("fayette")
embedder = Embedder()

print("=== REGSCOUT METADATA DEBUG ===")

# Test 1: Check if collection exists and get info
print("\n=== COLLECTION INFO ===")
if db.collection_exists():
    info = db.get_collection_info()
    print(f"Collection exists: {info.get('name', 'unknown')}")
    print(f"Points count: {info.get('points_count', 0)}")
    print(f"Storage mode: {info.get('storage_mode', 'unknown')}")
    print(f"Vector size: {info.get('vector_size', 'unknown')}")
else:
    print("❌ Collection 'fayette' doesn't exist")
    sys.exit(1)

# Test 2: Do a simple search to see what metadata structure we have
print("\n=== SAMPLE METADATA STRUCTURE ===")
try:
    query_embedding = embedder.embed_text("test query")
    results = db.search(query_embedding[0], top_k=3)
    
    if results:
        print(f"Found {len(results)} sample results")
        for i, result in enumerate(results[:2]):
            print(f"\nResult {i+1}:")
            print(f"  Score: {result['score']:.4f}")
            print(f"  Text preview: {result['text'][:100]}...")
            print(f"  Metadata keys: {list(result['metadata'].keys())}")
            
            # Check specific fields we want to filter on
            filename = result['metadata'].get('filename', 'NOT FOUND')
            file_type = result['metadata'].get('file_type', 'NOT FOUND')
            source = result['metadata'].get('source', 'NOT FOUND')
            
            print(f"  filename: '{filename}'")
            print(f"  file_type: '{file_type}'")
            print(f"  source: '{source}'")
    else:
        print("❌ No results found in simple search")
        sys.exit(1)
except Exception as e:
    print(f"❌ Error in simple search: {e}")
    sys.exit(1)

# Test 3: Check what storage mode we're actually using
print(f"\n=== STORAGE MODE ===")
print(f"Database storage mode: {db.storage_mode}")

# Test 4: Try filtering with exact filenames found above
print("\n=== TESTING FILTERING ===")
try:
    query_embedding = embedder.embed_text("utilities")
    
    # Use the actual filename from the first result
    if results:
        actual_filename = results[0]['metadata'].get('filename')
        actual_file_type = results[0]['metadata'].get('file_type')
        
        test_filters = [
            {"filename": actual_filename},
            {"file_type": actual_file_type},
        ]
        
        # Also test the specific filename from CLI
        test_filters.append({"filename": "Chapter_28___UTILITIES.docx"})
        
        for filter_test in test_filters:
            print(f"\nTesting filter: {filter_test}")
            try:
                # Catch the exact error without the graceful fallback
                search_params = {
                    "collection_name": db.collection_name,
                    "query_vector": query_embedding[0].tolist(),
                    "limit": 5
                }
                
                # Add the filter
                from qdrant_client.models import Filter, FieldCondition, MatchValue
                conditions = []
                for key, value in filter_test.items():
                    conditions.append(
                        FieldCondition(
                            key=key,
                            match=MatchValue(value=value)
                        )
                    )
                search_params["query_filter"] = Filter(must=conditions)
                
                # Try the raw search
                raw_results = db.client.search(**search_params)
                print(f"  ✅ SUCCESS: Found {len(raw_results)} results with filtering")
                
            except Exception as e:
                print(f"  ❌ FILTER ERROR: {e}")
                print(f"     Error type: {type(e).__name__}")
                
                # Now try with the graceful fallback
                try:
                    results_fallback = db.search(
                        query_embedding[0], 
                        top_k=5, 
                        metadata_filter=filter_test
                    )
                    print(f"  🔄 FALLBACK: Found {len(results_fallback)} results (unfiltered)")
                except Exception as e2:
                    print(f"  ❌ FALLBACK ALSO FAILED: {e2}")

except Exception as e:
    print(f"❌ Error in filtering test setup: {e}")

print("\n=== DEBUG COMPLETE ===")
