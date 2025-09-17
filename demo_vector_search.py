#!/usr/bin/env python3
"""
Demonstration script for vector store operations:
1. Creates a collection
2. Adds dummy documents with document_id payload
3. Searches using search_documents method
"""

import sys
import os
import numpy as np
import uuid

# Add the vector core directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'vector', 'core'))

try:
    from vector.core.vector_store import VectorStore
    
    def generate_dummy_vector(size: int = 384) -> list[float]:
        """Generate a random dummy vector of specified size."""
        return np.random.rand(size).tolist()

    def main():
        """Main demonstration function."""
        print("=== Vector Store Demonstration ===\n")
        
        # Initialize vector store
        vector_store = VectorStore()
        collection_name = "demo_collection"
        vector_size = 384
        
        print(f"1. Creating collection '{collection_name}'...")
        vector_store.create_collection(collection_name, vector_size)
        
        print(f"2. Current collections: {vector_store.list_collections()}\n")
        
        # Create dummy documents with document_id payload
        dummy_documents = [
            {
                "point_id": str(uuid.uuid4()),
                "document_id": "doc_001",
                "title": "Introduction to Machine Learning",
                "content": "Machine learning is a subset of artificial intelligence...",
                "category": "technology"
            },
            {
                "point_id": str(uuid.uuid4()),
                "document_id": "doc_002",
                "title": "Data Science Fundamentals", 
                "content": "Data science combines statistics, programming, and domain expertise...",
                "category": "technology"
            },
            {
                "point_id": str(uuid.uuid4()),
                "document_id": "doc_003",
                "title": "Python Programming Guide",
                "content": "Python is a versatile programming language...",
                "category": "programming"
            },
            {
                "point_id": str(uuid.uuid4()),
                "document_id": "doc_004",
                "title": "Web Development Basics",
                "content": "Web development involves creating websites and web applications...",
                "category": "programming"
            },
            {
                "point_id": str(uuid.uuid4()),
                "document_id": "doc_005",
                "title": "Database Design Principles",
                "content": "Database design is crucial for efficient data storage and retrieval...",
                "category": "database"
            }
        ]
        
        print("3. Adding dummy documents to collection...")
        for doc in dummy_documents:
            # Generate a random vector for each document
            vector = generate_dummy_vector(vector_size)
            
            # Prepare payload (everything except point_id which is used as the point identifier)
            payload = {k: v for k, v in doc.items() if k != "point_id"}
            
            # Insert the point
            vector_store.insert(
                collection_name=collection_name,
                point_id=doc["point_id"],
                vectors=vector,
                payload=payload
            )
        
        print("\n4. Documents added successfully!\n")
        
        # Demonstrate search_documents method
        print("5. Demonstrating search_documents method...")
        
        # Generate a query vector
        query_vector = generate_dummy_vector(vector_size)
        
        # Search for specific document IDs
        target_document_ids = ["doc_001", "doc_003", "doc_005"]
        print(f"Searching for documents with IDs: {target_document_ids}")
        
        try:
            search_results = vector_store.search_documents(
                query_vector=query_vector,
                collection=collection_name,
                top_k=3,
                document_ids=target_document_ids
            )
            
            print(f"\nFiltered Search Results ({len(search_results)} found):")
            print("-" * 60)
            
            for i, result in enumerate(search_results, 1):
                print(f"Result {i}:")
                print(f"  Point ID: {result.id}")
                print(f"  Score: {result.score:.4f}")
                print(f"  Document ID: {result.payload.get('document_id', 'N/A')}")
                print(f"  Title: {result.payload.get('title', 'N/A')}")
                print(f"  Category: {result.payload.get('category', 'N/A')}")
                print()
                
        except Exception as e:
            print(f"Error during search: {e}")
        
        # Demonstrate regular search (without document_id filter)
        print("6. Comparing with regular search (no document_id filter)...")
        try:
            regular_results = vector_store.search(
                query_vector=query_vector,
                collection=collection_name,
                top_k=5
            )
            
            print(f"\nRegular Search Results ({len(regular_results)} found):")
            print("-" * 60)
            
            for i, result in enumerate(regular_results, 1):
                print(f"Result {i}:")
                print(f"  Point ID: {result.id}")
                print(f"  Score: {result.score:.4f}")
                print(f"  Document ID: {result.payload.get('document_id', 'N/A')}")
                print(f"  Title: {result.payload.get('title', 'N/A')}")
                print()
                
        except Exception as e:
            print(f"Error during regular search: {e}")
        
        # Cleanup
        print("7. Cleaning up...")
        vector_store.delete_collection(collection_name)
        print(f"Collection '{collection_name}' deleted.")
        
        print(f"\nFinal collections: {vector_store.list_collections()}")
        print("\n=== Demonstration Complete ===")

    if __name__ == "__main__":
        main()
        
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running from the correct directory.")