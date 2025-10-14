from typing import List, Optional
from pydantic import BaseModel, Field
from vector.core.models import Chunk, Artifact
from ..embedder import Embedder
from ..vector_store import VectorStore

class SearchResult(BaseModel):
    id: str = Field(..., description="Unique identifier")
    score: float  # Qdrant scores can be outside [0,1] depending on distance metric
    text: str
    filename: str
    type: str
    chunk: Optional[Chunk] = None
    artifact: Optional[Artifact] = None

class SearchService:
    def __init__(self, embedder: Embedder, store: VectorStore,
                 chunks_collection: str = "chunks"):
        self.embedder = embedder
        self.store = store
        self.chunks_collection = chunks_collection

    def search_chunks(self, query: str, top_k: int = 5,
                      document_ids: Optional[List[str]] = None,
                      window: int = 0) -> List[SearchResult]:
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
                
                # If window is enabled and we have a chunk_id, get surrounding chunks
                if window > 0 and chunk_obj.chunk_id:
                    doc_id = r.payload.get("document_id")
                    if doc_id:
                        context_chunks = self.store.get_chunk_window(
                            collection=self.chunks_collection,
                            document_id=doc_id,
                            chunk_id=chunk_obj.chunk_id,
                            window=window
                        )
                        # Combine text from all chunks in the window
                        if context_chunks:
                            context_texts = []
                            for ctx_point in context_chunks:
                                try:
                                    ctx_data = ctx_point.payload.get("chunk", {})
                                    if isinstance(ctx_data, str):
                                        ctx_data = json.loads(ctx_data)
                                    ctx_chunk = Chunk.model_validate(ctx_data)
                                    context_texts.append(ctx_chunk.text)
                                except Exception:
                                    pass
                            if context_texts:
                                text = "\n\n".join(context_texts)
                
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

    def search(self, query: str, top_k: int = 5,
               document_ids: Optional[List[str]] = None,
               window: int = 0) -> List[SearchResult]:
        """Search chunks only (artifacts are no longer stored in vector db).
        
        Args:
            query: Search query text
            top_k: Number of results to return
            document_ids: Optional list of document IDs to filter by
            window: Number of surrounding chunks to include in context (0 = disabled)
            
        Returns:
            List of SearchResult objects
        """
        if not query.strip():
            raise ValueError("Search query cannot be empty")
        return self.search_chunks(query, top_k, document_ids, window)