# RegScout

A command-line tool for processing regulatory documents and querying them with AI-powered search and analysis.

## Features

- **Document Processing**: Supports PDF, DOCX, TXT, and Markdown files
- **Directory Processing**: Process entire directories recursively with duplicate detection
- **Vector Search**: Fast semantic search using embeddings
- **AI-Powered Q&A**: Get intelligent answers with document context
- **Configurable Response Lengths**: Short, medium, or long AI responses
- **Local Storage**: Works offline with local file-based vector database
- **Professional Focus**: Specialized for civil engineering and regulatory documents

## Quick Start

1. **Install dependencies:**
   ```cmd
   pip install -r requirements.txt
   ```

2. **Set up OpenAI API key (for AI features):**
   Create a `.env` file in the project root:
   ```cmd
   echo OPENAI_API_KEY=your_key_here > .env
   ```

## Usage

**Main CLI:** Use `regscout.py`

**Collection Management:**
All commands support the `--collection` or `-c` flag to specify which collection to use.

```cmd
# Process documents (supports PDF, DOCX, TXT, MD)
python regscout.py process data\Coweta\ordinances\APPENDIX_A___ZONING_AND_DEVELOPMENT.docx

# Process to specific collections
python regscout.py --collection zoning process data\zoning\
python regscout.py -c utilities process data\utilities\

# Process entire directories (skip duplicates automatically)
python regscout.py process data\

# Force reprocess files (including duplicates)
python regscout.py process data\ --force

# Search documents using semantic search
python regscout.py search "setback requirements"
python regscout.py --collection zoning search "setback requirements"

# Search with filename filtering
python regscout.py search "parking" --filename "zoning_ordinance.pdf"
python regscout.py -c fayette search "utilities" --filename "Chapter_28___UTILITIES.docx"

# Ask AI questions with different response lengths
python regscout.py ask "What are the parking regulations?"
python regscout.py ask --short "What is a setback?"
python regscout.py ask --long "Explain zoning regulations in detail"
python regscout.py --collection drainage ask "What are pipe sizing requirements?"

# Ask with context filtering
python regscout.py ask "What are height limits?" --filename "zoning_ordinance.pdf"

# Show knowledge base status
python regscout.py info
python regscout.py --collection all info    # Show info for all collections

# Clear knowledge base
python regscout.py clear
python regscout.py --collection temp clear  # Clear specific collection
```

## Commands

- **`--collection <name>`** - Global flag to specify collection (works with all commands)
- **`process <files/dirs>`** - Add documents to knowledge base (supports directories)
  - `--force` - Reprocess files even if already in knowledge base
- **`search <query>`** - Search for relevant content using semantic similarity
  - `--filename <name>` - Filter results by specific filename
- **`ask <question>`** - Get AI-powered answers with document context
  - `--short` - Brief answers (150 tokens)
  - `--medium` - Balanced answers (500 tokens) [default]
  - `--long` - Comprehensive answers (1500 tokens)
  - `--filename <name>` - Filter context by specific filename
- **`info`** - Show knowledge base information and statistics
  - Use `--collection all` to see all collections
- **`clear`** - Clear all chunks from knowledge base

## Collection Examples by Use Case

```cmd
# Separate by jurisdiction
python regscout.py -c coweta process coweta_docs\
python regscout.py -c fulton process fulton_docs\

# Separate by topic
python regscout.py -c zoning process zoning_ordinances\
python regscout.py -c stormwater process drainage_manuals\

# Separate by project
python regscout.py -c project_alpha process project_alpha_docs\
python regscout.py -c project_beta process project_beta_docs\

# Query specific collections
python regscout.py -c zoning search "setback requirements"
python regscout.py -c utilities ask "What are easement requirements?"
```

## Configuration

Edit `config/settings.yaml` to customize:
- Embedding models
- AI model settings
- Vector database configuration
- File processing options
- Response length presets

## Requirements

- Python 3.8+
- OpenAI API key (for AI features only)
- Dependencies listed in `requirements.txt`

## Project Structure

```
regscout/
├── regscout.py          # Main CLI entry point
├── config/
│   └── settings.yaml    # Main configuration file
├── src/
│   ├── agents/          # AI research agents
│   ├── ai_models/       # AI model implementations
│   └── data_pipeline/   # Document processing and embeddings
├── data/                # Document storage
└── qdrant_db/          # Local vector database
```

## Key Features Explained

### Document Processing
- Processes PDF, DOCX, TXT, and Markdown files
- Automatic chunking for better search results
- Preserves document structure and headings
- Duplicate detection prevents reprocessing

### Smart Search & Q&A
- Semantic search finds relevant content even with different wording
- Context-aware AI responses with source citations
- Configurable response lengths for different use cases
- Professional civil engineering focus
- Intelligent text chunking for optimal search results

The tool uses local file storage and works offline (except for AI features).
