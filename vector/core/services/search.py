from typing import List, Optional
from pydantic import BaseModel, Field
from vector.core.models import Chunk, Artifact
from ..embedder import Embedder
from ..vector_store import VectorStore

class SearchResult(BaseModel):
    id: str = Field(..., description="Unique identifier")
    score: float = Field(..., ge=0.0, le=1.0)
    text: str
    filename: str
    type: str
    chunk: Optional[Chunk] = None
    artifact: Optional[Artifact] = None

class SearchService:
    def __init__(self, embedder: Embedder, store: VectorStore,
                 chunks_collection: str = "chunks",
                 artifacts_collection: str = "artifacts"):
        self.embedder = embedder
        self.store = store
        self.chunks_collection = chunks_collection
        self.artifacts_collection = artifacts_collection

    def search_chunks(self, query: str, top_k: int = 5,
                      document_ids: Optional[List[str]] = None) -> List[SearchResult]:
        if not query.strip():
            raise ValueError("Search query cannot be empty")
        qv = self.embedder.embed_text(query)
        raw = self.store.search_documents(qv, self.chunks_collection, top_k, document_ids)
        results: List[SearchResult] = []
        import json
        for r in raw:
            chunk_obj = None
            try:
                data = r.payload.get("chunk", {}) or {}
                if isinstance(data, str):
                    data = json.loads(data)
                chunk_obj = Chunk.model_validate(data)
                text = chunk_obj.text
            except Exception as e:
                print(f"Warning: chunk validation failed ({r.id}): {e}")
                text = r.payload.get("text") or ""
            results.append(SearchResult(
                id=str(r.id),
                score=r.score,
                text=text,
                filename=r.payload.get("document_id", "Unknown"),
                type="chunk",
                chunk=chunk_obj
            ))
        return results

    def search_artifacts(self, query: str, top_k: int = 5,
                         document_ids: Optional[List[str]] = None) -> List[SearchResult]:
        if not query.strip():
            raise ValueError("Search query cannot be empty")
        qv = self.embedder.embed_text(query)
        raw = self.store.search_documents(qv, self.artifacts_collection, top_k, document_ids)
        results: List[SearchResult] = []
        import json
        for r in raw:
            artifact_obj = None
            try:
                data = r.payload.get("artifact", {}) or {}
                if isinstance(data, str):
                    data = json.loads(data)
                artifact_obj = Artifact.model_validate(data)
            except Exception as e:
                print(f"Warning: artifact validation failed ({r.id}): {e}")
            # Build display text
            parts = []
            if r.payload.get("caption"):
                parts.append(f"Caption: {r.payload['caption']}")
            if r.payload.get("before_text"):
                parts.append(f"Context: {r.payload['before_text']}")
            if r.payload.get("after_text"):
                parts.append(f"Context: {r.payload['after_text']}")
            if r.payload.get("headings"):
                parts.append("Headings: " + ", ".join(r.payload["headings"]))
            display = " | ".join(parts) if parts else "Artifact"
            results.append(SearchResult(
                id=str(r.id),
                score=r.score,
                text=display,
                filename=r.payload.get("document_id", "Unknown"),
                type=r.payload.get("type", "artifact"),
                artifact=artifact_obj
            ))
        return results

    def search(self, query: str, top_k: int = 5,
               search_type: str = "both",
               document_ids: Optional[List[str]] = None) -> List[SearchResult]:
        if not query.strip():
            raise ValueError("Search query cannot be empty")
        results: List[SearchResult] = []
        if search_type in ("chunks", "both"):
            results.extend(self.search_chunks(query, top_k, document_ids))
        if search_type in ("artifacts", "both"):
            results.extend(self.search_artifacts(query, top_k, document_ids))
        if search_type == "both":
            results.sort(key=lambda r: r.score, reverse=True)
            results = results[: top_k * 2]
        return results