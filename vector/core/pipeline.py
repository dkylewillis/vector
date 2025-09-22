from pathlib import Path
from typing import List
import uuid
import hashlib
import time
import os
from datetime import datetime, timezone
from PIL import Image
from sklearn import pipeline
from .converter import DocumentConverter
from .chunker import DocumentChunker
from .embedder import Embedder
from .vector_store import VectorStore
from .models import ConvertedDocument, Chunk, Artifact
from .document_registry import VectorRegistry, DocumentRecord

from docling_core.types.doc.document import ImageRefMode


class VectorPipeline:
    """Simple pipeline for document processing and vector storage."""
    
    def __init__(self):
        """Initialize pipeline with default components."""
        self.converter = DocumentConverter()
        self.chunker = DocumentChunker()
        self.embedder = Embedder()
        self.store = VectorStore()
        self.registry = VectorRegistry()

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

    def embed_chunks(self, chunks: List[Chunk]) -> List[List[float]]:
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

    def store_chunks(
        self,
        chunks: List[Chunk],
        embeddings: List[List[float]],
        document_record: DocumentRecord,
        collection_name: str = "chunks"
        ) -> None:
        """Store chunks with document metadata in payload."""
        
        for chunk, embedding in zip(chunks, embeddings):
            payload = {
                # Chunk-specific data
                "chunk_id": chunk.chunk_id,
                "text": chunk.text,
                "headings": chunk.headings,
                'pictures': chunk.picture_items,
                'tables': chunk.table_items,
                "page_number": chunk.page_number,
                
                # Document-level metadata (from registry)
                "document_id": document_record.document_id,
                "registered_date": document_record.registered_date.isoformat(),
            }
            
            self.store.insert(collection_name, str(uuid.uuid4()), embedding, payload)

    def embed_artifacts(self, artifacts: List[Artifact]) -> List[List[float]]:
        """Generate embeddings for artifacts.
        
        Args:
            artifacts: List of Artifact objects
            
        Returns:
            List of embeddings
        """
        artifact_texts = []
        for artifact in artifacts:
            artifact_text = (
                f"Headings: {artifact.headings or ''}\n"
                f"Caption: {artifact.caption or ''}\n"
                f"Before Text: {artifact.before_text or ''}\n"
                f"After Text: {artifact.after_text or ''}"
            )
            artifact_texts.append(artifact_text)
            
        embeddings = self.embedder.embed_texts(artifact_texts)
        print(f"✅ Generated embeddings for {len(embeddings)} artifacts")
        return embeddings

    def store_artifacts(
        self,
        artifacts: List[Artifact],
        embeddings: List[List[float]],
        document_record: DocumentRecord,
        collection_name: str = "artifacts"
    ) -> None:
        """Store artifacts with document metadata in payload."""
        
        for artifact, embedding in zip(artifacts, embeddings):
            payload = {
                # Artifact-specific data
                "artifact_id": artifact.artifact_id,
                "type": artifact.type,
                "ref_item": artifact.ref_item,
                "file_ref": artifact.file_ref,
                "headings": artifact.headings,
                "before_text": artifact.before_text,
                "after_text": artifact.after_text,
                "caption": artifact.caption,
                "page_number": artifact.page_number,
                
                # Document-level metadata (from registry)
                "document_id": document_record.document_id,
                "registered_date": document_record.registered_date.isoformat(),
            }
            
            self.store.insert(collection_name, str(uuid.uuid4()), embedding, payload)

    def create_thumbnail(self, image: Image.Image, thumbnail_size: tuple = (200, 200)) -> Image.Image:
        """Create a thumbnail from a PIL image.
        
        Args:
            image: PIL Image object
            thumbnail_size: Size of thumbnail as (width, height) tuple
            
        Returns:
            PIL Image thumbnail
        """
        thumbnail = image.copy()
        thumbnail.thumbnail(thumbnail_size, Image.Resampling.LANCZOS)
        return thumbnail

    def save_artifacts(self, artifacts: List[Artifact], document_name: str, 
                      base_path: str = "data/converted_documents", 
                      create_thumbnails: bool = False, 
                      thumbnail_size: tuple = (200, 200)) -> None:
        """Save artifact images to filesystem in document-specific folder structure.
        
        Args:
            artifacts: List of Artifact objects with PIL images
            document_name: Name of the document (used for folder structure)
            base_path: Base directory to save images
            create_thumbnails: Whether to also create and save thumbnails
            thumbnail_size: Size of thumbnails as (width, height) tuple
        """
        if not artifacts:
            print("No artifacts to save")
            return
            
        # Create document-specific directory with artifacts subfolder
        doc_dir = Path(base_path) / document_name
        artifacts_dir = doc_dir / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        
        saved_count = 0
        thumbnail_count = 0
        
        for artifact in artifacts:
            if artifact.image is not None:
                # Generate filename from artifact ID
                artifact_id = artifact.artifact_id.replace("/", "_").replace("#", "")
                # Remove leading underscore if present
                if artifact_id.startswith("_"):
                    artifact_id = artifact_id[1:]
                filename = f"{artifact_id}.png"
                file_path = artifacts_dir / filename
                
                try:
                    # Save PIL image as PNG
                    artifact.image.save(str(file_path), "PNG")
                    # Update artifact's file_ref to point to saved file
                    artifact.file_ref = str(file_path)
                    saved_count += 1
                    
                    # Create thumbnail if requested
                    if create_thumbnails:
                        thumbnail = self.create_thumbnail(artifact.image, thumbnail_size)
                        thumbnail_filename = f"thumb_{artifact_id}.png"
                        thumbnail_path = artifacts_dir / thumbnail_filename
                        
                        thumbnail.save(str(thumbnail_path), "PNG")
                        thumbnail_count += 1
                        
                except Exception as e:
                    print(f"❌ Failed to save artifact {artifact.artifact_id}: {e}")
        
        print(f"✅ Saved {saved_count} artifact images to {artifacts_dir}")
        if create_thumbnails:
            print(f"✅ Created {thumbnail_count} thumbnails")

    def save_converted_document(self, converted_doc: ConvertedDocument, document_name: str, base_path: str = "data/converted_documents") -> None:
        """Save the entire converted document as JSON in a document-specific folder.
        
        Args:
            converted_doc: ConvertedDocument object to save
            document_name: Name of the document (used for folder structure)
            base_path: Base directory to save the document
        """

        # Create document-specific directory
        doc_dir = Path(base_path) / document_name
        doc_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Save converted document in its own folder
            converted_doc.doc.save_as_json(
                doc_dir / f"{document_name}_document.json",
                image_mode=ImageRefMode.EMBEDDED,
            )
            print(f"✅ Saved converted document JSON to {doc_dir}")
        except Exception as e:
            print(f"❌ Failed to save converted document: {e}")

    def run(self, file_path: str) -> str:
        """Process a file through the complete pipeline.

        Args:
            file_path: Path to the file to process.

        Returns:
            Document ID (derived from file stem).
        """
        file_path = Path(file_path)
        document_name = file_path.stem
        base_path = "data/converted_documents"
        chunk_collection = "chunks"
        artifact_collection = "artifacts"

        converted_doc = self.convert(str(file_path))
        chunks, artifacts = self.chunk(converted_doc)

        # Save converted document
        self.save_converted_document(
            converted_doc,
            document_name,
            base_path=base_path,
        )

        # Save artifacts if any
        if artifacts:
            self.save_artifacts(
                artifacts,
                document_name,
                base_path=base_path,
                create_thumbnails=True,
                thumbnail_size=(150, 150),
            )

        # Register document in registry
        document_record = self.registry.register_document(file_path, document_name)
        document_record.has_artifacts = len(artifacts) > 0
        document_record.artifact_count = len(artifacts)
        document_record.chunk_count = len(chunks)
        document_record.chunk_collection = chunk_collection
        document_record.artifact_collection = artifact_collection
        document_record.tags = []
        self.registry.update_document(document_record)

        chunk_embeddings = self.embed_chunks(chunks)
        self.store_chunks(chunks, chunk_embeddings, document_record, collection_name=chunk_collection)

        if artifacts:
            artifact_embeddings = self.embed_artifacts(artifacts)
            self.store_artifacts(artifacts, artifact_embeddings, document_record, collection_name=artifact_collection)


        print(f"✅ Pipeline completed for {file_path.name}")
        return file_path.stem
    