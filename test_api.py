"""Quick test script for Vector API endpoints."""

import httpx
import json

BASE_URL = "http://localhost:8000"

def test_api():
    """Test Vector API endpoints."""
    
    print("=" * 60)
    print("Testing Vector API")
    print("=" * 60)
    
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        # Test root endpoint
        print("\n1. Testing root endpoint (GET /)...")
        resp = client.get("/")
        print(f"   Status: {resp.status_code}")
        print(f"   Response: {json.dumps(resp.json(), indent=2)}")
        
        # Test health endpoint
        print("\n2. Testing health endpoint (GET /health)...")
        resp = client.get("/health")
        print(f"   Status: {resp.status_code}")
        print(f"   Response: {json.dumps(resp.json(), indent=2)}")
        
        # Test list collections
        print("\n3. Testing list collections (GET /vectorstore/collections)...")
        resp = client.get("/vectorstore/collections")
        print(f"   Status: {resp.status_code}")
        print(f"   Response: {json.dumps(resp.json(), indent=2)}")
        
        # Test list documents
        print("\n4. Testing list documents (GET /vectorstore/documents)...")
        resp = client.get("/vectorstore/documents?limit=5")
        print(f"   Status: {resp.status_code}")
        data = resp.json()
        print(f"   Found {data['count']} documents")
        if data['documents']:
            print(f"   First document: {data['documents'][0]['document_id']}")
        
        # Test search (GET)
        print("\n5. Testing search GET endpoint (GET /retrieval/search)...")
        resp = client.get("/retrieval/search?query=zoning&top_k=3")
        print(f"   Status: {resp.status_code}")
        data = resp.json()
        print(f"   Found {data['count']} results")
        if data['results']:
            print(f"   Top result score: {data['results'][0]['score']:.4f}")
        
        # Test search (POST)
        print("\n6. Testing search POST endpoint (POST /retrieval/search)...")
        search_body = {
            "query": "building permits",
            "top_k": 3,
            "window": 0
        }
        resp = client.post("/retrieval/search", json=search_body)
        print(f"   Status: {resp.status_code}")
        data = resp.json()
        print(f"   Found {data['count']} results")
        
        # Test OpenAPI docs
        print("\n7. Testing OpenAPI docs (GET /docs)...")
        resp = client.get("/docs")
        print(f"   Status: {resp.status_code}")
        print(f"   Content-Type: {resp.headers.get('content-type')}")
        
    print("\n" + "=" * 60)
    print("✓ All API tests completed successfully!")
    print("=" * 60)
    print("\n📚 Interactive documentation available at:")
    print(f"   Swagger UI: {BASE_URL}/docs")
    print(f"   ReDoc:      {BASE_URL}/redoc")
    print()

if __name__ == "__main__":
    test_api()
