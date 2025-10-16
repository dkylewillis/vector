"""Document chunking utilities for Vector."""

from typing import List
from docling.chunking import HybridChunker
from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer
from transformers import AutoTokenizer
from docling_core.types.doc.document import DoclingDocument
from docling_core.transforms.chunker.hierarchical_chunker import (
    ChunkingDocSerializer,
    ChunkingSerializerProvider,
)
from docling_core.transforms.serializer.markdown import MarkdownParams

from vector.models import Chunk, Artifact, get_item_by_ref


class ImgPlaceholderSerializerProvider(ChunkingSerializerProvider):
    """Custom serializer provider for image placeholders."""
    
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
            model_name = "sentence-transformers/all-MiniLM-L6-v2"

        tokenizer = AutoTokenizer.from_pretrained(model_name)
        
        self.tokenizer = HuggingFaceTokenizer(
            tokenizer=tokenizer,
            max_tokens=tokenizer.model_max_length,
        )
        
        self.chunker = HybridChunker(
            tokenizer=self.tokenizer,
            serializer_provider=ImgPlaceholderSerializerProvider()
        )

    def chunk_document(self, doc: DoclingDocument) -> List[Chunk]:
        """Convert DoclingDocument to chunks.
        
        Args:
            doc: DoclingDocument from document conversion
            
        Returns:
            List of Chunk objects with text and metadata
        """
        # Chunk the document
        chunks = self.chunker.chunk(doc)
        if not chunks:
            print(f"No chunks created for {doc.name}")
            return []

        # Process chunks and add metadata
        processed_chunks = []
        for doc_chunk in chunks:  # Renamed to avoid variable collision            
            doc_items = [it.self_ref for it in doc_chunk.meta.doc_items]

            picture_items = [get_item_by_ref(doc, ref) for ref in doc_items if "pictures" in ref]
            table_items = [get_item_by_ref(doc, ref) for ref in doc_items if "tables" in ref]
            artifacts = (
                [Artifact.from_picture_item(item, doc) for item in picture_items if item is not None] +
                [Artifact.from_table_item(item, doc) for item in table_items if item is not None]
            )
            contextualized_text = self.chunker.contextualize(chunk=doc_chunk)

            # Create our Chunk model
            processed_chunk = Chunk(
                chunk_id=f"chunk_{len(processed_chunks)}",  # Generate sequential IDs
                chunk_index=len(processed_chunks),  # 0-based index for ordering and filtering
                text=contextualized_text,
                page_number=None,  # Not available in this version
                headings=getattr(doc_chunk.meta, 'headings', None) or [],  # Use safe attribute access
                doc_items=doc_items,
                artifacts=artifacts,
            )
            
            processed_chunks.append(processed_chunk)

        print(f"✅ Created {len(processed_chunks)} chunks from {doc.name}")
        return processed_chunks