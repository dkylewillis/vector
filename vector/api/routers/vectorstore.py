"""VectorStore CRUD endpoints.

Provides REST API for:
- Collection management (list, create, delete)
- Point operations (upsert)
- Document operations (list, delete)
"""

from fastapi import APIRouter, Depends, HTTPException
import logging

from vector.api.deps import get_deps, AppDeps
from vector.api.schemas import (
    CreateCollectionRequest,
    UpsertPointRequest,
    SuccessResponse,
    CollectionListResponse,
    DocumentListResponse
)
from vector.stores.base import DistanceType
from vector.search.dsl import FieldEquals

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/vectorstore", tags=["vectorstore"])


@router.get("/collections", response_model=CollectionListResponse)
def list_collections(deps: AppDeps = Depends(get_deps)):
    """List all available collections in the vector store.
    
    Returns:
        CollectionListResponse with list of collection names
    """
    try:
        collections = deps.store.list_collections()
        return CollectionListResponse(
            count=len(collections),
            collections=collections
        )
    except Exception as e:
        logger.error(f"Failed to list collections: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/collections", response_model=SuccessResponse)
def create_collection(body: CreateCollectionRequest, deps: AppDeps = Depends(get_deps)):
    """Create a new vector collection.
    
    Args:
        body: Collection configuration (name, vector_size, distance metric)
        
    Returns:
        SuccessResponse indicating collection was created
        
    Raises:
        HTTPException: If collection already exists or creation fails
    """
    try:
        # Map distance string to enum
        distance_map = {
            "cosine": DistanceType.COSINE,
            "dot": DistanceType.DOT,
            "euclidean": DistanceType.EUCLIDEAN
        }
        
        distance = distance_map.get(body.distance.lower())
        if not distance:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid distance metric: {body.distance}. Use: cosine, dot, or euclidean"
            )
        
        deps.store.create_collection(
            collection_name=body.name,
            vector_size=body.vector_size,
            distance=distance
        )
        
        logger.info(f"Created collection: {body.name}")
        return SuccessResponse(message=f"Collection '{body.name}' created successfully")
        
    except Exception as e:
        logger.error(f"Failed to create collection: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/collections/{name}", response_model=SuccessResponse)
def delete_collection(name: str, deps: AppDeps = Depends(get_deps)):
    """Delete a collection and all its data.
    
    Args:
        name: Collection name to delete
        
    Returns:
        SuccessResponse indicating collection was deleted
        
    Raises:
        HTTPException: If collection doesn't exist or deletion fails
    """
    try:
        deps.store.delete_collection(name)
        logger.info(f"Deleted collection: {name}")
        return SuccessResponse(message=f"Collection '{name}' deleted successfully")
        
    except Exception as e:
        logger.error(f"Failed to delete collection: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/points", response_model=SuccessResponse)
def upsert_point(body: UpsertPointRequest, deps: AppDeps = Depends(get_deps)):
    """Insert or update a point in a collection.
    
    Args:
        body: Point data (collection, point_id, vector, payload)
        
    Returns:
        SuccessResponse indicating point was upserted
        
    Raises:
        HTTPException: If collection doesn't exist or upsert fails
    """
    try:
        deps.store.upsert(
            collection_name=body.collection,
            point_id=body.point_id,
            vector=body.vector,
            payload=body.payload
        )
        
        logger.info(f"Upserted point {body.point_id} in collection {body.collection}")
        return SuccessResponse(message=f"Point '{body.point_id}' upserted successfully")
        
    except Exception as e:
        logger.error(f"Failed to upsert point: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents", response_model=DocumentListResponse)
def list_documents(
    collection: str = "chunks",
    limit: int = 100,
    deps: AppDeps = Depends(get_deps)
):
    """List documents in a collection.
    
    Args:
        collection: Collection name (default: "chunks")
        limit: Maximum number of documents to return (default: 100)
        
    Returns:
        DocumentListResponse with document metadata
    """
    try:
        # Use search with empty vector to get all documents
        # This is a workaround - ideally we'd have a scroll/list method
        from vector.search.dsl import SearchRequest
        
        request = SearchRequest(
            collection=collection,
            vector=None,  # Filter-only query
            top_k=limit,
            include_payload=True
        )
        
        response = deps.store.search(request)
        
        # Extract unique documents
        seen_docs = set()
        documents = []
        
        for hit in response.hits:
            payload = hit.payload or {}
            doc_id = payload.get("document_id")
            
            if doc_id and doc_id not in seen_docs:
                seen_docs.add(doc_id)
                documents.append({
                    "document_id": doc_id,
                    "filename": payload.get("filename", doc_id),
                    "source_file": payload.get("source_file"),
                    "registered_date": payload.get("registered_date")
                })
        
        return DocumentListResponse(
            count=len(documents),
            documents=documents
        )
        
    except Exception as e:
        logger.error(f"Failed to list documents: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/documents/{document_id}", response_model=SuccessResponse)
def delete_document(
    document_id: str,
    collection: str = "chunks",
    deps: AppDeps = Depends(get_deps)
):
    """Delete all chunks for a specific document.
    
    Args:
        document_id: Document ID to delete
        collection: Collection name (default: "chunks")
        
    Returns:
        SuccessResponse with number of points deleted
        
    Raises:
        HTTPException: If deletion fails
    """
    try:
        # Delete all points with matching document_id
        filter_expr = FieldEquals(key="document_id", value=document_id)
        deleted_count = deps.store.delete(collection, filter_expr)
        
        logger.info(f"Deleted {deleted_count} chunks for document: {document_id}")
        return SuccessResponse(
            message=f"Deleted {deleted_count} chunks for document '{document_id}'"
        )
        
    except Exception as e:
        logger.error(f"Failed to delete document: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
