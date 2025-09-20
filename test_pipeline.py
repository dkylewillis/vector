#!/usr/bin/env python3

from vector.core.pipeline import VectorPipeline

def test_pipeline():
    # Initialize pipeline
    pipeline = VectorPipeline()
    
    # Test with the same document we used before
    filename = r'data/converted_documents/bf9345120a19ee4110d3221c40a1636580e1c96429f2d12e2cd09dbc82429d85/docling_document.json'
    
    print(f"Testing pipeline with: {filename}")
    
    try:
        doc_id = pipeline.run(filename)
        print(f"✅ Pipeline completed successfully! Document ID: {doc_id}")
    except Exception as e:
        print(f"❌ Pipeline failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_pipeline()