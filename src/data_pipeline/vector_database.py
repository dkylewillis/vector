from qdrant_client import QdrantClient
import qdrant_client
from qdrant_client.models import (Distance, VectorParams, PointStruct,
                                  FilterSelector, Filter)
import numpy as np
from typing import List, Dict, Any, Optional, Union
import uuid
from pathlib import Path
import yaml

from dotenv import load_dotenv
import os

load_dotenv()

# Load vector database settings from YAML config
with open("./config/settings.yaml", "r", encoding="utf-8") as f:
    _vector_db_config = yaml.safe_load(f).get("vector_database", {})

QDRANT_LOCAL_PATH = _vector_db_config.get("local_path", None)
QDRANT_URL = os.getenv("QDRANT_API_URL")

# Initialize client at module level
if QDRANT_URL is None or QDRANT_LOCAL_PATH is not None:
    # Use local mode
    path = Path(QDRANT_LOCAL_PATH or "./qdrant_db")
    path.mkdir(parents=True, exist_ok=True)
    CLIENT = QdrantClient(path=str(path))
    STORAGE_MODE = "local"
    print(f"🔧 Using local Qdrant storage at: {path}")
else:
    # Use cloud mode with proper configuration
    api_key = os.getenv("QDRANT_API_KEY")
    if not api_key:
        print(f"⚠️  Warning: No API key found for {'QDRANT_API_KEY'}")
        print("🔄 Falling back to local mode...")
        path = Path("./qdrant_db")
        path.mkdir(parents=True, exist_ok=True)
        CLIENT = QdrantClient(path=str(path))
        STORAGE_MODE = "local"
    else:
        try:
            CLIENT = QdrantClient(
                url=QDRANT_URL,
                api_key=api_key,
                timeout=60,  # Set timeout to 30 seconds
                prefer_grpc=False,  # Use HTTP instead of gRPC
            )
            STORAGE_MODE = "server"
            print(f"🌐 Using Qdrant cloud at: {QDRANT_URL}")
        except Exception as e:
            print(f"❌ Cloud connection failed: {e}")
            print("🔄 Falling back to local mode...")
            path = Path("./qdrant_db")
            path.mkdir(parents=True, exist_ok=True)
            CLIENT = QdrantClient(path=str(path))
            STORAGE_MODE = "local"


class VectorDatabase:
    """
    A simple vector database service using Qdrant.
    Supports both server-based and local file-based persistence.
    """

    def __init__(self, collection_name: str = "chunks"):
        """
        Initialize the vector database connection.
        Args:
            collection_name: Name of the collection to use
        """
        self.collection_name = collection_name.lower()
        self.client = CLIENT
        self.storage_mode = STORAGE_MODE

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
        except Exception as e:
            error_str = str(e).lower()
            if "timeout" in error_str or "timed out" in error_str:
                print(f"❌ Connection timeout while checking collections")
                print(f"💡 Try switching to local mode in settings.yaml")
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

    def add_chunks(self,
                   texts: List[str],
                   embeddings: np.ndarray,
                   metadata: Optional[List[Dict[str, Any]]] = None) -> List[str]:
        """
        Add text chunks with their embeddings to the vector database.

        Args:
            texts: List of chunk texts
            embeddings: Corresponding embeddings as numpy array
            metadata: Optional metadata for each chunk

        Returns:
            List of chunk IDs
        """
        if metadata is None:
            metadata = [{"text": text} for text in texts]

        # Auto-create indexes for cloud mode
        if self.storage_mode == "server" and metadata:
            self._index_metadata(metadata[0])

        # Generate unique IDs for each chunk
        chunk_ids = [str(uuid.uuid4()) for _ in texts]

        # Create points for Qdrant
        points = []
        for i, (chunk_id, text, embedding) in enumerate(zip(chunk_ids, texts, embeddings)):
            payload = metadata[i] if i < len(metadata) else {"text": text}
            payload["text"] = text  # Ensure text is always included

            points.append(
                PointStruct(
                    id=chunk_id,
                    vector=embedding.tolist() if isinstance(
                        embedding,
                        np.ndarray) else embedding,
                    payload=payload))

        # Insert points into collection with error handling
        try:
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            print(
                f"✅ Added {
                    len(points)} chunks to collection '{
                    self.collection_name}'")
            return chunk_ids
        except Exception as e:
            error_str = str(e).lower()
            if "timeout" in error_str or "timed out" in error_str:
                print(f"❌ Connection timeout while adding chunks")
                print(f"💡 Try switching to local mode in settings.yaml:")
                print(f"   Set url: null and local_path: './qdrant_db'")
            elif "connection" in error_str or "refused" in error_str:
                print(f"❌ Connection refused. Check your Qdrant configuration.")
                print(f"💡 Try switching to local mode in settings.yaml")
            else:
                print(f"❌ Error adding chunks: {e}")
            raise e

    def search(self,
               query_embedding: np.ndarray,
               top_k: int = 5,
               score_threshold: Optional[float] = None,
               metadata_filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Search for similar chunks using a query embedding.

        Args:
            query_embedding: Query vector as numpy array
            top_k: Number of top results to return
            score_threshold: Minimum similarity score threshold
            metadata_filter: Optional dict to filter by metadata (e.g., {"filename": "doc.pdf"})

        Returns:
            List of search results with scores and metadata
        """
        search_params = {
            "collection_name": self.collection_name,
            "query_vector": query_embedding.tolist() if isinstance(
                query_embedding,
                np.ndarray) else query_embedding,
            "limit": top_k}

        if score_threshold is not None:
            search_params["score_threshold"] = score_threshold

        # Add metadata filtering if provided
        if metadata_filter:
            from qdrant_client.models import Filter, FieldCondition, MatchValue, MatchAny
            
            conditions = []
            for key, value in metadata_filter.items():
                if isinstance(value, list) and len(value) > 1:
                    # Multiple values - use MatchAny for OR logic within the same field
                    # Ensure all values are simple types
                    valid_values = [v for v in value if isinstance(v, (str, int, float, bool))]
                    if valid_values:
                        conditions.append(
                            FieldCondition(
                                key=key,
                                match=MatchAny(any=valid_values)
                            )
                        )
                elif isinstance(value, list) and len(value) == 1:
                    # Single value in list
                    if isinstance(value[0], (str, int, float, bool)):
                        conditions.append(
                            FieldCondition(
                                key=key,
                                match=MatchValue(value=value[0])
                            )
                        )
                elif isinstance(value, (str, int, float, bool)):
                    # Single value
                    conditions.append(
                        FieldCondition(
                            key=key,
                            match=MatchValue(value=value)
                        )
                    )
                else:
                    print(f"⚠️  Skipping invalid filter value for {key}: {type(value)} - {value}")
            
            if conditions:  # Only add filter if we have valid conditions
                search_params["query_filter"] = Filter(must=conditions)

        try:
            results = self.client.search(**search_params)
        except Exception as e:
            if "Index required" in str(e) and metadata_filter:
                print("⚠️  Metadata filtering not supported, searching all chunks...")
                search_params.pop("query_filter", None)
                results = self.client.search(**search_params)
            else:
                raise

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

    def clear_chunks(self):
        """Clear all chunks from the collection while keeping the
        collection structure."""
        try:
            # Delete all points from the collection
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=True  # This deletes all points
            )
            print(f"All chunks cleared from collection "
                  f"'{self.collection_name}'")
        except Exception as e:
            print(f"Error clearing chunks: {e}")

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
                "vector_size": info.config.params.vectors.size,
                "storage_mode": self.storage_mode,
            }
        except Exception as e:
            print(f"Error getting collection info: {e}")
            return {}

    def _index_metadata(self, sample_metadata: Dict[str, Any]):
        """Create indexes for metadata fields."""
        try:
            from qdrant_client.models import PayloadSchemaType
            
            for field_name in sample_metadata.keys():
                if field_name == "text":
                    continue  # Skip text field
                
                try:
                    self.client.create_payload_index(
                        collection_name=self.collection_name,
                        field_name=field_name,
                        field_schema=PayloadSchemaType.KEYWORD
                    )
                except Exception:
                    pass  # Index already exists or failed - continue
                    
        except Exception:
            pass  # Indexing failed - filtering won't work but that's ok

    def get_metadata_summary(self) -> Dict[str, Any]:
        """Get summary of all metadata in the collection."""
        if not self.collection_exists():
            return {"error": "Collection does not exist"}
        
        try:
            # Get all points with metadata
            result = self.client.scroll(
                collection_name=self.collection_name,
                limit=10000,
                with_payload=True,
                with_vectors=False
            )
            
            points = result[0]
            
            # Collect unique values
            filenames = set()
            sources = set()
            file_types = set()
            headings = set()
            
            for point in points:
                payload = point.payload
                
                if 'filename' in payload:
                    filenames.add(payload['filename'])
                if 'source' in payload:
                    sources.add(payload['source'])
                if 'file_type' in payload:
                    file_types.add(payload['file_type'])
                if 'headings' in payload:
                    heading_data = payload['headings']
                    if isinstance(heading_data, list):
                        for h in heading_data:
                            if isinstance(h, str):
                                headings.add(h)
                            elif isinstance(h, dict) and 'text' in h:
                                headings.add(h['text'])
            
            return {
                "total_chunks": len(points),
                "filenames": sorted(list(filenames)),
                "sources": sorted(list(sources)),
                "file_types": sorted(list(file_types)),
                "headings": sorted(list(headings))
            }
            
        except Exception as e:
            return {"error": f"Failed to get metadata: {e}"}

    def get_all_collections(self) -> List[str]:
        """Get list of all collection names."""
        try:
            collections = self.client.get_collections().collections
            return [col.name for col in collections]
        except Exception as e:
            print(f"Error getting collections: {e}")
            return []
