from pathlib import Path
from typing import List
import uuid
from PIL import Image
from .converter import DocumentConverter
from .chunker import DocumentChunker
from .embedder import Embedder
from .vector_store import VectorStore
from .models import ConvertedDocument, Chunk, Artifact, get_item_by_ref
from .document_registry import VectorRegistry, DocumentRecord
from ..config import Config

from docling_core.types.doc.document import ImageRefMode, DoclingDocument



class VectorPipeline:
    """Simple pipeline for document processing and vector storage."""
    
    def __init__(self, config=None):
        """Initialize pipeline with default components."""
        self.config = config or Config()
        self.converter = DocumentConverter()
        self.chunker = DocumentChunker()
        self.embedder = Embedder()
        self.store = VectorStore()
        self.registry = VectorRegistry(config=self.config)

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
                "chunk": chunk.model_dump_json(),
                
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
                'artifact': artifact.model_dump_json(),
                
                # Document-level metadata (from registry)
                "document_id": document_record.document_id,
                "registered_date": document_record.registered_date.isoformat(),
            }
            
            self.store.insert(collection_name, str(uuid.uuid4()), embedding, payload)

    def _get_unique_document_name(self, base_name: str, base_path: str) -> str:
        """Generate unique document name by adding counter suffix if needed.
        
        Args:
            base_name: Base name for the document
            base_path: Base directory to check for existing documents
            
        Returns:
            Unique document name with counter suffix if needed
        """
        base_dir = Path(base_path)
        original_name = base_name
        counter = 1
        
        while (base_dir / base_name).exists():
            base_name = f"{original_name}_{counter:02d}"
            counter += 1
        
        return base_name

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

    def save_artifacts(self, doc: DoclingDocument, artifacts: List[Artifact], document_name: str, 
                      base_path: str = None, 
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
        
        # Use config value if base_path not provided
        if base_path is None:
            base_path = self.config.storage_converted_documents_dir
            
        # Create document-specific directory with artifacts subfolder
        doc_dir = Path(base_path) / document_name
        artifacts_dir = doc_dir / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        
        saved_count = 0
        thumbnail_count = 0
        
        for artifact in artifacts:
            item = get_item_by_ref(doc, artifact.self_ref)
            image = item.get_image(doc=doc)
            if image is not None:
                # Generate filename from artifact ID
                artifact_id = artifact.self_ref.replace("/", "_").replace("#", "")
                # Remove leading underscore if present
                if artifact_id.startswith("_"):
                    artifact_id = artifact_id[1:]
                filename = f"{artifact_id}.png"
                file_path = artifacts_dir / filename
                
                try:
                    # Save PIL image as PNG
                    image.save(str(file_path), "PNG")
                    # Update artifact's image_file_path to point to saved file
                    artifact.image_file_path = str(file_path)
                    saved_count += 1
                    
                    # Create thumbnail if requested
                    if create_thumbnails:
                        thumbnail = self.create_thumbnail(image, thumbnail_size)
                        thumbnail_filename = f"thumb_{artifact_id}.png"
                        thumbnail_path = artifacts_dir / thumbnail_filename
                        
                        thumbnail.save(str(thumbnail_path), "PNG")
                        artifact.image_thumbnail_path = str(thumbnail_path)
                        thumbnail_count += 1
                        
                except Exception as e:
                    print(f"❌ Failed to save artifact {artifact.self_ref}: {e}")
        
        print(f"✅ Saved {saved_count} artifact images to {artifacts_dir}")
        if create_thumbnails:
            print(f"✅ Created {thumbnail_count} thumbnails")

    def save_converted_document(self, converted_doc: ConvertedDocument, document_name: str, base_path: str = None) -> None:
        """Save the entire converted document as JSON in a document-specific folder.
        
        Args:
            converted_doc: ConvertedDocument object to save
            document_name: Name of the document (used for folder structure)
            base_path: Base directory to save the document
        """
        
        # Use config value if base_path not provided
        if base_path is None:
            base_path = self.config.storage_converted_documents_dir

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

    def run(self, file_path: str, tags: List[str] = None) -> str:
        """Process a file through the complete pipeline.

        Args:
            file_path: Path to the file to process.
            tags: Optional list of tags to add to the document.

        Returns:
            Document ID (unique document name).
        """
        if tags is None:
            tags = []
        file_path = Path(file_path)
        base_path = self.config.storage_converted_documents_dir
        
        # Generate unique document name to prevent conflicts
        document_name = self._get_unique_document_name(file_path.stem, base_path)
        
        chunk_collection = "chunks"
        artifact_collection = "artifacts"

        converted_doc = self.convert(str(file_path))

        # Next 3 steps are needed to ensure chunk.artifacts point to the same objects as in converted_doc.artifacts
        # So that when we save chunks, they have correct image_file_path etc.
        
        # Get artifacts first
        artifacts = converted_doc.get_artifacts()
        
        # Create a mapping of self_ref to artifact objects
        artifact_map = {artifact.self_ref: artifact for artifact in artifacts}
        
        # Get chunks and update their artifact references
        chunks = converted_doc.get_chunks()
        
        # Update chunk artifacts to reference the same objects
        for chunk in chunks:
            # Replace chunk.artifacts with references to the main artifact objects
            chunk.artifacts = [artifact_map[ref] for ref in chunk.doc_items if ref in artifact_map]


        # Save converted document
        self.save_converted_document(
            converted_doc,
            document_name,
            base_path=base_path,
        )

        # Save artifacts if any
        if artifacts:
            self.save_artifacts(
                converted_doc.doc,
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
        document_record.tags = tags  # Use provided tags instead of empty list
        self.registry.update_document(document_record)

        chunk_embeddings = self.embed_chunks(chunks)
        self.store_chunks(chunks, chunk_embeddings, document_record, collection_name=chunk_collection)

        if artifacts:
            artifact_embeddings = self.embed_artifacts(artifacts)
            self.store_artifacts(artifacts, artifact_embeddings, document_record, collection_name=artifact_collection)


        print(f"✅ Pipeline completed for {file_path.name}")
        return document_name
    

    def delete_document(self, document_id: str, cleanup_files: bool = True) -> bool:
        """Delete a document and all its associated data.
        
        Args:
            document_id: Document identifier to delete
            cleanup_files: Whether to also delete saved files (artifacts, converted docs)
            
        Returns:
            True if deletion was successful, False otherwise
        """
        # Get document info before deletion
        document_record = self.registry.get_document(document_id)
        if not document_record:
            print(f"❌ Document {document_id} not found in registry")
            return False
        
        print(f"🗑️ Deleting document: {document_record.display_name}")
        
        success = True
        
        # Delete vectors from vector store
        try:
            # Delete chunks
            if document_record.chunk_collection:
                self.store.delete_document(
                    collection=document_record.chunk_collection,
                    document_id=document_id
                )
                print(f"✅ Deleted chunk vectors for document {document_id}")
            
            # Delete artifacts
            if document_record.artifact_collection and document_record.has_artifacts:
                self.store.delete_document(
                    collection=document_record.artifact_collection,
                    document_id=document_id
                )
                print(f"✅ Deleted artifact vectors for document {document_id}")
                
        except Exception as e:
            print(f"❌ Error deleting vectors: {e}")
            success = False
        
        # Delete files if requested
        if cleanup_files:
            try:
                base_path = Path(self.config.storage_converted_documents_dir)
                # Extract document name from display_name (remove counter suffix if present)
                doc_name = document_record.display_name
                if " (" in doc_name and doc_name.endswith(")"):
                    doc_name = doc_name.rsplit(" (", 1)[0]
                
                doc_dir = base_path / doc_name
                if doc_dir.exists():
                    import shutil
                    shutil.rmtree(doc_dir)
                    print(f"✅ Deleted document files: {doc_dir}")
            except Exception as e:
                print(f"❌ Error deleting files: {e}")
                success = False
        
        # Delete from registry (do this last)
        if not self.registry.delete_document_record(document_id):
            success = False
        
        if success:
            print(f"✅ Successfully deleted document: {document_record.display_name}")
        else:
            print(f"⚠️ Document deletion completed with errors")
        
        return success

    def delete_document_by_name(self, display_name: str, cleanup_files: bool = True) -> bool:
        """Delete a document by its display name.
        
        Args:
            display_name: Display name of document to delete
            cleanup_files: Whether to also delete saved files
            
        Returns:
            True if deletion was successful, False otherwise
        """
        # Find document by display name
        documents = self.registry.list_documents()
        matching_docs = [doc for doc in documents if doc.display_name == display_name]
        
        if not matching_docs:
            print(f"❌ Document '{display_name}' not found")
            return False
        
        if len(matching_docs) > 1:
            print(f"❌ Multiple documents found with name '{display_name}'. Use document_id instead.")
            return False
        
        return self.delete_document(matching_docs[0].document_id, cleanup_files)