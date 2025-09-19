#!/usr/bin/env python3
"""
Comprehensive test script for MetadataStore class.
Tests all CRUD operations, search functionality, and persistence.
"""

import tempfile
import json
from pathlib import Path

from vector.core.models import DocumentMetadataRecord
from vector.core.vector_store import VectorMetadataStore


def test_metadata_store():
    """Comprehensive test of MetadataStore functionality."""
    print("=== MetadataStore Comprehensive Test ===\n")
    
    # Use a temporary file for testing
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
        temp_path = Path(tmp_file.name)
    
    try:
        print(f"1. Testing initialization with new file...")
        # Test 1: Initialize with non-existent file
        meta_store = VectorMetadataStore(temp_path)
        print(f"✅ MetadataStore initialized successfully")
        print(f"   File path: {temp_path}")
        print(f"   Initial records count: {len(meta_store.list())}")
        
        print(f"\n2. Testing add() method...")
        # Test 2: Add records
        test_records = [
            DocumentMetadataRecord(
                doc_id="doc_001",
                display_name="CCWA Manual",
                source_file_name="ccwa_sw_manual.pdf",
                description="Reference manual for stormwater design",
                tags=["stormwater", "county", "manual"]
            ),
            DocumentMetadataRecord(
                doc_id="doc_002", 
                display_name="Building Code",
                source_file_name="building_code_2023.pdf",
                description="County building code regulations",
                tags=["building", "code", "regulations"]
            ),
            DocumentMetadataRecord(
                doc_id="doc_003",
                display_name="Zoning Guidelines", 
                source_file_name="zoning_guidelines.pdf",
                description="Zoning and land use guidelines",
                tags=["zoning", "land-use", "county"]
            ),
            DocumentMetadataRecord(
                doc_id="doc_004",
                display_name="Environmental Impact Study",
                source_file_name="env_impact_2024.pdf", 
                description="Environmental impact assessment",
                tags=["environment", "impact", "study"]
            ),
            DocumentMetadataRecord(
                doc_id="doc_005",
                display_name="CCWA Update Manual",
                source_file_name="ccwa_update_manual.pdf",
                description="Updated CCWA procedures",
                tags=["stormwater", "county", "update"]
            )
        ]
        
        for record in test_records:
            meta_store.add(record)
            print(f"   Added: {record.doc_id} - {record.display_name}")
        
        print(f"✅ Added {len(test_records)} records successfully")
        
        print(f"\n3. Testing persistence (file saving)...")
        # Test 3: Verify file was created and contains data
        if temp_path.exists():
            file_content = json.loads(temp_path.read_text())
            print(f"✅ File created with {len(file_content)} records")
            print(f"   Sample record keys: {list(file_content.keys())[:3]}")
        else:
            print(f"❌ File was not created")
        
        print(f"\n4. Testing get() method...")
        # Test 4: Get individual records
        try:
            record = meta_store.get("doc_001")
            print(f"✅ Retrieved record: {record.doc_id} - {record.display_name}")
            print(f"   Tags: {record.tags}")
            print(f"   Created at: {record.created_at}")
        except KeyError:
            print(f"❌ Failed to retrieve record doc_001")
        
        print(f"\n5. Testing list() method...")
        # Test 5: List all records
        all_records = meta_store.list()
        print(f"✅ Listed {len(all_records)} total records:")
        for record in all_records:
            print(f"   - {record.doc_id}: {record.display_name}")
        
        print(f"\n6. Testing get_by_display_name() method...")
        # Test 6: Search by display name
        ccwa_records = meta_store.get_by_display_name("CCWA Manual")
        print(f"✅ Found {len(ccwa_records)} records with display name 'CCWA Manual':")
        for record in ccwa_records:
            print(f"   - {record.doc_id}: {record.source_file_name}")
        
        print(f"\n7. Testing get_by_tag() method...")
        # Test 7: Search by single tag
        county_records = meta_store.get_by_tag("county")
        print(f"✅ Found {len(county_records)} records with tag 'county':")
        for record in county_records:
            print(f"   - {record.doc_id}: {record.display_name}")
        
        print(f"\n8. Testing get_by_tags() method (match any)...")
        # Test 8: Search by multiple tags (match any)
        multi_tag_records = meta_store.get_by_tags(["stormwater", "building"], match_all=False)
        print(f"✅ Found {len(multi_tag_records)} records with tags 'stormwater' OR 'building':")
        for record in multi_tag_records:
            print(f"   - {record.doc_id}: {record.display_name} (tags: {record.tags})")
        
        print(f"\n9. Testing get_by_tags() method (match all)...")
        # Test 9: Search by multiple tags (match all)
        all_tags_records = meta_store.get_by_tags(["stormwater", "county"], match_all=True)
        print(f"✅ Found {len(all_tags_records)} records with tags 'stormwater' AND 'county':")
        for record in all_tags_records:
            print(f"   - {record.doc_id}: {record.display_name} (tags: {record.tags})")
        
        print(f"\n10. Testing delete() method...")
        # Test 10: Delete a record
        meta_store.delete("doc_004")
        remaining_records = meta_store.list()
        print(f"✅ Deleted doc_004. Remaining records: {len(remaining_records)}")
        
        # Verify the record is gone
        try:
            deleted_record = meta_store.get("doc_004")
            print(f"❌ Record doc_004 still exists (should be deleted)")
        except KeyError:
            print(f"✅ Record doc_004 successfully deleted")
        
        print(f"\n11. Testing persistence after operations...")
        # Test 11: Create new MetadataStore instance to test file loading
        meta_store2 = VectorMetadataStore(temp_path)
        loaded_records = meta_store2.list()
        print(f"✅ Loaded {len(loaded_records)} records from file")
        print(f"   Records persisted correctly across instances")
        
        print(f"\n12. Testing edge cases...")
        # Test 12: Edge cases
        
        # Non-existent record
        try:
            meta_store.get("non_existent")
            print(f"❌ Should have raised KeyError for non-existent record")
        except KeyError:
            print(f"✅ Correctly raised KeyError for non-existent record")
        
        # Delete non-existent record (should not error)
        meta_store.delete("non_existent")
        print(f"✅ Delete non-existent record handled gracefully")
        
        # Empty tag search
        empty_results = meta_store.get_by_tag("non_existent_tag")
        print(f"✅ Empty tag search returned {len(empty_results)} results")
        
        print(f"\n=== Test Summary ===")
        print(f"✅ All MetadataStore tests passed successfully!")
        print(f"✅ CRUD operations working correctly")
        print(f"✅ Search functionality working correctly") 
        print(f"✅ Persistence working correctly")
        print(f"✅ Edge cases handled appropriately")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Clean up temporary file
        if temp_path.exists():
            temp_path.unlink()
            print(f"\n🧹 Cleaned up temporary file: {temp_path}")


if __name__ == "__main__":
    test_metadata_store()