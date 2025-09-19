from contextlib import contextmanager
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchAny, MatchValue
from typing import Dict, List, Any, Optional, Generator
from pydantic import BaseModel, Field
from pathlib import Path
import json

from .models import DocumentMetadataRecord

class VectorMetadataStore:
    def __init__(self, path: Path):
        self.path = path
        self._data: Dict[str, DocumentMetadataRecord] = {}
        if path.exists():
            self._load()

    def _load(self):
        try:
            content = self.path.read_text().strip()
            if not content:
                # Empty file, initialize with empty dict
                return
            raw = json.loads(content)
            self._data = {doc_id: DocumentMetadataRecord(**meta) for doc_id, meta in raw.items()}
        except (json.JSONDecodeError, FileNotFoundError):
            # Invalid JSON or file doesn't exist, start with empty data
            self._data = {}

    def _save(self):
        raw = {doc_id: rec.model_dump(mode='json') for doc_id, rec in self._data.items()}
        self.path.write_text(json.dumps(raw, indent=2))

    # CRUD
    def add(self, record: DocumentMetadataRecord):
        self._data[record.doc_id] = record
        self._save()

    def get(self, doc_id: str) -> DocumentMetadataRecord:
        return self._data[doc_id]
    
    # --- Lookup by display_name ---
    def get_by_display_name(self, name: str) -> List[DocumentMetadataRecord]:
        return [rec for rec in self._data.values() if rec.display_name == name]
    
    def get_by_tag(self, tag: str):
        return self.get_by_tags([tag])

    def get_by_tags(self, tags: List[str], match_all: bool = False) -> List[DocumentMetadataRecord]:
        results = []
        for rec in self._data.values():
            if match_all and all(tag in rec.tags for tag in tags):
                results.append(rec)
            elif not match_all and any(tag in rec.tags for tag in tags):
                results.append(rec)
        return results
    
    def list(self):
        return list(self._data.values())

    def delete(self, doc_id: str):
        if doc_id in self._data:
            del self._data[doc_id]
            self._save()

class VectorStore(BaseModel):
    """A Pydantic model for managing Qdrant vector store operations."""
    
    db_path: Optional[str] = Field(default="./qdrant_db", description="Path to Qdrant database (for local)")
    url: Optional[str] = Field(default=None, description="URL for remote Qdrant instance")
    api_key: Optional[str] = Field(default=None, description="API key for remote Qdrant instance")
    
    class Config:
        arbitrary_types_allowed = True
    
    @contextmanager
    def get_client(self) -> Generator[QdrantClient, None, None]:
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
        distance: Distance = Distance.COSINE,
    ) -> None:
        """Create a new collection if it doesn't exist."""
        with self.get_client() as client:
            if client.collection_exists(collection_name):
                return
            try:
                client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(size=vector_size, distance=distance),
                )
                print(f"Collection {collection_name} created successfully.")
            except Exception as e:
                print(f"Error creating collection: {e}")

    def delete_collection(self, name: str) -> None:
        """Delete a collection."""
        with self.get_client() as client:
            try:
                if client.collection_exists(name):
                    client.delete_collection(name)
                    print(f"Collection {name} deleted successfully.")
                else:
                    print(f"Collection {name} does not exist.")
            except Exception as e:
                print(f"Error deleting collection {name}: {e}")

    def list_collections(self) -> List[str]:
        """List all collections."""
        with self.get_client() as client:
            return [c.name for c in client.get_collections().collections]

    def insert(
        self,
        collection_name: str,
        point_id: str,
        vectors: Dict[str, List[float]],
        payload: Dict[str, Any],
    ) -> None:
        """Insert a point into a collection."""
        with self.get_client() as client:
            if client.collection_exists(collection_name):
                try:
                    client.upsert(
                        collection_name=collection_name,
                        points=[PointStruct(id=point_id, vector=vectors, payload=payload)],
                    )
                    print(f"Point {point_id} inserted successfully into {collection_name}.")
                except Exception as e:
                    print(f"Error inserting point: {e}")
            else:
                print(f"Collection {collection_name} does not exist.")

    def search(
        self,
        query_vector: List[float],
        collection: str,
        top_k: int = 5,
        filter_: Optional[Filter] = None,
    ) -> List[Any]:
        """Search for similar vectors in a collection."""
        with self.get_client() as client:
            return client.search(
                collection_name=collection,
                query_vector=query_vector,
                limit=top_k,
                query_filter=filter_,
            )
        
    def search_documents(
        self,
        query_vector: List[float],
        collection: str,
        top_k: int = 5,
        document_ids: list[str] = None
    ) -> List[Any]:
        """Search for similar vectors in a collection."""

        filter_ = Filter(
            must=[
                FieldCondition(
                    key="document_id",
                    match=MatchAny(any=document_ids)
                )
            ]
        )

        with self.get_client() as client:
            return client.search(
                collection_name=collection,
                query_vector=query_vector,
                limit=top_k,
                query_filter=filter_,
            )

    def delete_document(self, collection: str, document_id: str) -> None:
        """Delete a document from a collection."""

        filter_ = Filter(
            must=[
                FieldCondition(
                    key="doc_id",
                    match=MatchValue(value=document_id)
                )
            ]
        )

        with self.get_client() as client:
            try:
                client.delete(
                    collection_name=collection,
                    points_selector=filter_
                )
                print(f"Document {document_id} deleted successfully from {collection}.")
            except Exception as e:
                print(f"Error deleting document {document_id}: {e}")

