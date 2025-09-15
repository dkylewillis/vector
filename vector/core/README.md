# Vector Core

Document processing and indexing engine for Vector. Handles document conversion, chunking, embedding generation, and vector database storage with flexible workflow support.

## Overview

Vector Core is responsible for:
- **Document Conversion**: Convert PDF, DOCX, and DOC files independently using Docling
- **Document Storage**: Persistent filesystem storage for converted documents
- **Text Chunking**: Intelligent document segmentation for optimal retrieval
- **Embedding Generation**: Create vector embeddings using sentence transformers
- **Artifact Processing**: Extract and process images and tables from documents
- **Vector Storage**: Store embeddings in Qdrant vector database
- **Collection Management**: Organize and manage documents across multiple collections
- **Flexible Workflows**: Convert once, use in multiple collections

## CLI Usage

### Installation
```bash
# Install dependencies
pip install -e .

# Activate environment (Windows)
.venv/Scripts/python.exe
```

## CLI Usage

### Installation
```bash
# Install dependencies
pip install -e .

# Activate environment (Windows)
.venv/Scripts/python.exe
```

### Document Conversion (Independent)

Convert documents without adding them to collections:

```bash
# Convert single document to storage
python -m vector.core convert "document.pdf"

# Convert multiple documents
python -m vector.core convert "doc1.pdf" "doc2.docx" --verbose

# Convert directory
python -m vector.core convert "data/documents/" --verbose

# Convert with output files
python -m vector.core convert "document.pdf" --output-dir "./output" --format markdown

# Convert to JSON format
python -m vector.core convert "document.pdf" --output-dir "./output" --format json

# Skip artifact processing (faster)
python -m vector.core convert "document.pdf" --no-artifacts

# Use VLM pipeline (higher quality, slower)
python -m vector.core convert "document.pdf" --pipeline vlm
```

### Document Management

List and manage converted documents:

```bash
# List all documents
python -m vector.core docs

# List standalone documents (not in collections)
python -m vector.core docs --standalone

# List with detailed information
python -m vector.core docs --verbose

# Add converted documents to a collection
python -m vector.core add-to-collection "document.pdf" --collection "MyDocs"

# Add multiple documents to collection
python -m vector.core add-to-collection "doc1.pdf" "doc2.docx" --collection "Legal"

# Remove documents from collection
python -m vector.core remove-from-collection "document.pdf" --collection "MyDocs"
```

### Process Documents (All-in-One)

For traditional workflow - convert and add to collection in one step:

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

# Load from storage and add to collection
python -m vector.core process "document.pdf" --collection "MyDocs" --from-storage
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

## Flexible Workflows

### Workflow 1: Convert First, Organize Later

```bash
# Step 1: Convert documents independently
python -m vector.core convert "policy.pdf" "manual.docx" "guide.pdf"

# Step 2: Check converted documents
python -m vector.core docs --standalone

# Step 3: Create collections
python -m vector.core create-collection "Policies"
python -m vector.core create-collection "Manuals"
python -m vector.core create-collection "All Documents"

# Step 4: Add documents to appropriate collections
python -m vector.core add-to-collection "policy.pdf" --collection "Policies"
python -m vector.core add-to-collection "manual.docx" --collection "Manuals"
python -m vector.core add-to-collection "policy.pdf" "manual.docx" "guide.pdf" --collection "All Documents"

# Step 5: Reorganize as needed
python -m vector.core remove-from-collection "policy.pdf" --collection "All Documents"
```

### Workflow 2: Traditional All-in-One

```bash
# Convert and add to collection in one step
python -m vector.core process "document.pdf" --collection "MyDocs" --source "ordinances"
```

### Workflow 3: Batch Operations

```bash
# Convert entire directory
python -m vector.core convert "./documents/" --verbose

# Check what was converted
python -m vector.core docs --standalone

# Add all to a collection
python -m vector.core add-to-collection *.pdf *.docx --collection "Archive"
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

- **DocumentProcessor**: Main orchestration class for full pipeline processing
- **DocumentConverter**: Docling-based document conversion (standalone)
- **DocumentManager**: Document-collection lifecycle management
- **DocumentChunker**: Intelligent text segmentation
- **Embedder**: Vector embedding generation
- **VectorDatabase**: Qdrant integration
- **CollectionManager**: Collection lifecycle management
- **ArtifactProcessor**: Image and table processing
- **FileSystemStorage**: Local document storage and retrieval

### Processing Pipelines

#### Independent Conversion Pipeline
1. **Conversion**: PDF/DOCX → Docling Document
2. **Storage**: Document → Filesystem storage
3. **Metadata**: Document tracking

#### Collection Integration Pipeline
1. **Loading**: Filesystem storage → Document
2. **Chunking**: Document → Text segments
3. **Embedding**: Text segments → Vectors
4. **Storage**: Vectors → Qdrant database
5. **Metadata**: Collection membership tracking

#### All-in-One Pipeline
1. **Conversion**: PDF/DOCX → Docling Document
2. **Chunking**: Document → Text segments
3. **Embedding**: Text segments → Vectors
4. **Storage**: Vectors → Qdrant database + Filesystem
5. **Metadata**: Document and collection tracking

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
- **Processing Errors**: Document conversion failures with detailed diagnostics
- **Database Errors**: Connection and storage issues with retry mechanisms
- **File Errors**: Missing or corrupted documents with graceful degradation
- **Configuration Errors**: Invalid settings with helpful error messages
- **Storage Errors**: Filesystem issues with automatic recovery
- **Metadata Errors**: Collection inconsistencies with repair utilities
- **Rollback Support**: Transaction-like operations for data integrity

## Performance

### Optimization Features
- **Batch Processing**: Multiple documents at once
- **Incremental Updates**: Skip already processed documents
- **Memory Management**: Efficient resource usage
- **Parallel Processing**: Multi-threaded operations where possible
- **Storage Reuse**: Convert once, use in multiple collections
- **Lazy Loading**: Load documents only when needed

### Processing Speed
- **PDF Pipeline**: ~30-60 seconds per document
- **VLM Pipeline**: ~2-5 minutes per document
- **Batch Processing**: 10-50x faster than individual processing
- **Collection Addition**: ~5-10 seconds per document (from storage)
- **Storage Operations**: Near-instantaneous for metadata

## Storage Structure

```
data/
├── converted_documents/           # Processed documents by hash
│   └── <file_hash>/
│       ├── docling_document.json # Docling document
│       ├── metadata.json         # File metadata
│       ├── <filename>.md         # Markdown export
│       └── images/               # Extracted artifacts
│           ├── image_*.png       # Document images
│           ├── table_*.png       # Table images
│           └── *.json           # Artifact metadata
└── collection_metadata.json      # Collection definitions and document tracking
```

## Document States

### Standalone Documents
- **Converted**: Document processed and stored in filesystem
- **Not Indexed**: Not added to any vector database collection
- **Available**: Ready to be added to collections
- **Reusable**: Can be added to multiple collections

### Collection Documents  
- **Indexed**: Added to vector database collection(s)
- **Searchable**: Available for vector similarity search
- **Tracked**: Monitored in collection metadata
- **Manageable**: Can be moved between collections

## Supported Formats

- **Input**: PDF, DOCX, DOC
- **Output**: Markdown, JSON
- **Storage**: JSON, Binary vectors

## Dependencies

- **docling**: Document processing and conversion
- **sentence-transformers**: Embeddings generation
- **qdrant-client**: Vector database operations
- **pydantic**: Data validation and models
- **pathlib**: File operations and path handling
- **ulid**: Unique identifier generation
- **asyncio**: Asynchronous operations for artifacts

## Key Benefits

### Flexibility
- **Separate Concerns**: Convert documents independently from indexing
- **Multiple Collections**: Add same document to different collections
- **Workflow Options**: Choose between all-in-one or step-by-step processing
- **Easy Reorganization**: Move documents between collections without reconversion

### Efficiency  
- **Avoid Redundancy**: Convert once, reuse multiple times
- **Faster Operations**: Collection management without document reprocessing
- **Storage Optimization**: Shared document storage across collections
- **Resource Management**: Process large document libraries incrementally

### Reliability
- **Error Recovery**: Failed operations don't affect converted documents
- **Data Integrity**: Transactional operations with rollback support
- **Consistency**: Metadata tracking prevents orphaned documents
- **Validation**: Document state verification and repair utilities
