from pathlib import Path
from typing import List
import uuid
import hashlib
import time
from .converter import DocumentConverter
from .chunker import DocumentChunker
from .embedder import Embedder
from .vector_store import VectorStore
from .models import ConvertedDocument, Chunk, Artifact

from docling_core.types.doc.document import ImageRefMode


class VectorPipeline:
    """Simple pipeline for document processing and vector storage."""
    
    def __init__(self):
        """Initialize pipeline with default components."""
        self.converter = DocumentConverter()
        self.chunker = DocumentChunker()
        self.embedder = Embedder()
        self.store = VectorStore()

    def convert(self, file_path: str) -> ConvertedDocument:
        """Convert a document file to ConvertedDocument.
        
        Args:
            file_path: Path to the file to process
            
        Returns:
            ConvertedDocument object
        """
        file_path = Path(file_path)
        doc_data = self.converter.convert_document(file_path)
        converted_doc = ConvertedDocument(doc=doc_data)
        print(f"✅ Converted {file_path.name}")

        converted_doc.doc.save_as_json(
            f"data/converted_documents/{file_path.stem}_document.json",
            image_mode=ImageRefMode.EMBEDDED,
        )

        return converted_doc

    def chunk(self, converted_doc: ConvertedDocument) -> tuple[List[Chunk], List[Artifact]]:
        """Extract chunks and artifacts from a converted document.
        
        Args:
            converted_doc: ConvertedDocument object
            
        Returns:
            Tuple of (chunks, artifacts)
        """
        chunks = converted_doc.get_chunks()
        artifacts = converted_doc.get_artifacts()
        print(f"✅ Extracted {len(chunks)} chunks and {len(artifacts)} artifacts")
        return chunks, artifacts

    def embed(self, chunks: List[Chunk]) -> List[List[float]]:
        """Generate embeddings for chunks.
        
        Args:
            chunks: List of Chunk objects
            
        Returns:
            List of embeddings
        """
        chunk_texts = [chunk.text for chunk in chunks]
        embeddings = self.embedder.embed_texts(chunk_texts)
        print(f"✅ Generated embeddings for {len(embeddings)} chunks")
        return embeddings

    def store_chunks(self, chunks: List[Chunk], embeddings: List[List[float]], 
                    collection_name: str = "documents", source_file: str = None) -> None:
        """Store chunks with embeddings in vector database.
        
        Args:
            chunks: List of Chunk objects
            embeddings: List of embeddings
            collection_name: Name of the collection to store in
            source_file: Source file path for metadata
        """
        # Create collection if it doesn't exist
        self.store.create_collection(collection_name, self.embedder.get_embedding_dimension())
        
        # Insert chunks with embeddings
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            # Use UUID for guaranteed unique IDs - no conflicts possible
            point_id = str(uuid.uuid4())
            
            payload = {
                "chunk_id": chunk.chunk_id,
                "text": chunk.text,
                "headings": chunk.headings,
                "doc_items": chunk.doc_items,
                "source_file": source_file or "unknown",
            }
            self.store.insert(collection_name, point_id, embedding, payload)
        
        print(f"✅ Stored {len(chunks)} chunks in collection '{collection_name}'")

    def run(self, file_path: str, collection_name: str = "documents") -> str:
        """Process a file through the complete pipeline.
        
        Args:
            file_path: Path to the file to process
            collection_name: Name of the collection to store in
            
        Returns:
            Document ID
        """
        file_path = Path(file_path)
        
        # Run all steps
        converted_doc = self.convert(str(file_path))
        chunks, artifacts = self.chunk(converted_doc)
        embeddings = self.embed(chunks)
        self.store_chunks(chunks, embeddings, collection_name, str(file_path))
        
        print(f"✅ Pipeline completed for {file_path.name}")
        return file_path.stem
    