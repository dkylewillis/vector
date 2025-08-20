# Vector

A powerful document processing and AI-powered analysis tool with both command-line and web interfaces for regulatory and technical documents.

## Features

- **Document Processing**: Supports PDF, DOCX, TXT, and Markdown files with Docling converter
- **Directory Processing**: Process entire directories recursively with duplicate detection
- **Vector Search**: Fast semantic search using cloud Qdrant vector database
- **AI-Powered Q&A**: Get intelligent answers with document context using OpenAI GPT models
- **Web Interface**: Modern web UI with Gradio and comprehensive metadata filtering
- **Advanced Filtering**: Filter searches by filename, source, and document headings
- **Multiple Collections**: Organize documents into separate collections with ULID-based naming
- **Collection Management**: Create, rename, and manage collections with friendly display names
- **Configurable Response Lengths**: Short, medium, or long AI responses
- **Cloud Storage**: Cloud-based vector database with local fallback support
- **Professional Focus**: Specialized for municipal documents, ordinances, and regulations
- **Clean Architecture**: Separated concerns for search/AI, document processing, and database operations

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
- **Collection Management**: Create, rename, and delete collections with display names
- **Collection Switching**: Switch between different document collections seamlessly
- **Real-time Processing**: Upload and process documents with progress tracking

Launch with: `python vector_web.py` and navigate to http://127.0.0.1:7860

### Command Line Interface

**Main CLI:** Use `python -m vector`

**Collection Management:**
All commands support the `--collection` or `-c` flag to specify which collection to use. Collections use ULID-based naming internally but can be referenced by friendly display names.

```cmd
# Create new collections with display names
python -m vector create-collection "Legal Documents Q1 2024" chunks --description "Q1 legal documents"
python -m vector create-collection "Legal Docs Q1 Artifacts" artifacts --description "Tables and figures"

# List all collections
python -m vector collections

# Rename a collection's display name
python -m vector rename-collection "Legal Docs Q1" "Legal Documents Q1 2024"

# Delete a collection (requires --force for safety)
python -m vector delete-collection "Old Collection" --force

# Process individual documents (supports PDF, DOCX, TXT, MD)
python -m vector process "data\Coweta\ordinances\APPENDIX_A___ZONING_AND_DEVELOPMENT.docx"

# Process to specific collections
python -m vector process "data\zoning\zoning_ordinance.docx" --collection zoning
python -m vector process "data\utilities\utility_standards.pdf" -c utilities

# Process multiple files (use wildcards or specify each file)
python -m vector process "data\Coweta\ordinances\*.docx" -c coweta

# Search documents using semantic search
python -m vector search "setback requirements"
python -m vector search "setback requirements" --collection zoning

# Ask AI questions with different response lengths
python -m vector ask "What are the parking regulations?"
python -m vector ask "What is a setback?" --length short
python -m vector ask "Explain zoning regulations in detail" --length long
python -m vector ask "What are pipe sizing requirements?" --collection drainage

# Show knowledge base status
python -m vector info
python -m vector info --collection all    # Show info for all collections

# Show metadata for collections
python -m vector metadata
python -m vector metadata --collection coweta

# Delete specific documents based on metadata
python -m vector delete filename "old_document.pdf"
python -m vector delete source "outdated_manuals" --collection coweta
python -m vector delete heading "Chapter 1" --collection zoning

# List available AI models
python -m vector models
python -m vector models --provider openai
python -m vector models -p openai

# Clear knowledge base
python -m vector clear
python -m vector clear --collection temp  # Clear specific collection
```

**Note**: If you encounter permission errors when processing directories, process individual files instead or run as administrator.

## Commands

### Collection Management Commands
- **`collections`** - List all collections with metadata and display names
- **`create-collection <display_name> <modality>`** - Create new collection with friendly name
  - `<modality>` - Type of data: `chunks` (text) or `artifacts` (tables/figures)
  - `--description` - Optional description
- **`rename-collection <old_name> <new_name>`** - Change collection display name
- **`delete-collection <display_name>`** - Delete collection and all data
  - `--force` - Required flag to confirm deletion

### Document Processing & Search Commands
- **`--collection <name>`** - Global flag to specify collection (works with all commands)
- **`process <files/dirs>`** - Add documents to knowledge base (supports directories)
- **`search <query>`** - Search for relevant content using semantic similarity
- **`ask <question>`** - Get AI-powered answers with document context
  - `--length short|medium|long` - Response length (150/500/1500 tokens)
- **`info`** - Show knowledge base information and statistics
  - Use `--collection all` to see all collections
- **`metadata`** - Show document metadata and source information
- **`delete <key> <value>`** - Delete documents matching metadata filter
  - `<key>` - Metadata field to filter by (filename, source, heading, etc.)
  - `<value>` - Value to match for deletion
- **`models`** - List available AI models for the specified provider
  - `--provider openai` - Specify AI provider (currently supports: openai)
- **`clear`** - Clear all chunks from knowledge base

## Collection Examples by Use Case

```cmd
# Create collections for different purposes
python -m vector create-collection "Coweta Legal Documents" chunks -d "Coweta ordinances and regulations"
python -m vector create-collection "Fulton Zoning" chunks -d "Fulton County zoning documents"
python -m vector create-collection "Drainage Artifacts" artifacts -d "Tables and figures from drainage manuals"

# Process documents to specific collections (use display names)
python -m vector process "coweta_docs\ordinance1.docx" -c "Coweta Legal Documents"
python -m vector process "fulton_docs\zoning.pdf" -c "Fulton Zoning"

# Organize by topic
python -m vector create-collection "Zoning Ordinances" chunks
python -m vector create-collection "Stormwater Management" chunks
python -m vector process "zoning_ordinances\*.docx" -c "Zoning Ordinances"
python -m vector process "drainage_manuals\manual.pdf" -c "Stormwater Management"

# Query specific collections using display names
python -m vector search "setback requirements" -c "Zoning Ordinances"
python -m vector ask "What are easement requirements?" -c "Stormwater Management"

# Manage collections
python -m vector collections  # List all collections
python -m vector rename-collection "Legal Docs" "Legal Documents 2024"
python -m vector delete-collection "Temporary Collection" --force

# Remove outdated documents
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
│   │   ├── collection_manager.py # Collection naming & metadata management
│   │   ├── database.py   # Vector database operations
│   │   ├── embedder.py   # Text embeddings
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

2. **DocumentService** (`core/document_service.py`)
   - Manages document processing and indexing
   - Handles file processing pipelines
   - Batch processing with progress tracking
   - Uses DocumentProcessor for file conversion

3. **VectorDatabase** (`core/database.py`)
   - Direct database operations (CRUD)
   - Collection management with CollectionManager integration
   - Metadata indexing and filtering
   - ULID-based collection naming with display name resolution
   - No business logic

4. **CollectionManager** (`core/collection_manager.py`)
   - ULID-based collection naming convention
   - Display name to collection ID mapping
   - Metadata storage and management
   - Unique display name enforcement

5. **DocumentProcessor** (`core/processor.py`)
   - Low-level document conversion
   - Text chunking with Docling
   - File format support (PDF, DOCX, etc.)

### Interface Layer

- **CLI** (`cli/main.py`) - Routes commands to appropriate services
- **Web** (`web/main.py`) - Web interface using Gradio, routes through CLI
- **AI Factory** (`ai/factory.py`) - Creates AI model instances

This architecture ensures clean separation of concerns and makes the codebase more maintainable and testable.

## Key Features Explained

### Document Processing
- Processes PDF, DOCX, TXT, and Markdown files using Docling converter
- Automatic hybrid chunking for better search results
- Preserves document structure and headings
- Duplicate detection prevents reprocessing

### Smart Search & Q&A
- Semantic search finds relevant content even with different wording using sentence transformers
- Context-aware AI responses with source citations using OpenAI GPT models
- Configurable response lengths for different use cases (short/medium/long)
- Advanced metadata filtering in web interface
- Professional municipal and regulatory document focus
- Intelligent text chunking for optimal search results
- Separated search/AI logic from document processing for better performance

### Collection Management
- ULID-based collection naming for guaranteed uniqueness and sortability
- Friendly display names for easy human interaction
- Automatic metadata tracking (creation date, description, modality)
- Support for both `chunks` (text) and `artifacts` (tables/figures) modalities
- JSON-based metadata storage with collection lifecycle management
- CLI commands for creating, listing, renaming, and deleting collections

### Web Interface Features
- Modern, responsive web UI built with Gradio
- Real-time document upload and processing
- Interactive filtering with multiple selection support
- Collection management with visual feedback and full CRUD operations
- Collection creation, renaming, and deletion through intuitive interface
- Display name management for user-friendly collection identification
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
