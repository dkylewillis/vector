"""Simplified vector database for Vector."""

from qdrant_client import QdrantClient
from qdrant_client.models import (Distance, VectorParams, PointStruct, Filter, 
                                  PayloadSchemaType, CreateFieldIndex)
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import uuid

from ..config import Config
from ..interfaces import SearchResult
from ..exceptions import DatabaseError
from .collection_manager import CollectionManager


# Forward declaration for type hints
class Chunk:
    """Forward declaration for Chunk class."""
    pass

# Module-level shared client instance
_shared_client = None
_shared_config_hash = None


def _get_shared_client(config: Config) -> QdrantClient:
    """Get or create shared Qdrant client instance."""
    global _shared_client, _shared_config_hash
    
    # Create a hash of the config to detect if it changed
    config_hash = hash((
        config.use_cloud_qdrant,
        config.vector_db_url,
        config.vector_db_api_key,
        config.vector_db_path
    ))
    
    # Create new client if none exists or config changed
    if _shared_client is None or _shared_config_hash != config_hash:
        
        if _shared_client is not None:
            # Close the old client if it exists
            try:
                _shared_client.close()
            except:
                pass
        
        _shared_client = _create_client(config)
        _shared_config_hash = config_hash
    
    return _shared_client


def _create_client(config: Config) -> QdrantClient:
    """Create Qdrant client based on configuration."""
    # Use cloud Qdrant if URL is configured
    if config.use_cloud_qdrant:
        url = config.vector_db_url
        api_key = config.vector_db_api_key
        
        if api_key:
            return QdrantClient(url=url, api_key=api_key)
        else:
            # For public instances or if API key not needed
            return QdrantClient(url=url)
    else:
        # Fall back to local storage
        db_path = config.vector_db_path
        path = Path(db_path)
        path.mkdir(parents=True, exist_ok=True)
        return QdrantClient(path=str(path))


def close_shared_client():
    """Close the shared client instance."""
    global _shared_client, _shared_config_hash
    if _shared_client is not None:
        try:
            _shared_client.close()
        except Exception:
            pass
        _shared_client = None
        _shared_config_hash = None


class VectorDatabase:
    """Simplified vector database using Qdrant."""

    def __init__(self, collection_name: str, config: Config, collection_manager: Optional[CollectionManager] = None):
        """Initialize the vector database.

        Args:
            collection_name: Name of the collection (can be display name or actual collection name)
            config: Configuration object
            collection_manager: Optional collection manager for name resolution
        """
        self.collection_manager = collection_manager
        
        # Store the original collection name (could be display name or actual name)
        self.original_collection_name = collection_name
        
        # Resolve collection name if using collection manager and it looks like a display name
        if collection_manager and not collection_name.startswith('c_'):
            # Try to get pair info by display name
            pair_info = collection_manager.get_pair_by_display_name(collection_name)
            if pair_info:
                # Default to chunks collection if no specific type specified
                collection_name = pair_info['chunks_collection']
            # If not found as display name, assume it's an actual collection name
        
        # Store the resolved collection name (preserve case for Qdrant operations)
        self.collection_name = collection_name
        self.config = config
        self.client = _get_shared_client(config)

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

    def delete_documents(self, metadata_filter: Dict[str, Any]) -> int:
        """Delete documents from the collection based on metadata filter.

        Args:
            metadata_filter: Metadata filter to identify documents to delete

        Returns:
            Number of documents deleted

        Raises:
            DatabaseError: If deletion fails
        """
        if not metadata_filter:
            raise ValueError("metadata_filter cannot be empty for safety")

        try:
            filter_conditions = self._build_filter(metadata_filter)
            
            if filter_conditions is None:
                raise ValueError("Invalid metadata filter")

            # Delete points matching the filter
            result = self.client.delete(
                collection_name=self.collection_name,
                points_selector=filter_conditions
            )
            
            # Return the operation status - Qdrant returns an UpdateResult
            return getattr(result, 'operation_id', 0)
            
        except Exception as e:
            raise DatabaseError(f"Failed to delete documents: {e}")


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

    def store_chunks_batch(self, chunks_with_embeddings: List[Tuple['Chunk', List[float]]], 
                          batch_size: int = 100) -> None:
        """Store chunks and embeddings in batches.
        
        Args:
            chunks_with_embeddings: List of tuples (chunk, embedding_vector)
            batch_size: Number of chunks to process in each batch
        """
        if not chunks_with_embeddings:
            return
        
        # Process in batches
        for i in range(0, len(chunks_with_embeddings), batch_size):
            batch = chunks_with_embeddings[i:i + batch_size]
            texts = [chunk.text for chunk, _ in batch]
            vectors = [embedding for _, embedding in batch]
            metadata = [chunk.metadata.model_dump() for chunk, _ in batch]
            
            # Add to vector database
            self.add_documents(texts, vectors, metadata)
            print(f"📦 Stored batch: {len(batch)} chunks")

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

    def delete_collection(self) -> None:
        """Delete the entire collection and its metadata."""
        try:
            if self.collection_exists():
                # Delete from Qdrant
                self.client.delete_collection(self.collection_name)
        except Exception as e:
            raise DatabaseError(f"Failed to delete collection: {e}")

    def clear_collection(self) -> None:
        """Clear all documents from the collection (but keep the collection structure)."""
        try:
            if self.collection_exists():
                # Delete all points by scrolling through and deleting them
                # This is safer than trying to create a "match all" filter
                scroll_result = self.client.scroll(
                    collection_name=self.collection_name,
                    limit=10000,  # Process in batches
                    with_payload=False,
                    with_vectors=False
                )
                
                points, next_page_offset = scroll_result
                all_point_ids = [point.id for point in points]
                
                # Continue scrolling if there are more points
                while next_page_offset:
                    scroll_result = self.client.scroll(
                        collection_name=self.collection_name,
                        limit=10000,
                        offset=next_page_offset,
                        with_payload=False,
                        with_vectors=False
                    )
                    points, next_page_offset = scroll_result
                    all_point_ids.extend([point.id for point in points])
                
                # Delete all points if any were found
                if all_point_ids:
                    self.client.delete(
                        collection_name=self.collection_name,
                        points_selector=all_point_ids
                    )
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
        # Don't close the shared client from individual instances
        pass


