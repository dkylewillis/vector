"""File system storage implementation."""

import json
import hashlib
import asyncio
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

from docling_core.types.doc.document import DoclingDocument
from .base import DocumentStorage, ArtifactStorage, StorageBackend
from ..models import DocumentResult
from ...config import Config


class FileSystemDocumentStorage(DocumentStorage):
    """File system implementation of document storage."""
    
    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.docs_path = base_path / "docling_documents"
        self.docs_path.mkdir(parents=True, exist_ok=True)
    
    async def save_document(self, doc_result: DocumentResult) -> str:
        """Save document to file system."""
        doc_id = doc_result.file_hash
        doc_dir = self.docs_path / "by_doc" / doc_id
        doc_dir.mkdir(parents=True, exist_ok=True)
        
        # Save document JSON
        doc_path = doc_dir / "document.json"
        doc_dict = doc_result.document.export_to_dict()
        
        # Run file I/O in thread pool to avoid blocking
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
    
    async def load_document(self, doc_id: str) -> Optional[Tuple[DoclingDocument, Dict]]:
        """Load document from file system."""
        doc_dir = self.docs_path / "by_doc" / doc_id
        doc_path = doc_dir / "document.json"
        metadata_path = doc_dir / "metadata.json"
        
        if not doc_path.exists() or not metadata_path.exists():
            return None
        
        try:
            # Load in thread pool
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
        by_doc_path = self.docs_path / "by_doc"
        
        if not by_doc_path.exists():
            return documents
        
        for doc_dir in by_doc_path.iterdir():
            if doc_dir.is_dir():
                metadata_path = doc_dir / "metadata.json"
                if metadata_path.exists():
                    try:
                        metadata = await asyncio.get_event_loop().run_in_executor(
                            None, self._read_json, metadata_path
                        )
                        
                        # Apply filters if provided
                        if filters:
                            if not self._matches_filters(metadata, filters):
                                continue
                        
                        documents.append(metadata)
                    except Exception as e:
                        print(f"Error reading metadata for {doc_dir.name}: {e}")
        
        return documents
    
    async def delete_document(self, doc_id: str) -> bool:
        """Delete document from file system."""
        doc_dir = self.docs_path / "by_doc" / doc_id
        if doc_dir.exists():
            await asyncio.get_event_loop().run_in_executor(
                None, shutil.rmtree, doc_dir
            )
            return True
        return False
    
    def _write_json(self, path: Path, data: Dict) -> None:
        """Write JSON data to file."""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _read_json(self, path: Path) -> Dict:
        """Read JSON data from file."""
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _matches_filters(self, metadata: Dict, filters: Dict) -> bool:
        """Check if metadata matches filters."""
        for key, value in filters.items():
            if key not in metadata or metadata[key] != value:
                return False
        return True


class FileSystemArtifactStorage(ArtifactStorage):
    """File system implementation of artifact storage."""
    
    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.images_by_doc = base_path / "images" / "by_doc"
        
        # Create directory structure
        self.images_by_doc.mkdir(parents=True, exist_ok=True)
    
    async def save_artifact(self, artifact_data: bytes, doc_id: str, 
                           ref_item: str, artifact_type: str, 
                           metadata: Optional[Dict] = None) -> str:
        """Save artifact to file system using Docling naming convention."""
        from ..utils import extract_ref_id, image_to_hexhash
        from PIL import Image as PILImage
        import io
        
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
        
        # Use full hash like Docling does
        if not hexhash:
            hexhash = "unknown"
        
        # Use Docling naming convention: {type}_{id:06}_{hexhash}.png
        base_type = artifact_type.replace('_thumbnail', '')  # Remove _thumbnail suffix for naming
        if 'thumbnail' in artifact_type:
            filename = f"{base_type}_{ref_id:06}_{hexhash}_thumb.png"
        else:
            filename = f"{base_type}_{ref_id:06}_{hexhash}.png"
        
        # Generate artifact ID using the filename (without extension)
        artifact_id = filename.replace('.png', '')
        
        # Save directly to document directory (no deduplication)
        doc_dir = self.images_by_doc / doc_id
        doc_dir.mkdir(parents=True, exist_ok=True)
        doc_path = doc_dir / filename
        
        # Save the artifact data directly
        if not doc_path.exists():
            await asyncio.get_event_loop().run_in_executor(
                None, self._write_bytes, doc_path, artifact_data
            )
        
        # Save metadata
        meta_data = {
            'artifact_id': artifact_id,
            'doc_id': doc_id,
            'doc_hash': doc_id,  # Add for compatibility
            'ref_item': ref_item,  # Store original ref_item
            'ref_id': ref_id,  # Store extracted ref_id
            'artifact_type': artifact_type,
            'filename': filename,
            'hexhash': hexhash,  # Store full hexhash
            'size_bytes': len(artifact_data),
            'created_at': datetime.now().isoformat(),
            **(metadata or {})
        }
        
        metadata_path = doc_dir / f"{artifact_id}.json"
        await asyncio.get_event_loop().run_in_executor(
            None, self._write_json, metadata_path, meta_data
        )
        
        return artifact_id
    
    async def load_artifact(self, artifact_id: str) -> Optional[Tuple[bytes, Dict]]:
        """Load artifact from file system."""
        # With new naming convention, we need to search through all doc directories
        # since artifact_id format is now: {type}_{ref_id:06}_{hexhash}
        
        for doc_dir in self.images_by_doc.iterdir():
            if doc_dir.is_dir():
                # Look for the artifact file directly in the doc directory
                artifact_path = doc_dir / f"{artifact_id}.png"
                metadata_path = doc_dir / f"{artifact_id}.json"
                
                if artifact_path.exists() and metadata_path.exists():
                    try:
                        # Load metadata
                        metadata = await asyncio.get_event_loop().run_in_executor(
                            None, self._read_json, metadata_path
                        )
                        
                        # Load artifact data directly from doc directory
                        data = await asyncio.get_event_loop().run_in_executor(
                            None, self._read_bytes, artifact_path
                        )
                        
                        return data, metadata
                    except Exception as e:
                        print(f"Error loading artifact {artifact_id} from {doc_dir}: {e}")
                        continue
        
        return None
    
    async def list_artifacts(self, doc_id: Optional[str] = None, 
                            artifact_type: Optional[str] = None) -> List[Dict]:
        """List artifacts with optional filters."""
        artifacts = []
        
        search_dirs = [self.images_by_doc / doc_id] if doc_id else list(self.images_by_doc.iterdir())
        
        for doc_dir in search_dirs:
            if not doc_dir.is_dir():
                continue
                
            for metadata_file in doc_dir.glob("*.json"):
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
        """Delete artifact from file system."""
        parts = artifact_id.split('_', 1)  # Split only on first underscore
        if len(parts) < 2:
            return False
        doc_id = parts[0]
        
        doc_dir = self.images_by_doc / doc_id
        metadata_path = doc_dir / f"{artifact_id}.json"
        
        success = True
        if metadata_path.exists():
            try:
                # Load metadata to get content hash and doc_path
                metadata = await asyncio.get_event_loop().run_in_executor(
                    None, self._read_json, metadata_path
                )
                
                # Find and remove doc_path file
                content_hash = metadata.get('content_hash')
                if content_hash:
                    from ..utils import extract_ref_id
                    ref_id = extract_ref_id(metadata.get('ref_item', ''))
                    artifact_type = metadata.get('artifact_type', 'artifact')
                    doc_path = doc_dir / f"{artifact_type}_{ref_id:06}_{content_hash}.png"
                    
                    if doc_path.exists():
                        await asyncio.get_event_loop().run_in_executor(None, doc_path.unlink)
                
                # Remove metadata file
                await asyncio.get_event_loop().run_in_executor(None, metadata_path.unlink)
                
            except Exception as e:
                print(f"Error deleting artifact {artifact_id}: {e}")
                success = False
        
        return success
    
    def _write_bytes(self, path: Path, data: bytes) -> None:
        """Write bytes to file."""
        with open(path, 'wb') as f:
            f.write(data)
    
    def _read_bytes(self, path: Path) -> bytes:
        """Read bytes from file."""
        with open(path, 'rb') as f:
            return f.read()
    
    def _write_json(self, path: Path, data: Dict) -> None:
        """Write JSON data to file."""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _read_json(self, path: Path) -> Dict:
        """Read JSON data from file."""
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)


class FileSystemBackend(StorageBackend):
    """File system storage backend."""
    
    def __init__(self, config: Config):
        self.config = config
        self.base_path = Path(config.artifacts_dir)
        self.document_storage = FileSystemDocumentStorage(self.base_path)
        self.artifact_storage = FileSystemArtifactStorage(self.base_path)
    
    def get_document_storage(self) -> DocumentStorage:
        return self.document_storage
    
    def get_artifact_storage(self) -> ArtifactStorage:
        return self.artifact_storage
    
    async def initialize(self) -> None:
        """Initialize file system storage."""
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Create directory structure as described in README
        dirs = [
            self.base_path / "docling_documents" / "by_doc",
            self.base_path / "docling_documents" / "metadata",
            self.base_path / "images" / "by_doc"
        ]
        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    async def cleanup(self) -> Dict[str, int]:
        """Cleanup orphaned files."""
        stats = {'documents_removed': 0, 'artifacts_removed': 0}
        
        # Get all document hashes
        doc_hashes = set()
        docs_by_doc = self.base_path / "docling_documents" / "by_doc"
        if docs_by_doc.exists():
            doc_hashes = {d.name for d in docs_by_doc.iterdir() if d.is_dir()}
        
        # Clean up orphaned artifacts
        images_by_doc = self.base_path / "images" / "by_doc"
        if images_by_doc.exists():
            for doc_dir in images_by_doc.iterdir():
                if doc_dir.is_dir() and doc_dir.name not in doc_hashes:
                    await asyncio.get_event_loop().run_in_executor(
                        None, shutil.rmtree, doc_dir
                    )
                    stats['artifacts_removed'] += 1
        
        return stats
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        docs = await self.document_storage.list_documents()
        artifacts = await self.artifact_storage.list_artifacts()
        
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
