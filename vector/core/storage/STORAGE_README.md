# Vector Storage Architecture

## Overview

The Vector system uses an abstraction layer for document and artifact storage that allows seamless migration between storage backends (filesystem, PostgreSQL, etc.) without breaking existing code.

## Architecture

### Storage Abstraction Layer

The storage system is built on three main abstract interfaces:

- **DocumentStorage**: Handles document JSON storage and retrieval
- **ArtifactStorage**: Manages artifact (images, tables) binary data
- **StorageBackend**: Combines document and artifact storage with lifecycle management

### Current Implementation

Currently using **FileSystemBackend** with the following structure:

```
artifacts/
├── documents/          # Docling JSON documents
│   ├── by_hash/       # Organized by file hash
│   │   └── {file_hash}/
│   │       ├── document.json
│   │       └── metadata.json
│   └── metadata/      # Additional metadata files
├── images/            # Original artifact images
│   ├── by_doc/        # Organized by document
│   │   └── {doc_hash}/
│   │       └── {type}_{ref_id}_{content_hash}.png
│   └── by_hash/       # Deduplicated by content hash
│       └── {content_hash}.png
├── thumbnails/        # Generated thumbnails
│   └── {type}_{ref_id}_{content_hash}.png
└── cache/             # Temporary processing files
```

## Storage Interfaces

### DocumentStorage Interface

```python
class DocumentStorage(ABC):
    @abstractmethod
    async def save_document(self, doc_result: DocumentResult) -> str:
        """Save document and return document ID."""
        pass
    
    @abstractmethod
    async def load_document(self, doc_id: str) -> Optional[Tuple[DoclingDocument, Dict]]:
        """Load document by ID, return (document, metadata)."""
        pass
    
    @abstractmethod
    async def list_documents(self, filters: Optional[Dict] = None) -> List[Dict]:
        """List documents with optional filters."""
        pass
    
    @abstractmethod
    async def delete_document(self, doc_id: str) -> bool:
        """Delete document by ID."""
        pass
```

### ArtifactStorage Interface

```python
class ArtifactStorage(ABC):
    @abstractmethod
    async def save_artifact(self, artifact_data: bytes, doc_id: str, 
                           ref_item: str, artifact_type: str, 
                           metadata: Optional[Dict] = None) -> str:
        """Save artifact and return artifact ID."""
        pass
    
    @abstractmethod
    async def load_artifact(self, artifact_id: str) -> Optional[Tuple[bytes, Dict]]:
        """Load artifact by ID, return (data, metadata)."""
        pass
    
    @abstractmethod
    async def list_artifacts(self, doc_id: Optional[str] = None, 
                            artifact_type: Optional[str] = None) -> List[Dict]:
        """List artifacts with optional filters."""
        pass
    
    @abstractmethod
    async def delete_artifact(self, artifact_id: str) -> bool:
        """Delete artifact by ID."""
        pass
```

### StorageBackend Interface

```python
class StorageBackend(ABC):
    @abstractmethod
    def get_document_storage(self) -> DocumentStorage:
        """Get document storage instance."""
        pass
    
    @abstractmethod
    def get_artifact_storage(self) -> ArtifactStorage:
        """Get artifact storage instance."""
        pass
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize storage backend."""
        pass
    
    @abstractmethod
    async def cleanup(self) -> Dict[str, int]:
        """Cleanup orphaned data."""
        pass
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        pass
```

## File System Implementation

### FileSystemDocumentStorage

- Stores documents as JSON files organized by file hash
- Includes metadata with file paths, processing timestamps, and source information
- Uses async file I/O to prevent blocking operations

### FileSystemArtifactStorage

- Stores artifacts with content-based deduplication
- Creates both hash-based storage (for deduplication) and document-based organization (for browsing)
- Uses symlinks when possible, falls back to copying
- Supports rich metadata storage alongside binary data

### Key Features

1. **Deduplication**: Images stored by content hash to avoid duplicates
2. **Multiple Views**: Organized both by document and by hash for different access patterns
3. **Metadata Rich**: Comprehensive metadata storage with each document and artifact
4. **Async Support**: Non-blocking file operations using thread pools
5. **Error Resilient**: Graceful handling of missing files and corruption

## PostgreSQL Implementation (Future)

The system is designed to support PostgreSQL as a storage backend:

### Database Schema

```sql
-- Documents table
CREATE TABLE documents (
    doc_id VARCHAR(64) PRIMARY KEY,
    document_data JSONB NOT NULL,
    file_path TEXT NOT NULL,
    source_category VARCHAR(100),
    file_hash VARCHAR(64) NOT NULL,
    original_filename TEXT NOT NULL,
    processed_at TIMESTAMP NOT NULL
);

-- Artifacts table
CREATE TABLE artifacts (
    artifact_id VARCHAR(128) PRIMARY KEY,
    doc_id VARCHAR(64) REFERENCES documents(doc_id) ON DELETE CASCADE,
    ref_item TEXT NOT NULL,
    artifact_type VARCHAR(50) NOT NULL,
    artifact_data BYTEA NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    size_bytes INTEGER NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP NOT NULL
);
```

### Benefits of PostgreSQL Backend

- **ACID Transactions**: Guaranteed data consistency
- **Advanced Querying**: Complex filters and joins on metadata
- **Scalability**: Handle large datasets efficiently
- **Backup/Recovery**: Enterprise-grade data protection
- **Concurrent Access**: Multiple processes can safely access data

## Configuration

### Current Configuration (config.yaml)

```yaml
# Storage configuration
storage_backend: filesystem  # Options: 'filesystem', 'postgresql'
artifacts_dir: artifacts

# PostgreSQL configuration (when using postgresql backend)
postgres_connection_string: "postgresql://user:password@localhost/vectordb"
```

### Configuration Options

- `storage_backend`: Determines which storage implementation to use
- `artifacts_dir`: Base directory for filesystem storage
- `postgres_connection_string`: Connection string for PostgreSQL backend

## Migration Strategy

### Seamless Migration Path

1. **Phase 1**: Deploy with filesystem backend (current state)
2. **Phase 2**: Set up PostgreSQL database and tables
3. **Phase 3**: Change `storage_backend: postgresql` in configuration
4. **Phase 4**: Run optional data migration script

### Zero-Downtime Migration

The abstraction layer ensures that:
- No code changes required in ArtifactProcessor
- All existing functionality continues to work
- Migration can be tested thoroughly before switching

## Storage Factory

The `StorageFactory` handles backend creation and initialization:

```python
# Create storage backend based on configuration
backend = await StorageFactory.create_backend(config, backend_type='filesystem')

# Use in ArtifactProcessor
processor = ArtifactProcessor(
    embedder=embedder,
    vector_db=vector_db,
    storage_backend=backend
)
```

## Usage Examples

### Saving Documents

```python
# Save document with metadata
doc_id = await storage_backend.get_document_storage().save_document(doc_result)
print(f"Saved document: {doc_id}")
```

### Saving Artifacts

```python
# Save artifact with deduplication
artifact_id = await storage_backend.get_artifact_storage().save_artifact(
    image_data, doc_result.file_hash, item.self_ref, "image"
)
```

### Querying Documents

```python
# List documents with filters
documents = await storage_backend.get_document_storage().list_documents(
    filters={'source_category': 'ordinances'}
)
```

### Loading Artifacts

```python
# Load artifact by ID
artifact_data, metadata = await storage_backend.get_artifact_storage().load_artifact(artifact_id)
if artifact_data:
    image = PILImage.open(io.BytesIO(artifact_data))
```

## Maintenance Operations

### Storage Statistics

```python
# Get comprehensive storage statistics
stats = await storage_backend.get_stats()
print(f"Documents: {stats['total_documents']}")
print(f"Artifacts: {stats['total_artifacts']}")
print(f"Storage Size: {stats['storage_size_mb']} MB")
```

### Cleanup Operations

```python
# Remove orphaned files
cleanup_stats = await storage_backend.cleanup()
print(f"Removed {cleanup_stats['documents_removed']} orphaned documents")
```

## CLI Integration

The storage system integrates with CLI commands:

```bash
# Show storage statistics
python -m vector storage-stats

# Clean up orphaned files
python -m vector cleanup --dry-run  # Preview changes
python -m vector cleanup            # Execute cleanup
```

## Benefits

### Current Benefits

1. **Reliability**: File-based storage with content deduplication
2. **Performance**: Async operations prevent blocking
3. **Organization**: Multiple organizational schemes for efficient access
4. **Maintenance**: Built-in cleanup and statistics

### Future Benefits

1. **Scalability**: Easy migration to PostgreSQL for large datasets
2. **Concurrency**: Multiple processes can safely access shared data
3. **Backup**: Enterprise-grade backup and recovery options
4. **Querying**: Advanced SQL queries on document and artifact metadata

## Best Practices

### File System Storage

1. **Regular Cleanup**: Run cleanup operations to remove orphaned files
2. **Backup Strategy**: Include both document JSONs and artifact binaries
3. **Monitoring**: Track storage size and growth patterns
4. **Permissions**: Ensure appropriate file system permissions

### PostgreSQL Migration

1. **Testing**: Thoroughly test with a copy of production data
2. **Gradual Rollout**: Consider running both backends temporarily
3. **Monitoring**: Monitor database performance and connection pools
4. **Backup**: Ensure PostgreSQL backup strategy is in place

## Troubleshooting

### Common Issues

1. **File Permission Errors**: Ensure write access to artifacts directory
2. **Disk Space**: Monitor available disk space for filesystem backend
3. **Concurrent Access**: Be aware of file locking issues on Windows
4. **Symlink Support**: Verify symlink support on target filesystem

### Performance Considerations

1. **Async Operations**: All storage operations are async to prevent blocking
2. **Thread Pool**: File I/O uses thread pools to maintain responsiveness
3. **Batch Operations**: Consider batching multiple operations when possible
4. **Index Strategy**: Plan database indexes carefully for PostgreSQL backend

## Future Enhancements

1. **Additional Backends**: Support for cloud storage (S3, Azure Blob)
2. **Compression**: Optional compression for large artifacts
3. **Encryption**: At-rest encryption for sensitive documents
4. **Replication**: Multi-region replication for high availability
5. **Caching**: Intelligent caching layer for frequently accessed artifacts
