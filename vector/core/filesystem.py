"""Simplified filesystem storage for Vector.

Example usage with CLI convert command:
    # Convert and save to both output files and filesystem storage
    vector convert document.pdf --save-to-storage --output ./output --format markdown

Example usage with FileSystemStorage directly:
    from vector.core.filesystem import FileSystemStorage
    from vector.core.converter import DocumentConverter
    from pathlib import Path
    
    # Initialize storage (uses './data' by default)
    storage = FileSystemStorage(config)
    
    # Convert a document
    converter = DocumentConverter()
    doc_result = converter.convert_to_document_result(
        file_path=Path("document.pdf"),
        source="manuals"
    )
    
    # Save to filesystem storage
    doc_id = await storage.save_document(doc_result)
    print(f"Document saved with ID: {doc_id}")
    
    # Load document back
    loaded_doc, metadata = await storage.load_document(doc_id)
    print(f"Loaded document: {metadata['original_filename']}")
"""

import asyncio
import json
import hashlib
import shutil
import io
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

from docling_core.types.doc.document import DoclingDocument
from .models import DocumentResult
from ..config import Config


class FileSystemStorage:
    """Simple filesystem storage for documents and artifacts."""
    
    def __init__(self, config: Config):
        self.config = config
        self.base_path = Path(config.artifacts_dir)
        
        # New directory structure
        self.converted_docs_path = self.base_path / "converted_documents"
        
        # Create directory structure
        self._create_directories()
    
    def _create_directories(self) -> None:
        """Create necessary directory structure."""
        dirs = [
            self.base_path,
            self.converted_docs_path
        ]
        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    # Document operations
    async def save_document(self, doc_result: DocumentResult) -> str:
        """Save document to filesystem."""
        doc_id = doc_result.file_hash
        doc_dir = self.converted_docs_path / doc_id
        doc_dir.mkdir(parents=True, exist_ok=True)
        
        # Save document JSON
        doc_path = doc_dir / "docling_document.json"
        doc_dict = doc_result.document.export_to_dict()
        
        await asyncio.get_event_loop().run_in_executor(
            None, self._write_json, doc_path, doc_dict
        )
        
        # Save metadata
        metadata_path = doc_dir / "metadata.json"
        metadata = {
            'doc_id': doc_id,
            'file_path': str(doc_result.file_path),
            'source_category': doc_result.source_category,
            'file_hash': doc_result.file_hash,
            'processed_at': datetime.now().isoformat(),
            'original_filename': doc_result.file_path.name
        }
        
        await asyncio.get_event_loop().run_in_executor(
            None, self._write_json, metadata_path, metadata
        )
        
        return doc_id
    
    async def save_markdown(self, doc_result: DocumentResult, markdown_content: str) -> str:
        """Save markdown content to the document directory."""
        doc_id = doc_result.file_hash
        doc_dir = self.converted_docs_path / doc_id
        doc_dir.mkdir(parents=True, exist_ok=True)
        
        # Save as original filename with .md extension
        base_name = doc_result.file_path.stem
        markdown_path = doc_dir / f"{base_name}.md"
        
        await asyncio.get_event_loop().run_in_executor(
            None, self._write_text, markdown_path, markdown_content
        )
        
        return str(markdown_path)
    
    async def load_document(self, doc_id: str) -> Optional[Tuple[DoclingDocument, Dict]]:
        """Load document from filesystem."""
        doc_dir = self.converted_docs_path / doc_id
        doc_path = doc_dir / "docling_document.json"
        metadata_path = doc_dir / "metadata.json"
        
        if not doc_path.exists() or not metadata_path.exists():
            return None
        
        try:
            doc_dict, metadata = await asyncio.gather(
                asyncio.get_event_loop().run_in_executor(None, self._read_json, doc_path),
                asyncio.get_event_loop().run_in_executor(None, self._read_json, metadata_path)
            )
            
            document = DoclingDocument.model_validate(doc_dict)
            return document, metadata
            
        except Exception as e:
            print(f"Error loading document {doc_id}: {e}")
            return None
    
    async def list_documents(self, filters: Optional[Dict] = None) -> List[Dict]:
        """List all documents."""
        documents = []
        
        if not self.converted_docs_path.exists():
            return documents
        
        for doc_dir in self.converted_docs_path.iterdir():
            if doc_dir.is_dir():
                metadata_path = doc_dir / "metadata.json"
                if metadata_path.exists():
                    try:
                        metadata = await asyncio.get_event_loop().run_in_executor(
                            None, self._read_json, metadata_path
                        )
                        
                        if not filters or self._matches_filters(metadata, filters):
                            documents.append(metadata)
                            
                    except Exception as e:
                        print(f"Error reading document metadata {metadata_path}: {e}")
        
        return documents
    
    async def delete_document(self, doc_id: str) -> bool:
        """Delete document from filesystem."""
        doc_dir = self.converted_docs_path / doc_id
        if doc_dir.exists():
            await asyncio.get_event_loop().run_in_executor(
                None, shutil.rmtree, doc_dir
            )
            return True
        return False
    
    # Artifact operations
    async def save_artifact(self, artifact_data: bytes, doc_id: str, 
                           ref_item: str, artifact_type: str, 
                           metadata: Optional[Dict] = None) -> str:
        """Save artifact to filesystem using Docling naming convention."""
        from .utils import extract_ref_id, image_to_hexhash
        from PIL import Image as PILImage
        
        # Get ref_id and calculate hex hash (Docling style)
        ref_id = extract_ref_id(ref_item)
        
        # Calculate hex hash using the same method as Docling
        try:
            image = PILImage.open(io.BytesIO(artifact_data))
            hexhash = image_to_hexhash(image)
        except Exception:
            # Fallback to content hash if not an image
            hasher = hashlib.sha256(usedforsecurity=False)
            hasher.update(artifact_data)
            hexhash = hasher.hexdigest()
        
        if not hexhash:
            hexhash = "unknown"
        
        # Use Docling naming convention: {type}_{id:06}_{hexhash}.png
        base_type = artifact_type.replace('_thumbnail', '')
        if 'thumbnail' in artifact_type:
            filename = f"{base_type}_{ref_id:06}_{hexhash}_thumb.png"
        else:
            filename = f"{base_type}_{ref_id:06}_{hexhash}.png"
        
        artifact_id = filename.replace('.png', '')
        
        # Save to document's images subdirectory
        doc_dir = self.converted_docs_path / doc_id
        images_dir = doc_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        doc_path = images_dir / filename
        
        if not doc_path.exists():
            await asyncio.get_event_loop().run_in_executor(
                None, self._write_bytes, doc_path, artifact_data
            )
        
        # Save metadata
        meta_data = {
            'artifact_id': artifact_id,
            'doc_id': doc_id,
            'ref_item': ref_item,
            'ref_id': ref_id,
            'artifact_type': artifact_type,
            'filename': filename,
            'hexhash': hexhash,
            'size_bytes': len(artifact_data),
            'created_at': datetime.now().isoformat(),
            **(metadata or {})
        }
        
        metadata_path = images_dir / f"{artifact_id}.json"
        await asyncio.get_event_loop().run_in_executor(
            None, self._write_json, metadata_path, meta_data
        )
        
        return artifact_id
    
    async def load_artifact(self, artifact_id: str) -> Optional[Tuple[bytes, Dict]]:
        """Load artifact from filesystem."""
        # Search through all document directories
        if self.converted_docs_path.exists():
            for doc_dir in self.converted_docs_path.iterdir():
                if doc_dir.is_dir():
                    images_dir = doc_dir / "images"
                    if images_dir.exists():
                        artifact_path = images_dir / f"{artifact_id}.png"
                        metadata_path = images_dir / f"{artifact_id}.json"
                        
                        if artifact_path.exists() and metadata_path.exists():
                            try:
                                metadata, data = await asyncio.gather(
                                    asyncio.get_event_loop().run_in_executor(None, self._read_json, metadata_path),
                                    asyncio.get_event_loop().run_in_executor(None, self._read_bytes, artifact_path)
                                )
                                return data, metadata
                            except Exception as e:
                                print(f"Error loading artifact {artifact_id} from {images_dir}: {e}")
        
        return None
    
    async def list_artifacts(self, doc_id: Optional[str] = None, 
                            artifact_type: Optional[str] = None) -> List[Dict]:
        """List artifacts with optional filters."""
        artifacts = []
        
        if doc_id:
            # Look in specific document's images directory
            doc_dir = self.converted_docs_path / doc_id
            images_dir = doc_dir / "images"
            if images_dir.exists():
                search_dirs = [images_dir]
            else:
                search_dirs = []
        else:
            # Look in all document images directories
            search_dirs = []
            if self.converted_docs_path.exists():
                for doc_dir in self.converted_docs_path.iterdir():
                    if doc_dir.is_dir():
                        images_dir = doc_dir / "images"
                        if images_dir.exists():
                            search_dirs.append(images_dir)
        
        for images_dir in search_dirs:
            for metadata_file in images_dir.glob("*.json"):
                try:
                    metadata = await asyncio.get_event_loop().run_in_executor(
                        None, self._read_json, metadata_file
                    )
                    
                    if artifact_type and metadata.get('artifact_type') != artifact_type:
                        continue
                    
                    artifacts.append(metadata)
                except Exception as e:
                    print(f"Error reading artifact metadata {metadata_file}: {e}")
        
        return artifacts
    
    async def delete_artifact(self, artifact_id: str) -> bool:
        """Delete artifact from filesystem."""
        # Search through all document images directories
        if self.converted_docs_path.exists():
            for doc_dir in self.converted_docs_path.iterdir():
                if doc_dir.is_dir():
                    images_dir = doc_dir / "images"
                    if images_dir.exists():
                        artifact_path = images_dir / f"{artifact_id}.png"
                        metadata_path = images_dir / f"{artifact_id}.json"
                        
                        if metadata_path.exists():
                            try:
                                if artifact_path.exists():
                                    await asyncio.get_event_loop().run_in_executor(None, artifact_path.unlink)
                                await asyncio.get_event_loop().run_in_executor(None, metadata_path.unlink)
                                return True
                            except Exception as e:
                                print(f"Error deleting artifact {artifact_id}: {e}")
                                return False
        return False
    
    # Utility operations
    async def cleanup(self) -> Dict[str, int]:
        """Cleanup orphaned files."""
        stats = {'documents_removed': 0, 'artifacts_removed': 0}
        
        # Get all document hashes
        doc_hashes = set()
        if self.converted_docs_path.exists():
            doc_hashes = {d.name for d in self.converted_docs_path.iterdir() if d.is_dir()}
        
        # Artifacts are now stored within document directories, so no separate cleanup needed
        # The cleanup would be handled when deleting entire document directories
        
        return stats
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        docs = await self.list_documents()
        artifacts = await self.list_artifacts()
        
        total_size = 0
        for path in self.base_path.rglob("*"):
            if path.is_file():
                total_size += path.stat().st_size
        
        return {
            'backend_type': 'filesystem',
            'total_documents': len(docs),
            'total_artifacts': len(artifacts),
            'storage_size_mb': round(total_size / (1024 * 1024), 2),
            'base_path': str(self.base_path)
        }
    
    # Helper methods
    def _write_json(self, path: Path, data: Dict) -> None:
        """Write JSON data to file."""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _read_json(self, path: Path) -> Dict:
        """Read JSON data from file."""
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _write_text(self, path: Path, text: str) -> None:
        """Write text to file."""
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text)
    
    def _write_bytes(self, path: Path, data: bytes) -> None:
        """Write bytes to file."""
        with open(path, 'wb') as f:
            f.write(data)
    
    def _read_bytes(self, path: Path) -> bytes:
        """Read bytes from file."""
        with open(path, 'rb') as f:
            return f.read()
    
    def _matches_filters(self, metadata: Dict, filters: Dict) -> bool:
        """Check if metadata matches filters."""
        for key, value in filters.items():
            if key not in metadata or metadata[key] != value:
                return False
        return True
