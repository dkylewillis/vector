"""Document chunking utilities for Vector."""

import json
from typing import List
from pathlib import Path

from docling.chunking import HybridChunker
from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer
from transformers import AutoTokenizer
from docling_core.types.doc.document import DoclingDocument


from .models import Chunk, ChunkMetadata, DocumentResult
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
            contextualized_text = self.chunker.contextualize(chunk=chunk)
            metadata = chunk.meta.export_json_dict()

            chunk_metadata = ChunkMetadata(
                filename=doc_result.file_path.name,
                headings=metadata.get('headings', []),
                source=doc_result.source_category,
                file_path=str(doc_result.file_path),
                file_hash=doc_result.file_hash
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
