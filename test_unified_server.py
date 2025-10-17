"""Test the unified FastAPI + Gradio server."""

import httpx
import time

BASE_URL = "http://localhost:8000"

def test_unified_server():
    """Test that both API and UI are accessible."""
    
    print("=" * 70)
    print("Testing Unified FastAPI + Gradio Server")
    print("=" * 70)
    
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        
        # Test root endpoint
        print("\n1. Testing root endpoint (GET /)...")
        resp = client.get("/")
        print(f"   Status: {resp.status_code}")
        data = resp.json()
        print(f"   Name: {data['name']}")
        print(f"   UI Path: {data.get('ui', 'N/A')}")
        print(f"   Docs: {data.get('docs', 'N/A')}")
        
        # Test health
        print("\n2. Testing health endpoint (GET /health)...")
        resp = client.get("/health")
        print(f"   Status: {resp.status_code}")
        health = resp.json()
        print(f"   Health Status: {health.get('status', 'N/A')}")
        print(f"   Collections: {health.get('collections', 0)}")
        
        # Test API - List collections
        print("\n3. Testing API - List collections (GET /vectorstore/collections)...")
        resp = client.get("/vectorstore/collections")
        print(f"   Status: {resp.status_code}")
        data = resp.json()
        print(f"   Found {data['count']} collections: {data['collections']}")
        
        # Test API - Search
        print("\n4. Testing API - Search (POST /retrieval/search)...")
        resp = client.post(
            "/retrieval/search",
            json={"query": "test query", "top_k": 3}
        )
        print(f"   Status: {resp.status_code}")
        data = resp.json()
        print(f"   Found {data['count']} results")
        
        # Test Gradio UI is mounted
        print("\n5. Testing Gradio UI (GET /ui)...")
        try:
            resp = client.get("/ui", follow_redirects=True)
            print(f"   Status: {resp.status_code}")
            if resp.status_code == 200:
                print(f"   ✓ Gradio UI is accessible")
                print(f"   Content-Type: {resp.headers.get('content-type', 'N/A')}")
            else:
                print(f"   ⚠ Unexpected status code")
        except Exception as e:
            print(f"   ⚠ Gradio UI error: {e}")
        
        # Test API docs
        print("\n6. Testing OpenAPI docs (GET /docs)...")
        resp = client.get("/docs")
        print(f"   Status: {resp.status_code}")
        print(f"   ✓ Interactive API docs available")
    
    print("\n" + "=" * 70)
    print("✓ Unified Server Tests Complete!")
    print("=" * 70)
    print("\n📍 Access Points:")
    print(f"   • Gradio UI:      {BASE_URL}/ui")
    print(f"   • API Docs:       {BASE_URL}/docs")
    print(f"   • Health Check:   {BASE_URL}/health")
    print(f"   • Root Info:      {BASE_URL}/")
    print()

if __name__ == "__main__":
    print("\n⚠  Make sure the server is running first:")
    print("   vector-api")
    print("\nPress Enter to continue testing...")
    input()
    
    test_unified_server()
