# Vector Agent

AI-powered search and question-answering system for Vector. Provides semantic search and intelligent document analysis using Large Language Models.

## Overview

Vector Agent is responsible for:
- **Semantic Search**: Find relevant content using vector similarity
- **AI Question-Answering**: Get intelligent responses with document context
- **Multi-Modal Search**: Search text chunks and visual artifacts
- **Context Assembly**: Combine multiple sources for comprehensive answers
- **Metadata Filtering**: Refine searches by document properties

## CLI Usage

### Installation
```bash
# Install dependencies
pip install -e .

# Activate environment (Windows)
.venv/Scripts/python.exe
```

### Search Documents

```bash
# Basic search
python -m vector.agent search "setback requirements" --collection "Legal"

# Search specific type
python -m vector.agent search "building codes" --collection "Legal" --type chunks
python -m vector.agent search "diagrams" --collection "Technical" --type artifacts

# Control result count
python -m vector.agent search "zoning" --collection "Legal" --top-k 10

# Filter by metadata
python -m vector.agent search "permits" --collection "Legal" --filter source=ordinances
python -m vector.agent search "standards" --collection "Legal" --filter filename=chapter_14.docx

# Verbose output
python -m vector.agent search "requirements" --collection "Legal" --verbose
```

### Chat Sessions (Multi-turn Conversations)

Chat mode enables multi-turn conversations with context awareness:

```bash
# Start a new chat session
python -m vector.agent chat --start
# Returns: Started chat session: abc123-def456-...

# Send messages in the session
python -m vector.agent chat --session abc123-def456 --message "What are R-1 setback requirements?"
python -m vector.agent chat --session abc123-def456 --message "How about for corner lots?"
python -m vector.agent chat --session abc123-def456 --message "What about parking requirements?"

# Control search and response settings
python -m vector.agent chat --session abc123-def456 --message "Tell me more" --length long --type chunks

# Get session information
python -m vector.agent chat --session abc123-def456 --info

# End the session
python -m vector.agent chat --session abc123-def456 --end
```

#### Chat Features
- **Multi-turn context**: Agent remembers prior messages in the conversation
- **Automatic summarization**: Long conversations are automatically summarized to stay within token limits
- **Context-aware retrieval**: Search queries are enhanced based on conversation history
- **Session persistence**: Sessions persist for the lifetime of the agent process

### System Information

```bash
# Show AI model configuration
python -m vector.agent model-info --collection "Legal"

# Show collection information  
python -m vector.agent collection-info --collection "Legal"
```

## Search Types

### Chunks (Default)
- **Text segments** from documents
- **Contextual information** with headings
- **Detailed content** for comprehensive answers

### Artifacts
- **Images and diagrams** with captions
- **Tables and charts** with structured data
- **Visual elements** with descriptive metadata

### Both
- **Combined search** across text and visuals
- **Ranked results** by relevance score
- **Comprehensive coverage** of document content

## Response Lengths

### Short
- **Concise answers** (100-200 tokens)
- **Key points only**
- **Quick reference**

### Medium (Default)
- **Balanced responses** (300-500 tokens)
- **Detailed explanations**
- **Professional depth**

### Long
- **Comprehensive analysis** (800-1000 tokens)
- **Multiple perspectives**
- **Thorough coverage**

## Metadata Filtering

Filter searches by document properties:

```bash
# By source category
--filter source=ordinances
--filter source=manuals

# By filename
--filter filename=chapter_14.docx

# By document path
--filter file_path="data/legal/zoning.pdf"

# Multiple filters
--filter source=ordinances --filter filename=zoning.docx
```

## AI Models

### Search Model
- **Query preprocessing**: Expand search terms
- **Context optimization**: Generate search keywords
- **Semantic understanding**: Interpret user intent

### Answer Model
- **Response generation**: Create comprehensive answers
- **Context integration**: Combine multiple sources
- **Professional formatting**: Municipal document focus

### Supported Providers
- **OpenAI**: GPT-3.5, GPT-4 series
- **Anthropic**: Claude series
- **Local Models**: Via compatible APIs

## Architecture

### Core Components

- **ResearchAgent**: Main orchestration class
- **Retriever**: Pipeline-based retrieval orchestration
- **Pipeline**: Pluggable step execution framework
- **VectorDatabase**: Search and retrieval
- **Embedder**: Query vector generation
- **AIModelFactory**: LLM provider abstraction
- **CLIFormatter**: Result formatting

### Retrieval Pipeline

The agent uses a **pluggable pipeline architecture** for retrieval operations. See [PIPELINE_USAGE.md](PIPELINE_USAGE.md) for details.

**Default Pipeline:**
1. **QueryExpansionStep**: Expand query using AI and conversation context
2. **SearchStep**: Perform vector similarity search
3. **ScoreFilter** (optional): Filter by minimum score threshold
4. **DiagnosticsStep**: Add metadata about results

**Custom Pipeline Example:**
```python
from vector.agent import Pipeline, SearchStep, ScoreFilter, DiagnosticsStep

# Build custom pipeline
pipeline = Pipeline()
pipeline.add_step(SearchStep(search_service, top_k=20))
pipeline.add_step(ScoreFilter(min_score=0.5))
pipeline.add_step(MyCustomStep())  # Your custom step!
pipeline.add_step(DiagnosticsStep())

# Use custom pipeline
bundle, metrics = retriever.retrieve(
    session, message,
    custom_pipeline=pipeline
)
```

See [example_pipeline.py](example_pipeline.py) for working examples.

### Search Pipeline

1. **Query Processing**: User query → Search terms
2. **Vector Search**: Search terms → Document embeddings
3. **Result Ranking**: Embeddings → Scored results
4. **Context Assembly**: Results → Formatted context

### Q&A Pipeline

1. **Query Enhancement**: Question → Expanded search terms
2. **Context Retrieval**: Search terms → Relevant documents
3. **Response Generation**: Context + Question → AI answer
4. **Result Formatting**: AI response → User display

## Collection Resolution

Agent automatically resolves collection display names:

```bash
# Uses collection manager to find:
"Legal Documents" → c_01ABC123__chunks + c_01ABC123__artifacts
"Technical Manuals" → c_01DEF456__chunks + c_01DEF456__artifacts
```

## Configuration

Agent uses the main Vector configuration:

```yaml
# AI Provider settings
ai:
  provider: "openai"
  api_key: "your-api-key"
  search_model: "gpt-3.5-turbo"
  answer_model: "gpt-4"
  
# Response settings
response_lengths:
  short: 200
  medium: 500
  long: 1000

# Search settings
ai_search_max_tokens: 150

# Chat settings
chat:
  max_history_messages: 40          # Maximum messages to keep in session
  summary_trigger_messages: 14      # Trigger summarization after this many messages
  max_context_results: 40           # Maximum search results to use for context
  default_top_k: 12                 # Default number of search results per chat turn
```

## Chat Session Management

### Session Lifecycle

1. **Start Session**: Creates new session with unique ID
2. **Send Messages**: Add user messages and receive AI responses
3. **Context Maintenance**: Agent maintains message history
4. **Automatic Summarization**: Long conversations are compressed
5. **End Session**: Clean up when conversation is complete

### Memory Management

The agent automatically manages conversation memory:

- **Rolling Context**: Recent messages are kept in full
- **Summarization**: Older messages are compressed into summaries
- **Token Limits**: Ensures conversations stay within model limits
- **Context Pruning**: Removes oldest messages when needed

### Session Persistence

- Sessions exist in-memory during agent runtime
- Sessions are lost when agent process terminates
- For persistent sessions, consider:
  - Saving session state to database
  - Implementing session recovery on restart
  - Using external session store (Redis, etc.)

## Error Handling

Agent handles:
- **AI Service Errors**: API failures and rate limits
- **Search Errors**: Database connection issues
- **Collection Errors**: Missing or invalid collections
- **Query Errors**: Invalid search parameters

## Performance

### Search Speed
- **Vector Search**: < 100ms
- **Result Processing**: < 50ms
- **Total Response**: < 200ms

### AI Response Times
- **Search Enhancement**: 1-3 seconds
- **Answer Generation**: 3-10 seconds
- **Total Q&A**: 5-15 seconds

## Best Practices

### Effective Searching
- **Use specific terms** related to your domain
- **Include context** in your queries
- **Try different search types** for comprehensive results
- **Use filters** to narrow scope

### Question Asking
- **Be specific** about what you need
- **Ask focused questions** for better answers
- **Use appropriate length** for your use case
- **Reference specific documents** when needed

### Performance Optimization
- **Use shorter queries** for faster results
- **Filter by source** to reduce search space
- **Choose appropriate response length**
- **Batch similar questions** when possible

## Examples

### Municipal Use Cases

```bash
# Zoning Questions
python -m vector.agent search "R-1 setback requirements" --collection "Zoning"

# Building Codes
python -m vector.agent search "fire safety requirements" --collection "Codes" --type chunks

# Permit Processes
python -m vector.agent search "building permit application" --collection "Permits" --type both

# Technical Standards
python -m vector.agent search "drainage diagrams" --collection "Engineering" --type artifacts
```

### Advanced Filtering

```bash
# Recent ordinances only
python -m vector.agent search "parking standards" --collection "Legal" --filter source=ordinances

# Specific document analysis
python -m vector.agent search "Chapter 14 requirements" --collection "Codes" --filter filename=chapter_14.docx

# Multi-source comparison
python -m vector.agent search "zoning requirements" --collection "Legal" --type both
```

## Dependencies

- **sentence-transformers**: Query embeddings
- **qdrant-client**: Vector search
- **openai**: AI model access
- **anthropic**: Claude model access
- **pydantic**: Data validation
