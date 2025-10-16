"""Qdrant vector store adapter.

This module implements the BaseVectorStore interface for Qdrant,
translating the provider-agnostic DSL into Qdrant-specific queries.
"""

from contextlib import contextmanager
from typing import Any, Dict, Generator, List, Optional, Union

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance as QDistance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchAny,
    MatchValue,
    Range,
)

from .base import BaseVectorStore, DistanceType
from vector.search.dsl import (
    SearchRequest,
    SearchResponse,
    Hit,
    FilterExpr,
    And,
    Or,
    Not,
    FieldEquals,
    FieldIn,
    RangeFilter,
)


def _map_distance(d: DistanceType) -> QDistance:
    """Map our DistanceType enum to Qdrant's Distance enum."""
    if d == DistanceType.COSINE:
        return QDistance.COSINE
    if d == DistanceType.DOT:
        return QDistance.DOT
    if d == DistanceType.EUCLIDEAN:
        return QDistance.EUCLID
    return QDistance.COSINE


class QdrantVectorStore(BaseVectorStore):
    """Qdrant implementation of the vector store interface.
    
    This adapter translates DSL filters to Qdrant filters and handles
    both vector similarity search and filter-only queries (via scroll).
    """
    
    def __init__(
        self,
        *,
        db_path: Optional[str] = None,
        url: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        """Initialize the Qdrant store.
        
        Args:
            db_path: Path to local Qdrant database (for embedded mode)
            url: URL for remote Qdrant instance
            api_key: API key for authentication with remote instance
        """
        self.db_path = db_path
        self.url = url
        self.api_key = api_key
    
    @contextmanager
    def _client(self) -> Generator[QdrantClient, None, None]:
        """Get a Qdrant client connection."""
        if self.url:
            client = QdrantClient(url=self.url, api_key=self.api_key)
        else:
            client = QdrantClient(path=self.db_path)
        
        try:
            yield client
        finally:
            client.close()
    
    def create_collection(
        self,
        collection_name: str,
        vector_size: int,
        distance: DistanceType = DistanceType.COSINE
    ) -> None:
        """Create a new collection if it doesn't exist."""
        with self._client() as client:
            if client.collection_exists(collection_name):
                return
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=_map_distance(distance)
                ),
            )
    
    def delete_collection(self, name: str) -> None:
        """Delete a collection."""
        with self._client() as client:
            if client.collection_exists(name):
                client.delete_collection(name)
    
    def list_collections(self) -> List[str]:
        """List all collections."""
        with self._client() as client:
            return [c.name for c in client.get_collections().collections]
    
    def upsert(
        self,
        collection_name: str,
        point_id: Union[str, int],
        vector: List[float],
        payload: Dict[str, Any]
    ) -> None:
        """Insert or update a point in the collection."""
        with self._client() as client:
            if not client.collection_exists(collection_name):
                raise ValueError(f"Collection {collection_name} does not exist.")
            client.upsert(
                collection_name=collection_name,
                points=[
                    PointStruct(
                        id=point_id,
                        vector=vector,
                        payload=payload
                    )
                ]
            )
    
    def delete(
        self,
        collection_name: str,
        filter_expr: FilterExpr
    ) -> int:
        """Delete points from a collection matching the filter.
        
        Args:
            collection_name: Name of the collection
            filter_expr: Filter expression (from search.dsl) to select points to delete
            
        Returns:
            Number of points deleted
        """
        # Convert DSL filter to Qdrant filter
        q_filter = self._to_qdrant_filter(filter_expr)
        
        with self._client() as client:
            # First, count how many points will be deleted
            count_result = client.count(
                collection_name=collection_name,
                count_filter=q_filter,
                exact=True
            )
            count = count_result.count if hasattr(count_result, 'count') else count_result
            
            # Delete the points
            client.delete(
                collection_name=collection_name,
                points_selector=q_filter
            )
            
            return count
    
    def search(self, request: SearchRequest) -> SearchResponse:
        """Execute a search query.
        
        Supports both vector similarity search (when request.vector is provided)
        and filter-only queries (when request.vector is None, uses scroll).
        """
        q_filter = self._to_qdrant_filter(request.filter) if request.filter else None
        hits: List[Hit] = []
        
        with self._client() as client:
            if request.vector is None:
                # Filter-only query: use scroll
                points, _ = client.scroll(
                    collection_name=request.collection,
                    limit=request.top_k,
                    with_payload=request.include_payload,
                    scroll_filter=q_filter,
                )
                for p in points:
                    hits.append(
                        Hit(
                            id=p.id,
                            score=None,
                            payload=p.payload if request.include_payload else None
                        )
                    )
            else:
                # Vector similarity search
                results = client.search(
                    collection_name=request.collection,
                    query_vector=request.vector,
                    limit=request.top_k,
                    query_filter=q_filter,
                    with_payload=request.include_payload,
                )
                for r in results:
                    hits.append(
                        Hit(
                            id=r.id,
                            score=float(r.score) if hasattr(r, "score") else None,
                            payload=r.payload if request.include_payload else None
                        )
                    )
        
        return SearchResponse(hits=hits)
    
    def _to_qdrant_filter(self, expr: FilterExpr) -> Filter:
        """Translate a DSL filter expression to a Qdrant Filter.
        
        This recursively converts our abstract filter AST into
        Qdrant's native filter format.
        """
        if isinstance(expr, And):
            parts = [self._to_qdrant_filter(e) for e in expr.all]
            return self._merge_filters(must=parts)
        
        if isinstance(expr, Or):
            parts = [self._to_qdrant_filter(e) for e in expr.any]
            return self._merge_filters(should=parts)
        
        if isinstance(expr, Not):
            inner = self._to_qdrant_filter(expr.expr)
            return self._merge_filters(must_not=[inner])
        
        if isinstance(expr, FieldEquals):
            return Filter(
                must=[
                    FieldCondition(
                        key=expr.key,
                        match=MatchValue(value=expr.value)
                    )
                ]
            )
        
        if isinstance(expr, FieldIn):
            return Filter(
                must=[
                    FieldCondition(
                        key=expr.key,
                        match=MatchAny(any=expr.values)
                    )
                ]
            )
        
        if isinstance(expr, RangeFilter):
            rng = Range(
                gt=expr.gt,
                gte=expr.gte,
                lt=expr.lt,
                lte=expr.lte
            )
            return Filter(
                must=[
                    FieldCondition(
                        key=expr.key,
                        range=rng
                    )
                ]
            )
        
        # Default: empty filter
        return Filter(must=[])
    
    def _merge_filters(
        self,
        must: Optional[List[Filter]] = None,
        should: Optional[List[Filter]] = None,
        must_not: Optional[List[Filter]] = None
    ) -> Filter:
        """Merge multiple Qdrant filters into a single Filter.
        
        This flattens nested filters and combines their conditions
        into appropriate must/should/must_not lists.
        """
        m, s, n = [], [], []
        
        # Collect all must conditions
        for fl in must or []:
            m.extend(getattr(fl, "must", []) or [])
            s.extend(getattr(fl, "should", []) or [])
            n.extend(getattr(fl, "must_not", []) or [])
        
        # Collect all should conditions
        for fl in should or []:
            s.extend(getattr(fl, "must", []) or [])
            s.extend(getattr(fl, "should", []) or [])
            n.extend(getattr(fl, "must_not", []) or [])
        
        # Collect all must_not conditions
        for fl in must_not or []:
            n.extend(getattr(fl, "must", []) or [])
            n.extend(getattr(fl, "should", []) or [])
            n.extend(getattr(fl, "must_not", []) or [])
        
        return Filter(
            must=m or None,
            should=s or None,
            must_not=n or None
        )
