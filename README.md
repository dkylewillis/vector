# RegScout

A command-line tool for processing regulatory documents and querying them with AI-powered search and analysis.

## Features

- **Document Processing**: Supports PDF, DOCX, TXT, and Markdown files
- **Vector Search**: Fast semantic search using embeddings
- **AI-Powered Q&A**: Get intelligent answers with document context
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

```cmd
# Process documents (supports PDF, DOCX, TXT, MD)
python regscout.py process data\Coweta\ordinances\APPENDIX_A___ZONING_AND_DEVELOPMENT.docx

# Search documents using semantic search
python regscout.py search "setback requirements"

# Ask AI questions with document context (requires API key)
python regscout.py ask "What are the parking regulations?"

# Show knowledge base status
python regscout.py info

# Clear knowledge base
python regscout.py clear
```

## Commands

- **`process <files>`** - Add documents to knowledge base
- **`search <query>`** - Search for relevant content using semantic similarity
- **`ask <question>`** - Get AI-powered answers with document context
- **`info`** - Show knowledge base information and statistics
- **`clear`** - Clear all documents from knowledge base

## Configuration

Edit `config/settings.yaml` to customize:
- Embedding models
- AI model settings
- Vector database configuration
- File processing options

## Requirements

- Python 3.8+
- OpenAI API key (for AI features only)
- Dependencies listed in `requirements.txt`

## Project Structure

```
regscout/
├── regscout.py          # Main CLI entry point
├── config/
│   └── settings.yaml    # Configuration file
├── src/
│   ├── agents/          # AI research agents
│   ├── ai_models/       # AI model implementations
│   └── data_pipeline/   # Document processing and embeddings
├── data/                # Document storage
└── qdrant_db/          # Local vector database
```

The tool uses local file storage and works offline (except for AI features).
