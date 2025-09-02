"""Test 1: Convert PDF and save to storage system."""

import asyncio
from pathlib import Path
from vector.core.converter import DocumentConverter
from vector.core.artifacts import ArtifactProcessor
from vector.core.models import DocumentResult
from vector.core.storage import StorageFactory
from vector.config import Config


async def test_save_to_storage():
    """Test converting PDF and saving to storage."""
    
    print("🚀 Test 1: Save Document to Storage")
    print("=" * 50)
    
    # Initialize configuration and storage
    config = Config()
    print(f"🔧 Using storage backend: {config.storage_backend}")
    print(f"📁 Artifacts directory: {config.artifacts_dir}")
    
    # Create storage backend
    storage_backend = await StorageFactory.create_backend(config)
    print(f"✅ Storage backend initialized: {type(storage_backend).__name__}")
    
    # Convert PDF document
    file_path = Path("data/source_documents/gsmm/gsmm_75_85.pdf")
    converter = DocumentConverter()
    
    print(f"\n🔄 Converting PDF document: {file_path}")
    doc = converter.convert_document(file_path)
    print(f"✅ Document converted successfully")
    
    # Create artifact processor with storage backend
    artifact_processor = ArtifactProcessor(
        config=config,
        storage_backend=storage_backend,
        debug=True,
        generate_thumbnails=True
    )
    
    # Create document result
    doc_result = DocumentResult(
        document=doc,
        file_path=file_path,
        source_category="gsmm",
        file_hash="gsmm_75_85_test"
    )
    
    print(f"\n🔄 Processing and saving document with storage backend...")
    await artifact_processor.process_document(doc_result)
    
    # Get storage statistics
    stats = await storage_backend.get_stats()
    print(f"\n📊 Storage Statistics After Save:")
    print(f"  Backend Type: {stats['backend_type']}")
    print(f"  Documents: {stats['total_documents']}")
    print(f"  Artifacts: {stats['total_artifacts']}")
    print(f"  Storage Size: {stats['storage_size_mb']} MB")
    
    # List what we saved
    documents = await storage_backend.get_document_storage().list_documents()
    print(f"\n📄 Saved Documents: {len(documents)}")
    for doc_info in documents:
        # Handle different possible metadata structures
        filename = doc_info.get('filename') or doc_info.get('file_path', 'Unknown')
        source = doc_info.get('source') or doc_info.get('source_category', 'Unknown')
        print(f"  - {doc_info['doc_id']}: {filename} ({source})")
    
    artifacts = await storage_backend.get_artifact_storage().list_artifacts()
    print(f"\n🖼️ Saved Artifacts: {len(artifacts)}")
    artifact_types = {}
    for artifact in artifacts:
        artifact_type = artifact.get('artifact_type', 'unknown')
        artifact_types[artifact_type] = artifact_types.get(artifact_type, 0) + 1
    
    for artifact_type, count in artifact_types.items():
        print(f"  - {artifact_type}: {count}")
    
    print(f"\n✅ Save test completed!")
    print(f"📝 Document ID to use for loading: 'gsmm_75_85_test'")


if __name__ == "__main__":
    asyncio.run(test_save_to_storage())
