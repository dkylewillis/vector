"""Document chunking utilities for Vector."""

import json
from typing import List, Tuple
from pathlib import Path

from docling.chunking import HybridChunker
from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer
from transformers import AutoTokenizer
from docling_core.types.doc.document import DoclingDocument


from .models import Chunk, ChunkMetadata, DocumentResult, ChunkEmbeddingData, StorageResult
from docling_core.transforms.chunker.hierarchical_chunker import (
    ChunkingDocSerializer,
    ChunkingSerializerProvider,
    
)
from docling_core.transforms.serializer.markdown import MarkdownParams
from docling_core.types.doc.base import ImageRefMode

# needed to add ImageItem to chunk metadata
class ImgPlaceholderSerializerProvider(ChunkingSerializerProvider):
    def get_serializer(self, doc):
        return ChunkingDocSerializer(
            doc=doc,
            params=MarkdownParams(
                image_placeholder="<!-- image -->",
            ),
        )

class DocumentChunker:
    """Handles document chunking operations."""
    
    def __init__(self, model_name: str = None):
        """Initialize chunker with tokenizer.
        
        Args:
            model_name: Name of the model for tokenization
        """
        if model_name is None:
            model_name = "sentence-transformers/all-MiniLM-L6-v2"  # or any sensible default

        tokenizer = AutoTokenizer.from_pretrained(model_name)
        
        self.tokenizer = HuggingFaceTokenizer(
            tokenizer=tokenizer,
            max_tokens=tokenizer.model_max_length,
        )
        
        self.chunker = HybridChunker(
            tokenizer=self.tokenizer,
            serializer_provider=ImgPlaceholderSerializerProvider()
        )

    def _debug_save_metadata(self, metadata: ChunkMetadata) -> None:
        """Save chunk metadata to debug file."""
        with open('chunks_debug.txt', 'a', encoding='utf-8') as f:
            f.write(f"{json.dumps(metadata.model_dump(), indent=2)}\n")
            f.write("-" * 50 + "\n")

    def chunk_document(self, doc_result: DocumentResult) -> List[Chunk]:
        """Convert DocumentResult to chunks.
        
        Args:
            doc_result: DocumentResult from document conversion
            
        Returns:
            List of Chunk objects with text and metadata
        """
        # Chunk the document
        chunks = self.chunker.chunk(doc_result.document)
        if not chunks:
            print(f"No chunks created for {doc_result.file_path.name}")
            return []

        # Process chunks and add metadata
        processed_chunks = []
        for chunk in chunks:
            doc_items = [it.self_ref for it in chunk.meta.doc_items]
            picture_items = [it.self_ref for it in chunk.meta.doc_items if "pictures" in it.self_ref]
            table_items = [it.self_ref for it in chunk.meta.doc_items if "tables" in it.self_ref]
            contextualized_text = self.chunker.contextualize(chunk=chunk)
            metadata = chunk.meta.export_json_dict()

            chunk_metadata = ChunkMetadata(
                doc_items=doc_items,
                filename=doc_result.file_path.name,
                headings=metadata.get('headings', []),
                source=doc_result.source_category,
                file_path=str(doc_result.file_path),
                file_hash=doc_result.file_hash,
                picture_items=picture_items,
                table_items=table_items
            )
            
            # Debug: Save metadata to file
            self._debug_save_metadata(chunk_metadata)
            
            chunk_obj = Chunk(
                text=contextualized_text,
                metadata=chunk_metadata
            )
            processed_chunks.append(chunk_obj)

        print(f"✅ Created {len(processed_chunks)} chunks from {doc_result.file_path.name}")
        return processed_chunks

    def chunk_documents_batch(self, doc_results: List['DocumentResult']) -> List['Chunk']:
        """Convert multiple DocumentResults to chunks in batch.
        
        Args:
            doc_results: List of DocumentResult objects from document conversion
            
        Returns:
            List of Chunk objects with text and metadata
        """
        all_chunks = []
        for doc_result in doc_results:
            chunks = self.chunk_document(doc_result)
            all_chunks.extend(chunks)
        
        print(f"✅ Created {len(all_chunks)} total chunks from {len(doc_results)} documents")
        return all_chunks

class ChunkStorageManager:
    """Handles chunk storage orchestration - consistent with ArtifactStorageManager."""
    
    def __init__(self, chunks_vector_db, embedder):
        self.chunks_vector_db = chunks_vector_db
        self.embedder = embedder
    
    def store_chunks(self, chunks_with_embeddings: List[Tuple[Chunk, List[float]]], 
                    batch_size: int = 100) -> StorageResult:
        """Store chunks using consistent Pydantic models."""
        if not chunks_with_embeddings:
            return StorageResult(processed_count=0, stored_count=0)
            
        # Ensure collection exists
        if not self.chunks_vector_db.collection_exists():
            vector_size = self.embedder.get_embedding_dimension()
            self.chunks_vector_db.create_collection(vector_size=vector_size)
            self.chunks_vector_db.ensure_indexes()
        
        # Convert to embedding data using consistent Pydantic model
        embedding_data_list = []
        for chunk, embedding in chunks_with_embeddings:
            embedding_data = ChunkEmbeddingData.from_chunk_and_embedding(chunk, embedding)
            embedding_data_list.append(embedding_data)
        
        errors = []
        stored_count = 0
        
        # Process in batches
        for i in range(0, len(embedding_data_list), batch_size):
            batch = embedding_data_list[i:i + batch_size]
            try:
                # Extract data for vector storage using consistent interface
                texts = [data.text for data in batch]
                embeddings = [data.embedding for data in batch]
                metadata_list = [data.metadata.model_dump() for data in batch]
                
                # Store using standard database method
                self.chunks_vector_db.add_chunks(texts, embeddings, metadata_list)
                stored_count += len(batch)
                print(f"📦 Stored batch: {len(batch)} chunks")
                
            except Exception as e:
                error_msg = f"Error storing chunk batch {i//batch_size + 1}: {e}"
                errors.append(error_msg)
        
        return StorageResult(
            processed_count=len(chunks_with_embeddings),
            stored_count=stored_count,
            errors=errors
        )
