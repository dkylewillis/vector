"""Simple test script for ResearchAgent."""

import sys
import os
from pathlib import Path

# Add the vector package to the path
sys.path.insert(0, str(Path(__file__).parent))

from vector.config import Config
from vector.core.agent import ResearchAgent
from vector.core.collection_manager import CollectionManager
from vector.exceptions import VectorError, AIServiceError


def test_agent_initialization():
    """Test basic agent initialization."""
    print("🧪 Testing agent initialization...")
    
    try:
        # Load config
        config = Config()
        
        # Initialize collection manager (optional)
        collection_manager = CollectionManager(config)
        
        # Test collection name - adjust this to match your actual collection
        test_collection = "Coweta"
        
        # Initialize agent
        agent = ResearchAgent(config, test_collection, collection_manager)
        
        print(f"✅ Agent initialized successfully")
        print(f"   Collection: {agent.collection_name}")
        print(f"   Config loaded: {config is not None}")
        
        return agent
        
    except Exception as e:
        print(f"❌ Agent initialization failed: {e}")
        return None


def test_model_info(agent):
    """Test model information retrieval."""
    print("\n🧪 Testing model info...")
    
    try:
        model_info = agent.get_model_info()
        print("✅ Model info retrieved:")
        print(f"   {model_info}")
        
    except Exception as e:
        print(f"❌ Model info test failed: {e}")


def test_search(agent):
    """Test search functionality."""
    print("\n🧪 Testing search functionality...")
    
    test_queries = [
        "building permits",
        "zoning regulations",
        "parking requirements"
    ]
    
    for query in test_queries:
        try:
            print(f"\n   Searching for: '{query}'")
            results = agent.search(query, top_k=3)
            
            if results:
                print(f"✅ Search successful")
                print(f"   Results preview: {results[:200]}...")
            else:
                print(f"⚠️  No results found for '{query}'")
                
        except VectorError as e:
            print(f"❌ Search failed for '{query}': {e}")
        except Exception as e:
            print(f"❌ Unexpected error searching for '{query}': {e}")


def test_ask(agent):
    """Test AI question functionality."""
    print("\n🧪 Testing ask functionality...")
    
    test_questions = [
        "What are the basic requirements for building permits?",
        "Are there any parking regulations mentioned?",
        "What zoning information is available?"
    ]
    
    for question in test_questions:
        try:
            print(f"\n   Asking: '{question}'")
            response = agent.ask(question, response_length='short')
            
            if response:
                print(f"✅ AI response received")
                print(f"   Response preview: {response[:200]}...")
            else:
                print(f"⚠️  Empty response for question")
                
        except AIServiceError as e:
            print(f"❌ AI service error for question: {e}")
        except VectorError as e:
            print(f"❌ Vector error for question: {e}")
        except Exception as e:
            print(f"❌ Unexpected error for question: {e}")


def test_edge_cases(agent):
    """Test edge cases and error handling."""
    print("\n🧪 Testing edge cases...")
    
    # Test empty query
    try:
        agent.search("")
        print("❌ Empty search should have failed")
    except VectorError:
        print("✅ Empty search properly rejected")
    except Exception as e:
        print(f"❌ Unexpected error for empty search: {e}")
    
    # Test empty question
    try:
        agent.ask("")
        print("❌ Empty question should have failed")
    except VectorError:
        print("✅ Empty question properly rejected")
    except Exception as e:
        print(f"❌ Unexpected error for empty question: {e}")
    
    # Test with metadata filter
    try:
        results = agent.search("test query", metadata_filter={"source": "test_doc"})
        print("✅ Search with metadata filter completed")
    except Exception as e:
        print(f"⚠️  Search with metadata filter failed: {e}")


def test_response_lengths(agent):
    """Test different response lengths."""
    print("\n🧪 Testing response lengths...")
    
    test_question = "What information is available about regulations?"
    
    for length in ['short', 'medium', 'long']:
        try:
            print(f"\n   Testing '{length}' response...")
            response = agent.ask(test_question, response_length=length)
            
            if response:
                print(f"✅ {length.capitalize()} response received ({len(response)} chars)")
            else:
                print(f"⚠️  Empty {length} response")
                
        except Exception as e:
            print(f"❌ {length.capitalize()} response test failed: {e}")


def main():
    """Run all tests."""
    print("🚀 Starting ResearchAgent tests...\n")
    
    # Test initialization
    agent = test_agent_initialization()
    
    if not agent:
        print("\n❌ Cannot proceed with tests - agent initialization failed")
        return
    
    # Run tests
    test_model_info(agent)
    test_search(agent)
    test_ask(agent)
    test_edge_cases(agent)
    test_response_lengths(agent)
    
    print("\n🏁 Tests completed!")
    print("\nNote: Some tests may show warnings if:")
    print("   - No documents are in the collection")
    print("   - AI services are not configured")
    print("   - Collection doesn't exist")


if __name__ == "__main__":
    main()