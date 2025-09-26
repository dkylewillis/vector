#!/usr/bin/env python3
"""Test script to verify thumbnail gallery functionality."""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from vector.web.service import VectorWebService
from vector.config import Config

def test_thumbnail_functionality():
    """Test that thumbnail functionality works."""
    print("🧪 Testing thumbnail functionality...")
    
    # Initialize service
    config = Config()
    service = VectorWebService(config)
    
    # Test search with thumbnails
    print("\n📝 Testing search with thumbnails...")
    try:
        results, thumbnails = service.search_with_thumbnails(
            query="test query", 
            collection="chunks", 
            top_k=5, 
            metadata_filter=None,
            search_type="both"
        )
        
        print(f"✅ Search returned: {len(thumbnails)} thumbnails")
        if thumbnails:
            print(f"   📷 Thumbnail paths: {thumbnails}")
            
            # Verify thumbnail files exist
            for thumb in thumbnails:
                if Path(thumb).exists():
                    print(f"   ✅ Thumbnail exists: {thumb}")
                else:
                    print(f"   ❌ Thumbnail missing: {thumb}")
        else:
            print("   ⚠️  No thumbnails returned")
            
    except Exception as e:
        print(f"❌ Search test failed: {e}")
    
    # Test AI with thumbnails
    print("\n🤖 Testing AI with thumbnails...")
    try:
        response, thumbnails = service.ask_ai_with_thumbnails(
            question="What is this about?",
            collection="chunks",
            length="medium",
            metadata_filter=None,
            search_type="both"
        )
        
        print(f"✅ AI returned: {len(thumbnails)} thumbnails")
        if thumbnails:
            print(f"   📷 Thumbnail paths: {thumbnails}")
        else:
            print("   ⚠️  No thumbnails returned")
            
    except Exception as e:
        print(f"❌ AI test failed: {e}")

if __name__ == "__main__":
    test_thumbnail_functionality()
    print("\n🎉 Thumbnail test completed!")