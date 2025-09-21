#!/usr/bin/env python3
"""
Simple test script for VectorRegistry.list_documents() method.
"""

from pathlib import Path
from vector.core.document_registry import VectorRegistry
from vector.core.models import DocumentRecord

def test_list_documents():
    """Test the list_documents functionality."""
    
    # Use a test registry directory
    test_registry_path = "test_registry_list"
    registry = VectorRegistry(test_registry_path)
    
    print("🧪 Testing VectorRegistry.list_documents()")
    print("=" * 50)
    
    try:
        # Clean start - should be empty
        docs = registry.list_documents()
        print(f"✅ Initial state: {len(docs)} documents")
        assert len(docs) == 0, "Registry should start empty"
        
        # Create test documents with different statuses
        test_files = [
            ("test1.pdf", "doc1", "registered"),
            ("test2.pdf", "doc2", "processing"), 
            ("test3.pdf", "doc3", "completed"),
            ("test4.pdf", "doc4", "failed"),
            ("test5.pdf", "doc5", "completed")
        ]
        
        print(f"\n📝 Creating {len(test_files)} test documents...")
        
        for filename, doc_id, status in test_files:
            # Create fake file path
            file_path = Path(filename)
            
            # Register document
            doc_record = registry.register_document(file_path, doc_id)
            
            # Update status if not 'registered'
            if status != "registered":
                doc_record.status = status
                registry.update_document(doc_record)
            
            print(f"  ✅ Created {doc_id} with status '{status}'")
        
        # Test 1: List all documents
        print(f"\n🔍 Test 1: List all documents")
        all_docs = registry.list_documents()
        print(f"  Found {len(all_docs)} documents")
        assert len(all_docs) == 5, f"Expected 5 documents, got {len(all_docs)}"
        
        # Verify they're sorted by registered_date (default)
        for i, doc in enumerate(all_docs):
            print(f"  {i+1}. {doc.document_id} - {doc.status} - {doc.display_name}")
        
        # Test 2: Filter by status
        print(f"\n🔍 Test 2: Filter by status")
        
        completed_docs = registry.list_documents(status="completed")
        print(f"  Completed documents: {len(completed_docs)}")
        assert len(completed_docs) == 2, f"Expected 2 completed docs, got {len(completed_docs)}"
        
        failed_docs = registry.list_documents(status="failed")
        print(f"  Failed documents: {len(failed_docs)}")
        assert len(failed_docs) == 1, f"Expected 1 failed doc, got {len(failed_docs)}"
        
        processing_docs = registry.list_documents(status="processing")
        print(f"  Processing documents: {len(processing_docs)}")
        assert len(processing_docs) == 1, f"Expected 1 processing doc, got {len(processing_docs)}"
        
        # Test 3: Sort by different field
        print(f"\n🔍 Test 3: Sort by document_id")
        docs_by_id = registry.list_documents(sort_by="document_id", reverse=False)
        doc_ids = [doc.document_id for doc in docs_by_id]
        print(f"  Sorted by document_id: {doc_ids}")
        assert doc_ids == sorted(doc_ids), "Documents should be sorted by document_id"
        
        # Test 4: Sort by display_name
        print(f"\n🔍 Test 4: Sort by display_name")
        docs_by_name = registry.list_documents(sort_by="display_name", reverse=False)
        display_names = [doc.display_name for doc in docs_by_name]
        print(f"  Sorted by display_name: {display_names}")
        assert display_names == sorted(display_names), "Documents should be sorted by display_name"
        
        # Test 5: Combined filter and sort
        print(f"\n🔍 Test 5: Filter completed docs, sort by document_id")
        completed_sorted = registry.list_documents(
            status="completed", 
            sort_by="document_id", 
            reverse=False
        )
        print(f"  Completed docs sorted by ID:")
        for doc in completed_sorted:
            print(f"    {doc.document_id} - {doc.status}")
        assert len(completed_sorted) == 2, "Should have 2 completed documents"
        
        # Test 6: Invalid sort field (should fallback to registered_date)
        print(f"\n🔍 Test 6: Invalid sort field (should fallback)")
        docs_invalid_sort = registry.list_documents(sort_by="nonexistent_field")
        print(f"  Documents with invalid sort field: {len(docs_invalid_sort)}")
        assert len(docs_invalid_sort) == 5, "Should still return all documents"
        
        print(f"\n✅ All tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise
    
    finally:
        # Clean up test registry
        print(f"\n🧹 Cleaning up test registry...")
        import shutil
        if Path(test_registry_path).exists():
            shutil.rmtree(test_registry_path)
            print(f"  Removed {test_registry_path}")

def test_empty_registry():
    """Test list_documents on empty/non-existent registry."""
    
    print("\n🧪 Testing empty registry")
    print("=" * 30)
    
    # Test with non-existent path
    registry = VectorRegistry("nonexistent_registry")
    docs = registry.list_documents()
    print(f"✅ Non-existent registry: {len(docs)} documents")
    assert len(docs) == 0, "Non-existent registry should return empty list"
    
    # Test with different status filters on empty registry
    for status in ["registered", "processing", "completed", "failed"]:
        filtered_docs = registry.list_documents(status=status)
        print(f"✅ Empty registry with status '{status}': {len(filtered_docs)} documents")
        assert len(filtered_docs) == 0, f"Empty registry should return 0 docs for status {status}"

if __name__ == "__main__":
    print("🚀 Starting VectorRegistry.list_documents() tests\n")
    
    test_empty_registry()
    test_list_documents()
    
    print("\n🎉 All tests completed successfully!")