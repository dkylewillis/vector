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

    def convert(self, file_path: str) -> tuple[ConvertedDocument, bool]:
        """Convert a document file to ConvertedDocument.

        Args:
            file_path: Path to the file to process

        Returns:
            Tuple of (ConvertedDocument object, was_loaded_from_json boolean)
        """
        file_path = Path(file_path)
        was_loaded_from_json = False

        # Check if it's a JSON file
        if file_path.suffix.lower() == '.json':
            # Check if it's a valid DoclingDocument JSON
            if self.converter.is_valid_docling_json(file_path):
                print(f"Loading DoclingDocument from JSON: {file_path.name}")
                doc_data = self.converter.load_from_json(file_path)
                was_loaded_from_json = True
            else:
                # If not a valid DoclingDocument, try regular conversion
                print(f"Converting JSON file (not DoclingDocument): {file_path.name}")
                doc_data = self.converter.convert_document(file_path)
        else:
            # Regular file conversion
            doc_data = self.converter.convert_document(file_path)

        converted_doc = ConvertedDocument(doc=doc_data)
        print(f"✅ Converted {file_path.name}")

        return converted_doc, was_loaded_from_json

    def chunk(self, converted_doc: ConvertedDocument) -> List[Chunk]:
        """Extract chunks from a converted document.

        Args:
            converted_doc: ConvertedDocument object

        Returns:
            List of chunks
        """
        chunks = converted_doc.get_chunks()
        print(f"✅ Extracted {len(chunks)} chunks")
        return chunks

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
                "chunk": chunk.model_dump_json(),
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

    def save_artifacts(
        self,
        doc: DoclingDocument,
        artifacts: List[Artifact],
        document_name: str,
        base_path: str = None,
        create_thumbnails: bool = False,
        thumbnail_size: tuple = (200, 200)
    ) -> None:
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

        if base_path is None:
            base_path = self.config.storage_converted_documents_dir

        doc_dir = Path(base_path) / document_name
        artifacts_dir = doc_dir / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        saved_count = 0
        thumbnail_count = 0

        for artifact in artifacts:
            item = get_item_by_ref(doc, artifact.self_ref)
            image = item.get_image(doc=doc)
            if image is not None:
                artifact_id = artifact.self_ref.replace("/", "_").replace("#", "")
                if artifact_id.startswith("_"):
                    artifact_id = artifact_id[1:]
                filename = f"{artifact_id}.png"
                file_path = artifacts_dir / filename

                try:
                    image.save(str(file_path), "PNG")
                    artifact.image_file_path = str(file_path)
                    saved_count += 1

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

    def save_converted_document(
        self,
        converted_doc: ConvertedDocument,
        document_name: str,
        base_path: str = None
    ) -> None:
        """Save the entire converted document as JSON in a document-specific folder.

        Args:
            converted_doc: ConvertedDocument object to save
            document_name: Name of the document (used for folder structure)
            base_path: Base directory to save the document
        """
        if base_path is None:
            base_path = self.config.storage_converted_documents_dir

        doc_dir = Path(base_path) / document_name
        doc_dir.mkdir(parents=True, exist_ok=True)

        try:
            json_path = doc_dir / f"{document_name}_document.json"
            DocumentConverter.save_to_json(converted_doc.doc, json_path, ImageRefMode.EMBEDDED)
            print(f"✅ Saved converted document JSON to {doc_dir}")
        except Exception as e:
            print(f"❌ Failed to save converted document: {e}")

    def delete_document(self, document_id: str, cleanup_files: bool = True) -> bool:
        """Delete a document and all its associated data.

        Args:
            document_id: Document identifier to delete
            cleanup_files: Whether to also delete saved files (artifacts, converted docs)

        Returns:
            True if deletion was successful, False otherwise
        """
        document_record = self.registry.get_document(document_id)
        if not document_record:
            print(f"❌ Document {document_id} not found in registry")
            return False

        print(f"🗑️ Deleting document: {document_record.display_name}")

        success = True

        try:
            if document_record.chunk_collection:
                self.store.delete_document(
                    collection=document_record.chunk_collection,
                    document_id=document_id
                )
                print(f"✅ Deleted chunk vectors for document {document_id}")

        except Exception as e:
            print(f"❌ Error deleting vectors: {e}")
            success = False

        if cleanup_files:
            try:
                base_path = Path(self.config.storage_converted_documents_dir)
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
        documents = self.registry.list_documents()
        matching_docs = [doc for doc in documents if doc.display_name == display_name]

        if not matching_docs:
            print(f"❌ Document '{display_name}' not found")
            return False

        if len(matching_docs) > 1:
            print(f"❌ Multiple documents found with name '{display_name}'. Use document_id instead.")
            return False

        return self.delete_document(matching_docs[0].document_id, cleanup_files)

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

        document_name = self._get_unique_document_name(file_path.stem, base_path)

        chunk_collection = "chunks"

        converted_doc, was_loaded_from_json = self.convert(str(file_path))

        artifacts = converted_doc.get_artifacts()
        artifact_map = {artifact.self_ref: artifact for artifact in artifacts}
        chunks = converted_doc.get_chunks()

        for chunk in chunks:
            chunk.artifacts = [artifact_map[ref] for ref in chunk.doc_items if ref in artifact_map]

        if not was_loaded_from_json:
            self.save_converted_document(
                converted_doc,
                document_name,
                base_path=base_path,
            )
        else:
            print(f"ℹ️ Skipped saving document (already loaded from JSON)")

        if artifacts:
            self.save_artifacts(
                converted_doc.doc,
                artifacts,
                document_name,
                base_path=base_path,
                create_thumbnails=True,
                thumbnail_size=(150, 150),
            )

        document_record = self.registry.register_document(file_path, document_name)
        document_record.has_artifacts = len(artifacts) > 0
        document_record.artifact_count = len(artifacts)
        document_record.chunk_count = len(chunks)
        document_record.chunk_collection = chunk_collection
        document_record.tags = tags
        self.registry.update_document(document_record)

        chunk_embeddings = self.embed_chunks(chunks)
        
        # Ensure chunk collection exists
        existing = set(self.store.list_collections())
        if chunk_collection not in existing:
            self.store.create_collection(
                collection_name=chunk_collection,
                vector_size=len(chunk_embeddings[0])
            )

        self.store_chunks(chunks, chunk_embeddings, document_record, collection_name=chunk_collection)

        print(f"✅ Pipeline completed for {file_path.name}")
        return document_name
