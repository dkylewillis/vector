# Vector

A powerful document processing and AI-powered analysis tool with both command-line and web interfaces for regulatory and technical documents.

## Features

- **Document Processing**: Supports PDF, DOCX, TXT, and Markdown files with Docling converter
- **Pipeline Options**: Choose between VLM Pipeline (better quality) or PDF Pipeline (faster processing)
- **Artifact Processing**: Optional indexing of images and tables with `--no-artifacts` for faster processing
- **Directory Processing**: Process entire directories recursively with duplicate detection
- **Vector Search**: Fast semantic search using cloud Qdrant vector database
- **AI-Powered Q&A**: Get intelligent answers with document context using OpenAI GPT models
- **Web Interface**: Modern web UI with Gradio and comprehensive metadata filtering
- **Advanced Filtering**: Filter searches by filename, source, and document headings
- **Multiple Collection Pairs**: Organize documents into collection pairs with linked chunks and artifacts collections
- **Collection Management**: Create, rename, and manage collection pairs with friendly display names
- **Configurable Response Lengths**: Short, medium, or long AI responses
- **Cloud Storage**: Cloud-based vector database with local fallback support
- **Professional Focus**: Specialized for municipal documents, ordinances, and regulations
- **Clean Architecture**: Separated concerns for search/AI, document processing, and database operations
- **Modular Pipeline**: Refactored processing pipeline for better maintainability and testing
- **Type-Safe Configuration**: PipelineType enum for consistent pipeline selection

## Quick Start

### Web Interface (Recommended)

1. **Install dependencies:**
   ```cmd
   pip install -r requirements.txt
   ```

2. **Set up OpenAI API key:**
   ```cmd
   set OPENAI_API_KEY=your_key_here
   ```

3. **Launch the web interface:**
   ```cmd
   python vector_web.py
   ```
   
   Navigate to: http://127.0.0.1:7860

### Command Line Interface

1. **Install dependencies:**
   ```cmd
   pip install -r requirements.txt
   ```

2. **Set up OpenAI API key:**
   ```cmd
   set OPENAI_API_KEY=your_key_here
   ```

3. **Run CLI commands:**
   ```cmd
   python -m vector --help
   ```

**Note**: If you encounter permission errors when processing directories, try processing individual files or run the command as administrator.

## Usage

### Web Interface

The web interface provides an intuitive way to interact with Vector:

- **Ask AI**: Get intelligent answers with customizable response lengths
- **Search Documents**: Perform semantic search with result ranking
- **Advanced Filters**: Filter by filename, source, and document headings
- **Upload Documents**: Process new documents directly through the web UI
- **Collection Management**: Create, rename, and delete collection pairs with display names
- **Collection Switching**: Switch between different document collection pairs seamlessly
- **Real-time Processing**: Upload and process documents with progress tracking

Launch with: `python vector_web.py` and navigate to http://127.0.0.1:7860

### Command Line Interface

**Main CLI:** Use `python -m vector`

**Collection Management:**
All commands support the `--collection` or `-c` flag to specify which collection pair to use. Collection pairs use ULID-based naming internally but can be referenced by friendly display names. Each collection pair contains both a chunks collection (for text) and an artifacts collection (for images/tables).

```cmd
# Create new collection pairs with display names
python -m vector create-collection "Legal Documents Q1 2024" --description "Q1 legal documents"
python -m vector create-collection "Technical Manuals" --description "Engineering manuals and specs"

# List all collection pairs
python -m vector collections

# Rename a collection pair's display name
python -m vector rename-collection "Legal Docs Q1" "Legal Documents Q1 2024"

# Delete a collection pair (requires --force for safety)
python -m vector delete-collection "Old Collection" --force

# Process individual documents (supports PDF, DOCX, TXT, MD)
python -m vector process "data\Coweta\ordinances\APPENDIX_A___ZONING_AND_DEVELOPMENT.docx"

# Process documents without indexing artifacts (faster processing)
python -m vector process "data\large_documents\*.pdf" --no-artifacts

# Use PDF Pipeline for faster processing (less accurate than VLM)
python -m vector process "data\technical_manuals\*.pdf" --use-pdf-pipeline

# Combine flags for fastest processing
python -m vector process "data\large_batch\*.pdf" --no-artifacts --use-pdf-pipeline

# Process to specific collection pairs
python -m vector process "data\zoning\zoning_ordinance.docx" --collection "Legal Documents"
python -m vector process "data\utilities\utility_standards.pdf" -c "Technical Manuals"

# Process multiple files (use wildcards or specify each file)
python -m vector process "data\Coweta\ordinances\*.docx" -c "Legal Documents"

# Search documents using semantic search
python -m vector search "setback requirements"
python -m vector search "setback requirements" --collection "Legal Documents"

# Search different content types
python -m vector search "flow chart" --type artifacts --collection "Technical Manuals"
python -m vector search "diagram" --type both --collection "Engineering Specs"

# Ask AI questions with different response lengths
python -m vector ask "What are the parking regulations?"
python -m vector ask "What is a setback?" --length short
python -m vector ask "Explain zoning regulations in detail" --length long
python -m vector ask "What are pipe sizing requirements?" --collection "Engineering Specs"

# Show knowledge base status
python -m vector info
python -m vector info --collection "Legal Documents"

# Show metadata for collections
python -m vector metadata
python -m vector metadata --collection "Technical Manuals"

# Delete specific documents based on metadata
python -m vector delete filename "old_document.pdf"
python -m vector delete source "outdated_manuals" --collection "Legal Documents"
python -m vector delete heading "Chapter 1" --collection "Technical Manuals"

# List available AI models
python -m vector models
python -m vector models --provider openai
python -m vector models -p openai

# Clear knowledge base
python -m vector clear
python -m vector clear --collection "Temporary Collection"
```

**Note**: If you encounter permission errors when processing directories, process individual files instead or run as administrator.

## Commands

### Collection Management Commands
- **`collections`** - List all collection pairs with metadata and display names
- **`create-collection <display_name>`** - Create new collection pair with friendly name
  - Automatically creates both chunks and artifacts collections linked together
  - `--description` - Optional description
- **`rename-collection <old_name> <new_name>`** - Change collection pair display name
- **`delete-collection <display_name>`** - Delete collection pair and all data
  - `--force` - Required flag to confirm deletion

### Document Processing & Search Commands
- **`--collection <name>`** - Global flag to specify collection pair (works with all commands)
- **`process <files/dirs>`** - Add documents to knowledge base (supports directories)
  - Automatically stores chunks in the chunks collection and artifacts in the artifacts collection
  - `--no-artifacts` - Skip indexing of images and tables for faster processing
  - `--use-pdf-pipeline` - Use PDF Pipeline instead of VLM Pipeline (faster but less accurate)
  - `--force` - Force reprocessing of existing documents
  - `--source <type>` - Specify document source type (ordinances, manuals, checklists, other)
- **`search <query>`** - Search for relevant content using semantic similarity
- **`ask <question>`** - Get AI-powered answers with document context
  - `--length short|medium|long` - Response length (150/500/1500 tokens)
- **`info`** - Show knowledge base information and statistics
- **`metadata`** - Show document metadata and source information
- **`delete <key> <value>`** - Delete documents matching metadata filter
  - `<key>` - Metadata field to filter by (filename, source, heading, etc.)
  - `<value>` - Value to match for deletion
- **`models`** - List available AI models for the specified provider
  - `--provider openai` - Specify AI provider (currently supports: openai)
- **`clear`** - Clear all chunks from knowledge base

## Collection Examples by Use Case

```cmd
# Create collection pairs for different purposes
python -m vector create-collection "Coweta Legal Documents" -d "Coweta ordinances and regulations"
python -m vector create-collection "Fulton Zoning" -d "Fulton County zoning documents"
python -m vector create-collection "Drainage Engineering" -d "Technical drainage manuals with diagrams"

# Process documents to specific collection pairs (use display names)
# Documents are automatically split: text goes to chunks, images/tables go to artifacts
python -m vector process "coweta_docs\ordinance1.docx" -c "Coweta Legal Documents"
python -m vector process "fulton_docs\zoning.pdf" -c "Fulton Zoning"

# Process large documents without artifacts for faster processing
python -m vector process "large_manuals\*.pdf" -c "Technical Manuals" --no-artifacts

# Use PDF Pipeline for batch processing (fastest option)
python -m vector process "batch_docs\*.pdf" -c "Batch Collection" --use-pdf-pipeline --no-artifacts

# Organize by topic - each pair contains both text and visual elements
python -m vector create-collection "Zoning Ordinances"
python -m vector create-collection "Stormwater Management"
python -m vector process "zoning_ordinances\*.docx" -c "Zoning Ordinances"
python -m vector process "drainage_manuals\manual.pdf" -c "Stormwater Management"

# Query specific collection pairs using display names
python -m vector search "setback requirements" -c "Zoning Ordinances"
python -m vector search "flow charts" --type artifacts -c "Stormwater Management"
python -m vector search "diagrams" --type both -c "Engineering Specifications"
python -m vector ask "What are easement requirements?" -c "Stormwater Management"

# Manage collection pairs
python -m vector collections  # List all collection pairs
python -m vector rename-collection "Legal Docs" "Legal Documents 2024"
python -m vector delete-collection "Temporary Collection" --force

# Remove outdated documents (affects both chunks and artifacts)
python -m vector delete source "old_manual_v1" -c "Stormwater Management"
python -m vector delete filename "deprecated_spec.pdf" -c "Zoning Ordinances"
```

## Configuration

Edit `config.yaml` to customize:
- Embedding models (sentence-transformers/all-MiniLM-L6-v2)
- AI model settings (OpenAI GPT-4o-mini)
- Vector database configuration (cloud Qdrant)
- Response length presets

## Requirements

- Python 3.8+
- OpenAI API key (for AI features)
- Dependencies listed in `requirements.txt`
- Cloud Qdrant database (with local fallback)

## Project Structure

```
vector/
├── vector_cli.py         # CLI entry point
├── vector_web.py         # Web interface entry point
├── config.yaml           # Main configuration file
├── collection_metadata.json # Collection pair metadata storage
├── vector/               # Main package
│   ├── __init__.py       # Package initialization
│   ├── config.py         # Configuration management
│   ├── exceptions.py     # Custom exceptions
│   ├── interfaces.py     # Protocol definitions
│   ├── cli/              # Command-line interface
│   │   ├── main.py       # CLI coordinator
│   │   └── parser.py     # Argument parsing
│   ├── web/              # Web interface
│   │   ├── main.py       # Gradio web app
│   │   └── styles.css    # Web styling
│   ├── core/             # Core functionality
│   │   ├── agent.py      # Research agent (search & AI)
│   │   ├── artifacts.py  # Artifact processing for images/tables
│   │   ├── chunking.py   # Text chunking utilities
│   │   ├── collection_manager.py # Collection naming & metadata management
│   │   ├── converter.py  # Document conversion with Docling
│   │   ├── database.py   # Vector database operations
│   │   ├── embedder.py   # Text embeddings
│   │   ├── filesystem.py # File system storage management
│   │   ├── processor.py  # Document processing engine
│   │   └── models.py     # Data models
│   ├── ai/               # AI model implementations
│   │   ├── factory.py    # AI model factory
│   │   ├── base.py       # Base AI model
│   │   └── openai.py     # OpenAI integration
│   └── utils/            # Utility functions
│       ├── formatting.py # Output formatting
│       ├── files.py      # File utilities
│       └── text.py       # Text processing
├── data/                 # Document storage
└── qdrant_db/           # Local vector database (fallback)
```

## Architecture

Vector follows a clean architecture with separated concerns:

### Core Components

1. **ResearchAgent** (`core/agent.py`)
   - Handles search and AI interactions only
   - Semantic search with vector similarity
   - AI-powered question answering with context
   - No document processing logic

2. **DocumentProcessor** (`core/processor.py`)
   - Manages document processing and indexing with modular pipeline architecture
   - **execute_processing_pipeline()**: Main orchestration method for the 3-step process
   - **convert_documents()**: Handles Docling conversion with VLM/PDF pipeline options
   - **chunk_and_embed()**: Text chunking and vector embedding generation
   - **store_chunks()**: Batch storage in vector database with metadata
   - Batch processing with progress tracking and error handling
   - File format support (PDF, DOCX, TXT, MD) with duplicate detection
   - Integrated artifact processing for comprehensive document analysis

3. **VectorDatabase** (`core/database.py`)
   - Direct database operations (CRUD)
   - Collection management with CollectionManager integration
   - Metadata indexing and filtering
   - ULID-based collection naming with display name resolution
   - No business logic

4. **CollectionManager** (`core/collection_manager.py`)
   - ULID-based collection pair naming convention
   - Display name to collection pair ID mapping
   - Metadata storage and management for linked chunks and artifacts collections
   - Unique display name enforcement
   - Document tracking within collection pairs

5. **ArtifactProcessor** (`core/artifacts.py`)
   - Specialized processing for images and tables extracted from documents
   - Metadata generation for visual elements
   - Integration with filesystem storage for artifact management

### Interface Layer

- **CLI** (`cli/main.py`) - Routes commands to appropriate services
- **Web** (`web/main.py`) - Web interface using Gradio, routes through services
- **AI Factory** (`ai/factory.py`) - Creates AI model instances

This architecture ensures clean separation of concerns and makes the codebase more maintainable and testable.

## Processing Pipeline Options

Vector offers two document processing pipelines to balance quality and speed:

### VLM Pipeline (Default - Recommended)
- **Best Quality**: Uses Vision Language Models for superior document understanding
- **Better Artifact Detection**: More accurate extraction of images, tables, and complex layouts
- **Slower Processing**: Takes more time due to advanced AI processing
- **Use Cases**: High-quality document analysis, complex layouts, important documents

### PDF Pipeline (Fast Alternative)
- **Faster Processing**: Traditional PDF processing for speed
- **Good Quality**: Reliable text extraction with basic layout understanding
- **Less Accurate Artifacts**: May miss some complex visual elements
- **Use Cases**: Batch processing, simple documents, quick indexing

### Modular Processing Pipeline

Vector's document processing follows a clean, modular 3-step pipeline:

1. **Convert**: Document conversion using Docling with configurable pipelines (VLM/PDF)
2. **Chunk & Embed**: Text chunking with hybrid chunking and vector embeddings
3. **Store**: Batch storage in vector database with metadata indexing

This modular approach ensures:
- **Easy Testing**: Each step can be tested independently
- **Better Error Handling**: Clear separation of concerns for debugging
- **Flexible Configuration**: Pipeline options can be mixed and matched
- **Maintainable Code**: Changes to one step don't affect others

### Performance Comparison

| Configuration | Pipeline | Artifacts | Speed | Quality | Best For |
|--------------|----------|-----------|-------|---------|----------|
| *(default)* | VLM | Yes | Slowest | Excellent | Important documents |
| `--no-artifacts` | VLM | No | Medium | Very Good | Text-focused analysis |
| `--use-pdf-pipeline` | PDF | Yes | Medium | Good | Balanced processing |
| `--no-artifacts --use-pdf-pipeline` | PDF | No | Fastest | Basic | Batch processing |

### Usage Examples

```cmd
# High quality processing (default)
python -m vector process important_docs/*.pdf -c "Legal Documents"

# Fast batch processing
python -m vector process large_batch/*.pdf -c "Archive" --use-pdf-pipeline --no-artifacts

# Text-only processing with VLM quality
python -m vector process reports/*.pdf -c "Reports" --no-artifacts

# Balanced speed/quality
python -m vector process manuals/*.pdf -c "Manuals" --use-pdf-pipeline
```

## Key Features Explained

### Document Processing
- Processes PDF, DOCX, TXT, and Markdown files using Docling converter
- **VLM Pipeline**: Uses Vision Language Models for superior document understanding (default)
- **PDF Pipeline**: Traditional processing for faster speed with `--use-pdf-pipeline` flag
- **Modular Pipeline Architecture**: Clean 3-step process (Convert → Chunk → Embed → Store)
- Automatic hybrid chunking for better search results
- Preserves document structure and headings
- Duplicate detection prevents reprocessing
- Optional artifact indexing (images/tables) with `--no-artifacts` flag for faster processing
- Configurable document conversion based on processing needs
- Integrated artifact processing for comprehensive document analysis
- Improved error handling and progress tracking

### Smart Search & Q&A
- Semantic search finds relevant content even with different wording using sentence transformers
- Context-aware AI responses with source citations using OpenAI GPT models
- Configurable response lengths for different use cases (short/medium/long)
- Advanced metadata filtering in web interface
- Professional municipal and regulatory document focus
- Intelligent text chunking for optimal search results
- Multi-type search supporting text chunks, artifacts, or both
- Separated search/AI logic from document processing for better performance

### Collection Management
- ULID-based collection pair naming for guaranteed uniqueness and sortability
- Friendly display names for easy human interaction
- Automatic metadata tracking (creation date, description, document count)
- Linked chunks and artifacts collections for comprehensive document storage
- JSON-based metadata storage with collection pair lifecycle management
- CLI commands for creating, listing, renaming, and deleting collection pairs

### Web Interface Features
- Modern, responsive web UI built with Gradio
- Real-time document upload and processing
- Interactive filtering with multiple selection support
- Collection management with visual feedback and full CRUD operations
- Collection pair creation, renaming, and deletion through intuitive interface
- Display name management for user-friendly collection pair identification
- Scrollable filter lists for large document sets
- Professional styling with Inter font
- Safety mechanisms for destructive operations (deletion confirmations)

### Cloud Infrastructure
- Cloud Qdrant vector database for scalable storage
- Local fallback support for offline usage
- Environment-based configuration management
- Modern Python packaging with proper imports
- Clean architecture with separated document processing, search, and database layers

The tool uses cloud vector database with local fallback and works with OpenAI for AI features. The modular architecture ensures maintainability and allows for easy testing and extension.

## Recent Improvements

### Refactored Processing Pipeline
- **Modular Design**: Clean separation of Convert → Chunk → Embed → Store steps
- **Better Testability**: Each pipeline step can be tested independently
- **Improved Error Handling**: Clear error boundaries between processing stages
- **Enhanced Maintainability**: Changes to one step don't affect others
- **Type Safety**: PipelineType enum for consistent configuration
- **Backward Compatibility**: All existing functionality preserved

### CLI Integration
- Updated to use new pipeline methods directly
- Better argument mapping with PipelineType enum
- Maintained all existing command-line functionality
- Improved consistency between CLI and processor APIs

This refactoring makes the codebase more robust, easier to understand, and better aligned with the core purpose of document conversion, embedding, and vector storage.
