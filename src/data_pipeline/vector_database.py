from qdrant_client import QdrantClient
import qdrant_client
from qdrant_client.models import Distance, VectorParams, PointStruct, FilterSelector, Filter
import numpy as np
from typing import List, Dict, Any, Optional, Union
import uuid
from pathlib import Path
import yaml


# Load vector database settings from YAML config
with open("./config/settings.yaml", "r", encoding="utf-8") as f:
    _vector_db_config = yaml.safe_load(f).get("vector_database", {})

QDRANT_LOCAL_PATH = _vector_db_config.get("local_path", "./qdrant_data")
QDRANT_HOST = _vector_db_config.get("host", "localhost")
QDRANT_PORT = _vector_db_config.get("port", 6333)

if QDRANT_LOCAL_PATH is not None or QDRANT_HOST is None:
    path = Path(QDRANT_LOCAL_PATH)
    path.mkdir(parents=True, exist_ok=True)
    client =  QdrantClient(path=str(path))
else:
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

class VectorDatabase:
    """
    A simple vector database service using Qdrant.
    Supports both server-based and local file-based persistence.
    """

    def __init__(self, collection_name: str = "documents"):
        """
        Initialize the vector database connection.
        Args:
            collection_name: Name of the collection to use
        """
        self.collection_name = collection_name

        self.client = client
        self.storage_mode = "local" if QDRANT_LOCAL_PATH is not None or QDRANT_HOST is None else "server"

    def close(self):
        """Close this database connection."""
        try:
            self.client.close()
        except Exception:
            pass

    def collection_exists(self) -> bool:
        """Check if the collection exists."""
        try:
            collections = self.client.get_collections().collections
            return any(col.name == self.collection_name for col in collections)
        except:
            return False
    
    def create_collection(self, vector_size: int, distance: Distance = Distance.COSINE):
        """Create collection only if it doesn't exist."""
        if self.collection_exists():
            return  # Collection already exists, nothing to do
        
        try:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=vector_size, distance=distance)
            )
            print(f"Collection '{self.collection_name}' created successfully")
        except Exception as e:
            print(f"Error creating collection: {e}")
    
    def add_documents(self, 
                     texts: List[str], 
                     embeddings: np.ndarray, 
                     metadata: Optional[List[Dict[str, Any]]] = None) -> List[str]:
        """
        Add documents with their embeddings to the vector database.
        
        Args:
            texts: List of document texts
            embeddings: Corresponding embeddings as numpy array
            metadata: Optional metadata for each document
            
        Returns:
            List of document IDs
        """
        if metadata is None:
            metadata = [{"text": text} for text in texts]
        
        # Generate unique IDs for each document
        doc_ids = [str(uuid.uuid4()) for _ in texts]
        
        # Create points for Qdrant
        points = []
        for i, (doc_id, text, embedding) in enumerate(zip(doc_ids, texts, embeddings)):
            payload = metadata[i] if i < len(metadata) else {"text": text}
            payload["text"] = text  # Ensure text is always included
            
            points.append(PointStruct(
                id=doc_id,
                vector=embedding.tolist() if isinstance(embedding, np.ndarray) else embedding,
                payload=payload
            ))
        
        # Insert points into collection
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
        
        print(f"Added {len(points)} documents to collection '{self.collection_name}'")
        return doc_ids
    
    def search(self, 
               query_embedding: np.ndarray, 
               top_k: int = 5, 
               score_threshold: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Search for similar documents using a query embedding.
        
        Args:
            query_embedding: Query vector as numpy array
            top_k: Number of top results to return
            score_threshold: Minimum similarity score threshold
            
        Returns:
            List of search results with scores and metadata
        """
        search_params = {
            "collection_name": self.collection_name,
            "query_vector": query_embedding.tolist() if isinstance(query_embedding, np.ndarray) else query_embedding,
            "limit": top_k
        }
        
        if score_threshold is not None:
            search_params["score_threshold"] = score_threshold
        
        results = self.client.search(**search_params)
        
        # Format results
        formatted_results = []
        for result in results:
            formatted_results.append({
                "id": result.id,
                "score": result.score,
                "text": result.payload.get("text", ""),
                "metadata": result.payload
            })
        
        return formatted_results
    
    def delete_collection(self):
        """
        Delete the collection from Qdrant.
        """
        try:
            self.client.delete_collection(collection_name=self.collection_name)
            print(f"Collection '{self.collection_name}' deleted successfully")
        except Exception as e:
            print(f"Error deleting collection: {e}")

    def clear_documents(self):
        """Clear all documents from the collection while keeping the collection structure."""
        try:
            # Delete all points from the collection
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=True  # This deletes all points
            )
            print(f"All documents cleared from collection '{self.collection_name}'")
        except Exception as e:
            print(f"Error clearing documents: {e}")
    
    def get_collection_info(self) -> Dict[str, Any]:
        """
        Get information about the collection.
        
        Returns:
            Collection information
        """
        try:
            info = self.client.get_collection(collection_name=self.collection_name)
            return {
                "name": self.collection_name,
                "points_count": info.points_count,
                "status": info.status,
                "vector_size": info.config.params.vectors.size
            }
        except Exception as e:
            print(f"Error getting collection info: {e}")
            return {}

# Example usage
if __name__ == "__main__":
    print("=== Testing Local File Storage ===")
    # Initialize vector database with local storage
    vector_db = VectorDatabase(collection_name="test_documents")
    
    # Create collection (assuming 384-dimensional embeddings)
    vector_db.create_collection(vector_size=384)
    
    # Example documents and embeddings
    documents = [
        "This document is about zoning regulations.",
        "Building codes and construction requirements are important.",
        "Environmental protection policies must be followed."
    ]
    
    # Mock embeddings (in real usage, you'd get these from your embedder)
    embeddings = np.random.rand(3, 384)
    
    # Add documents to the database
    
    #doc_ids = vector_db.add_documents(documents, embeddings)
    #print(f"Added documents with IDs: {doc_ids}")
    
    # Search for similar documents
    query_embedding = np.random.rand(384)
    results = vector_db.search(query_embedding, top_k=2)
    
    print("\nSearch results:")
    for result in results:
        print(f"Score: {result['score']:.4f}")
        print(f"Text: {result['text']}")
        print("---")
    
    # Get collection info
    info = vector_db.get_collection_info()
    print(f"\nCollection info: {info}")
    
    print(f"\nStorage mode: {vector_db.storage_mode}")
    if vector_db.storage_mode == "local":
        print(f"Local storage path: {QDRANT_LOCAL_PATH}")
    
    print("\n=== Configuration ===")
    print("# Storage settings are configured in config/settings.yaml")
    print("# All VectorDatabase instances share the same client connection")
    print("# Multiple collections can use the same underlying storage")
