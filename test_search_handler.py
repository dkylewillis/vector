#!/usr/bin/env python3
"""Test script to check if search thumbnails gallery is working."""

import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from vector.web.handlers import perform_search
from vector.web.service import VectorWebService
from vector.config import Config

def test_search_handler():
    """Test search handler directly."""
    print("🧪 Testing search handler...")
    
    service = VectorWebService(Config())
    
    # Call the handler directly
    result_text, thumbnails = perform_search(
        web_service=service,
        query="test query",
        top_k=5,
        collection="chunks",
        selected_documents=[],
        search_type="both"
    )
    
    print(f"✅ Handler returned:")
    print(f"   Result text type: {type(result_text)}")
    print(f"   Thumbnails type: {type(thumbnails)}")
    print(f"   Thumbnails length: {len(thumbnails)}")
    print(f"   Thumbnails content: {thumbnails}")
    
    return result_text, thumbnails

if __name__ == "__main__":
    test_search_handler()
    print("\n🎉 Handler test completed!")