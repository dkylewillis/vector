# RegScout

A command-line tool for processing regulatory documents and querying them with AI-powered search and analysis.

## Features

- **Document Processing**: Supports PDF, DOCX, TXT, and Markdown files
- **Directory Processing**: Process entire directories recursively with duplicate detection
- **Vector Search**: Fast semantic search using embeddings
- **AI-Powered Q&A**: Get intelligent answers with document context
- **Comprehensive Research**: Multi-step research with question generation and professional reports
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

```cmd
# Process documents (supports PDF, DOCX, TXT, MD)
python regscout.py process data\Coweta\ordinances\APPENDIX_A___ZONING_AND_DEVELOPMENT.docx

# Process entire directories (skip duplicates automatically)
python regscout.py process data\

# Force reprocess files (including duplicates)
python regscout.py process data\ --force

# Search documents using semantic search
python regscout.py search "setback requirements"

# Ask AI questions with different response lengths
python regscout.py ask "What are the parking regulations?"
python regscout.py ask --short "What is a setback?"
python regscout.py ask --long "Explain zoning regulations in detail"

# Conduct comprehensive research with automated question generation
python regscout.py research "stormwater management"
python regscout.py research "parking" --depth shallow
python regscout.py research "drainage" --save

# Add custom questions to research
python regscout.py research "setbacks" --questions "What about corner lots?" "How are setbacks measured?"

# Show knowledge base status
python regscout.py info

# Clear knowledge base
python regscout.py clear
```

## Commands

- **`process <files/dirs>`** - Add documents to knowledge base (supports directories)
  - `--force` - Reprocess files even if already in knowledge base
- **`search <query>`** - Search for relevant content using semantic similarity
- **`ask <question>`** - Get AI-powered answers with document context
  - `--short` - Brief answers (150 tokens)
  - `--medium` - Balanced answers (500 tokens) [default]
  - `--long` - Comprehensive answers (1500 tokens)
- **`research <topic>`** - Conduct multi-step research with automated question generation
  - `--depth shallow|medium|comprehensive` - Research depth
  - `--questions "Q1?" "Q2?"` - Add custom research questions
  - `--save` - Save detailed report to file
- **`info`** - Show knowledge base information and statistics
- **`clear`** - Clear all documents from knowledge base

## Configuration

Edit `config/settings.yaml` to customize:
- Embedding models
- AI model settings
- Vector database configuration
- File processing options
- Response length presets

Edit `config/research.yaml` to customize:
- Research question templates
- System prompts for different purposes
- Research depth configurations

## Requirements

- Python 3.8+
- OpenAI API key (for AI features only)
- Dependencies listed in `requirements.txt`

## Project Structure

```
regscout/
├── regscout.py          # Main CLI entry point
├── config/
│   ├── settings.yaml    # Main configuration file
│   └── research.yaml    # Research templates and prompts
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

### AI-Powered Research
- Generates targeted research questions automatically
- Conducts systematic research using your document corpus
- Compiles professional reports with structured findings
- Supports custom questions and configurable research depth

### Smart Search & Q&A
- Semantic search finds relevant content even with different wording
- Context-aware AI responses with source citations
- Configurable response lengths for different use cases
- Professional civil engineering focus

The tool uses local file storage and works offline (except for AI features).
