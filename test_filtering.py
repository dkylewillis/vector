#!/usr/bin/env python3
"""Test metadata filtering functionality."""

from src.agents.research_agent import ResearchAgent
from config import Config

def test_filtering():
    """Test basic metadata filtering."""
    config = Config('./config/settings.yaml')
    agent = ResearchAgent(config, collection_name='fayette')
    
    # Test without filter
    print("🔍 Testing search without filter...")
    results_all = agent.search('setback', top_k=5)
    print(f"Found {len(results_all)} total results")
    
    # Test with filename filter
    print("\n🔍 Testing search with file_type filter...")
    results_filtered = agent.search('setback', top_k=5, metadata_filter={'file_type': 'docx'})
    print(f"Found {len(results_filtered)} filtered results")
    
    # Show first result metadata
    if results_filtered:
        print(f"\nFirst filtered result metadata:")
        print(f"  Filename: {results_filtered[0]['metadata'].get('filename', 'N/A')}")
        print(f"  File type: {results_filtered[0]['metadata'].get('file_type', 'N/A')}")
        print(f"  Score: {results_filtered[0]['score']:.4f}")

if __name__ == "__main__":
    test_filtering()
