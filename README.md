# Vector

A powerful document processing and AI-powered analysis tool with both command-line and web interfaces for regulatory and technical documents.

## Features

- **Document Processing**: Supports PDF, DOCX, TXT, and Markdown files with Docling converter
- **Directory Processing**: Process entire directories recursively with duplicate detection
- **Vector Search**: Fast semantic search using cloud Qdrant vector database
- **AI-Powered Q&A**: Get intelligent answers with document context using OpenAI GPT models
- **Web Interface**: Modern web UI with Gradio and comprehensive metadata filtering
- **Advanced Filtering**: Filter searches by filename, source, and document headings
- **Multiple Collections**: Organize documents into separate collections
- **Configurable Response Lengths**: Short, medium, or long AI responses
- **Cloud Storage**: Cloud-based vector database with local fallback support
- **Professional Focus**: Specialized for civil engineering and regulatory documents

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
- **Collection Management**: Switch between different document collections
- **Real-time Processing**: Upload and process documents with progress tracking

Launch with: `python vector_web.py` and navigate to http://127.0.0.1:7860

### Command Line Interface

**Main CLI:** Use `python -m vector`

**Collection Management:**
All commands support the `--collection` or `-c` flag to specify which collection to use.

```cmd
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

# Clear knowledge base
python -m vector clear
python -m regscout clear --collection temp  # Clear specific collection
```

**Note**: If you encounter permission errors when processing directories, process individual files instead or run as administrator.

## Commands

- **`--collection <name>`** - Global flag to specify collection (works with all commands)
- **`process <files/dirs>`** - Add documents to knowledge base (supports directories)
- **`search <query>`** - Search for relevant content using semantic similarity
- **`ask <question>`** - Get AI-powered answers with document context
  - `--length short|medium|long` - Response length (150/500/1500 tokens)
- **`info`** - Show knowledge base information and statistics
  - Use `--collection all` to see all collections
- **`metadata`** - Show document metadata and source information
- **`clear`** - Clear all chunks from knowledge base

## Collection Examples by Use Case

```cmd
# Separate by jurisdiction (process individual files)
python -m regscout process "coweta_docs\ordinance1.docx" -c coweta
python -m regscout process "fulton_docs\zoning.pdf" -c fulton

# Separate by topic
python -m regscout process "zoning_ordinances\*.docx" -c zoning
python -m regscout process "drainage_manuals\manual.pdf" -c stormwater

# Separate by project
python -m regscout process "project_alpha_docs\spec.pdf" -c project_alpha
python -m regscout process "project_beta_docs\*.docx" -c project_beta

# Query specific collections
python -m regscout search "setback requirements" -c zoning
python -m regscout ask "What are easement requirements?" -c utilities
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
regscout/
├── regscout_cli.py       # CLI entry point
├── regscout_web.py       # Web interface entry point
├── config.yaml           # Main configuration file
├── regscout/             # Main package
│   ├── __init__.py       # Package initialization
│   ├── config.py         # Configuration management
│   ├── exceptions.py     # Custom exceptions
│   ├── interfaces.py     # Protocol definitions
│   ├── cli/              # Command-line interface
│   │   ├── main.py       # CLI coordinator
│   │   └── parser.py     # Argument parsing
│   ├── web/              # Web interface
│   │   └── main.py       # Gradio web app
│   ├── core/             # Core functionality
│   │   ├── agent.py      # Research agent
│   │   ├── database.py   # Vector database
│   │   ├── embedder.py   # Text embeddings
│   │   └── processor.py  # Document processing
│   ├── ai/               # AI model implementations
│   │   └── openai.py     # OpenAI integration
│   └── utils/            # Utility functions
│       └── formatting.py # Output formatting
├── data/                 # Document storage
└── qdrant_db/           # Local vector database (fallback)
```

## Key Features Explained

### Document Processing
- Processes PDF, DOCX, TXT, and Markdown files using Docling converter
- Automatic hybrid chunking for better search results
- Preserves document structure and headings
- Duplicate detection prevents reprocessing

### Smart Search & Q&A
- Semantic search finds relevant content even with different wording
- Context-aware AI responses with source citations using OpenAI GPT models
- Configurable response lengths for different use cases (short/medium/long)
- Advanced metadata filtering in web interface
- Professional civil engineering focus
- Intelligent text chunking for optimal search results

### Web Interface Features
- Modern, responsive web UI built with Gradio
- Real-time document upload and processing
- Interactive filtering with multiple selection support
- Collection management with visual feedback
- Scrollable filter lists for large document sets
- Professional styling with Inter font

### Cloud Infrastructure
- Cloud Qdrant vector database for scalable storage
- Local fallback support for offline usage
- Environment-based configuration management
- Modern Python packaging with proper imports

The tool uses cloud vector database with local fallback and works with OpenAI for AI features.
