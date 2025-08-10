"""Simplified vector database for Vector."""

from qdrant_client import QdrantClient
from qdrant_client.models import (Distance, VectorParams, PointStruct, Filter, 
                                  PayloadSchemaType, CreateFieldIndex)
from pathlib import Path
from typing import List, Dict, Any, Optional
import uuid

from ..config import Config
from ..interfaces import SearchResult
from ..exceptions import DatabaseError


class VectorDatabase:
    """Simplified vector database using Qdrant."""

    def __init__(self, collection_name: str, config: Config):
        """Initialize the vector database.

        Args:
            collection_name: Name of the collection
            config: Configuration object
        """
        self.collection_name = collection_name.lower()
        self.config = config
        self.client = self._create_client()

    def _create_client(self) -> QdrantClient:
        """Create Qdrant client based on configuration."""
        # Use cloud Qdrant if URL is configured
        if self.config.use_cloud_qdrant:
            url = self.config.vector_db_url
            api_key = self.config.vector_db_api_key
            
            if api_key:
                return QdrantClient(url=url, api_key=api_key)
            else:
                # For public instances or if API key not needed
                return QdrantClient(url=url)
        else:
            # Fall back to local storage
            db_path = self.config.vector_db_path
            path = Path(db_path)
            path.mkdir(parents=True, exist_ok=True)
            return QdrantClient(path=str(path))

    def collection_exists(self) -> bool:
        """Check if the collection exists."""
        try:
            collections = self.client.get_collections().collections
            return any(col.name == self.collection_name for col in collections)
        except Exception as e:
            raise DatabaseError(f"Failed to check collection existence: {e}")

    def create_collection(self, vector_size: int, distance: Distance = Distance.COSINE):
        """Create collection if it doesn't exist."""
        if self.collection_exists():
            return

        try:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=vector_size, distance=distance)
            )
            
            # Create indexes for metadata fields to enable filtering
            self._create_metadata_indexes()
            
        except Exception as e:
            raise DatabaseError(f"Failed to create collection: {e}")

    def _create_metadata_indexes(self):
        """Create indexes for metadata fields to enable efficient filtering."""
        try:
            # Define fields that need indexing for filtering
            index_fields = [
                ("filename", PayloadSchemaType.KEYWORD),
                ("source", PayloadSchemaType.KEYWORD),
                ("file_path", PayloadSchemaType.KEYWORD),
                ("file_hash", PayloadSchemaType.KEYWORD),
                ("headings", PayloadSchemaType.KEYWORD)  # For array of headings
            ]
            
            for field_name, field_type in index_fields:
                try:
                    self.client.create_payload_index(
                        collection_name=self.collection_name,
                        field_name=field_name,
                        field_schema=field_type
                    )
                    print(f"✅ Created index for '{field_name}' field")
                except Exception as e:
                    # Index might already exist, or field might not be used yet
                    print(f"ℹ️  Index for '{field_name}': {e}")
                    
        except Exception as e:
            print(f"⚠️  Warning: Could not create some metadata indexes: {e}")

    def ensure_indexes(self):
        """Ensure all necessary indexes exist (can be called anytime)."""
        if self.collection_exists():
            self._create_metadata_indexes()

    def add_documents(self, texts: List[str], vectors: List[List[float]], 
                     metadata: List[Dict[str, Any]]) -> None:
        """Add documents to the database.

        Args:
            texts: List of text content
            vectors: List of embedding vectors
            metadata: List of metadata dictionaries
        """
        if not (len(texts) == len(vectors) == len(metadata)):
            raise ValueError("texts, vectors, and metadata must have the same length")

        try:
            points = []
            for text, vector, meta in zip(texts, vectors, metadata):
                point_id = str(uuid.uuid4())
                # Add text to payload for retrieval
                payload = {"text": text, **meta}
                points.append(PointStruct(id=point_id, vector=vector, payload=payload))

            self.client.upsert(collection_name=self.collection_name, points=points)
        except Exception as e:
            raise DatabaseError(f"Failed to add documents: {e}")

    def search(self, query_vector: List[float], top_k: int = 5, 
               metadata_filter: Optional[Dict] = None) -> List[SearchResult]:
        """Search for similar vectors.

        Args:
            query_vector: Query vector
            top_k: Number of results to return
            metadata_filter: Optional metadata filter

        Returns:
            List of search results
        """
        try:
            filter_conditions = None
            if metadata_filter:
                filter_conditions = self._build_filter(metadata_filter)

            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=top_k,
                query_filter=filter_conditions
            )

            results = []
            for scored_point in search_result:
                payload = scored_point.payload
                text = payload.pop("text", "")
                results.append(SearchResult(
                    score=scored_point.score,
                    text=text,
                    metadata=payload
                ))

            return results
        except Exception as e:
            raise DatabaseError(f"Search failed: {e}")

    def get_collection_info(self) -> Dict[str, Any]:
        """Get collection information."""
        try:
            info = self.client.get_collection(self.collection_name)
            return {
                "name": self.collection_name,
                "status": info.status,
                "vectors_count": info.vectors_count or 0,
                "points_count": info.points_count or 0,
                "config": {
                    "distance": info.config.params.vectors.distance,
                    "size": info.config.params.vectors.size
                }
            }
        except Exception as e:
            raise DatabaseError(f"Failed to get collection info: {e}")

    def get_metadata_summary(self) -> Dict[str, Any]:
        """Get metadata summary."""
        try:
            # Simple implementation - in a real scenario you might want to scroll through all points
            scroll_result = self.client.scroll(
                collection_name=self.collection_name,
                limit=1000,  # Adjust based on your needs
                with_payload=True,
                with_vectors=False
            )

            points = scroll_result[0]
            
            # Aggregate metadata
            filenames = set()
            sources = set()
            headings = set()

            for point in points:
                payload = point.payload
                if 'filename' in payload:
                    filenames.add(payload['filename'])
                if 'source' in payload:
                    sources.add(payload['source'])
                # Handle both 'heading' and 'headings' fields
                if 'heading' in payload:
                    headings.add(payload['heading'])
                if 'headings' in payload:
                    # Handle both single strings and lists
                    heading_data = payload['headings']
                    if isinstance(heading_data, list):
                        for heading in heading_data:
                            headings.add(heading)
                    else:
                        headings.add(heading_data)

            return {
                "filenames": sorted(list(filenames)),
                "sources": sorted(list(sources)),
                "headings": sorted(list(headings)),
                "total_documents": len(points)
            }
        except Exception as e:
            raise DatabaseError(f"Failed to get metadata summary: {e}")

    def clear_collection(self) -> None:
        """Clear all documents from the collection."""
        try:
            if self.collection_exists():
                self.client.delete_collection(self.collection_name)
        except Exception as e:
            raise DatabaseError(f"Failed to clear collection: {e}")

    def _build_filter(self, metadata_filter: Dict) -> Filter:
        """Build Qdrant filter from metadata filter dict."""
        # Simple implementation - can be extended for more complex filters
        must_conditions = []
        
        for key, value in metadata_filter.items():
            if isinstance(value, list):
                # Multiple values - use "should" (OR) condition
                should_conditions = []
                for v in value:
                    should_conditions.append({"key": key, "match": {"value": v}})
                must_conditions.append({"should": should_conditions})
            else:
                # Single value
                must_conditions.append({"key": key, "match": {"value": value}})
        
        if must_conditions:
            return Filter(must=must_conditions)
        return None

    def close(self):
        """Close the database connection."""
        try:
            self.client.close()
        except Exception:
            pass
