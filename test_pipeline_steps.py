#!/usr/bin/env python3

from vector.core.pipeline import VectorPipeline

def test_independent_steps():
    """Test running each pipeline step independently."""
    
    # Initialize pipeline
    pipeline = VectorPipeline()
    
    # Test file
    filename = r'data/converted_documents/bf9345120a19ee4110d3221c40a1636580e1c96429f2d12e2cd09dbc82429d85/docling_document.json'
    
    print("=== Testing Independent Pipeline Steps ===\n")
    
    try:
        # Step 1: Convert document
        print("Step 1: Converting document...")
        converted_doc = pipeline.convert(filename)
        
        # Step 2: Extract chunks and artifacts
        print("\nStep 2: Extracting chunks and artifacts...")
        chunks, artifacts = pipeline.chunk(converted_doc)
        
        # Step 3: Generate embeddings
        print("\nStep 3: Generating embeddings...")
        embeddings = pipeline.embed(chunks)
        
        # Step 4: Store in vector database
        print("\nStep 4: Storing in vector database...")
        pipeline.store_chunks(chunks, embeddings, collection_name="test_collection", source_file=filename)
        
        print(f"\n✅ All steps completed successfully!")
        print(f"   - Processed: {len(chunks)} chunks")
        print(f"   - Generated: {len(embeddings)} embeddings")
        print(f"   - Found: {len(artifacts)} artifacts")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def test_full_pipeline():
    """Test the full pipeline run method."""
    
    print("\n=== Testing Full Pipeline ===\n")
    
    pipeline = VectorPipeline()
    filename = r'data/converted_documents/bf9345120a19ee4110d3221c40a1636580e1c96429f2d12e2cd09dbc82429d85/docling_document.json'
    
    try:
        doc_id = pipeline.run(filename, collection_name="full_pipeline_test")
        print(f"✅ Full pipeline completed! Document ID: {doc_id}")
    except Exception as e:
        print(f"❌ Pipeline failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_independent_steps()
    test_full_pipeline()