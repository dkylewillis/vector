# Vector Core

Document processing and indexing engine for Vector. Handles document conversion, chunking, embedding generation, and vector database storage.

## Overview

Vector Core is responsible for:
- **Document Processing**: Convert PDF, DOCX, and DOC files using Docling
- **Text Chunking**: Intelligent document segmentation for optimal retrieval
- **Embedding Generation**: Create vector embeddings using sentence transformers
- **Artifact Processing**: Extract and process images and tables from documents
- **Vector Storage**: Store embeddings in Qdrant vector database
- **Collection Management**: Organize documents into searchable collections

## CLI Usage

### Installation
```bash
# Install dependencies
pip install -e .

# Activate environment (Windows)
.venv/Scripts/python.exe
```

### Process Documents

```bash
# Process single document
python -m vector.core process "document.pdf" --collection "MyDocs" --source "ordinances"

# Process directory
python -m vector.core process "data/documents/" --collection "Legal" --source "ordinances"

# Force reprocessing
python -m vector.core process "document.pdf" --collection "MyDocs" --force

# Skip artifact processing (faster)
python -m vector.core process "document.pdf" --collection "MyDocs" --no-artifacts

# Use VLM pipeline (higher quality, slower)
python -m vector.core process "document.pdf" --collection "MyDocs" --pipeline vlm
```

### Collection Management

```bash
# List all collections
python -m vector.core collections

# List with details
python -m vector.core collections --verbose

# Create new collection
python -m vector.core create-collection "Legal Documents" --description "City ordinances and regulations"

# Rename collection
python -m vector.core rename-collection "Old Name" "New Name"

# Delete collection
python -m vector.core delete-collection "Unused Collection" --force
```

### Document Conversion

```bash
# Convert to markdown without indexing
python -m vector.core convert "document.pdf" --output-dir "./output" --format markdown

# Convert to JSON
python -m vector.core convert "document.pdf" --output-dir "./output" --format json

# Convert with storage
python -m vector.core convert "document.pdf" --output-dir "./output" --save-storage
```

## Pipeline Options

### PDF Pipeline (Default)
- **Faster processing**
- **Lower resource usage**
- **Good for text-heavy documents**
- **Limited visual element understanding**

### VLM Pipeline
- **Higher quality extraction**
- **Better visual element processing**
- **AI-powered layout understanding**
- **Slower processing**

## Collection Pairs

Collections are organized as pairs:
- **Chunks Collection**: Text segments with metadata
- **Artifacts Collection**: Images, tables, and visual elements

Each collection pair has:
- **Display Name**: Human-readable identifier
- **ULID**: Unique sortable identifier
- **Metadata**: Creation date, document count, description
- **Status**: Active/inactive state

## Source Categories

Documents can be categorized by source:
- `ordinances`: Municipal ordinances and regulations
- `manuals`: Technical manuals and guides
- `checklists`: Process checklists and forms
- `other`: Uncategorized documents

## Architecture

### Core Components

- **DocumentProcessor**: Main orchestration class
- **DocumentConverter**: Docling-based document conversion
- **DocumentChunker**: Intelligent text segmentation
- **Embedder**: Vector embedding generation
- **VectorDatabase**: Qdrant integration
- **CollectionManager**: Collection lifecycle management
- **ArtifactProcessor**: Image and table processing
- **FileSystemStorage**: Local document storage

### Processing Pipeline

1. **Conversion**: PDF/DOCX → Docling Document
2. **Chunking**: Document → Text segments
3. **Embedding**: Text segments → Vectors
4. **Storage**: Vectors → Qdrant database
5. **Metadata**: Document tracking and indexing

## Configuration

Core uses the main Vector configuration (`config.yaml`):

```yaml
# Database settings
qdrant:
  url: "your-qdrant-url"
  api_key: "your-api-key"

# Embedding model
embedder_model: "all-MiniLM-L6-v2"

# Storage paths
storage_path: "./data/storage"
```

## Error Handling

Core handles:
- **Processing Errors**: Document conversion failures
- **Database Errors**: Connection and storage issues
- **File Errors**: Missing or corrupted documents
- **Configuration Errors**: Invalid settings

## Performance

### Optimization Features
- **Batch Processing**: Multiple documents at once
- **Incremental Updates**: Skip already processed documents
- **Memory Management**: Efficient resource usage
- **Parallel Processing**: Multi-threaded operations where possible

### Processing Speed
- **PDF Pipeline**: ~30-60 seconds per document
- **VLM Pipeline**: ~2-5 minutes per document
- **Batch Processing**: 10-50x faster than individual processing

## Storage Structure

```
data/
├── converted_documents/           # Processed documents by hash
│   └── <file_hash>/
│       ├── document.json         # Docling document
│       ├── metadata.json         # File metadata
│       └── <filename>.md         # Markdown export
└── collection_metadata.json      # Collection definitions
```

## Supported Formats

- **Input**: PDF, DOCX, DOC
- **Output**: Markdown, JSON
- **Storage**: JSON, Binary vectors

## Dependencies

- **docling**: Document processing
- **sentence-transformers**: Embeddings
- **qdrant-client**: Vector database
- **pydantic**: Data validation
- **pathlib**: File operations
